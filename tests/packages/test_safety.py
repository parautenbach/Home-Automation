"""Tests for home_assistant/packages/safety.yaml.

Manual coverage that cannot be automated (physical detectors, the iOS
notification actions) is in tests/manual_smoke_escalation.md.

Fixtures return the *call log* for the service they mock — a list that grows by
one ServiceCall each time it is invoked. So `assert not countdown_starts` means
it was never called, and `len(countdown_starts) == 1` means exactly once, which
matters wherever several paths lead to the same service.
"""

from datetime import timedelta

import homeassistant.util.dt as dt_util

import pytest
from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import CoreState
from pytest_homeassistant.common import async_mock_service

from harness import called_entities, start_running

# Automations under test, by the id in safety.yaml.
START_SMOKE_ESCALATION = "b91bdf98-8f34-468a-b588-b4b268ce5cd1"
RAISE_PANIC_ON_EXPIRY = "4221201c-8ba5-49b4-93d2-8a035847d26f"
DISABLE_STALE_TEST_MODE = "5f8e2c31-4b7a-4e19-a6d8-9c0b3e5f7a24"
CLEAR_STALE_RUN_RECORD = "6ac1d4db-1f41-48ee-acfd-f898aeef3f1b"
CANCEL_WHEN_SMOKE_CLEARS = "7d2c0eef-252a-45ae-b7ec-7994f65f1489"
ALERT_WHEN_SMOKE_DETECTED = "3f2d5457-34db-464f-88d2-515fbb3e202a"
ESCALATE_ON_SECOND_DETECTOR = "d2ac5554-a947-4f45-b1b5-d4e996d97122"
ESCALATE_FROM_ALERT_ACTION = "6e9cf386-4a30-4fb2-983b-fbe308d6327e"
CANCEL_FROM_ALERT_ACTION = "7a2d263a-2159-4f94-bee9-7285a61a9f67"
CANCEL_WHEN_PANIC_RAISED = "971e2838-1956-4ac1-8295-679457cc1935"
LIVE_ACTIVITY = "185ad503-4de8-425b-823b-9eb7ebb28947"
RESUME_AFTER_RESTART = "09112fc8-58d0-45fb-b23c-9579c3eaa7cc"
SHOW_LIVE_ACTIVITY = "185ad503-4de8-425b-823b-9eb7ebb28947"
RESUME_AFTER_RESTART = "09112fc8-58d0-45fb-b23c-9579c3eaa7cc"

# The arming switch a human flips, and the record of what the run in flight is.
TEST_MODE = "input_boolean.smoke_escalation_test_mode"
RUN_IS_TEST = "input_boolean.smoke_escalation_run_is_test"

# Comfortably longer than the 1 sec delay inside script.escalate_smoke_alarm, but
# not so long that asyncio's debug loop reports the jump as a slow callback.
PAST_THE_ESCALATION_DELAY = timedelta(seconds=5)


# ---------------------------------------------------------------------------
# "Start Smoke Escalation" — the first detector opens a countdown
# ---------------------------------------------------------------------------


