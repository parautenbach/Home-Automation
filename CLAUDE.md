# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Is

A Home Assistant smart home configuration running in South Africa (Cape Town, Africa/Johannesburg timezone, ZAR currency). HA runs in Docker on a generic-x86-64 host. The config is entirely YAML-based (no GUI-managed automations); all entities, automations, scripts, and UI cards live in this repo.

## Managing Home Assistant

All management scripts live in `scripts/management/` and are run on the Docker host, not locally. The Docker container is named `homeassistant`, image `ghcr.io/home-assistant/generic-x86-64-homeassistant`, config at `/root/.homeassistant`.

```bash
scripts/management/upgrade_ha.sh [version]   # upgrade (auto-backs up config)
scripts/management/rollback_ha.sh            # roll back to :previous image
scripts/management/restart_ha.sh             # restart the container
scripts/management/tail_logs_ha.sh           # stream HA logs
scripts/management/docker_shell.sh           # open a shell in the container
```

There is no build step, linter, or test runner for the YAML config. Changes take effect after reloading or restarting HA. Use the **Test** dashboard (`ui-test.yaml`) and the `test.yaml` package for manual validation.

## ESPHome

Device configs are in `esphome/`. Each device has a `<device>.yaml` and optionally a directory of the same name for generated build artefacts. A shared `esphome/common.yaml` holds base substitutions and packages used by most devices. Flash/compile via the ESPHome CLI — not via scripts in this repo.

## Configuration Architecture

### Package System

`home_assistant/configuration.yaml` loads all packages with:
```yaml
packages: !include_dir_named packages
```
Each file in `home_assistant/packages/` is a self-contained domain slice (e.g. `lights.yaml`, `surveillance.yaml`, `olarm.yaml`). Entities, automations, scripts, sensors, and input helpers that belong to the same concern live together in one package file.

Key packages:
| Package | Concern |
|---|---|
| `home.yaml` | Human-facing routines: presence, wake-up/bedtime, sleep mode, guest/contractor modes |
| `devices.yaml` | Device/system health: battery levels, connectivity, availability, maintenance reminders |
| `lights.yaml` + `light_fader.yaml` | Light groups, motion triggers, gradual fading |
| `surveillance.yaml` | Cameras, motion detection/recording, snapshot gallery, doorbell motion tracking |
| `access.yaml` | Gates, garage doors, doorbell, cover timers/alerts, cabinet-opened |
| `safety.yaml` | Water and smoke detection, smoke detector testing reminders |
| `olarm.yaml` | Olarm alarm panel integration |
| `activity.yaml` | Pieter's driving/activity detection |
| `entertainment.yaml` | Apple TV, media players |
| `irrigation.yaml` | Irrigation scheduling and zones |
| `remotes.yaml` | IR/RF remote-control command scripts (Hi-Fi, DStv, etc.) |
| `work.yaml` | Workday sensors |
| `weather.yaml` | Weather: station telemetry (wind, rain, pressure, UV, illuminance), OpenWeatherMap forecast/alerts, fair-weather sensors |
| `marine.yaml` | Ocean conditions (Stormglass): tides, current, swell, wave, water temp |
| `astronomical.yaml` | Sun position/day-night sensors: Golden Hour, Nighttime/Daytime, Sun Angle, Daylight Length |
| `health.yaml` | Pollen and air quality (SAAQIS, OpenWeatherMap pollution) |
| `hazards.yaml` | Environmental risk indices — currently fire danger index; may grow to cover flood/storm/drought risk |
| `climate.yaml` | Indoor comfort telemetry: room temperature/humidity trends and stats, inside-vs-outside comparison |
| `dams.yaml` | Western Cape dam levels (scraped) |
| `resources.yaml` | Natural resource monitoring — currently solar/battery/grid energy; water and gas may join later |
| `internet.yaml` | Connectivity monitoring |
| `system.yaml` | System diagnostics, storage, uptime |
| `eskomsepush.yaml` | South African load-shedding (EskomSePush API) |
| `common.yaml` | Shared scripts and the polled-sensor update automation |
| `test.yaml` | Sandbox entities used during development |

`home.yaml` vs `devices.yaml`: the axis is audience, not subject. If a family member needs to know or do something as a result — a chore just finished, an appliance needs cleaning, someone's arriving or going to bed — it belongs in `home.yaml`. If only the person maintaining the smart-home system would care — battery level, connectivity, entity availability — it belongs in `devices.yaml`.

### Automation Conventions

Every automation must have a stable UUID as its `id` and a human-readable `alias`. Example:
```yaml
- alias: "Descriptive Name"
  id: "9faa1fce-c700-4ec2-87e4-d46c467c91f7"
  initial_state: true
```
Use `scripts/helpers/generate_uuid.sh` to generate a new UUID.

### Lovelace UI

Four YAML dashboards are declared in `configuration.yaml`:

| File | Dashboard | Notes |
|---|---|---|
| `ui-lovelace.yaml` | Overview | Main dashboard; includes views from `ui-lovelace/` |
| `ui-gallery.yaml` | Gallery | Camera snapshot gallery |
| `ui-system.yaml` | System | Admin-only system health view |
| `ui-test.yaml` | Test | Admin-only testing sandbox |

Views within the main dashboard are split into files under `ui-lovelace/` (e.g. `security.yaml`, `environment.yaml`). `ui-lovelace/resources.yaml` holds the large library of reusable `button_card_templates`.

`button_card_templates.yaml` contains global card templates used heavily throughout the dashboards.

HACS custom cards are loaded in `configuration.yaml` under `lovelace.resources`. All HACS files are served from `/hacsfiles/`.

### Custom Jinja2 Templates

Reusable Jinja2 macros live in `home_assistant/custom_templates/`. They are available anywhere in HA templates via `{% from 'utilities.jinja' import sec_to_hour_and_min %}`. Key files:

- `utilities.jinja` — time formatting (`sec_to_hour_and_min`), trigger-origin detection (`get_triggered_by_details`), entity-by-state queries (`get_entities_by_state`), integration label lookup
- `dynamic_colors.jinja` — colour generation for card theming
- `environment.jinja` — air quality / weather formatting helpers
- `security.jinja` — security state helpers

### Secrets

All credentials and location data are in `home_assistant/secrets.yaml` (git-ignored). Templates reference them with `!secret <key>`. Never hard-code values that belong in secrets.

### Blueprints

`home_assistant/blueprints/automation/` contains two Shelly button blueprints (`shelly_button.yaml`, `shelly_bt_button.yaml`) used to configure physical button behaviours without duplicating automation logic.

## Hardware Integrations

| System | Detail |
|---|---|
| Cameras | Amcrest, Raspberry Pi, Imou/Dahua; snapshots written to `/config/www/gallery/` |
| Alarm | Olarm panel (custom integration) |
| Smart switches | Shelly, Sonoff, TP-Link |
| Smart bulbs | Shelly, Sonoff, TP-Link |
| Sensors | Shelly, ESPHome, BTHome |
| Power/water | ESPHome pulse counter, Shelly |
| Load shedding | EskomSePush integration |
| Weather | OpenWeatherMap, Breezometer, SAAQIS (air quality) |
| iOS | Companion App, Apple Home, HomeKit bridges (port 21063 + camera bridges), Scriptable widgets |
| Network | SNMP for networking stats |
