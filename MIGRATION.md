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
- **Added**: two template alarm panels that wrap the integration's panels to require a
  code, taking over `alarm_control_panel.home` and `.flatlet`; 14 template switches
  (`switch.alarm_bypass_*`) wrapping the integration's bypass buttons + bypass state
  sensors; `homeassistant.customize` entries giving the motion zones a `device_class`
  and every real zone a clean, type-suffixed friendly name.
- **Reworked**: "Alarm State Changed" is pure notification logic (state from the
  integration is ground truth; names the person when HA context identifies one, and
  lists bypassed zones when arming); "Notify When Alarm Triggered" includes the
  `zone_in_alarm` attribute and disarms only the triggered partition; both are
  `mode: queued` (a panic can trigger both partitions at once); bypass-garage arming
  waits for the panel to confirm the bypass instead of a blind 5 s delay; service calls
  pass `code:` again, since the template panels require one.
- **Notification stacking fix** (`671d078`): the three senders sharing the
  `arm-alarm-reminder` tag now clear before sending, with a re-check after the gap,
  because iOS can neither replace nor group critical notifications. Also gave the living
  room lamp trigger an id, without which it could never satisfy the condition.
- **Temporary**: "Log Olarm Webhook Events" — passive, independent alarm/panic signal
  during the soak period. Touches no alarm entities.

**`home_assistant/custom_templates/security.jinja`** — `get_active_zones(partition, scope)`
is now partition-aware (`'home'`/`'flatlet'`), excludes bypassed zones, and filters doors
by device class; `get_bypassed_zones(partition)` resolves each bypassed zone back to its
zone sensor so the names match the rest of the UI; `get_ha_actor(context)` names the
person behind a state change when HA knows one. The partition→zone map lives here
(flatlet = zone 018; only the remote receiver channels 011/012 are ignored — an
unused zone that gets activated later announces itself rather than being silently
dropped).

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
   in notifications, and the entity IDs are already fixed regardless. (Zone 8 is
   "Bedroom", which is what this branch expects.)