@pytest.fixture
async def countdown_starts(hass, load_states, setup_automation):
    """"Start Smoke Escalation" set up against its fixture, with the script mocked."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", START_SMOKE_ESCALATION)
    return async_mock_service(hass, "script", "start_smoke_escalation")


async def test_starts_a_90_second_countdown_when_nobody_is_home(
    hass, countdown_starts
):
    hass.states.async_set("binary_sensor.anybody_home", "off")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "1")
    await hass.async_block_till_done()

    assert len(countdown_starts) == 1
    assert countdown_starts[0].data["duration"] == 90


async def test_starts_a_3_minute_countdown_when_somebody_is_home(
    hass, countdown_starts
):
    hass.states.async_set("binary_sensor.anybody_home", "on")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "1")
    await hass.async_block_till_done()

    assert len(countdown_starts) == 1
    assert countdown_starts[0].data["duration"] == 180


async def test_a_second_detector_does_not_restart_a_running_countdown(
    hass, countdown_starts
):
    """1 -> 2 belongs to the panic shortcut, which must not have its timer reset."""
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "2")
    await hass.async_block_till_done()

    assert not countdown_starts


async def test_zero_to_two_in_one_change_does_not_start_a_countdown(
    hass, countdown_starts
):
    """0 -> 2 crosses both thresholds and the order of the two automations is not
    defined. The panic path owns this case; a countdown started after the panic
    had already been raised would be worse than none at all."""
    # idle, so what blocks this can only be the count guard and not the timer one
    hass.states.async_set("timer.smoke_escalation", "idle")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "2")
    await hass.async_block_till_done()

    assert not countdown_starts


# ---------------------------------------------------------------------------
# "Raise Panic When Smoke Escalation Expires" — the countdown running out
# ---------------------------------------------------------------------------


async def test_panic_is_raised_when_the_countdown_expires(
    hass, load_states, setup_automation, setup_domain, settle
):
    """The real timer, the real timer.finished event, in about a millisecond."""
    await load_states("safety/smoke_escalation", exclude=["timer.smoke_escalation"])
    await setup_domain("safety", "timer")
    await setup_automation("safety", RAISE_PANIC_ON_EXPIRY)
    escalations = async_mock_service(hass, "script", "escalate_smoke_alarm")

    await hass.services.async_call(
        "timer",
        "start",
        {"entity_id": "timer.smoke_escalation", "duration": 90},
        blocking=True,
    )
    assert not escalations

    await settle(timedelta(seconds=91))

    assert len(escalations) == 1


# ---------------------------------------------------------------------------
# script.escalate_smoke_alarm — the suppression contract
# ---------------------------------------------------------------------------


@pytest.fixture
async def outward(hass, load_states, setup_domain):
    """The escalation's outward-facing calls, each mocked and logged.

    With test mode on, none of the three outward steps may fire; with it off,
    all three must.
    """
    await load_states("safety/smoke_escalation")
    await setup_domain("safety", "script")
    async_mock_service(hass, "notify", "mobile_app_ceres")
    async_mock_service(hass, "light", "turn_on")
    return {
        # notify_tenant and open_pedestrian_gap are both called via script.turn_on
        "scripts": async_mock_service(hass, "script", "turn_on"),
        "panics": async_mock_service(hass, "button", "press"),
        "acs_off": async_mock_service(hass, "climate", "turn_off"),
        "countdown_cancels": async_mock_service(hass, "timer", "cancel"),
        "test_mode_clears": async_mock_service(hass, "input_boolean", "turn_off"),
    }


async def run_escalation(hass, settle, test_mode):
    """Call the escalation and drive it past its internal 1 sec delay."""
    call = hass.async_create_task(
        hass.services.async_call(
            "script", "escalate_smoke_alarm", {"test_mode": test_mode}, blocking=True
        )
    )
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)
    await call


async def test_a_rehearsal_raises_no_panic_and_tells_nobody(hass, outward, settle):
    """Test mode suppresses the panic, the tenant SMS and the gate — all three.

    The escalation is told what this run is; it does not look a helper up for
    itself, precisely so nothing can change the answer under it.
    """
    await run_escalation(hass, settle, test_mode=True)

    assert not outward["panics"]
    assert not outward["scripts"]
    assert not outward["acs_off"]
    # the rehearsal ends where it stops — the record, never the arming switch, which
    # is the human's and must survive for the next attempt
    assert called_entities(outward["test_mode_clears"]) == [RUN_IS_TEST]


async def test_a_real_escalation_raises_the_panic_and_opens_the_gap(
    hass, outward, settle
):
    """The direction that matters: with test mode off, nothing may be suppressed.

    An undefined or mistyped test_mode would fail this way round, silently, and
    a real fire would never reach the control room.
    """
    await run_escalation(hass, settle, test_mode=False)

    assert called_entities(outward["panics"]) == ["button.home_user_panic"]

    scripts = called_entities(outward["scripts"])
    assert "script.notify_tenant" in scripts
    assert "script.open_pedestrian_gap" in scripts

    # hvac recirculates smoke, so both ACs go off with the gap
    assert called_entities(outward["acs_off"]) == [
        "climate.living_room_ac",
        "climate.main_bedroom_ac",
    ]

    # nothing to end: this was not a rehearsal
    assert not outward["test_mode_clears"]


# ---------------------------------------------------------------------------
# "Clear Stale Smoke Escalation Run Record" — the other backstop
# ---------------------------------------------------------------------------


@pytest.fixture
async def run_record_clears(hass, load_states, setup_automation):
    """"Clear Stale Smoke Escalation Run Record" with the helper mocked."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", CLEAR_STALE_RUN_RECORD)
    yield async_mock_service(hass, "input_boolean", "turn_off")

    # release the 5 min `for:` tracker, or HA fails teardown on a pending timer
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()


async def test_the_record_is_cleared_when_the_countdown_is_long_over(
    hass, run_record_clears, settle
):
    """The four exits clear it themselves, so this is for a rehearsal that ended some
    other way — a timer reload, a bare timer.cancel. Left on, the next escalation
    without a countdown of its own labels a real fire "[Test]"."""
    hass.states.async_set(RUN_IS_TEST, "on")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    hass.states.async_set("timer.smoke_escalation", "idle")
    await settle(timedelta(minutes=6))

    assert called_entities(run_record_clears) == [RUN_IS_TEST]


async def test_the_record_is_left_alone_while_a_countdown_runs(
    hass, run_record_clears, settle
):
    """Mid-rehearsal it is not stale — it is the only thing describing the run."""
    hass.states.async_set(RUN_IS_TEST, "on")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    await settle(timedelta(minutes=6))

    assert not run_record_clears


async def test_the_record_is_not_cleared_the_moment_a_countdown_ends(
    hass, run_record_clears, settle
):
    """The exits cancel the timer first and read the record several steps later, so
    clearing on an idle timer straight away would take the "[Test]" off their own
    messages."""
    hass.states.async_set(RUN_IS_TEST, "on")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    hass.states.async_set("timer.smoke_escalation", "idle")
    await settle(PAST_THE_ESCALATION_DELAY)

    assert not run_record_clears


