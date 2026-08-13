# Home-Automation

A YAML-driven [Home Assistant](https://www.home-assistant.io/) configuration for a smart home — plus the firmware, scripts, and supporting services that run alongside it. No GUI-managed automations: every entity, automation, script, and dashboard card is version-controlled here.

## Repository layout

| Path | What's in it |
|---|---|
| `home_assistant/` | The HA config itself — packages, dashboards, Jinja2 templates, blueprints |
| `esphome/` | Firmware configs for ESPHome devices (garage doors, gate, irrigation, pulse counters, etc.) |
| `scripts/` | Host-side management, deployment, and helper scripts, organised by target (`management/`, `server/`, `rpi/`, `mac/`, `networking/`, `db/`, `helpers/`) |
| `homebridge/` | Homebridge config for HomeKit bridging |
| `weewx/` | weewx weather station configuration |
| `shairport-sync/` | AirPlay receiver configuration |
| `scriptable/` | iOS Scriptable widgets (energy, load shedding) |
| `docs/` | Reference notes, pinouts, and API docs used while building the system |

## Home Assistant configuration

HA runs in Docker (`ghcr.io/home-assistant/generic-x86-64-homeassistant`) on a generic x86-64 host, with config mounted at `/root/.homeassistant`. The config loads every file under `home_assistant/packages/` as a self-contained domain package:

```yaml
packages: !include_dir_named packages
```

Each package groups the entities, automations, scripts, and sensors for one concern — lights, security, irrigation, weather, dams, load-shedding, and so on — so related logic lives together instead of being split across HA's default domain-first folders. See `home_assistant/packages/` and [CLAUDE.md](CLAUDE.md) for the full package breakdown.

Dashboards live under `home_assistant/ui-lovelace*.yaml` and `home_assistant/ui-lovelace/`, all hand-written YAML (no UI editor).

### Managing the running instance

Management scripts run on the Docker host itself, not locally, with support for backups and image tagging:

```bash
scripts/management/upgrade_ha.sh [version]   # upgrade (auto-backs up config)
scripts/management/rollback_ha.sh            # roll back to the previous image
scripts/management/restart_ha.sh             # restart the container
scripts/management/tail_logs_ha.sh           # stream HA logs
scripts/management/docker_shell.sh           # open a shell in the container
```

There's no build step, linter, or test suite for the YAML — changes take effect on reload/restart. A dedicated **Test** dashboard (`ui-test.yaml`) backed by the `test.yaml` package is used for manual validation before rolling changes into the real packages.

## ESPHome devices

Each device under `esphome/` has its own `<device>.yaml`, sharing common substitutions and packages from `esphome/common.yaml`. Devices are flashed/compiled via the ESPHome CLI, not through scripts in this repo.

## Hardware, integrations and APIs

| System | Detail |
|---|---|
| Cameras | Amcrest, Raspberry Pi, Imou/Dahua |
| Alarm | Olarm panel (custom integration) |
| Smart switches | Shelly, Sonoff, TP-Link |
| Smart bulbs | Shelly, Sonoff, TP-Link |
| Sensors | Shelly, ESPHome, BTHome |
| Power/water | ESPHome pulse counter, Shelly |
| Load shedding | EskomSePush API |
| Weather | OpenWeatherMap, Breezometer, SAAQIS, Stormglass (marine) |
| iOS | Companion App, Apple Home, HomeKit bridges and Scriptable widgets |
| Network | SNMP for networking stats |

## Secrets

Credentials and location data live in `home_assistant/secrets.yaml`, which is git-ignored. Templates reference values with `!secret <key>` — never commit real credentials in their place.

## More detail

[CLAUDE.md](CLAUDE.md) has the deeper architectural notes (package responsibilities, automation conventions, Jinja2 macro reference) written for AI-assisted development on this repo, but it doubles as the most complete internal reference for how the config is organised.
