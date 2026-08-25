# Olarm Migration: Custom REST/Webhook Integration → Official Olarm Integration

Branch: `olarm-migration` (this worktree). Main checkout stays on `master` for unrelated work.

## What changed in this branch

- `home_assistant/packages/olarm.yaml` — rewritten:
  - **Deleted**: both `manual` alarm panels, all `rest_command`s (get state, arm/disarm,
    bypass/unbypass), the "Sync Alarm State" automation, the old "Receive Olarm Event"
    webhook automation, and all 18 `alarm_zone_*_bypass` input booleans.
  - **Added**: 14 template switches (`switch.alarm_bypass_*`) wrapping the integration's
    bypass buttons + bypass state sensors; `homeassistant.customize` entries giving the
    motion zones a `device_class` and all real zones clean friendly names.
  - **Reworked**: "Alarm State Changed" is pure notification logic (state from the
    integration is ground truth; includes `changed_by` and bypassed zones when arming);
    "Notify When Alarm Triggered" includes the `zone_in_alarm` attribute and disarms only
    the triggered partition; bypass-garage arming now waits for the panel to confirm the
    bypass instead of a blind 5 s delay; `code:` no longer passed (panels have
    `code_arm_required: false`).
  - **Temporary**: "Log Olarm Webhook Events" — passive, independent alarm/panic signal
    during the soak period. Touches no alarm entities.
- `home_assistant/custom_templates/security.jinja` — `get_active_zones(partition, scope)`
  is now partition-aware (`'home'`/`'flatlet'`), excludes bypassed zones, and filters
  doors by device class; new `get_bypassed_zones(partition)`. The partition→zone map
  lives here (flatlet = zone 018; spares 002/014–016/021–024 and remotes 011/012 ignored).
- `home_assistant/ui-lovelace/security.yaml` — logbook zone entities renamed
  `home_test_zone_*` → `home_zone_*`; fixed the "Kitchen door" entry, which pointed at
  zone 006 (kitchen PIR) instead of zone 007 (kitchen door).
- `home_assistant/packages/test.yaml` — test scripts updated for the new macro signature.

## Housekeeping

After committing this branch, discard the superseded alarm WIP still sitting
uncommitted on the master checkout (this branch carries the improved versions):

    git -C ~/Github/Home-Automation checkout -- \
      home_assistant/custom_templates/security.jinja \
      home_assistant/packages/olarm.yaml \
      home_assistant/packages/test.yaml

The other uncommitted master work (health, lights, resources) is unrelated — leave it.
The stray `olarm.txt` in the master checkout can be deleted; the branch has a copy.

## Manual steps (in order)

### Before cutover

1. In the Olarm app: rename zone 8 to **Bedroom** (currently fine) and check the other
   zone names match reality. Entity ids stay static; only display names change upstream.