@pytest.fixture
async def run_record_backstop_at_startup(hass, load_states, setup_automation):
    """The backstop as it is attached during HA's own startup. See
    `backstop_at_startup` for why the start trigger needs `starting`."""

    async def _start(record_on, timer="idle"):
        await load_states("safety/smoke_escalation")
        if record_on:
            hass.states.async_set(RUN_IS_TEST, "on")
        hass.states.async_set("timer.smoke_escalation", timer)
        await hass.async_block_till_done()
        hass.set_state(CoreState.starting)
        await setup_automation("safety", CLEAR_STALE_RUN_RECORD)
        clears = async_mock_service(hass, "input_boolean", "turn_off")

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        return clears

    yield _start


async def test_the_record_is_cleared_across_a_restart(run_record_backstop_at_startup):
    """A restart mid-rehearsal is the likeliest way it gets stranded, and a `for:`
    window does not survive one."""
    clears = await run_record_backstop_at_startup(record_on=True)

    assert called_entities(clears) == [RUN_IS_TEST]


async def test_the_record_is_not_touched_at_startup_when_already_off(
    run_record_backstop_at_startup,
):
    clears = await run_record_backstop_at_startup(record_on=False)

    assert not clears


async def test_a_countdown_restored_across_a_restart_keeps_its_record(
    run_record_backstop_at_startup,
):
    """The timer restores before automations attach, so a rehearsal interrupted by a
    restart comes back mid-countdown with the start trigger firing. Clearing here would
    take the "[Test]" off the run that is still in flight."""
    clears = await run_record_backstop_at_startup(record_on=True, timer="active")

    assert not clears


# ---------------------------------------------------------------------------
# "Disable Stale Smoke Escalation Test Mode" — the backstop
# ---------------------------------------------------------------------------


@pytest.fixture
async def test_mode_clears(hass, load_states, setup_automation):
    """"Disable Stale Smoke Escalation Test Mode" with the helper mocked."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", DISABLE_STALE_TEST_MODE)
    async_mock_service(hass, "notify", "mobile_app_ceres")
    yield async_mock_service(hass, "input_boolean", "turn_off")

    # Tests that stop inside a 5 min `for:` window leave that trigger's tracker armed,
    # and HA fails teardown on a pending timer. The automation has two such triggers —
    # the helper going on, and the timer going idle — so release both by putting each
    # watched entity back to the state that cancels its window.
    hass.states.async_set(TEST_MODE, "off")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()


async def test_backstop_clears_a_helper_left_on_with_no_countdown(
    hass, test_mode_clears, settle
):
    hass.states.async_set(TEST_MODE, "on")
    await hass.async_block_till_done()

    await settle(timedelta(minutes=6))

    assert len(test_mode_clears) == 1


@pytest.fixture
async def backstop_at_startup(hass, load_states, setup_automation):
    """The backstop as it is attached during Home Assistant's own startup.

    The `homeassistant` start trigger arms a one-shot bus listener for
    EVENT_HOMEASSISTANT_STARTED — past tense, and not the same thing as the trigger's
    own `event: start`. It only fires if that listener is armed before the event, which
    in production is guaranteed because automations are set up during the starting
    phase. So hass is put in `starting`, not `not_running`: at `not_running` the
    automation defers its own setup until EVENT_HOMEASSISTANT_STARTED, arms the listener
    while that event is already being dispatched, and never sees it.
    """

    async def _start(test_mode_on):
        await load_states("safety/smoke_escalation")
        if test_mode_on:
            hass.states.async_set(TEST_MODE, "on")
            await hass.async_block_till_done()
        hass.set_state(CoreState.starting)
        await setup_automation("safety", DISABLE_STALE_TEST_MODE)
        async_mock_service(hass, "notify", "mobile_app_ceres")
        clears = async_mock_service(hass, "input_boolean", "turn_off")

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        return clears

    yield _start

    # the 5 min `for:` tracker is still armed, and HA fails teardown on a pending timer
    hass.states.async_set(TEST_MODE, "off")
    await hass.async_block_till_done()


async def test_backstop_clears_a_helper_left_on_across_a_restart(backstop_at_startup):
    """The only hazard the arming switch still carries: forgotten, it would stamp a
    real fire as a rehearsal. A `for:` window does not survive a restart, so the start
    trigger is the one that catches this."""
    clears = await backstop_at_startup(test_mode_on=True)

    assert len(clears) == 1


async def test_backstop_leaves_a_helper_that_is_already_off_alone(backstop_at_startup):
    """Every restart attaches this trigger, and almost every restart has nothing to do."""
    clears = await backstop_at_startup(test_mode_on=False)

    assert not clears


# ---------------------------------------------------------------------------
# "Cancel Smoke Escalation When Smoke Clears" — calling the countdown off
# ---------------------------------------------------------------------------


@pytest.fixture
async def countdown_cancels(hass, load_states, setup_automation):
    """"Cancel Smoke Escalation When Smoke Clears" with the timer mocked."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", CANCEL_WHEN_SMOKE_CLEARS)
    async_mock_service(hass, "notify", "mobile_app_ceres")
    async_mock_service(hass, "input_boolean", "turn_off")
    return async_mock_service(hass, "timer", "cancel")


def set_count(hass, count, unavailable=()):
    hass.states.async_set(
        "sensor.smoke_detectors_in_alarm",
        str(count),
        {
            "in_alarm": [],
            "unavailable": list(unavailable),
            "unavailable_count": len(unavailable),
        },
    )


