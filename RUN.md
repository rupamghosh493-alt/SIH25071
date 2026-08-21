# OpenPit / MindShield360-style Flask App

## Stack
- Python + Flask
- Flask-SQLAlchemy + SQLite
- Jinja2 templates
- HTML/CSS/JavaScript
- Bootstrap 5.3 CDN for responsive utilities/components
- Chart.js for dashboard charts

No React, Node.js, Vite or Tailwind CSS is required.

## Demo login
- Admin: `admin@gmail.com` / `admin123`
- Worker: `worker@gmail.com` / `worker123`

## Run
Create/activate a Python virtual environment, install `requirements.txt`, then run `python app.py`.

The bundled SQLite database is in `instance/slopesafe.db`. The application also creates/seeds the database automatically if tables/data are missing.

## CSV upload
Required columns:
- `fs`
- `reinforcement`

Optional columns:
- `timestamp`
- `zone`
- `displacement_mm`
- `rainfall_mm`
- `slope_angle`

The upload page now lets an administrator choose the target mine. Invalid rows abort the import instead of silently inserting partial data.
