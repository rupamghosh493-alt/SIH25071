# MindShield360 — Live Sensor Setup

## What was fixed

- The Sensors page now has dedicated responsive CSS instead of relying on unrelated `.ms-*` styles.
- CSS cache-busting was added so an old `style.css` is not silently reused by the browser.
- The Sensors page polls `/api/sensors/live` every 5 seconds.
- New readings are stored against the actual `sensor_code` and selected mine.
- Sensor status changes automatically to `Warning` for High/Critical risk and `Online` otherwise.
- High/Critical live telemetry creates an open alert only when one is not already open for that zone.
- Existing SQLite databases are migrated automatically with the new `sensor_code` column.
- CSV upload no longer writes everything to hard-coded `mine_id=1`.

## Hardware API

POST JSON to:

    /api/sensors/reading

Required header:

    X-Sensor-Key: mindshield-demo-sensor-key

Example JSON:

```json
{
  "sensor_code": "S-5-01",
  "fs": 1.42,
  "reinforcement": 0.58,
  "displacement_mm": 7.4,
  "rainfall_mm": 3.2,
  "slope_angle": 61
}
```

The development key is only a local/demo default. Before deployment set `SENSOR_API_KEY` in the environment.

## Quick test without hardware

1. Start Flask with `python app.py`.
2. Keep the server running.
3. Run `python sensor_test.py` from the project folder.
4. Open the Sensors page and watch the card for `S-5-01` update.

The test script uses only Python's standard library.