async def test_a_detector_going_offline_mid_alarm_does_not_clear_the_smoke(
    hass, countdown_cancels
):
    """That is what a fire looks like, not what a cleared alarm looks like."""
    hass.states.async_set("timer.smoke_escalation", "active")
    set_count(hass, 1)
    await hass.async_block_till_done()

    set_count(hass, 0, unavailable=["binary_sensor.kitchen_smoke"])
    await hass.async_block_till_done()

    assert not countdown_cancels


async def test_a_detector_coming_back_clear_stops_the_countdown(
    hass, countdown_cancels
):
    """The count never crosses a threshold here — it is already 0 — so this only
    works because the automation triggers on the attribute change too."""
    hass.states.async_set("timer.smoke_escalation", "active")
    set_count(hass, 1)
    await hass.async_block_till_done()

    set_count(hass, 0, unavailable=["binary_sensor.kitchen_smoke"])
    await hass.async_block_till_done()
    assert not countdown_cancels

    set_count(hass, 0)
    await hass.async_block_till_done()

    assert len(countdown_cancels) == 1


async def test_the_count_sensor_itself_going_unavailable_does_not_cancel(
    hass, countdown_cancels
):
    """A template error or a reload must not read as "the smoke cleared". It self-heals:
    the sensor coming back at 0 is another change, and that one does cancel."""
    hass.states.async_set("timer.smoke_escalation", "active")
    set_count(hass, 1)
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "unavailable")
    await hass.async_block_till_done()
    assert not countdown_cancels

    set_count(hass, 0)
    await hass.async_block_till_done()

    assert len(countdown_cancels) == 1


# ---------------------------------------------------------------------------
# script.start_smoke_escalation — stamping what kind of run this is
# ---------------------------------------------------------------------------


@pytest.fixture
async def countdown_helpers(hass, load_states, setup_domain):
    """script.start_smoke_escalation against real input_booleans.

    The helpers are set up for real rather than stubbed: what is under test is the
    state they end up in, not which services were called.
    """
    await load_states("safety/smoke_escalation", exclude=[TEST_MODE, RUN_IS_TEST])
    await setup_domain("safety", "input_boolean")
    await setup_domain("safety", "script")
    async_mock_service(hass, "timer", "start")
    async_mock_service(hass, "notify", "mobile_app_ceres")


async def set_helper(hass, entity_id, on):
    await hass.services.async_call(
        "input_boolean",
        "turn_on" if on else "turn_off",
        {"entity_id": entity_id},
        blocking=True,
    )


async def start_countdown(hass, duration=180):
    await hass.services.async_call(
        "script", "start_smoke_escalation", {"duration": duration}, blocking=True
    )


async def test_starting_a_countdown_stamps_the_run_as_a_rehearsal(
    hass, countdown_helpers
):
    await set_helper(hass, TEST_MODE, True)

    await start_countdown(hass)

    assert hass.states.get(RUN_IS_TEST).state == "on"


async def test_starting_a_countdown_stamps_a_real_run_as_real(hass, countdown_helpers):
    """Written on every start, so a record left over from an earlier rehearsal can
    never suppress a later fire. That is why nothing else has to clear it."""
    await set_helper(hass, RUN_IS_TEST, True)
    await set_helper(hass, TEST_MODE, False)

    await start_countdown(hass)

    assert hass.states.get(RUN_IS_TEST).state == "off"


async def test_the_arming_switch_moving_mid_countdown_does_not_change_the_run(
    hass, countdown_helpers
):
    """The point of the whole split: both real dispatches came from the arming
    switch being cleared between the countdown starting and the escalation reading
    it. Now only the record is read, and only the countdown start writes it."""
    await set_helper(hass, TEST_MODE, True)
    await start_countdown(hass)
    assert hass.states.get(RUN_IS_TEST).state == "on"

    # whatever now happens to the arming switch — a backstop, a stray tap, a restart
    await set_helper(hass, TEST_MODE, False)

    assert hass.states.get(RUN_IS_TEST).state == "on"


# ---------------------------------------------------------------------------
# Which flag each caller of the escalation reads
# ---------------------------------------------------------------------------


@pytest.fixture
async def escalations(hass, load_states):
    """The escalation script mocked, so the test_mode each caller passes is visible."""
    await load_states("safety/smoke_escalation")
    return async_mock_service(hass, "script", "escalate_smoke_alarm")


async def test_the_second_detector_shortcut_reads_the_arming_switch(
    hass, escalations, setup_automation
):
    """No countdown on this path, so there is no run record to read — and nothing has
    elapsed between the decision and the action. The record is deliberately wrong here
    to prove which one is used."""
    await setup_automation("safety", ESCALATE_ON_SECOND_DETECTOR)
    hass.states.async_set(TEST_MODE, "on")
    hass.states.async_set(RUN_IS_TEST, "off")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "2")
    await hass.async_block_till_done()

    assert len(escalations) == 1
    # a bool, not the string "True": `not test_mode` on a non-empty string is False,
    # which would suppress a real fire
    assert escalations[0].data["test_mode"] is True


