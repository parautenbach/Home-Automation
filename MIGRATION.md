# Olarm Migration: Custom REST/Webhook Integration → Official Olarm Integration

Branch: `olarm-migration` (worktree at `~/Github/Home-Automation-olarm`).
The main checkout stays on `master` for unrelated work.

The code side is complete and committed. What remains is the manual sequence below:
soak, cut over, verify, then clean up.

## What changed in this branch

Commits: `8d73053` (phase 1), `b734cb9` (phase 2), `a8b18ba` (phase 3),
`671d078` (notification stacking fix).

**`home_assistant/packages/olarm.yaml`** — rewritten around the official integration:

- **Deleted**: both `manual` alarm panels, all `rest_command`s (get state, arm/disarm,
  bypass/unbypass), the "Sync Alarm State" automation, the old "Receive Olarm Event"
  webhook automation, and all 18 `alarm_zone_*_bypass` input booleans.
- **Added**: 14 template switches (`switch.alarm_bypass_*`) wrapping the integration's
  bypass buttons + bypass state sensors; `homeassistant.customize` entries giving the
  motion zones a `device_class` and all real zones clean friendly names.
- **Reworked**: "Alarm State Changed" is pure notification logic (state from the
  integration is ground truth; includes `changed_by` and bypassed zones when arming);
  "Notify When Alarm Triggered" includes the `zone_in_alarm` attribute and disarms only
  the triggered partition; both are `mode: queued` (a panic can trigger both partitions
  at once); bypass-garage arming waits for the panel to confirm the bypass instead of a
  blind 5 s delay; `code:` no longer passed (panels have `code_arm_required: false`).
- **Notification stacking fix** (`671d078`): the three senders sharing the
  `arm-alarm-reminder` tag now clear before sending, with a re-check after the gap,
  because iOS can neither replace nor group critical notifications. Also gave the living
  room lamp trigger an id, without which it could never satisfy the condition.
- **Temporary**: "Log Olarm Webhook Events" — passive, independent alarm/panic signal
  during the soak period. Touches no alarm entities.

**`home_assistant/custom_templates/security.jinja`** — `get_active_zones(partition, scope)`
is now partition-aware (`'home'`/`'flatlet'`), excludes bypassed zones, and filters doors
by device class; new `get_bypassed_zones(partition)`. The partition→zone map lives here
(flatlet = zone 018; spares 002/014–016/021–024 and remotes 011/012 ignored).

**`home_assistant/ui-lovelace/security.yaml`**

- Logbook zone entities renamed `home_test_zone_*` → `home_zone_*`; fixed the
  "Kitchen door" entry, which pointed at zone 006 (kitchen PIR) instead of zone 007.
- Door Zones and Motion Zones glance cards (state-coloured icons), listing each zone.
- Panic tile: hold + confirmation dialog pressing `button.home_user_panic`; tap disabled.

**`home_assistant/ui-lovelace/main.yaml`** — the same panic tile, replacing the todo
marker under the Home Alarm tile.

**`home_assistant/packages/test.yaml`** — test scripts updated for the new macro signature.

## Manual steps (in order)

### Before cutover

1. In the Olarm app: check the zone names match reality — they become the friendly names
   in notifications, and the entity ids are already fixed regardless. (Zone 8 is
   "Bedroom", which is what this branch expects.)
