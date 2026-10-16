# Owlet Smart Sock for Home Assistant

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)

A modern, fully UI-configurable Home Assistant integration for the **Owlet
Smart Sock 2 and Smart Sock 3**. Sign in once from the UI and every sock on
your account is discovered automatically and exposed as rich sensors and
binary sensors — no YAML required.

This is a ground-up rewrite of
[`jlamendo/ha-sensor.owlet`](https://github.com/jlamendo/ha-sensor.owlet),
preserving its reverse-engineered Owlet/Ayla API logic while adding a config
flow, device discovery, a data update coordinator, and proper entities.

> [!WARNING]
> **This is not a medical device.** The Owlet Smart Sock and this integration
> must not be relied upon for medical monitoring or to detect life-threatening
> conditions. Do not use it to make health decisions. This project is
> unofficial and not affiliated with or endorsed by Owlet.

## Features

- 🔐 **UI login** — set up through *Settings → Devices & Services*, with a
  password prompt and automatic re-authentication when your session expires.
- 🧦 **Automatic discovery** — every sock on your account becomes a Home
  Assistant device with its own entities.
- 🌍 **World & Europe regions** supported.
- ❤️ **Smart Sock 2 and 3** supported (real-time vitals on the Sock 3).
- ⏱️ **Configurable polling interval** via the options flow (3–300 s).
- 🩺 Clean sensors and binary sensors (see below) with long-term statistics.

## Installation

### HACS (recommended)

1. In HACS, open the three-dot menu → **Custom repositories**.
2. Add `https://github.com/AlexShubovich/ha-owlet-integration` with category
   **Integration**.
3. Search for **Owlet Smart Sock**, install it, and restart Home Assistant.

### Manual

Copy `custom_components/owlet_smart_sock` into your Home Assistant
`config/custom_components` directory and restart Home Assistant.

### Running alongside the original `owlet` integration

This integration uses its own domain, **`owlet_smart_sock`**, and its own
folder (`custom_components/owlet_smart_sock`). It therefore installs and runs
**side by side** with the original
[`jlamendo/ha-sensor.owlet`](https://github.com/jlamendo/ha-sensor.owlet)
(domain `owlet`, configured in YAML) without overwriting it or conflicting with
its entities. Once you're happy with this integration you can remove the old
`sensor: - platform: owlet` block from your `configuration.yaml`.

## Configuration

1. Go to **Settings → Devices & Services → Add Integration**.
2. Search for **Owlet Smart Sock**.
3. Enter the email, password, and region for your Owlet account.

That's it — your socks and their entities appear automatically. To change how
often vitals are polled, open the integration and click **Configure**.

The Smart Sock streams real-time vitals roughly **every 3 seconds**, so the
update interval can be set anywhere from **3 to 300 seconds** (default: 10).
Polling faster than 3 seconds brings no fresher data — the minimum is capped at
3 seconds — while slower intervals reduce load on the Owlet cloud.

## Entities

Each sock is added as a device with the following entities:

### Sensors

| Entity | Description |
| --- | --- |
| Status | `monitoring`, `charging`, `charged`, `no_signal`, `disconnected`, or `error` |
| Heart rate | Beats per minute (while monitoring) |
| Oxygen saturation | SpO₂ % (while monitoring) |
| Movement | Movement % (while monitoring) |
| Battery | Battery % |
| Signal strength | BLE RSSI in dBm *(diagnostic, disabled by default)* |
| Last update | Timestamp of the most recent reading *(diagnostic, disabled by default)* |

### Binary sensors

| Entity | Device class | On means |
| --- | --- | --- |
| Monitoring | — | The sock is actively reading vitals |
| Charging | battery charging | The battery is actively charging |
| Base station | power | Base station is powered on *(diagnostic)* |
| Low battery alert | battery | Battery is low |
| High heart rate alert | problem | High heart-rate alert is active |
| Low heart rate alert | problem | Low heart-rate alert is active |
| Low oxygen alert | problem | Low oxygen alert is active |
| Sock connection | connectivity | The sock is connected |
| Low integrity reading | problem | The sock can't get a reliable reading *(diagnostic)* |

## Credits

This integration is based on the original
**[jlamendo/ha-sensor.owlet](https://github.com/jlamendo/ha-sensor.owlet)**
by [@jlamendo](https://github.com/jlamendo) — all of the Owlet/Ayla/Firebase
API logic and the Smart Sock 2/3 vitals parsing originate there. This project
reorganises that work into a modern, UI-configurable Home Assistant integration.

- Original integration and API reverse-engineering:
  [jlamendo/ha-sensor.owlet](https://github.com/jlamendo/ha-sensor.owlet).
- Underlying Owlet API work credited to
  [@mbevand](https://github.com/mbevand/owlet_monitor).

## License

[MIT](LICENSE)