async def test_the_alert_action_reads_the_run_record(
    hass, escalations, setup_automation
):
    """A prompt implies a countdown, so what matters is what that countdown was
    stamped as — not what the arming switch has been moved to since."""
    await setup_automation("safety", ESCALATE_FROM_ALERT_ACTION)
    hass.states.async_set(TEST_MODE, "off")
    hass.states.async_set(RUN_IS_TEST, "on")
    await hass.async_block_till_done()

    hass.bus.async_fire(
        "mobile_app_notification_action", {"action": "ESCALATE_SMOKE_ALARM"}
    )
    await hass.async_block_till_done()

    assert len(escalations) == 1
    assert escalations[0].data["test_mode"] is True


async def test_a_real_run_is_passed_as_real_even_with_a_stale_record(
    hass, escalations, setup_automation
):
    """The direction that dispatches: neither flag may leak a rehearsal into a fire."""
    await setup_automation("safety", ESCALATE_ON_SECOND_DETECTOR)
    hass.states.async_set(TEST_MODE, "off")
    hass.states.async_set(RUN_IS_TEST, "on")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "2")
    await hass.async_block_till_done()

    assert escalations[0].data["test_mode"] is False


async def test_zero_to_two_escalates_once_and_opens_no_countdown(
    hass, escalations, setup_automation
):
    """Both detectors inside one state-machine cycle, so the count never passes
    through 1 and both automations fire on the same state change in an order HA does
    not define.

    This is the pair under test rather than either one alone: the start automation's
    `state == "1"` condition is what makes the ordering irrelevant. Without it a
    countdown could be left running after the panic had gone out, to expire later
    into a stale prompt.
    """
    await setup_automation("safety", START_SMOKE_ESCALATION, ESCALATE_ON_SECOND_DETECTOR)
    countdown_starts = async_mock_service(hass, "script", "start_smoke_escalation")
    hass.states.async_set("timer.smoke_escalation", "idle")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "2")
    await hass.async_block_till_done()

    assert len(escalations) == 1
    assert not countdown_starts


# ---------------------------------------------------------------------------
# "Cancel Smoke Escalation When Panic Raised" — a panic raised by hand
# ---------------------------------------------------------------------------


@pytest.fixture
async def panic_cancels(hass, load_states, setup_automation):
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", CANCEL_WHEN_PANIC_RAISED)
    async_mock_service(hass, "notify", "mobile_app_ceres")
    async_mock_service(hass, "input_boolean", "turn_off")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()
    return async_mock_service(hass, "timer", "cancel")


async def press_panic(hass, ago):
    """Write the button state the way a press does: the timestamp of that press."""
    hass.states.async_set(
        "button.home_user_panic", (dt_util.utcnow() - ago).isoformat()
    )
    await hass.async_block_till_done()


async def test_a_panic_raised_by_hand_stops_the_countdown(hass, panic_cancels):
    """Otherwise it expires later onto a stale prompt, behind a panic already sent."""
    await press_panic(hass, timedelta(seconds=0))

    assert len(panic_cancels) == 1


async def test_a_restored_button_timestamp_does_not_stop_the_countdown(
    hass, panic_cancels
):
    """A button's state is restored on startup and arrives as a state change. Only a
    fresh timestamp is a press; an old one must not cancel a live countdown."""
    await press_panic(hass, timedelta(minutes=30))

    assert not panic_cancels


# ---------------------------------------------------------------------------
# script.cancel_smoke_escalation — the shared way to call a countdown off
# ---------------------------------------------------------------------------


@pytest.fixture
async def cancellation(hass, load_states, setup_domain):
    await load_states("safety/smoke_escalation")
    await setup_domain("safety", "script")
    async_mock_service(hass, "timer", "cancel")
    async_mock_service(hass, "notify", "mobile_app_ceres")
    # script.notify_tenant lives in home.yaml, so the real turn_on would miss it
    async_mock_service(hass, "script", "turn_on")
    return async_mock_service(hass, "input_boolean", "turn_off")


async def run_cancellation(hass, settle):
    call = hass.async_create_task(
        hass.services.async_call(
            "script", "cancel_smoke_escalation", blocking=True
        )
    )
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)
    await call


async def test_cancelling_a_rehearsal_ends_it(hass, cancellation, settle):
    hass.states.async_set(RUN_IS_TEST, "on")
    await hass.async_block_till_done()

    await run_cancellation(hass, settle)

    assert called_entities(cancellation) == [RUN_IS_TEST]


async def test_cancelling_a_real_countdown_touches_no_helper(
    hass, cancellation, settle
):
    hass.states.async_set(RUN_IS_TEST, "off")
    await hass.async_block_till_done()

    await run_cancellation(hass, settle)

    assert not cancellation


async def test_the_tenant_is_told_the_smoke_cleared(hass, countdown_cancels, settle):
    """The warning went out at T=0 for any detector, so this path owes them the
    all-clear — without it they are left holding "be ready to evacuate"."""
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set("timer.smoke_escalation", "active")
    hass.states.async_set(RUN_IS_TEST, "off")
    set_count(hass, 1)
    await hass.async_block_till_done()

    set_count(hass, 0)
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)

    assert called_entities(tenant_notices) == ["script.notify_tenant"]