2. Map the panic sources. The panel is an IDS X64 and the remotes are Sherlotronics, so
   the receivers are relay units wired into zone inputs (not the IDS bus receiver).

   **Zones 011/012 are almost certainly Arm/Disarm zones, not panic.** The X64 has a zone
   type for exactly this — type 05, Arm/Disarm: "Violation of an Arm/Disarm zone will
   cause the panel to toggle between (away) armed and disarmed. It is typical to connect
   a momentary key-switch, or non-latching remote control unit to this zone", with the
   note "A zone must be added to a partition in order for it to arm". That last line
   explains why there are exactly two, one per partition, which is what the P1/P2 labels
   say. Sherlo's own wiring diagram shows the receiver's relay COM/N.O. going to a panel
   zone input for "typical alarm panel wiring", while panic is a separate output.
   Panic on the X64 is a different zone type: 03 (Panic/Priority) or 12 (24 Hour Alarm).
   Caveat: type 05 toggles *away* armed only — if a remote can arm stay, it is wired some
   other way.

   So the two hard-wired panic buttons are likely on their own zone(s) programmed as
   type 03, plausibly among the unnamed zones (002, 014–016, 021–024).

   To confirm without pressing anything, cheapest first:
   - **HA history**: `binary_sensor.home_zone_011_p1_remotes` / `..._012_p2_remotes` have
     been recording since the integration was installed. Any past remote arm/disarm will
     show as a pulse there, next to the panel's state change. This needs no access to the
     panel at all.
   - **Olarm API**: the device endpoint's profile may expose zone types (the bearer token
     and endpoint are still in `secrets.yaml` until the post-soak cleanup).
   - **Panel event log**: past arm/disarm events already record the source, via the keypad
     or IDS Download software.
   - **Installer programming**: location 1 holds the zone type per zone
     (`[#][installer code][*]`, then `[1][*]`, then `[zone][*]`). Definitive, but that is
     programming mode on a live panel — read, do not change.

   If a panic source does map to an identifiable zone, use that sensor for per-partition
   panic detection in the trigger notification (panic vs breach — the last open item from
   the old integration's wishlist). The remotes zones stay excluded from the arming checks
   in `security.jinja` regardless: a receiver channel is not an open door or motion zone.
   (Unexplained: the March 2024 panic in the old webhook examples logged
   `EMERGENCY! - Area 4` and `Area 5` events.)

   References: [IDS X64 Installer Manual, Table 5, p.24](https://www.totalprotection.gr/uploads/product_0_1_2_13.pdf) ·
   [IDS X64 Remote Receiver Installer Manual](https://www.idsprotect.co.za/site-documents/product-download/intrusion/xseries/IDS%20X64%20Remote%20Receiver.pdf) ·
   [Sherlotronics RX1-500 installation manual](https://www.sherlotronics.co.za/wp-content/uploads/2020/03/RX1-500_Installation-manual_Revision-2020.pdf)
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

### Soak findings

**2026-08-28 — armed home from HA via `alarm_control_panel.home_test_area_01_home`:**

    state: armed_home
    code_format: null          code_arm_required: false
    changed_by: null           zone_in_alarm: null
    supported_features: 3

- Arming from HA works and needs no code — the `code:`-free service calls are correct.
- `supported_features: 3` is arm-home + arm-away only. So: no `armed_night` (the
  "Set To Stay If Night Mode Activated" automation is almost certainly dead code —
  confirm the Home app no longer offers night mode, then delete it), no
  `alarm_control_panel.alarm_trigger` (panic must go through `button.home_user_panic`,
  as built), and no custom bypass.
- `zone_in_alarm` null while merely armed is expected; it only means anything during an
  alarm.

**2026-08-28 — disarmed and armed stay from the Olarm app:** state followed correctly,
and `changed_by` was **still null**. Combined with the HA-initiated arm above, that is
two of the three sources confirmed null, so `changed_by` is dead for our purposes — the
old webhook's `userFullname` has no MQTT equivalent, which is a genuine regression from
the custom integration. Attribution now comes from the HA context instead
(`get_ha_actor` in `security.jinja`): a name when a person did it in HA, nothing
otherwise. Correlating the webhook's `userFullname` with the MQTT state change was
considered and rejected — two async channels, and `userFullname` was empty in six of the
seven captured webhook examples anyway.

Note the context can also be lost on a slow round trip through the panel, so a missing
name means "not known to be a person", never "it happened at the panel" — the message
omits the attribution rather than guessing. Worth watching during the soak: how often an
HA-initiated arm actually carries the user through.

**Parity confirmed:** the manual `alarm_control_panel.home` followed the new panel's
state via the old webhook, so both paths agree on a real event.

Still to test: force-arm with a zone open, and the panic (coordinate with the security
company).

**2026-09-02 — a real panic, and what the recorder shows.** The alarm was triggered at
07:58:09 (both partitions, 46 ms apart), disarmed at 07:58:14, and the old webhook sent
`EMERGENCY! - Panic` followed by one push per panel area, 1 through 8. Three things are
now settled:

- **Zones 011/012 are the arm/disarm channels, confirmed.** Zone 011 pulsed at
  07:58:12.9, 1.4 s before the disarm at 07:58:14.4 — a remote being used to disarm,
  exactly as the IDS type 05 (Arm/Disarm) reading of the manuals predicted. They stay
  excluded from the arming checks.
- **The panic circuit is invisible to Home Assistant.** No zone changed state at the
  trigger; the nearest activity was the garage PIR 21 s earlier. So a panic cannot be
  identified from zone sensors, now or later, and the unnamed spares are not panic
  inputs.
- **`zone_in_alarm` was null on both panels** — which is *correct* for a panic, since no
  zone was in alarm. Unlike `changed_by`, it is therefore unproven rather than dead, and
  is left in place: if it populates on a genuine zone breach, that becomes the
  panic-vs-breach distinction the webhook used to provide (a named zone means a breach,
  no zone means a panic).

The "Area 4"/"Area 5" oddity from the 2024 webhook captures is also explained: a panic
broadcasts to all eight areas the panel supports, of which only two are in use.

On the strength of the first two points the webhook was removed — it arrived *after* the
integration and cost eight critical pushes for one event.

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

   This removes the manual panels and frees the `home`/`flatlet` entity IDs. Expect
   errors and unavailable entities until the renames below are done.
5. In HA (Settings → Devices & Services → Olarm): rename the device
   **"Home Test" → "Home"** and accept the entity ID rename prompt (`home_test_*` →
   `home_*`). That prompt is a one-time offer and renames all of the device's entities
   at once; declining it means renaming ~100 entities by hand.
6. Reload template entities (or restart once more) so the template panels and switches
   bind to the renamed entities.

   (The zone 19/20 ids that used to lack their name suffix — the bypass sensors and
   three of the buttons — were regenerated on 2026-08-30 and now carry the full names,
   so no per-entity renames are needed. Verified: all 62 olarm entities the config
   references exist on the panel, modulo the `home_test` → `home` prefix.)

**No panel renames are needed.** The template alarm panels in `olarm.yaml` are named
"Home" and "Flatlet", so they take `alarm_control_panel.home` and `.flatlet`, and the
47 existing references across `olarm.yaml`, `home.yaml`, `security.yaml`, `homekit.yaml`
and `main.yaml` keep working untouched, HomeKit keeps its accessories (their ids derive
from the entity ID), and the recorder history stays continuous. The integration's own
panels stay at their generated ids and are only ever addressed by the template panels.

### Entities left behind

The 18 `input_boolean.alarm_zone_*_bypass` helpers, replaced by the bypass switches,
survived the config change as registry entries and had to be deleted by hand
(Settings → Devices & services → Entities, filter Status = Unavailable).

Automations removed in the same change did **not** need this — "Sync Alarm State" and
the renamed webhook automation left nothing behind, so HA prunes those itself. Verified
after the cutover: no alarm-related entity was left unavailable.

The manual alarm panels leave nothing behind either — the `manual` platform sets no
unique ID, so they were never registered, which is also why the template panels could
take `alarm_control_panel.home` and `.flatlet` straight over.

To check for strays:

    {{ states | selectattr('state', 'eq', 'unavailable')
       | map(attribute='entity_id') | select('search', 'alarm|olarm') | list }}

### Verify after cutover

- [ ] The template panels came up as `alarm_control_panel.home` and `.flatlet` (rename
      them if the ids were still taken when they first registered).
- [ ] Both panels show correct state, mirroring the integration's panels.
- [ ] Arm/disarm from the HA UI prompts for the code; a wrong code does nothing and logs
      a warning; the correct code works. Flatlet offers no stay mode.
- [ ] Automations still arm/disarm (they pass the code): the notification actions and
      the presence flows.
- [ ] Arming from the HA UI names you in the notification ("armed by Pieter"); arming
      from the app or keypad omits the name rather than claiming anything.
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
- [ ] HomeKit: both alarms still work in the Home app (entity IDs are unchanged, so the
      accessories should carry over); night mode no longer offered — then delete the
      "Set To Stay If Night Mode Activated" automation.
- [ ] Presence flows (ask to arm when leaving, ask to disarm when arriving) fire.
- [ ] Panic tile on both the main and security views: hold shows the confirmation dialog
      and tap does nothing. Only confirm the dialog if the panic test is coordinated with
      the security company — confirming raises a real panic.

### If it goes wrong

Everything is version-controlled YAML, so rollback is a deploy away:

1. Deploy `master` to the host and restart — the manual panels come back with their
   original entity IDs, and the REST/webhook automations resume.
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
