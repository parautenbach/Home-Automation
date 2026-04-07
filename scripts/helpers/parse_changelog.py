#!/bin/python

# find .storage -type f ! -name 'hacs.repositories' -exec sed -nr 's/[[:space:]]+"domain": "(.+)",/\1/p' {} + | sort | uniq > /tmp/integrations.tmp
# grep -ir "platform:" * |grep ".yaml" |grep -v community |grep -v custom_components |sed -r 's/.+platform: (.+)/\1/p' |sort |uniq >>/tmp/integrations.tmp
# sort /tmp/hintegrations.tmp |uniq > /tmp/integrations.txt

import subprocess
import re
from collections import defaultdict
from pathlib import Path
import argparse

def run(cmd):
    return subprocess.check_output(cmd).decode().splitlines()

def sync_repo():
    print("Fetching all branches and tags from upstream...")
    run(["git", "fetch", "--all", "--tags"])
    print("Repo sync complete.")

def update_branch():
    # ensure current branch matches upstream
    try:
        branch = run(["git", "rev-parse", "--abbrev-ref", "HEAD"])[0]
        print(f"Current branch: {branch}")

        # try upstream first (typical setup)
        print("Updating branch from upstream...")
        run(["git", "merge", "--ff-only", f"upstream/{branch}"])
        print("Branch updated from upstream.")

    except subprocess.CalledProcessError:
        print("Upstream not available or fast-forward failed, trying origin...")
        try:
            run(["git", "merge", "--ff-only", f"origin/{branch}"])
            print("Branch updated from origin.")
        except subprocess.CalledProcessError:
            print("WARNING: Could not fast-forward branch. You may be out of sync.")

def resolve_tag(tag):
    sha = run(["git", "rev-list", "-n", "1", tag])[0]
    msg = run(["git", "log", "-1", "--pretty=format:%s", sha])[0]
    return sha, msg

def get_latest_tags():
    """
    Returns:
      from_tag: previous minor base (e.g. 2026.3.0)
      to_tag:   latest stable release (e.g. 2026.4.1)
    """

    tags = run(["git", "tag", "--list", "--sort=v:refname"])

    # keep only stable tags like 2026.4.1
    stable_tags = [t for t in tags if re.match(r"\d+\.\d+\.\d+$", t)]

    if len(stable_tags) < 2:
        raise RuntimeError("Not enough stable release tags found.")

    latest_tag = stable_tags[-1]

    m = re.match(r"(\d+)\.(\d+)\.(\d+)", latest_tag)
    major, minor, _ = map(int, m.groups())

    prev_minor = minor - 1

    prev_base = f"{major}.{prev_minor}.0"

    if prev_base not in stable_tags:
        raise RuntimeError(f"Expected base tag {prev_base} not found.")

    print(f"Detected previous base tag: {prev_base}, latest tag: {latest_tag}")
    return prev_base, latest_tag

def is_non_release_pr(line):
    # must look like a non-release pr
    if not re.search(r"\(#\d+\)", line):
        return False

    # exclude releases like "2026.4.1 (#12345)"
    title = line.split("|", 1)[1]
    if re.match(r"\d+\.\d+\.\d+", title):
        return False

    return True

def get_pr_commits(old, new):
    # full hash plus message (pr title)
    lines = run([
        "git", "log",
        f"{old}..{new}",
        "--pretty=format:%H|%s"
    ])
    return [l for l in lines if is_non_release_pr(l)]

def get_files(commit):
    return run([
        "git", "diff-tree",
        "--no-commit-id",
        "--name-only",
        "-r",
        commit
    ])

def detect_integrations(files):
    integrations = set()
    for f in files:
        m = re.match(r"homeassistant/components/([^/]+)/", f)
        if m:
            integrations.add(m.group(1))
    return sorted(integrations) if integrations else ["core"]

def load_filter(enabled, path="integrations.txt"):
    f = Path(path)

    if not enabled:
        print("Filtering disabled.")
        return None

    if not f.is_file():
        raise RuntimeError("Filtering enabled but integrations.txt not found.")

    included = set(
        line.strip()
        for line in f.read_text().splitlines()
        if line.strip()
    )

    print(f"Filtering enabled. Integrations: {included}")
    return included

def main():
    parser = argparse.ArgumentParser(description="Generate HA changelog grouped by integration.")
    parser.add_argument("--from", dest="old", help="From tag/version (e.g., 2026.3.0)")
    parser.add_argument("--to", dest="new", help="To tag/version (e.g., 2026.4.1)")
    parser.add_argument(
        "--filter",
        action="store_true",
        help="Enable integration filtering using integrations.txt"
    )
    args = parser.parse_args()

    sync_repo()
    update_branch()
    filter_set = load_filter(args.filter)

    # determine range
    if args.old and args.new:
        print(f"Using user-supplied tags: {args.old} → {args.new}")
        old_tag, new_tag = args.old, args.new
    else:
        old_tag, new_tag = get_latest_tags()

    old_sha, old_msg = resolve_tag(old_tag)
    new_sha, new_msg = resolve_tag(new_tag)

    # metadata output
    print("\n# Home Assistant Changelog\n")
    print(f"From: {old_tag} ({old_sha})")
    print(f"To:   {new_tag} ({new_sha})")
    print(f"Integration filter: {'Enabled' if args.filter else 'Disabled'}")
    if args.filter:
        print(f"Filter file: integrations.txt")
    print("--------------------------------------------------\n")

    commits = get_pr_commits(old_sha, new_sha)
    print(f"Found {len(commits)} merged PR commits between the two releases.")

    grouped = defaultdict(list)

    for line in commits:
        commit, title = line.split("|", 1)
        files = get_files(commit)
        integrations = detect_integrations(files)

        integrations = [
            i for i in integrations
            if (filter_set is None or i in filter_set or i == "core")
        ]
        if not integrations:
            continue

        for integration in integrations:
            grouped[integration].append(title.strip())

    for integration in sorted(grouped.keys()):
        print(f"\n{integration}:\n")
        for title in sorted(grouped[integration]):
            print(f"- {title}")
    print()

if __name__ == "__main__":
    main()