async def test_the_tenant_hears_nothing_when_a_rehearsal_clears(
    hass, countdown_cancels, settle
):
    """Nothing to take back: the T=0 warning was suppressed for the drill."""
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set("timer.smoke_escalation", "active")
    hass.states.async_set(RUN_IS_TEST, "on")
    set_count(hass, 1)
    await hass.async_block_till_done()

    set_count(hass, 0)
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)

    assert not called_entities(tenant_notices)


async def test_a_panic_by_hand_tells_the_tenant_to_evacuate(
    hass, panic_cancels, settle
):
    """Not an all-clear: someone pressed panic, which means they decided it is real."""
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set(RUN_IS_TEST, "off")
    await hass.async_block_till_done()

    # not press_panic: its async_block_till_done waits for the run to finish, and this
    # one parks in a delay that only a clock move releases.
    hass.states.async_set("button.home_user_panic", dt_util.utcnow().isoformat())
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)

    assert called_entities(tenant_notices) == ["script.notify_tenant"]
    assert "evacuate" in tenant_notices[0].data["variables"]["message"]


async def test_cancelling_tells_the_tenant_there_is_no_need_to_evacuate(
    hass, cancellation, settle
):
    """The shared script is what the dashboard tile and the notification action both
    call, so the all-clear has to live here too, not only on the smoke-cleared path."""
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set(RUN_IS_TEST, "off")
    set_count(hass, 0)
    await hass.async_block_till_done()

    await run_cancellation(hass, settle)

    assert called_entities(tenant_notices) == ["script.notify_tenant"]
    message = tenant_notices[0].data["variables"]["message"]
    assert "has been cleared" in message
    assert "no need to evacuate" in message


async def test_cancelling_with_smoke_still_detected_keeps_the_tenant_ready(
    hass, cancellation, settle
):
    """Cancelling is a decision about the response, not about the smoke. Our own message
    says smoke is still being detected, and the tenant must not be told the opposite in
    the same breath."""
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set(RUN_IS_TEST, "off")
    set_count(hass, 1)
    await hass.async_block_till_done()

    await run_cancellation(hass, settle)

    message = tenant_notices[0].data["variables"]["message"]
    assert "still being detected" in message
    assert "no need to evacuate" not in message


async def test_cancelling_a_rehearsal_tells_the_tenant_nothing(
    hass, cancellation, settle
):
    tenant_notices = async_mock_service(hass, "script", "turn_on")
    hass.states.async_set(RUN_IS_TEST, "on")
    await hass.async_block_till_done()

    await run_cancellation(hass, settle)

    assert not called_entities(tenant_notices)


