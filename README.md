# Solar Web Public

Custom integration for Home Assistant to monitor Fronius Solar.web public/shared plant pages.

This integration does **not** require Solar.web username, password, token login, or API credentials.

It works with the public display URL generated from a Solar.web account, for example:

`https://www.solarweb.com/PublicDisplay?token=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`

## Features

- No Solar.web login required
- No credentials stored in Home Assistant
- One public URL = one monitored plant
- Main plant status sensor with rich attributes
- Separate Home Assistant sensors for:
  - Current PV power
  - Production power
  - Consumption power
  - Grid power
  - Feed-in power
  - Grid import power
  - Battery power
  - Battery state of charge
  - Daily energy
  - Monthly energy
  - Yearly energy
  - Total energy
  - Daily grid export energy
  - Daily grid import energy
  - Earnings today
  - Earnings month
  - Earnings year
  - Earnings total
- Diagnostics
- Tested data source

## Supported Solar.web endpoints

The integration reads public Solar.web endpoints exposed by the shared display page:

- `/PublicDisplay/PvSystem?token=...`
- `/ActualData/GetCompareDataForPublicDisplay?PublicDisplayToken=...`
- `/PvSystems/GetPvSystemProductionsAndEarningsForPublicDisplay?token=...`
- `/Chart/GetWidgetChartForPublicDisplay?publicDisplayToken=...`

## Installation

### HACS custom repository

1. Open HACS
2. Go to `Integrations`
3. Open the three-dot menu
4. Select `Custom repositories`
5. Add your repository URL
6. Set `Category` to `Integration`
7. Install `Solar Web Public`
8. Restart Home Assistant

### Manual installation

Copy this folder:

`custom_components/solar_web_public`

into:

`/config/custom_components/solar_web_public`

Then restart Home Assistant.

## Configuration

1. Go to `Settings → Devices & services → Add integration`
2. Search for `Solar Web Public`
3. Enter the following fields:

| Field | Description |
|---|---|
| Plant name | Friendly name used in Home Assistant |
| Shared URL | Solar.web public display URL |
| Refresh interval | Update interval in seconds |

Recommended refresh interval: `300` seconds.

## Example entities

For a plant named `NAME_ID`, Home Assistant may create entities like:

- `sensor.NAME_ID`
- `sensor.NAME_ID_potenza_attuale`
- `sensor.NAME_ID_potenza_produzione`
- `sensor.NAME_ID_potenza_consumo`
- `sensor.NAME_ID_potenza_rete`
- `sensor.NAME_ID_potenza_immessa_in_rete`
- `sensor.NAME_ID_potenza_prelevata_dalla_rete`
- `sensor.NAME_ID_potenza_batteria`
- `sensor.NAME_ID_batteria`
- `sensor.NAME_ID_energia_oggi`
- `sensor.NAME_ID_energia_mese`
- `sensor.NAME_ID_energia_anno`
- `sensor.NAME_ID_energia_totale`
- `sensor.NAME_ID_energia_immessa_oggi`
- `sensor.NAME_ID_energia_prelevata_oggi`
- `sensor.NAME_ID_guadagno_oggi`
- `sensor.NAME_ID_guadagno_mese`
- `sensor.NAME_ID_guadagno_anno`
- `sensor.NAME_ID_guadagno_totale`
- `sensor.NAME_ID_diagnostica`

> Entity names may vary depending on your Home Assistant language and entity registry.

## Main sensor attributes

The main plant sensor exposes useful attributes such as:

- `plant_name`: `NAME_ID`
- `location`: `LOCATION`
- `status`: `online`
- `is_online`: `true`
- `peak_power_wp`: `8260`
- `current_power_w`: `6256`
- `production_w`: `6256`
- `consumption_w`: `658`
- `grid_power_w`: `-5606`
- `feed_in_w`: `5606`
- `energy_from_grid_w`: `0`
- `battery_power_w`: `8`
- `battery_soc`: `100`
- `today_energy_kwh`: `25.74`
- `month_energy_kwh`: `334.91`
- `year_energy_kwh`: `3322.98`
- `total_energy_kwh`: `17210`
- `today_earning`: `2.06`
- `earning_currency`: `EUR`

## Grid power sign convention

The public Solar.web endpoint exposes grid power as:

- `negative` = export/feed-in to grid
- `positive` = import from grid

This integration also creates separate positive-only sensors for:

- `Potenza immessa in rete`
- `Potenza prelevata dalla rete`

## Privacy

The Solar.web public display token is not a username/password credential, but anyone with the URL can view the shared public page.

Do not publish real public display tokens in screenshots, issues, examples, or documentation.

## Current limitations

- Depends on Solar.web public endpoints, which are not officially documented for third-party use.
- If Fronius changes the public display page or endpoint names, the integration may need updates.
- Battery values are available only when Solar.web exposes them for that plant.
- Earnings depend on Solar.web plant configuration.

## Development status

Current version: `0.3.0`

Early but functional.

---

# `hacs.json`

```json
{
  "name": "Solar Web Public",
  "render_readme": true,
  "homeassistant": "2025.1.0",
  "domains": ["sensor"],
  "iot_class": "cloud_polling"
}
