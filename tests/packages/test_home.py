"""The bedlamp sleep timer in home_assistant/packages/home.yaml."""

from datetime import timedelta

import pytest
from homeassistant.util import dt as dt_util

SLEEP_TIMER = "5cbc04a8-9390-4cff-8209-91b553b693e1"
TIMER = "timer.bedroom_bedlamp_timer"


@pytest.fixture
async def asleep_and_still(hass, freezer, setup_domain, setup_automation):
    """Asleep under her night light, no motion for well over 10 min."""
    hass.states.async_set("input_boolean.baby_sleep_mode", "on")
    hass.states.async_set("binary_sensor.baby_monitor_motion_alarm", "off")
    hass.states.async_set("binary_sensor.nursery_lit", "off")
    hass.states.async_set("light.bedroom_bedlamp", "on", {"brightness": 3})
    hass.states.async_set("input_boolean.child_keep_night_light", "on")
    freezer.move_to(dt_util.utcnow() + timedelta(hours=1))
    await setup_domain("lights", "timer")
    await setup_automation("home", SLEEP_TIMER)
    yield
    # its now() trigger re-renders every minute, and a running timer would outlive the test too
    await hass.services.async_call(
        "automation", "turn_off", {"entity_id": "all"}, blocking=True
    )
    await hass.services.async_call("timer", "cancel", {"entity_id": TIMER}, blocking=True)


async def lamp_brightens(hass, phase):
    hass.states.async_set("sensor.child_sleep_phase", phase)
    hass.states.async_set("binary_sensor.nursery_lit", "on")
    await hass.async_block_till_done()


async def test_the_wake_up_light_is_left_on(hass, asleep_and_still):
    await lamp_brightens(hass, "wake_up")
    assert hass.states.get(TIMER).state == "idle"


async def test_a_lamp_lit_in_the_night_is_dimmed(hass, asleep_and_still):
    await lamp_brightens(hass, "sleep")
    assert hass.states.get(TIMER).state == "active"
    assert hass.states.get(TIMER).attributes["duration"] == "0:10:00"