2. Map the panic sources. Zones 011/012 are the channels the remote *receivers* are wired
   to: 011 = the home remotes (partition 1), 012 = the flatlet remotes (partition 2).
   There are also two hard-wired panic buttons in the house whose wiring is unknown —
   possibly onto the same inputs, possibly elsewhere; confirm with the security company.
   During the panic test (step 3): press each hard-wired button and a remote panic
   separately, and note which zone sensors, panel states and webhook events fire. If
   panics register on identifiable zones, use those sensors for per-partition panic
   detection in the trigger notification (panic vs breach — the last open item from the
   old integration's wishlist). The remotes zones stay excluded from the arming checks in
   `security.jinja` regardless: a receiver channel is not an open door or motion zone.
   (Unexplained: the March 2024 panic in the old webhook examples logged
   `EMERGENCY! - Area 4` and `Area 5` events — see what the test produces.)
3. Parity soak with both systems live (manual panels still authoritative):
   - Arm/disarm both partitions from HA, the app, the keypad and remotes — the
     integration panels must follow in real time.
   - Verify the integration panel reaches `triggered` during an alarm test, and check
     what `zone_in_alarm` contains (number or name) — adjust the trigger notification
     if needed.
   - Check whether `changed_by` populates on arm/disarm from the app, keypad and
     remotes (it was null in the entity snapshot).
   - Arm with a zone deliberately open: does the panel force-arm (system setting), and
     if the arm is rejected, how does it surface in HA? (Assumed: no state change, no
     error. The "Alarm State Changed" notification logic relies on state being mirrored
     from the panel — verify nothing shows a false "armed".)

### Cutover (quiet day, single restart)

All renames happen here, after the legacy manual panels are gone. The zone and device
renames could technically be done earlier (the new ids collide with nothing), but waiting
avoids ambiguity while both systems run side by side.

**Between step 4 and step 7 there is no working alarm control in Home Assistant**: the
manual panels are gone and `alarm_control_panel.home`/`.flatlet` do not exist yet, so the
automations, dashboards and HomeKit have nothing to bind to. The physical alarm is
unaffected throughout — the keypad, remotes and the Olarm app keep working — but do the
renames in one sitting.

4. Merge the latest `master` into this branch (master keeps moving with unrelated work),
   deploy to the host, and restart HA:

       git -C ~/Github/Home-Automation-olarm merge master
       # sync the config to the host, then:
       scripts/management/restart_ha.sh

   This removes the manual panels and frees the `home`/`flatlet` entity ids. Expect
   errors and unavailable entities until the renames below are done.
5. In HA (Settings → Devices & Services → Olarm): rename the device
   **"Home Test" → "Home"** and accept the entity id rename prompt (`home_test_*` →
   `home_*`). That prompt is a one-time offer and renames all of the device's entities
   at once; declining it means renaming ~100 entities by hand.
6. Normalise the zone 19/20 entity ids in the registry. These two wireless zones were
   added recently and were unnamed when the integration created their entities, so the
   generated ids lack the name suffix (ids are generated once from the name and never
   regenerated, so they will not fix themselves):
   - `binary_sensor.home_zone_019_bypass` → `binary_sensor.home_zone_019_bypass_music_room_door`
   - `button.home_zone_019_unbypass` → `button.home_zone_019_unbypass_music_room_door`
   - `binary_sensor.home_zone_020_bypass` → `binary_sensor.home_zone_020_bypass_braai_room_door`
   - `button.home_zone_020_bypass` → `button.home_zone_020_bypass_braai_room_door`
   - `button.home_zone_020_unbypass` → `button.home_zone_020_unbypass_braai_room_door`

   (`button.home_zone_019_bypass_music_room_door` is already correct. The template
   switches reference the normalised ids, so this step is mandatory. Deleting and
   re-adding the integration would also regenerate every id from the current names, but
   that rebuilds everything — targeted renames are safer.)
7. Rename the two panels (entity id *and* display name):
   - `alarm_control_panel.home_area_01_home` → `alarm_control_panel.home` ("Home")
   - `alarm_control_panel.home_area_02_flatlet` → `alarm_control_panel.flatlet` ("Flatlet")

   These two renames are the pivot of the whole migration: the panels take over the ids
   the manual panels used, so the 47 existing references across `olarm.yaml` (17),
   `home.yaml` (14), `security.yaml` (6), `homekit.yaml` (4) and `main.yaml` (2) keep
   working untouched. Keeping the integration's default ids instead would mean rewriting
   all 47, and HomeKit would re-create the alarm accessories (the accessory id derives
   from the entity id), so they would lose their room assignment and any Apple Home
   automations referencing them would break. Renaming also keeps the recorder history
   continuous, since history is keyed on entity id.
8. Reload template entities (or restart once more) so the template switches bind to the
   renamed entities.

### Verify after cutover

- [ ] Both panels show correct state; arm/disarm from HA works without a code.
- [ ] Arm/disarm from the app/keypad/remote notifies (via "Alarm State Changed").
- [ ] No notification spam after an HA restart (unknown → state is filtered).
- [ ] Only one arm-reminder notification is present at a time (the stacking fix): let a
      reminder fire, then trigger another sender and confirm the first is replaced.
- [ ] Zone sensors show the clean friendly names and correct door/motion icons
      (`homeassistant.customize` applied).
- [ ] Door Zones and Motion Zones glance cards populate and colour on state.
- [ ] Bypass switches reflect and control bypass state; "Arm (bypass garage)" from the
      notification works end to end.
- [ ] Stay-arm reminder lists active door zones (test via `script.test_active_zones`).
- [ ] HomeKit: both alarms still work in the Home app (entity ids are unchanged, so the
      accessories should carry over); night mode no longer offered — then delete the
      "Set To Stay If Night Mode Activated" automation.
- [ ] Presence flows (ask to arm when leaving, ask to disarm when arriving) fire.
- [ ] Panic tile on both the main and security views: hold shows the confirmation dialog
      and tap does nothing. Only confirm the dialog if the panic test is coordinated with
      the security company — confirming raises a real panic.

### If it goes wrong

Everything is version-controlled YAML, so rollback is a deploy away:

1. Deploy `master` to the host and restart — the manual panels come back with their
   original entity ids, and the REST/webhook automations resume.
2. The Olarm-side webhook is still registered during the soak, so state sync resumes too.
3. The device/entity renames in the registry do not need reverting: master's config does
   not reference the integration's entities (bar four logbook rows on the security view).

The physical alarm is never dependent on any of this — the panel, keypad, remotes and the
Olarm app keep working regardless of what Home Assistant is doing.

### After the soak period (a week or so of stable running)

- [ ] Delete the "Log Olarm Webhook Events" automation.
- [ ] Delete the webhook on Olarm's portal (user.olarm.com → API).
- [ ] Remove from `secrets.yaml`: `olarm_webhook_id`, `olarm_bearer_token`,
      `olarm_device_endpoint`, `olarm_actions_endpoint` (nothing references the REST API
      anymore). `alarm_code` stays — still used by `homekit.yaml`, the test panel in
      `test.yaml`, and two disarm calls in `home.yaml`.
- [ ] Optional: drop the now-redundant `code:` from the `home.yaml` disarm calls (lines
      ~618 and ~665) — the new panels do not require one, so it is simply ignored.
- [ ] Delete `olarm.txt` (entity inventory snapshot) and this file, or fold what is left
      into the package header.
- [ ] Merge `olarm-migration` into `master`, then
      `git worktree remove ~/Github/Home-Automation-olarm` and delete the branch.

## Ideas not pursued

- `binary_sensor.home_ac_power` (panel mains supply) → monitoring in `devices.yaml`.
- A bypass panel on the security view (the 14 `switch.alarm_bypass_*` entities).
- Real-time "zone X was bypassed" notifications off the bypass sensors (deliberately
  skipped as noise; the arm notifications already list bypassed zones).
- Positive arm-failure detection: a watchdog that alerts when a command is sent but no
  state change follows within ~30 s. Depends on what step 3's force-arm test shows.
