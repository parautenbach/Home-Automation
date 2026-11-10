# Tests

Tests for the automations, scripts and templates in `home_assistant/`.

They run a real Home Assistant instance in-process with nothing loaded except
the integrations a test asks for, so a single automation can be set up straight
out of its package file, by `id`, and driven by injecting states. No container,
no test-mode flags in the config, no clock to wait for.

## Layout

The tree mirrors `home_assistant/`, so a test file sits at the same relative path
as the config it covers:

```
tests/
  conftest.py                              # fixtures (anything needing a live hass)
  harness.py                               # pure helpers, importable anywhere
  packages/test_safety.py                  # home_assistant/packages/safety.yaml
  fixtures/safety/smoke_escalation.yaml    # contracts, mirrored the same way
  manual_smoke_escalation.md               # what can't be automated
```

The split is the rule for where new shared code goes: if it needs a live `hass`
it is a fixture in `conftest.py`, otherwise it is a function in `harness.py`.
`pytest.ini` puts `tests/` on the path, so `from harness import ...` works from
any subdirectory.

Tests live at the repo root rather than under `home_assistant/` deliberately.
`sync_to_server.sh` is an extension allowlist with no path awareness, so it is
correct only while every `.yaml` (and `.csv`) under `home_assistant/` is
deployable. Fixtures there would be silently pushed to the production config dir.

Keep test file basenames unique across the tree — pytest imports them as
top-level modules, so `packages/test_safety.py` and `custom_templates/test_safety.py`
would collide.

## Setup

Needs Python 3.14 (HA 2026.3+ requires it).

```bash
/opt/homebrew/bin/python3.14 -m venv .venv-tests
.venv-tests/bin/pip install -r tests/requirements.txt
```

## Running

From the repo root:

```bash
.venv-tests/bin/pytest                          # everything
.venv-tests/bin/pytest -v                       # one line per test
.venv-tests/bin/pytest tests/packages/test_safety.py
.venv-tests/bin/pytest -k countdown             # by name
```

Or with the venv activated, just `pytest`.

**From the repo root** matters. `testpaths` in `pytest.ini` is only honoured when the
invocation directory is the rootdir, so running `pytest` from anywhere else collects the
current directory instead. From inside `.venv-tests` that means site-packages: ~350 of
Home Assistant's own test modules, and a collection error on a missing `hassil`.

## Writing a test

Four fixtures do the work:

- `load_states(name, exclude=())` — seed the state machine from
  `tests/fixtures/<name>.yaml`, e.g. `load_states("safety/smoke_escalation")`.
  That file is the automation's **contract**: every
  entity it reads, in the state it reads them in before anything happens.
  Triggers are edge-triggered, so the pre-state matters as much as the value the
  test later injects.
- `setup_automation(package, id)` — set up exactly one automation, by its `id`,
  from `home_assistant/packages/<package>.yaml`.
- `setup_domain(package, domain)` — set up a whole domain as configured in
  production. For dependencies whose behaviour over time is part of what is under
  test, mainly timers.
- `settle(ahead)` — move the clock forward and let everything it wakes finish.

`harness.py` adds `called_entities(calls)` — the entity_ids a set of calls was
aimed at, flattened — and `start_running()`, which yields far enough for a script
to reach its first delay. See its docstring for why `async_block_till_done()`
deadlocks in that spot.

The rule of thumb: **stub** what the automation reads, **mock** what it calls,
make **real** anything whose behaviour over time is being tested.

Stubbing an entity *and* setting up the integration that owns it collides — HA
resolves it by suffixing the entity_id (`timer.smoke_escalation_2`) and the test
then drives a different entity from the one the automation watches. Pass the
entity to `load_states(..., exclude=[...])` when a test sets it up for real.

Assertions go through `async_mock_service`, which records calls without anything
being dispatched:

```python
start = async_mock_service(hass, "script", "start_smoke_escalation")
hass.states.async_set("sensor.smoke_detectors_in_alarm", "1")
await hass.async_block_till_done()
assert start[0].data["duration"] == 90
```

To move time, request `settle` and await it. It carries a frozen clock, so a
90-second countdown expires in about a millisecond:

```python
await settle(timedelta(seconds=91))
```

## Version pinning

`pytest-homeassistant` pins an exact HA version, and trigger and script semantics do
shift between releases, so keep it matched to production. See `tests/requirements.txt`.

It is Home Assistant's own plugin, which replaced
`pytest-homeassistant-custom-component` from 2026.11. One wrinkle comes with it: HA
aliases its own httpx build over `httpx`, and the alias has to be installed before
anything imports `httpx`. respx's pytest plugin imports it at entry-point load, too
early, so `pytest.ini` carries `-p no:respx`. respx itself still works.