2. Map the panic sources. Zones 011/012 are the channels the remote *receivers* are
   wired to: 011 = the home remotes (partition 1), 012 = the flatlet remotes
   (partition 2). There are also two hard-wired panic buttons in the house whose
   wiring is unknown — possibly onto the same inputs, possibly elsewhere; confirm
   the wiring with the security company. During the
   panic test (step 3): press each hard-wired button and a remote panic separately
   and note which zone sensors, panel states and webhook events fire. If panics
   register on identifiable zones, use those sensors for per-partition panic
   detection in the trigger notification (panic vs breach — the last open item from
   the old integration's wishlist). The remotes zones stay excluded from the arming
   checks in `security.jinja` regardless (a receiver channel is not an open
   door/motion zone).
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
     if the arm is rejected, how does it surface in HA? (Assumed: no state change,
     no error. The "Alarm State Changed" notification logic relies on state being
     mirrored from the panel — verify nothing shows a false "armed".)

### Cutover (quiet day, single restart)

All renames happen here, after the legacy manual panels are gone — technically the
zone/device renames could be done earlier (the new ids collide with nothing), but
waiting avoids any ambiguity while both systems run side by side.

4. Merge the latest `master` into this branch (master keeps moving with unrelated
   work), then deploy this branch to the host and restart HA — this removes the manual
   panels and frees the `home`/`flatlet` entity ids. (The template switches and customize entries
   reference entities that only exist after the renames below; they sit unavailable
   until step 8.)
5. In HA (Settings → Devices → Olarm): rename the device **"Home Test" → "Home"** and
   accept the entity id renames (`home_test_*` → `home_*`).
6. Normalise the zone 19/20 entity ids in the registry (these two wireless zones were
   added recently and were unnamed when the integration created their entities, so the
   generated ids lack the name suffix; ids are static upstream and won't fix themselves):
   - `binary_sensor.home_zone_019_bypass` → `binary_sensor.home_zone_019_bypass_music_room_door`
   - `button.home_zone_019_unbypass` → `button.home_zone_019_unbypass_music_room_door`
   - `binary_sensor.home_zone_020_bypass` → `binary_sensor.home_zone_020_bypass_braai_room_door`
   - `button.home_zone_020_bypass` → `button.home_zone_020_bypass_braai_room_door`
   - `button.home_zone_020_unbypass` → `button.home_zone_020_unbypass_braai_room_door`
   (`button.home_zone_019_bypass_music_room_door` is already correct. The package's
   template switches reference the normalised ids, so this step is mandatory.
   Deleting and re-adding the integration would also regenerate every id from the
   current names, but that rebuilds everything — targeted renames are safer.)
7. Rename the two panels (entity id *and* display name):
   - `alarm_control_panel.home_area_01_home` → `alarm_control_panel.home` ("Home")
   - `alarm_control_panel.home_area_02_flatlet` → `alarm_control_panel.flatlet` ("Flatlet")
8. Reload template entities (or restart once more) so the template switches bind to the
   renamed entities.

### Verify after cutover

- [ ] Both panels show correct state; arm/disarm from HA works without a code.
- [ ] Arm/disarm from the app/keypad/remote notifies (via "Alarm State Changed").
- [ ] No notification spam after an HA restart (unknown → state is filtered).
- [ ] Bypass switches reflect and control bypass state; "Arm (bypass garage)" from the
      notification works end to end.
- [ ] Stay-arm reminder lists active door zones (test via `script.test_active_zones`).
- [ ] HomeKit: both alarms still work in the Home app; night mode no longer offered
      (then delete the "Set To Stay If Night Mode Activated" automation).
- [ ] Presence flows (ask to arm when leaving, ask to disarm when arriving) fire.
- [ ] Panic button: hold shows the confirmation dialog and tap does nothing. Only
      confirm the dialog if the panic test is coordinated with the security company —
      confirming raises a real panic.

### After the soak period (a week or so of stable running)

- [ ] Delete the "Log Olarm Webhook Events" automation.
- [ ] Delete the webhook on Olarm's portal (user.olarm.com → API).
- [ ] Remove from `secrets.yaml`: `olarm_webhook_id`, `olarm_bearer_token`,
      `olarm_device_endpoint`, `olarm_actions_endpoint` (nothing references the REST
      API anymore; `alarm_code` stays — still used by the test panel and HomeKit).
- [ ] Delete `olarm.txt` (entity inventory snapshot) and this file, or fold what's left
      into the package header.
- [ ] Merge `olarm-migration` into `master`; `git worktree remove ../Home-Automation-olarm`.

## Still to do on this branch

- Done (phase 2): the zone sensors shown individually on the security view, grouped
  into a Door Zones and a Motion Zones glance card (state-coloured icons).
- Done (phase 3): panic button on the security and main views — hold plus a
  confirmation dialog pressing `button.home_user_panic` (tap deliberately disabled).
- Consider: `binary_sensor.home_ac_power` (panel mains) → `devices.yaml` monitoring.
- Consider: a bypass panel (the 14 `switch.alarm_bypass_*` entities) on the security view.
