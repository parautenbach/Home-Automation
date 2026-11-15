"""Stalled arms and open-door bypasses in home_assistant/packages/olarm.yaml."""

from datetime import timedelta

import pytest
from pytest_homeassistant.common import async_fire_time_changed, async_mock_service

from harness import called_entities, start_running

STALL = "42ac5942-bcd3-4aec-9d64-9e76341435de"
HANDLER = "c7a55b28-a909-4cf0-8f91-23f1d8a0e45a"
LEFT = "e8a63da5-4d84-40ab-9c05-dca93ba4900d"


@pytest.fixture
async def arming(hass, load_states, custom_templates):
    await load_states("olarm/arming")
    return {
        "notify": async_mock_service(hass, "notify", "mobile_app_ceres"),
        "press": async_mock_service(hass, "button", "press"),
        "arm_away": async_mock_service(hass, "alarm_control_panel", "alarm_arm_away"),
    }


def alerts(calls):
    """The notifications that say something, not the clear_notification calls."""
    return [c.data for c in calls if c.data["message"] != "clear_notification"]


def action_ids(alert):
    return [a["action"] for a in alert["data"]["actions"]]


# none of these block till done: a run parked on a delay or a wait under the frozen
# clock never finishes, so they only yield far enough for it to get there


async def set_state(hass, entity_id, state):
    hass.states.async_set(entity_id, state, hass.states.get(entity_id).attributes)
    await start_running()


async def tap(hass, action, panel="alarm_control_panel.home"):
    hass.bus.async_fire(
        "mobile_app_notification_action",
        {"action": action, "action_data": {"entity_ids": [panel]}},
    )
    await start_running()


@pytest.fixture
def advance(hass, freezer):
    async def _advance(ahead):
        freezer.tick(ahead)
        async_fire_time_changed(hass)
        await start_running()

    return _advance


@pytest.fixture
async def stall(arming, setup_automation):
    await setup_automation("olarm", STALL)
    return arming


async def request_arm(hass, mode):
    """What the home template panel does before it sends the arm."""
    hass.bus.async_fire("alarm_arm_requested", {"mode": mode})
    hass.states.async_set("alarm_control_panel.home", "pending")
    await start_running()


async def test_a_stalled_full_arm_offers_to_bypass_the_open_door(hass, stall, advance):
    await set_state(hass, "binary_sensor.home_zone_001_front_door", "on")
    await request_arm(hass, "away")
    await advance(timedelta(seconds=30))
    await advance(timedelta(seconds=2))
    [alert] = alerts(stall["notify"])
    assert alert["message"].endswith("still open:\n  - Front Door")
    assert action_ids(alert) == ["ARM_ALARM_BYPASS_DOORS", "ARM_ALARM"]


async def test_a_stalled_stay_arm_asks_to_close_the_door(hass, stall, advance):
    await set_state(hass, "binary_sensor.home_zone_001_front_door", "on")
    await request_arm(hass, "home")
    await advance(timedelta(seconds=30))
    await advance(timedelta(seconds=2))
    [alert] = alerts(stall["notify"])
    assert alert["message"].endswith("Close them and try again.")
    assert action_ids(alert) == ["ARM_STAY_ALARM"]


async def test_a_stall_with_no_door_open_offers_a_retry(hass, stall, advance):
    await request_arm(hass, "away")
    await advance(timedelta(seconds=30))
    await advance(timedelta(seconds=2))
    [alert] = alerts(stall["notify"])
    assert "No door is open" in alert["message"]
    assert action_ids(alert) == ["ARM_ALARM"]


async def test_an_arm_confirmed_in_time_is_not_a_stall(hass, stall, advance):
    await request_arm(hass, "away")
    await advance(timedelta(seconds=5))
    await set_state(hass, "alarm_control_panel.home", "armed_away")
    await advance(timedelta(seconds=30))
    await advance(timedelta(seconds=2))
    assert alerts(stall["notify"]) == []


async def test_arming_in_the_other_mode_is_still_a_stall(hass, stall, advance):
    await request_arm(hass, "home")
    await set_state(hass, "alarm_control_panel.home", "armed_away")
    await advance(timedelta(seconds=30))
    await advance(timedelta(seconds=2))
    assert len(alerts(stall["notify"])) == 1


@pytest.fixture
async def handler(hass, arming, setup_automation):
    # arming turns the yard lights off
    await setup_automation("olarm", HANDLER)
    return arming


@pytest.fixture
async def doors_open(hass):
    await set_state(hass, "binary_sensor.home_zone_001_front_door", "on")
    await set_state(hass, "binary_sensor.home_zone_007_kitchen_door", "on")


async def test_bypass_and_arm_bypasses_only_the_open_doors(hass, handler, advance):
    await set_state(hass, "binary_sensor.home_zone_001_front_door", "on")
    await set_state(hass, "binary_sensor.home_zone_004_living_area", "on")
    await tap(hass, "ARM_ALARM_BYPASS_DOORS")
    assert called_entities(handler["press"]) == ["button.home_zone_001_bypass_front_door"]
    assert handler["arm_away"] == []
    await set_state(hass, "binary_sensor.home_zone_001_bypass_front_door", "on")
    # nothing left to park on, so the run can be waited out
    await hass.async_block_till_done()
    assert called_entities(handler["arm_away"]) == ["alarm_control_panel.home"]


async def test_arm_waits_for_every_door_to_be_bypassed(hass, handler, doors_open, advance):
    await tap(hass, "ARM_ALARM_BYPASS_DOORS")
    assert sorted(called_entities(handler["press"])) == [
        "button.home_zone_001_bypass_front_door",
        "button.home_zone_007_bypass_kitchen_door",
    ]
    await set_state(hass, "binary_sensor.home_zone_001_bypass_front_door", "on")
    await advance(timedelta(seconds=16))
    assert handler["arm_away"] == []
    [alert] = alerts(handler["notify"])
    assert "couldn't be bypassed" in alert["message"]


async def test_doors_closed_since_the_alert_just_arm(hass, handler):
    await tap(hass, "ARM_ALARM_BYPASS_DOORS")
    await hass.async_block_till_done()
    assert handler["press"] == []
    assert called_entities(handler["arm_away"]) == ["alarm_control_panel.home"]


@pytest.fixture
async def leaving(arming, setup_automation):
    await setup_automation("olarm", LEFT)
    return arming


async def last_person_leaves(hass, advance):
    await set_state(hass, "binary_sensor.anybody_home", "off")
    await set_state(hass, "binary_sensor.pieter_present", "off")
    await advance(timedelta(seconds=2))


async def test_leaving_with_a_door_open_says_so(hass, leaving, advance):
    await set_state(hass, "binary_sensor.home_zone_007_kitchen_door", "on")
    await last_person_leaves(hass, advance)
    [alert] = alerts(leaving["notify"])
    assert alert["message"].endswith("are open:\n  - Kitchen Door")
    assert action_ids(alert)[0] == "ARM_ALARM_BYPASS_DOORS"


async def test_leaving_with_the_doors_shut_asks_as_before(hass, leaving, advance):
    await last_person_leaves(hass, advance)
    [alert] = alerts(leaving["notify"])
    assert alert["message"] == "The last person left home. Would you like to arm the alarm?"
    assert action_ids(alert) == ["ARM_ALARM", "ARM_ALARM_BYPASS_GARAGE", "ENABLE_GUEST_MODE"]