async def test_the_cancel_alert_action_calls_the_shared_script(
    hass, load_states, setup_automation
):
    """The notification action and the dashboard tile must end a countdown the same
    way: a bare timer.cancel leaves no message and no way to end a rehearsal."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", CANCEL_FROM_ALERT_ACTION)
    cancels = async_mock_service(hass, "script", "cancel_smoke_escalation")

    hass.bus.async_fire(
        "mobile_app_notification_action", {"action": "CANCEL_SMOKE_ESCALATION"}
    )
    await hass.async_block_till_done()

    assert len(cancels) == 1


# ---------------------------------------------------------------------------
# "Alert When Smoke Detected" — the alert at T=0
# ---------------------------------------------------------------------------


@pytest.fixture
async def smoke_alerts(hass, load_states, setup_automation):
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", ALERT_WHEN_SMOKE_DETECTED)
    async_mock_service(hass, "notify", "mobile_app_ceres")
    return async_mock_service(hass, "script", "turn_on")


async def detect_smoke(hass, settle, detector="binary_sensor.kitchen_smoke"):
    hass.states.async_set(detector, "on")
    await start_running()
    # the automation waits a second between clearing a notification and sending one
    await settle(PAST_THE_ESCALATION_DELAY)


@pytest.mark.parametrize(
    "detector",
    [
        "binary_sensor.kitchen_smoke",
        "binary_sensor.braai_room_smoke",
        "binary_sensor.garage_smoke",
    ],
)
async def test_the_tenant_is_told_about_smoke_anywhere_in_the_building(
    hass, smoke_alerts, settle, detector
):
    """They share the building, so a warning they can act on beats hearing at
    escalation that it is already too late — including for the toast, which is the
    price of every path out of a countdown now closing the loop with them."""
    await detect_smoke(hass, settle, detector)

    assert called_entities(smoke_alerts) == ["script.notify_tenant"]


async def test_the_tenant_is_not_dragged_into_a_rehearsal(
    hass, smoke_alerts, settle
):
    """T5 on 2026-09-09 sent this for real during a drill: the automation only knew
    about the webhook self-test, and a forced detector state is not one."""
    hass.states.async_set(TEST_MODE, "on")
    await hass.async_block_till_done()

    await detect_smoke(hass, settle, "binary_sensor.garage_smoke")

    assert not smoke_alerts


async def test_we_are_still_alerted_the_moment_smoke_is_detected(
    hass, load_states, setup_automation, settle
):
    """Dropping the tenant step must not quieten our own T=0 alert.

    The area name is not asserted: nothing registers these entities to an area here,
    so `area_name()` renders as "none". That part is T5's job.
    """
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", ALERT_WHEN_SMOKE_DETECTED)
    async_mock_service(hass, "script", "turn_on")
    notifications = async_mock_service(hass, "notify", "mobile_app_ceres")

    await detect_smoke(hass, settle)

    messages = [c.data.get("message", "") for c in notifications]
    assert any(m.startswith("Smoke has been detected") for m in messages)


# ---------------------------------------------------------------------------
# "Show Smoke Escalation Live Activity" — the countdown on the lock screen
# ---------------------------------------------------------------------------


@pytest.fixture
async def live_activity(hass, load_states, setup_automation, setup_domain):
    """The live activity automation against the real timer, with notify mocked."""
    await load_states("safety/smoke_escalation", exclude=["timer.smoke_escalation"])
    await setup_domain("safety", "timer")
    await setup_automation("safety", SHOW_LIVE_ACTIVITY)
    return async_mock_service(hass, "notify", "mobile_app_ceres")


async def start_timer(hass, duration=90):
    await hass.services.async_call(
        "timer",
        "start",
        {"entity_id": "timer.smoke_escalation", "duration": duration},
        blocking=True,
    )
    await hass.async_block_till_done()


async def cancel_timer(hass):
    """A timer left running fails the test as a lingering timer."""
    await hass.services.async_call(
        "timer", "cancel", {"entity_id": "timer.smoke_escalation"}, blocking=True
    )
    await hass.async_block_till_done()


async def test_the_live_activity_counts_down_to_the_timer_expiry(
    hass, live_activity
):
    hass.states.async_set(RUN_IS_TEST, "off")
    await start_timer(hass)

    assert len(live_activity) == 1
    data = live_activity[0].data
    expiry = dt_util.parse_datetime(
        hass.states.get("timer.smoke_escalation").attributes["finishes_at"]
    )
    assert data["title"] == "Smoke escalation"
    assert data["data"]["live_update"] is True
    assert data["data"]["when"] == int(expiry.timestamp())
    await cancel_timer(hass)


async def test_a_rehearsal_live_activity_is_marked_as_a_test(hass, live_activity):
    hass.states.async_set(RUN_IS_TEST, "on")
    await start_timer(hass)

    assert live_activity[0].data["title"] == "[Test] Smoke escalation"
    await cancel_timer(hass)


async def test_the_live_activity_ends_when_the_countdown_is_cancelled(
    hass, live_activity
):
    await start_timer(hass)
    await cancel_timer(hass)

    assert live_activity[-1].data["message"] == "clear_notification"


async def test_the_live_activity_ends_when_the_countdown_expires(
    hass, live_activity, settle
):
    await start_timer(hass)
    await settle(timedelta(seconds=91))

    assert len(live_activity) == 2
    assert live_activity[-1].data["message"] == "clear_notification"


# ---------------------------------------------------------------------------
# Extra guards found by the manual run
# ---------------------------------------------------------------------------


async def test_a_hand_raised_panic_says_why_the_countdown_stopped(
    hass, load_states, setup_automation, settle
):
    """T9: the prompt vanishing with nothing in its place reads as a bug."""
    await load_states("safety/smoke_escalation")
    await setup_automation("safety", CANCEL_WHEN_PANIC_RAISED)
    async_mock_service(hass, "timer", "cancel")
    async_mock_service(hass, "input_boolean", "turn_off")
    notifications = async_mock_service(hass, "notify", "mobile_app_ceres")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    hass.states.async_set("button.home_user_panic", dt_util.utcnow().isoformat())
    await start_running()
    await settle(PAST_THE_ESCALATION_DELAY)

    messages = [c.data.get("message", "") for c in notifications]
    assert "clear_notification" in messages
    assert any("panic has been raised by hand" in m for m in messages)


async def test_the_backstop_leaves_a_running_countdown_armed(
    hass, test_mode_clears, settle
):
    """A restart mid-countdown must not clear the switch and claim it
    had been left on, taking the arming away from the rest of the session."""
    hass.states.async_set(TEST_MODE, "on")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    await settle(timedelta(minutes=6))

    assert not test_mode_clears


# ---------------------------------------------------------------------------
# "Resume Smoke Escalation After Restart" — picking a lost countdown back up
# ---------------------------------------------------------------------------


@pytest.fixture
async def resumes(hass, load_states, setup_automation):
    """The automation attached the way it is during HA's own startup."""

    async def _start(detectors_in_alarm, **states):
        await load_states("safety/smoke_escalation")
        hass.states.async_set(
            "sensor.smoke_detectors_in_alarm",
            str(detectors_in_alarm),
            {"detectors": ["binary_sensor.kitchen_smoke"], "unavailable_count": 0},
        )
        for entity_id, state in states.items():
            hass.states.async_set(entity_id.replace("__", "."), state)
        await hass.async_block_till_done()

        hass.set_state(CoreState.starting)
        await setup_automation("safety", RESUME_AFTER_RESTART)
        starts = async_mock_service(hass, "script", "start_smoke_escalation")

        hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
        await hass.async_block_till_done()
        return starts

    return _start


async def test_smoke_still_present_after_a_restart_reopens_a_countdown(resumes):
    """timer.finished for a restored timer is fired during component setup, before any
    automation has attached, so the escalation it should have triggered is lost."""
    starts = await resumes(1)

    assert len(starts) == 1
    assert starts[0].data["duration"] == 90


