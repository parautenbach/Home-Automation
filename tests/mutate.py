#!/usr/bin/env python3
"""Mutation-test a package's automations and scripts against its test file.

Breaks one piece of config at a time, reruns the tests, and reports any mutation
that nothing caught. A survivor is either a path no test covers, or config that
makes no difference.

The off-the-shelf tools (mutmut, cosmic-ray) mutate Python source, which here is
only the test harness. The thing under test is YAML, so this walks the loaded
package instead.

Usage:
    mutate.py safety                      # the lot
    mutate.py safety --list               # just show what it would try
    mutate.py safety -k countdown         # only tests matching -k
    mutate.py safety --limit 20 --workers 8
"""

import argparse
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from harness import MUTATION_ENV, PACKAGES, REPO_ROOT, load_package  # noqa: E402

# Only these are behavioural; mutating a template sensor's Jinja needs its own operators.
ROOTS = ("automation", "script")

# Lists where dropping one element is a meaningful change.
STEP_KEYS = ("condition", "action", "sequence", "then", "else", "default")


def mutations(package):
    """Every mutation worth trying in this package, as path + op + label."""
    config = load_package(package)
    out = []
    for root in ROOTS:
        if root in config:
            _walk(config[root], [root], out, config)
    return out


def _walk(node, path, out, config):
    if isinstance(node, dict):
        for key, value in node.items():
            here = path + [key]
            if key in STEP_KEYS and isinstance(value, list):
                for i, step in enumerate(value):
                    out.append(_mutation(
                        here + [i], "drop", None,
                        f"drop {key}[{i}] ({_describe(step)})", config,
                    ))
            elif key == "condition" and value in ("and", "or"):
                other = "or" if value == "and" else "and"
                out.append(_mutation(here, "set", other, f"{value} -> {other}", config))
            elif key == "state" and value in ("on", "off"):
                other = "off" if value == "on" else "on"
                out.append(_mutation(here, "set", other, f"state {value} -> {other}", config))
            elif key in ("above", "below") and isinstance(value, (int, float)):
                out.append(_mutation(
                    here, "set", value + 1, f"{key} {value} -> {value + 1}", config,
                ))
            elif key == "for":
                out.append(_mutation(here, "drop", None, "drop for:", config))
            _walk(value, here, out, config)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            _walk(item, path + [i], out, config)


def _describe(step):
    """A short label for a step, for the report."""
    if isinstance(step, dict):
        for key in ("service", "action", "alias", "condition", "stop"):
            if isinstance(step.get(key), str):
                return f"{key}: {step[key]}"
        # blocks whose value is a dict or list, so there is no string to quote
        for key in ("repeat", "variables", "if", "choose", "parallel", "delay",
                    "wait_template", "wait_for_trigger", "event"):
            if key in step:
                return f"{key}:"
        return "+".join(list(step)[:3])
    return str(step)[:40]


def _owner(path, config):
    """Which automation or script this path sits in, for the report."""
    if path[0] == "automation" and len(path) > 1:
        entry = config["automation"][path[1]]
        return entry.get("alias", entry.get("id", "?"))
    if path[0] == "script" and len(path) > 1:
        return f"script.{path[1]}"
    return path[0]


def _mutation(path, op, value, label, config):
    return {"path": path, "op": op, "value": value,
            "label": label, "owner": _owner(path, config)}


def run(package, mutation, tests, keyword, timeout):
    """Run the tests with this mutation applied.

    Returns pytest's own verdict: 0 every test still passed (the mutation
    survived), 1 something failed (killed), anything else means pytest could not
    run — a usage error, an internal error, or nothing collected.
    """
    env = dict(os.environ, **{MUTATION_ENV: json.dumps({**mutation, "package": package})})
    command = [sys.executable, "-m", "pytest", "-x", "-q", "--no-header",
               f"--timeout={timeout}", str(tests)]
    if keyword:
        command += ["-k", keyword]
    result = subprocess.run(
        command, cwd=REPO_ROOT, env=env, capture_output=True, text=True
    )
    return result.returncode, result


# HA skips a config it cannot validate and logs it, rather than failing setup, so a
# schema-invalid mutation looks like a test failure. That is a false kill: it proves the
# config broke, not that a test covers the node.
INVALID_CONFIG = (
    # what HA logs for an automation or script it refuses to load
    "could not be validated and has been disabled",
    "Invalid config for",
    "Unable to set up",
    "Setup failed for",
)


def broke_the_config(result):
    output = result.stdout + result.stderr
    return any(marker in output for marker in INVALID_CONFIG)


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("package", help="package stem, e.g. safety")
    parser.add_argument("--tests", type=Path, help="default: tests/packages/test_<package>.py")
    parser.add_argument("-k", dest="keyword", help="pass through to pytest")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--list", action="store_true", help="show mutations, run nothing")
    args = parser.parse_args()

    if not (PACKAGES / f"{args.package}.yaml").exists():
        sys.exit(f"no such package: {args.package}")
    tests = args.tests or Path("tests/packages") / f"test_{args.package}.py"
    if not (REPO_ROOT / tests).exists():
        sys.exit(f"no test file: {tests}")

    found = mutations(args.package)
    if args.limit:
        found = found[: args.limit]

    if args.list:
        for mutation in found:
            print(f"{mutation['owner']}: {mutation['label']}")
        print(f"\n{len(found)} mutations", file=sys.stderr)
        return

    print(f"{len(found)} mutations against {tests}", file=sys.stderr)
    survivors = []
    errors = []
    with ThreadPoolExecutor(args.workers) as pool:
        futures = {
            pool.submit(run, args.package, mutation, tests, args.keyword, args.timeout): mutation
            for mutation in found
        }
        for i, future in enumerate(as_completed(futures), 1):
            mutation = futures[future]
            code, result = future.result()
            if code == 0:
                survivors.append(mutation)
            elif code != 1 or broke_the_config(result):
                # either pytest could not run, or the mutation made the config invalid
                # and HA dropped it — nothing was proved about test coverage
                errors.append((mutation, result))
            print(f"\r{i}/{len(found)}  {len(survivors)} survived", end="", file=sys.stderr)

    print(file=sys.stderr)
    if survivors:
        print(f"\n{len(survivors)} SURVIVED — nothing failed when this was broken:\n")
        for owner in dict.fromkeys(m["owner"] for m in survivors):
            print(f"{owner}")
            for mutation in (m for m in survivors if m["owner"] == owner):
                path = ".".join(str(part) for part in mutation["path"])
                print(f"    {mutation['label']:<52} {path}")
            print()
    else:
        print("\nno survivors")

    if errors:
        print(f"\n{len(errors)} NOT EVALUATED — the mutation broke the config, so the "
              f"test failure proves nothing:\n")
        for mutation, _ in errors:
            print(f"    {mutation['owner']}: {mutation['label']}")

    evaluated = len(found) - len(errors)
    killed = evaluated - len(survivors)
    print(f"\nkilled {killed}/{evaluated} evaluated ({len(errors)} skipped as invalid)")
    return 1 if survivors else 0


if __name__ == "__main__":
    sys.exit(main())
