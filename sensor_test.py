"""Send one fake telemetry packet to MindShield360 for testing the live pipeline."""
import json
from urllib.request import Request, urlopen

URL = "http://127.0.0.1:5000/api/sensors/reading"
API_KEY = "mindshield-demo-sensor-key"

payload = {
    "sensor_code": "S-5-01",  # Central Coal Pit demo sensor
    "fs": 1.42,
    "reinforcement": 0.58,
    "displacement_mm": 7.4,
    "rainfall_mm": 3.2,
    "slope_angle": 61
}

body = json.dumps(payload).encode("utf-8")
request = Request(
    URL,
    data=body,
    method="POST",
    headers={
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-Sensor-Key": API_KEY,
    },
)

try:
    with urlopen(request, timeout=10) as response:
        print(response.status)
        print(response.read().decode("utf-8"))
except Exception as exc:
    print("Sensor test failed:", exc)
    print("Make sure Flask is running with: python app.py")