async def test_a_restart_with_no_smoke_resumes_nothing(resumes):
    starts = await resumes(0)

    assert not starts


async def test_a_restart_does_not_stack_behind_a_panic_already_raised(hass, resumes):
    """A restored timer that expired during the downtime may already have escalated."""
    starts = await resumes(
        1, button__home_user_panic=dt_util.utcnow().isoformat()
    )

    assert not starts


async def test_a_restart_mid_countdown_resumes_nothing(hass, resumes):
    """T11.1: the timer survived, so it is still counting and owns the escalation."""
    starts = await resumes(1, timer__smoke_escalation="active")

    assert not starts


async def test_a_stale_live_activity_is_cleared_on_startup(
    hass, load_states, setup_automation
):
    """A countdown that ended while HA was down leaves a chronometer counting on the
    lock screen with nothing behind it."""
    await load_states("safety/smoke_escalation")
    hass.set_state(CoreState.starting)
    await setup_automation("safety", LIVE_ACTIVITY)
    notifications = async_mock_service(hass, "notify", "mobile_app_ceres")

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert len(notifications) == 1
    assert notifications[0].data["message"] == "clear_notification"


async def test_a_live_activity_for_a_surviving_countdown_is_left_alone(
    hass, load_states, setup_automation
):
    """T11.1: the activity raised before the restart is still correct, and iOS still
    has it on the lock screen."""
    await load_states("safety/smoke_escalation")
    hass.states.async_set("timer.smoke_escalation", "active")
    hass.set_state(CoreState.starting)
    await setup_automation("safety", LIVE_ACTIVITY)
    notifications = async_mock_service(hass, "notify", "mobile_app_ceres")

    hass.bus.async_fire(EVENT_HOMEASSISTANT_STARTED)
    await hass.async_block_till_done()

    assert not notifications

# ---------------------------------------------------------------------------
# Guards the mutation runner found nothing depending on
# ---------------------------------------------------------------------------


async def test_a_countdown_already_running_blocks_a_new_one_on_its_own(
    hass, countdown_starts
):
    """The timer-idle condition, isolated.

    `test_a_second_detector_does_not_restart_a_running_countdown` sets the timer
    active *and* the count to 2, so the count condition alone accounts for the
    block. Here the count is 1, which the count condition allows, leaving the
    timer condition as the only thing that can stop it.
    """
    hass.states.async_set("timer.smoke_escalation", "active")
    hass.states.async_set("sensor.smoke_detectors_in_alarm", "0")
    await hass.async_block_till_done()

    hass.states.async_set("sensor.smoke_detectors_in_alarm", "1")
    await hass.async_block_till_done()

    assert not countdown_starts


async def test_smoke_clearing_with_no_countdown_cancels_nothing(
    hass, countdown_cancels
):
    """The timer-active condition, isolated: the count drops to 0 with everything
    else satisfied, so only the timer state can stop a pointless cancel."""
    hass.states.async_set("timer.smoke_escalation", "idle")
    set_count(hass, 1)
    await hass.async_block_till_done()

    set_count(hass, 0)
    await hass.async_block_till_done()

    assert not countdown_cancels


async def test_a_panic_with_no_countdown_running_cancels_nothing(
    hass, panic_cancels
):
    """Same shape for the panic path: a fresh press, so the timestamp condition
    passes and the timer state is the only guard left."""
    hass.states.async_set("timer.smoke_escalation", "idle")
    await hass.async_block_till_done()

    hass.states.async_set("button.home_user_panic", dt_util.utcnow().isoformat())
    await hass.async_block_till_done()

    assert not panic_cancels


async def test_a_countdown_ending_does_not_immediately_clear_the_switch(
    hass, test_mode_clears, settle
):
    """The `for:` on the timer-idle trigger, which nothing else covers.

    Without it the backstop fires the moment a countdown ends and takes the
    arming switch with it — the T13 regression, where a second attempt needed
    re-arming. Stays under 5 min so the test-mode trigger cannot account for it.
    """
    hass.states.async_set(TEST_MODE, "on")
    hass.states.async_set("timer.smoke_escalation", "active")
    await hass.async_block_till_done()

    hass.states.async_set("timer.smoke_escalation", "idle")
    await hass.async_block_till_done()
    await settle(timedelta(minutes=2))

    assert not test_mode_clears


async def test_an_escalation_stands_down_behind_a_panic_already_raised(
    hass, outward, settle
):
    """The script's first step: a panic within the last 5 min means the control
    room already has the signal, so this run has nothing to add."""
    hass.states.async_set("button.home_user_panic", dt_util.utcnow().isoformat())
    await hass.async_block_till_done()

    await run_escalation(hass, settle, test_mode=False)

    assert not outward["panics"]
    assert not outward["scripts"]


async def test_a_real_escalation_cancels_the_countdown_it_came_from(
    hass, outward, settle
):
    """Otherwise the timer survives the escalation and expires behind it, raising
    a second panic for the same fire."""
    await run_escalation(hass, settle, test_mode=False)

    assert called_entities(outward["countdown_cancels"]) == ["timer.smoke_escalation"]
