# MindShield360 — SIH PS 25071 Flask Prototype

MindShield360 is a Flask + Jinja2 + SQLite prototype for **SIH Problem Statement 25071: AI-Based Rockfall Prediction and Alert System for Open-Pit Mines**.

The UI has been redesigned using the uploaded SIH presentation and the supplied MindShield360 reference screenshots as visual direction. It is intentionally **inspired by** those references, not a pixel-for-pixel copy.

## Stack
- Python
- Flask
- Flask-SQLAlchemy
- Jinja2 templates
- SQLite
- HTML / CSS / vanilla JavaScript
- Chart.js via CDN for dashboard charts
- No Streamlit
- No external API key required

## Run on Windows
```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

Or double-click `run_windows.bat`.

Then open: http://127.0.0.1:5000

## Demo access
The welcome page now leads to a role-selection login flow.

### Admin
- Password: `admin123`
- Full dashboard and monitoring access
- Manage Workers
- Data Upload
- Settings
- Alert creation / manual override

### Worker
- Password: `worker123`
- Dashboard
- Risk Map
- Alerts
- Sensors
- Analytics & Reports
- Mine Overview
- Scenario Lab
- AI Safety
- Help & Support

For the demo, the ID/email field accepts any non-empty value.

## Existing routes preserved
The original application routes are still present, including:
`/dashboard`, `/risk-map`, `/alerts`, `/sensors`, `/analytics`, `/mine`, `/upload`, `/scenario`, `/ai`, `/workers`, `/help`, `/settings`, and `/export`.

Additional routes were added only for role-based access: `/login` and `/logout`.

## Database
The database is created automatically at:
`instance/slopesafe.db`

Do not create the database manually. `models.py` contains the models and `db.create_all()` creates the SQLite tables when the application starts. Demo data is seeded automatically on the first run.

## Export CSV
There is **no static data.csv file required**. The Export CSV button generates a CSV from the current `SensorReading` records in the SQLite database and downloads it as `rockfall_assessment.csv`.

## CSV upload
Required columns: `fs`, `reinforcement`

Optional: `timestamp`, `zone`, `displacement_mm`, `rainfall_mm`, `slope_angle`.

## Feature basis
The SIH presentation describes a data-to-alert workflow, sensor health monitoring, fail-safe prediction, alert escalation, prediction explainability, worker safety, system health, ensemble AI, DEM/drone/geotechnical/environmental data, risk mapping, analytics, and auditable reports. The current prototype keeps the implemented features practical and demo-friendly while presenting them in a more polished Mission Control UI.

This is a hackathon/learning prototype. Real mine deployment requires validated geotechnical models, calibrated ML, real sensor integrations, domain-expert verification, and production security.
