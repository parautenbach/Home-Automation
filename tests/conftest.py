"""Fixtures for the Home Assistant YAML config tests.

Runs a real HomeAssistant instance in-process with nothing loaded except the
integrations a test asks for, so a single automation can be set up in isolation
and driven by injecting states.

Fixtures only — pure helpers live in harness.py.
"""

import pytest
import yaml
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import async_fire_time_changed

from harness import FIXTURES, domain_config, find_automation


@pytest.fixture
def load_states(hass):
    """Seed the state machine from a fixture file.

    The fixture is the automation's contract: every entity it reads, with the
    pre-state it reads them in. Triggers are edge-triggered, so the pre-state
    matters as much as the value the test later injects.

    Pass `exclude` for entities a test sets up for real instead: stubbing one and
    loading the integration that owns it collides, and HA resolves the collision
    by suffixing the entity_id, which is a confusing way to find out.
    """

    async def _load(name, exclude=()):
        path = FIXTURES / f"{name}.yaml"
        for entity_id, spec in yaml.safe_load(path.read_text()).items():
            if entity_id in exclude:
                continue
            hass.states.async_set(
                entity_id, spec["state"], spec.get("attributes", {})
            )
        await hass.async_block_till_done()

    return _load


@pytest.fixture
def setup_automation(hass):
    """Set up one or more automations from a package, by id.

    Pass several when the behaviour under test is how they interact — the
    automation component can only be set up once, so a second call would be a
    silent no-op.
    """

    async def _setup(package, *automation_ids):
        configs = [find_automation(package, id_) for id_ in automation_ids]
        assert await async_setup_component(hass, "automation", {"automation": configs})
        await hass.async_block_till_done()

    return _setup


@pytest.fixture
def setup_domain(hass):
    """Set up a whole domain from a package, as configured in production.

    Used for the few dependencies whose behaviour over time is part of what is
    under test — timers, mainly.
    """

    async def _setup(package, domain):
        assert await async_setup_component(
            hass, domain, {domain: domain_config(package, domain)}
        )
        await hass.async_block_till_done()

    return _setup


@pytest.fixture
def settle(hass, freezer):
    """Move the clock and let everything it wakes finish.

    Requesting this gives you a frozen clock, so anything waiting on time waits
    for you rather than for real seconds.
    """

    async def _settle(ahead):
        freezer.tick(ahead)
        async_fire_time_changed(hass)
        await hass.async_block_till_done()

    return _settle
