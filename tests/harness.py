"""Helpers for driving a Home Assistant instance in tests.

Pure functions only — anything that needs a live `hass` is a fixture in
conftest.py. Importable from any test module because pytest.ini puts `tests/`
on the path.
"""

import asyncio
import json
import os
from pathlib import Path

from homeassistant.util.yaml import load_yaml

# Set by tests/mutate.py to break one piece of config on purpose, so it can check
# that some test notices. Unset in a normal run.
MUTATION_ENV = "HA_MUTATE"

TESTS_ROOT = Path(__file__).resolve().parent
REPO_ROOT = TESTS_ROOT.parent
PACKAGES = REPO_ROOT / "home_assistant" / "packages"
FIXTURES = TESTS_ROOT / "fixtures"


class PlaceholderSecrets:
    """Every `!secret` reads as its own name, so no test depends on the real secrets.yaml."""

    def get(self, requester_path, secret):
        return f"<{secret}>"


def load_package(name):
    """Load a package file. `name` is the bare stem, e.g. "safety".

    The single place config enters the tests, so it is also where a mutation is
    applied — both `find_automation` and `domain_config` read through here.
    """
    config = load_yaml(str(PACKAGES / f"{name}.yaml"), PlaceholderSecrets())
    mutation = os.environ.get(MUTATION_ENV)
    if mutation:
        mutation = json.loads(mutation)
        if mutation["package"] == name:
            apply_mutation(config, mutation)
    return config


def apply_mutation(config, mutation):
    """Break one node of a loaded package, in place.

    `path` is a list of dict keys and list indices leading to the node. `drop`
    removes it; `set` replaces it with `value`.
    """
    node = config
    for key in mutation["path"][:-1]:
        node = node[key]
    last = mutation["path"][-1]
    if mutation["op"] == "drop":
        del node[last]
    elif mutation["op"] == "set":
        node[last] = mutation["value"]
    else:
        raise ValueError(f"unknown mutation op {mutation['op']!r}")


def domain_config(package, domain):
    """The raw config for one domain out of a package, as HA would see it."""
    return load_package(package).get(domain)


def find_automation(package, automation_id):
    """Pull a single automation out of a package by its stable id."""
    for automation in load_package(package).get("automation", []):
        if automation.get("id") == automation_id:
            return automation
    raise LookupError(f"no automation with id {automation_id!r} in {package}.yaml")


def called_entities(calls):
    """Every entity_id these calls were aimed at, flattened, in call order.

    A service call's entity_id may be a bare string or a list depending on how the
    caller wrote the target, so accept either and always hand back flat ids.
    """
    entities = []
    for call in calls:
        target = call.data.get("entity_id", [])
        entities.extend([target] if isinstance(target, str) else target)
    return entities


async def start_running():
    """Yield far enough for a run to begin and reach its first delay.

    Deliberately not async_block_till_done(): that waits for the run to *finish*,
    and one parked in a delay under a frozen clock never will. The clock has to be
    moved to release it — but only once it is actually waiting on the clock, or the
    time change fires before the delay is registered and nothing wakes up.
    """
    for _ in range(3):
        await asyncio.sleep(0)
