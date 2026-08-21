from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file, session
from extensions import db
from datetime import datetime, timedelta
from pathlib import Path
from functools import wraps
import csv, io, random, math, os

BASE = Path(__file__).resolve().parent
INSTANCE = BASE / 'instance'
INSTANCE.mkdir(exist_ok=True)

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'slopesafe-demo-key')
app.config['SENSOR_API_KEY'] = os.environ.get('SENSOR_API_KEY', 'mindshield-demo-sensor-key')
app.config['SQLALCHEMY_DATABASE_URI'] = f"sqlite:///{INSTANCE / 'slopesafe.db'}"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

from models import Mine, Sensor, SensorReading, Alert, Worker, Prediction, Scenario
from risk_engine import assess_risk


def ensure_sensor_schema():
    """Apply the tiny migration needed by the live sensor pipeline.

    SQLAlchemy's create_all() does not add columns to an existing SQLite table,
    so the existing demo database needs this explicit, idempotent migration.
    """
    from sqlalchemy import text
    columns = db.session.execute(text("PRAGMA table_info(sensor_reading)")).fetchall()
    names = {row[1] for row in columns}
    if 'sensor_code' not in names:
        db.session.execute(text("ALTER TABLE sensor_reading ADD COLUMN sensor_code VARCHAR(30)"))
        db.session.commit()


def parse_sensor_timestamp(value):
    if not value:
        return datetime.now()
    try:
        value = str(value).strip()
        if value.endswith('Z'):
            value = value[:-1]
        parsed = datetime.fromisoformat(value)
        return parsed.replace(tzinfo=None) if parsed.tzinfo else parsed
    except (TypeError, ValueError):
        raise ValueError('timestamp must be ISO-8601, e.g. 2026-08-18T20:15:00')


def number(payload, key, minimum=None, maximum=None, default=0.0):
    raw = payload.get(key, default)
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise ValueError(f'{key} must be a number')
    if not math.isfinite(value):
        raise ValueError(f'{key} must be a finite number')
    if minimum is not None and value < minimum:
        raise ValueError(f'{key} cannot be below {minimum}')
    if maximum is not None and value > maximum:
        raise ValueError(f'{key} cannot be above {maximum}')
    return value


def seed_demo():
    # ---------------------------------------------------------
    # Create demo mines if they do not already exist
    # ---------------------------------------------------------
    mine_names = [
        ('Eastern Ridge Open Pit', 'Demo Mining Zone'),
        ('Dhanbad Open Pit', 'Dhanbad, Jharkhand'),
        ('North Valley Mine', 'North Mining Zone'),
        ('South Ridge Mine', 'South Mining Zone'),
        ('Central Coal Pit', 'Central Mining Zone'),
        ('Western Bench Mine', 'West Mining Zone'),
        ('Greenfield Open Pit', 'Greenfield Mining Zone'),
        ('Sunrise Mine', 'East Mining Zone'),
        ('Kalinga Open Pit', 'Kalinga Mining Zone'),
        ('Highland Mine', 'Highland Mining Zone')
    ]

    mines = []

    for name, location in mine_names:
        mine = Mine.query.filter_by(name=name).first()

        if not mine:
            mine = Mine(
                name=name,
                location=location,
                status='Operational'
            )
            db.session.add(mine)
            db.session.flush()

        mines.append(mine)

    zones = [
        'North Bench',
        'East Wall',
        'South Ramp',
        'West Bench'
    ]

    # ---------------------------------------------------------
    # FIX: Seed sensors and readings for ALL mines (not just main_mine)
    # ---------------------------------------------------------
    for m in mines:
        if not Sensor.query.filter_by(mine_id=m.id).first():

            for i in range(1, 9):
                sensor = Sensor(
                    code=f'S-{m.id}-{i:02}',
                    zone=zones[(i - 1) % 4],
                    sensor_type=[
                        'Displacement',
                        'Slope',
                        'Rainfall',
                        'Reinforcement'
                    ][i % 4],
                    status='Online' if i != 7 else 'Warning',
                    mine_id=m.id
                )
                db.session.add(sensor)

            db.session.flush()
            sensors_by_zone = {}
            for sensor in Sensor.query.filter_by(mine_id=m.id).order_by(Sensor.id).all():
                sensors_by_zone.setdefault(sensor.zone, []).append(sensor.code)

            # Generate 90 readings for each mine
            for i in range(90):
                ts = datetime.now() - timedelta(hours=89 - i)

                for j in range(4):
                    zone = zones[j]
                    trend = i / 90

                    fs = max(
                        .85,
                        1.72
                        - random.random() * .18
                        - trend * .28
                        - (.12 if zone == 'East Wall' else 0)
                    )

                    rein = max(
                        .12,
                        .72
                        - random.random() * .15
                        - trend * .16
                        - (.08 if zone == 'South Ramp' else 0)
                    )

                    disp = max(
                        .5,
                        3
                        + random.random() * 2
                        + trend * 10
                        + (4 if zone == 'East Wall' else 0)
                    )

                    rain = max(
                        0,
                        random.random() * 8
                        + (3 if i > 70 else 0)
                    )

                    zone_sensors = sensors_by_zone.get(zone, [])
                    reading = SensorReading(
                        timestamp=ts,
                        sensor_code=zone_sensors[i % len(zone_sensors)] if zone_sensors else None,
                        zone=zone,
                        fs=round(fs, 3),
                        reinforcement=round(rein, 3),
                        displacement_mm=round(disp, 2),
                        rainfall_mm=round(rain, 2),
                        slope_angle=round(
                            52 + random.random() * 16,
                            1
                        ),
                        mine_id=m.id
                    )

                    score, level, reasons = assess_risk(
                        reading.fs,
                        reading.reinforcement,
                        reading.displacement_mm,
                        reading.rainfall_mm,
                        reading.slope_angle
                    )

                    reading.risk_score = score
                    reading.risk_level = level

                    db.session.add(reading)

                    if (
                        i > 78
                        and score >= 60
                        and random.random() < .12
                    ):
                        db.session.add(
                            Alert(
                                title=f'{level} risk detected',
                                zone=zone,
                                severity=level,
                                status='Open',
                                message=(
                                    'Slope stability conditions crossed '
                                    'the monitoring threshold.'
                                ),
                                created_at=ts,
                                mine_id=m.id
                            )
                        )

    # ---------------------------------------------------------
    # Demo workers
    # ---------------------------------------------------------
    if not Worker.query.first():

        worker_data = [
            (
                'Arjun Kumar',
                'Supervisor',
                'North Bench'
            ),
            (
                'Riya Sen',
                'Geotechnical Engineer',
                'East Wall'
            ),
            (
                'Rahul Das',
                'Safety Officer',
                'South Ramp'
            ),
            (
                'Ananya Roy',
                'Operator',
                'West Bench'
            ),
            (
                'Vikram Singh',
                'Inspector',
                'North Bench'
            )
        ]

        for name, role, zone in worker_data:

            db.session.add(
                Worker(
                    name=name,
                    role=role,
                    zone=zone,
                    status='Active'
                )
            )

    db.session.commit()


@app.context_processor
def globals_():
    selected_mine = None
    open_alert_count = 0
    header_mines = Mine.query.order_by(Mine.name).all() if session.get('role') else []

    if session.get('role'):
        mine_id = request.args.get('mine', type=int)
        if mine_id:
            selected_mine = Mine.query.get(mine_id)

        if not selected_mine:
            selected_mine = (
                Mine.query.filter_by(
                    name='Central Coal Pit'
                ).first()
                or Mine.query.order_by(Mine.name).first()
            )

        if selected_mine:
            open_alert_count = Alert.query.filter_by(
                mine_id=selected_mine.id,
                status='Open'
            ).count()

    return {
        'now': datetime.now(),
        'current_role': session.get('role'),
        'current_user': session.get('user_name'),
        'header_mine': selected_mine,
        'header_mines': (
            Mine.query.order_by(Mine.name).all()
            if session.get('role')
            else []
        ),
        'open_alert_count': open_alert_count,
    }


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('role'):
            flash('Please choose Admin or Worker access first.', 'danger')
            return redirect(url_for('login'))
        return view(*args, **kwargs)
    return wrapped



def get_selected_mine():
    """Return the mine selected by the current request."""
    mine_id = request.args.get("mine", type=int)

    if mine_id:
        mine = Mine.query.get(mine_id)
        if mine:
            return mine

    central = Mine.query.filter_by(name='Central Coal Pit').first()
    return central or Mine.query.order_by(Mine.name).first()


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if session.get('role') != 'admin':
            flash('This section is available to administrators only.', 'danger')
            return redirect(url_for('dashboard'))
        return view(*args, **kwargs)
    return wrapped


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':

        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '').strip()

        # Demo accounts
        if email == 'admin@gmail.com' and password == 'admin123':
            session['role'] = 'admin'
            session['user_name'] = 'Administrator'

            flash('Signed in as Administrator.', 'success')
            return redirect(url_for('dashboard'))

        elif email == 'worker@gmail.com' and password == 'worker123':
            session['role'] = 'worker'
            session['user_name'] = 'Mine Safety Worker'

            flash('Signed in as Mine Safety Worker.', 'success')
            return redirect(url_for('dashboard'))

        else:
            flash('Invalid email or password.', 'danger')

    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out safely.', 'success')
    return redirect(url_for('home'))


@app.route('/dashboard')
@login_required
def dashboard():
    mines = Mine.query.order_by(Mine.name).all()

    mine_id = request.args.get('mine', type=int)
    selected_mine = Mine.query.get(mine_id) if mine_id else None

    if not selected_mine:
        selected_mine = (
            next((m for m in mines if m.name == 'Central Coal Pit'), None)
            or (mines[0] if mines else None)
        )

    source = request.args.get('source', 'all').lower()
    valid_sources = {'all', 'dem', 'drone', 'geotechnical', 'environmental'}
    if source not in valid_sources:
        source = 'all'

    readings_query = SensorReading.query
    if selected_mine:
        readings_query = readings_query.filter(
            SensorReading.mine_id == selected_mine.id
        )

    # Every demo reading contains all signal fields. The source tabs change the
    # dashboard emphasis without hiding otherwise valid monitoring records.
    readings = (
        readings_query
        .order_by(SensorReading.timestamp.desc())
        .limit(180)
        .all()
    )

    latest = readings[0] if readings else None
    latest_reasons = []
    if latest:
        _, _, latest_reasons = assess_risk(
            latest.fs,
            latest.reinforcement,
            latest.displacement_mm,
            latest.rainfall_mm,
            latest.slope_angle
        )

    # Latest reading for each real zone in the selected mine.
    zone_latest = {}
    for reading in readings:
        if reading.zone not in zone_latest:
            zone_latest[reading.zone] = reading

    zone_order = ['North Bench', 'East Wall', 'South Ramp', 'West Bench']
    zones = [(name, zone_latest.get(name)) for name in zone_order]

    alerts_query = Alert.query
    if selected_mine:
        alerts_query = alerts_query.filter(Alert.mine_id == selected_mine.id)

    alerts = (
        alerts_query
        .order_by(Alert.created_at.desc())
        .limit(5)
        .all()
    )

    sensors_query = Sensor.query
    if selected_mine:
        sensors_query = sensors_query.filter(Sensor.mine_id == selected_mine.id)

    sensor_total = sensors_query.count()
    online = sensors_query.filter_by(status='Online').count()
    warning_sensors = sensors_query.filter_by(status='Warning').count()

    high = sum(1 for r in readings if r.risk_score >= 60)
    critical = sum(1 for r in readings if r.risk_score >= 80)

    avg_risk = (
        round(sum(r.risk_score for r in readings) / len(readings), 1)
        if readings else 0
    )

    open_alerts = sum(1 for a in alerts if a.status == 'Open')

    # OPENPIT_DASHBOARD_MINES_V5
    # Show every existing database-backed mine on the dashboard.
    mine_summaries = []

    for mine in mines:

        latest_mine_reading = (
            SensorReading.query
            .filter_by(mine_id=mine.id)
            .order_by(SensorReading.timestamp.desc())
            .first()
        )

        mine_sensors = Sensor.query.filter_by(
            mine_id=mine.id
        )

        total_mine_sensors = mine_sensors.count()

        online_mine_sensors = mine_sensors.filter_by(
            status='Online'
        ).count()

        mine_open_alerts = Alert.query.filter_by(
            mine_id=mine.id,
            status='Open'
        ).count()

        mine_summaries.append({
            'id': mine.id,
            'name': mine.name,
            'location': mine.location or 'Location unavailable',
            'status': mine.status or 'Operational',
            'risk_score': (
                round(float(latest_mine_reading.risk_score), 1)
                if latest_mine_reading else 0
            ),
            'risk_level': (
                latest_mine_reading.risk_level
                if latest_mine_reading else 'No Data'
            ),
            'sensor_total': total_mine_sensors,
            'online': online_mine_sensors,
            'open_alerts': mine_open_alerts
        })

    return render_template(
        'dashboard.html',
        latest=latest,
        alerts=alerts,
        online=online,
        sensor_total=sensor_total,
        warning_sensors=warning_sensors,
        high=high,
        critical=critical,
        avg_risk=avg_risk,
        open_alerts=open_alerts,
        latest_reasons=latest_reasons,
        readings=list(reversed(readings)),
        zone_latest=zone_latest,
        zones=zones,
        mines=mines,
        selected_mine=selected_mine,
        selected_source=source,
        mine_summaries=mine_summaries
    )


@app.route('/risk-map')
@login_required
def risk_map():

    # =========================================================
    # RISK MAP HAS ITS OWN CLEAN MINE SELECTION.
    # Central Coal Pit is the default.
    # =========================================================

    mines = Mine.query.order_by(Mine.name).all()

    requested_id = request.args.get(
        'mine',
        type=int
    )

    selected_mine = None

    if requested_id:
        selected_mine = Mine.query.get(
            requested_id
        )

    if selected_mine is None:

        selected_mine = (
            Mine.query.filter_by(
                name='Central Coal Pit'
            ).first()
            or (
                mines[0]
                if mines
                else None
            )
        )

    zone_order = [
        'North Bench',
        'East Wall',
        'South Ramp',
        'West Bench'
    ]

    zone_latest = {}

    if selected_mine:

        readings = (
            SensorReading.query
            .filter(
                SensorReading.mine_id ==
                selected_mine.id
            )
            .order_by(
                SensorReading.timestamp.desc()
            )
            .all()
        )

        for reading in readings:

            if reading.zone not in zone_latest:

                zone_latest[
                    reading.zone
                ] = reading

    zones = [
        zone_latest.get(name)
        for name in zone_order
    ]

    zones = [
        z
        for z in zones
        if z is not None
    ]

    # ---------------------------------------------------------
    # Real summary values from database.
    # ---------------------------------------------------------

    low_count = sum(
        1
        for z in zones
        if str(z.risk_level).lower() == 'low'
    )

    moderate_count = sum(
        1
        for z in zones
        if str(z.risk_level).lower()
        in ('moderate', 'medium')
    )

    high_count = sum(
        1
        for z in zones
        if str(z.risk_level).lower() == 'high'
    )

    critical_count = sum(
        1
        for z in zones
        if str(z.risk_level).lower() == 'critical'
    )

    avg_rainfall = (
        sum(z.rainfall_mm for z in zones)
        / len(zones)
        if zones else 0
    )

    avg_slope = (
        sum(z.slope_angle for z in zones)
        / len(zones)
        if zones else 0
    )

    avg_movement = (
        sum(z.displacement_mm for z in zones)
        / len(zones)
        if zones else 0
    )

    sensors_query = Sensor.query

    if selected_mine:
        sensors_query = sensors_query.filter(
            Sensor.mine_id ==
            selected_mine.id
        )

    sensor_count = sensors_query.count()

    return render_template(
        'risk_map.html',

        mines=mines,

        selected_mine=selected_mine,

        zones=zones,

        low_count=low_count,

        moderate_count=moderate_count,

        high_count=high_count,

        critical_count=critical_count,

        avg_rainfall=avg_rainfall,

        avg_slope=avg_slope,

        avg_movement=avg_movement,

        sensor_count=sensor_count
    )


@app.route('/sensors')
@login_required
def sensors():
    selected_mine = get_selected_mine()
    sensor_query = Sensor.query
    reading_query = SensorReading.query

    if selected_mine:
        sensor_query = sensor_query.filter(Sensor.mine_id == selected_mine.id)
        reading_query = reading_query.filter(SensorReading.mine_id == selected_mine.id)

    sensor_rows = sensor_query.order_by(Sensor.code).all()
    readings = reading_query.order_by(SensorReading.timestamp.desc()).limit(50).all()

    # Build the latest reading for every physical sensor. Old databases may have
    # NULL sensor_code, so zone is used as a safe fallback for demo records.
    latest_by_sensor = {}
    latest_by_zone = {}
    all_readings = reading_query.order_by(SensorReading.timestamp.desc()).limit(500).all()
    for r in all_readings:
        if r.sensor_code and r.sensor_code not in latest_by_sensor:
            latest_by_sensor[r.sensor_code] = r
        if r.zone and r.zone not in latest_by_zone:
            latest_by_zone[r.zone] = r

    sensor_cards = []
    for sensor in sensor_rows:
        latest = latest_by_sensor.get(sensor.code) or latest_by_zone.get(sensor.zone)
        sensor_cards.append({
            'id': sensor.id,
            'code': sensor.code,
            'zone': sensor.zone or 'Unassigned',
            'sensor_type': sensor.sensor_type or 'Geotechnical',
            'status': sensor.status or 'Offline',
            'latest': latest,
        })

    return render_template(
        'sensors.html',
        sensors=sensor_cards,
        readings=readings,
        selected_mine=selected_mine
    )


@app.route('/api/sensors/live')
@login_required
def api_sensors_live():
    selected_mine = get_selected_mine()
    if not selected_mine:
        return jsonify({'ok': False, 'message': 'No mine available'}), 404

    sensors = Sensor.query.filter_by(mine_id=selected_mine.id).order_by(Sensor.code).all()
    readings = (SensorReading.query
                .filter_by(mine_id=selected_mine.id)
                .order_by(SensorReading.timestamp.desc())
                .limit(500).all())

    latest_by_sensor = {}
    latest_by_zone = {}
    for r in readings:
        if r.sensor_code and r.sensor_code not in latest_by_sensor:
            latest_by_sensor[r.sensor_code] = r
        if r.zone and r.zone not in latest_by_zone:
            latest_by_zone[r.zone] = r

    rows = []
    for sensor in sensors:
        r = latest_by_sensor.get(sensor.code) or latest_by_zone.get(sensor.zone)
        rows.append({
            'id': sensor.id,
            'code': sensor.code,
            'zone': sensor.zone or 'Unassigned',
            'sensor_type': sensor.sensor_type or 'Geotechnical',
            'status': sensor.status or 'Offline',
            'reading': ({
                'timestamp': r.timestamp.isoformat(),
                'fs': round(float(r.fs), 3),
                'reinforcement': round(float(r.reinforcement), 3),
                'displacement_mm': round(float(r.displacement_mm or 0), 2),
                'rainfall_mm': round(float(r.rainfall_mm or 0), 2),
                'slope_angle': round(float(r.slope_angle or 0), 1),
                'risk_score': round(float(r.risk_score or 0), 1),
                'risk_level': r.risk_level or 'Low'
            } if r else None)
        })

    return jsonify({
        'ok': True,
        'server_time': datetime.now().isoformat(),
        'mine': {'id': selected_mine.id, 'name': selected_mine.name},
        'sensors': rows
    })


@app.route('/api/sensors/reading', methods=['POST'])
def api_sensor_reading():
    """Receive one telemetry packet from ESP32/Arduino/gateway software."""
    supplied_key = request.headers.get('X-Sensor-Key') or request.args.get('key')
    if supplied_key != app.config['SENSOR_API_KEY']:
        return jsonify({'ok': False, 'message': 'Invalid sensor API key'}), 401

    payload = request.get_json(silent=True) or {}
    sensor_code = str(payload.get('sensor_code') or payload.get('code') or '').strip()
    if not sensor_code:
        return jsonify({'ok': False, 'message': 'sensor_code is required'}), 400

    sensor = Sensor.query.filter_by(code=sensor_code).first()
    if not sensor:
        return jsonify({'ok': False, 'message': f'Unknown sensor: {sensor_code}'}), 404

    try:
        fs = number(payload, 'fs', 0, 10)
        reinforcement = number(payload, 'reinforcement', 0, 10)
        displacement = number(payload, 'displacement_mm', 0, 10000)
        rainfall = number(payload, 'rainfall_mm', 0, 10000)
        slope = number(payload, 'slope_angle', 0, 90)
        timestamp = parse_sensor_timestamp(payload.get('timestamp'))
    except ValueError as exc:
        return jsonify({'ok': False, 'message': str(exc)}), 400

    score, level, reasons = assess_risk(
        fs, reinforcement, displacement, rainfall, slope
    )

    reading = SensorReading(
        timestamp=timestamp,
        sensor_code=sensor.code,
        zone=sensor.zone,
        fs=round(fs, 3),
        reinforcement=round(reinforcement, 3),
        displacement_mm=round(displacement, 2),
        rainfall_mm=round(rainfall, 2),
        slope_angle=round(slope, 1),
        risk_score=score,
        risk_level=level,
        mine_id=sensor.mine_id
    )
    db.session.add(reading)

    # Keep the physical node status in sync with the latest risk state.
    sensor.status = 'Warning' if level in {'High', 'Critical'} else 'Online'

    # Avoid creating an alert on every telemetry packet.
    if level in {'High', 'Critical'}:
        existing = (Alert.query
                    .filter_by(mine_id=sensor.mine_id, zone=sensor.zone, status='Open')
                    .first())
        if not existing:
            db.session.add(Alert(
                title=f'{level} risk detected by {sensor.code}',
                zone=sensor.zone,
                severity=level,
                status='Open',
                message='Live sensor telemetry crossed the monitoring threshold.'
                        + (f" {'; '.join(reasons)}." if reasons else ''),
                created_at=timestamp,
                mine_id=sensor.mine_id
            ))

    db.session.commit()

    return jsonify({
        'ok': True,
        'message': 'Sensor reading accepted',
        'sensor': sensor.code,
        'mine_id': sensor.mine_id,
        'timestamp': timestamp.isoformat(),
        'risk_score': score,
        'risk_level': level,
        'reasons': reasons
    }), 201


@app.route('/alerts', methods=['GET','POST'])
@login_required
def alerts():
    selected_mine = get_selected_mine()

    if request.method == 'POST':
        mine_id = request.form.get('mine_id', type=int) or (selected_mine.id if selected_mine else None)
        if not mine_id or not Mine.query.get(mine_id):
            flash('Please select a valid mine before creating an alert.', 'danger')
            return redirect(url_for('alerts'))

        severity = request.form.get('severity', 'Moderate').strip().title()
        if severity not in {'Low', 'Moderate', 'High', 'Critical'}:
            severity = 'Moderate'

        alert = Alert(
            title=request.form.get('title', 'Manual safety alert').strip() or 'Manual safety alert',
            zone=request.form.get('zone', 'Unknown').strip() or 'Unknown',
            severity=severity,
            status='Open',
            message=request.form.get('message', '').strip(),
            created_at=datetime.now(),
            mine_id=mine_id
        )
        db.session.add(alert)
        db.session.commit()
        flash('Alert created successfully.', 'success')
        return redirect(url_for('alerts', mine=mine_id))

    query = Alert.query.order_by(Alert.created_at.desc())
    if selected_mine:
        query = query.filter(Alert.mine_id == selected_mine.id)

    rows = query.all()
    return render_template(
        'alerts.html',
        alerts=rows,
        selected_mine=selected_mine
    )


@app.route('/alerts/<int:alert_id>/close', methods=['POST'])
@login_required
def close_alert(alert_id):
    alert = Alert.query.get_or_404(alert_id)
    alert.status = 'Closed'
    db.session.commit()
    flash('Alert closed.', 'success')
    return redirect(url_for('alerts', mine=alert.mine_id) if alert.mine_id else url_for('alerts'))


@app.route('/analytics')
@login_required
def analytics():
    selected_mine = get_selected_mine()

    query = SensorReading.query

    if selected_mine:
        query = query.filter(
            SensorReading.mine_id == selected_mine.id
        )

    readings = (
        query
        .order_by(SensorReading.timestamp)
        .all()
    )

    return render_template(
        'analytics.html',
        readings=readings,
        selected_mine=selected_mine
    )


@app.route('/mine')
@login_required
def mine():
    selected_mine = get_selected_mine()

    workers = Worker.query.order_by(
        Worker.name
    ).all()

    sensor_query = Sensor.query

    if selected_mine:
        sensor_query = sensor_query.filter(
            Sensor.mine_id == selected_mine.id
        )

    sensors = sensor_query.order_by(
        Sensor.code
    ).all()

    return render_template(
        'mine.html',
        mine=selected_mine,
        workers=workers,
        sensors=sensors
    )


@app.route('/upload', methods=['GET','POST'])
@admin_required
def upload():
    selected_mine = get_selected_mine()
    if request.method == 'POST':
        file = request.files.get('file')
        if not file or not file.filename:
            flash('Choose a CSV file first.', 'danger')
            return redirect(url_for('upload', mine=selected_mine.id if selected_mine else None))
        try:
            if not selected_mine:
                raise ValueError('No mine is selected')
            content = file.read().decode('utf-8-sig')
            reader = csv.DictReader(io.StringIO(content))
            required = {'fs', 'reinforcement'}
            if not required.issubset(set(reader.fieldnames or [])):
                raise ValueError('CSV must contain fs and reinforcement columns')
            count = 0
            for row in reader:
                fs = number(row, 'fs', 0, 10)
                rein = number(row, 'reinforcement', 0, 10)
                disp = number(row, 'displacement_mm', 0, 10000, 0)
                rain = number(row, 'rainfall_mm', 0, 10000, 0)
                slope = number(row, 'slope_angle', 0, 90, 55)
                ts = parse_sensor_timestamp(row.get('timestamp'))
                code = (row.get('sensor_code') or '').strip() or None
                if code and not Sensor.query.filter_by(code=code, mine_id=selected_mine.id).first():
                    raise ValueError(f'Unknown sensor_code for selected mine: {code}')
                score, level, _ = assess_risk(fs, rein, disp, rain, slope)
                db.session.add(SensorReading(
                    timestamp=ts, sensor_code=code, zone=row.get('zone', 'Imported Zone'),
                    fs=fs, reinforcement=rein, displacement_mm=disp, rainfall_mm=rain,
                    slope_angle=slope, risk_score=score, risk_level=level, mine_id=selected_mine.id
                ))
                count += 1
            db.session.commit()
            flash(f'{count} readings imported and assessed for {selected_mine.name}.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Upload error: {e}', 'danger')
        return redirect(url_for('upload', mine=selected_mine.id if selected_mine else None))
    return render_template('upload.html', selected_mine=selected_mine)


@app.route('/scenario', methods=['GET','POST'])
@login_required
def scenario():
    result=None
    if request.method=='POST':
        fs=float(request.form['fs']); rein=float(request.form['reinforcement']); disp=float(request.form['displacement_mm']); rain=float(request.form['rainfall_mm']); slope=float(request.form['slope_angle'])
        score,level,reasons=assess_risk(fs,rein,disp,rain,slope)
        result={'score':score,'level':level,'reasons':reasons,'fs':fs,'rein':rein,'disp':disp,'rain':rain,'slope':slope}
        db.session.add(Prediction(timestamp=datetime.now(),fs=fs,reinforcement=rein,displacement_mm=disp,rainfall_mm=rain,slope_angle=slope,risk_score=score,risk_level=level,source='Scenario')); db.session.commit()
    return render_template('scenario.html', result=result)


@app.route('/ai')
@login_required
def ai():
    selected_mine = get_selected_mine()

    query = SensorReading.query

    if selected_mine:
        query = query.filter(
            SensorReading.mine_id == selected_mine.id
        )

    readings = (
        query
        .order_by(SensorReading.risk_score.desc())
        .all()
    )

    worst = readings[0] if readings else None

    return render_template(
        'ai.html',
        worst=worst,
        selected_mine=selected_mine
    )


@app.route('/workers', methods=['GET','POST'])
@admin_required
def workers():
    if request.method=='POST':
        db.session.add(Worker(name=request.form['name'],role=request.form['role'],zone=request.form['zone'],status='Active')); db.session.commit(); flash('Worker added.','success'); return redirect(url_for('workers'))
    return render_template('workers.html', workers=Worker.query.order_by(Worker.name).all())


@app.route('/help')
@login_required
def help_page(): return render_template('help.html')


@app.route('/settings')
@login_required
def settings(): return render_template('settings.html')


@app.route('/export')
@login_required
def export():
    selected_mine = get_selected_mine()

    query = SensorReading.query

    if selected_mine:
        query = query.filter(
            SensorReading.mine_id == selected_mine.id
        )

    rows = query.order_by(
        SensorReading.timestamp
    ).all()
    out=io.StringIO(); w=csv.writer(out); w.writerow(['timestamp','zone','fs','reinforcement','displacement_mm','rainfall_mm','slope_angle','risk_score','risk_level'])
    for r in rows: w.writerow([r.timestamp,r.zone,r.fs,r.reinforcement,r.displacement_mm,r.rainfall_mm,r.slope_angle,r.risk_score,r.risk_level])
    mem=io.BytesIO(out.getvalue().encode()); mem.seek(0)
    return send_file(mem, mimetype='text/csv', as_attachment=True, download_name='rockfall_assessment.csv')




@app.route('/api/overview')
@login_required
def api_overview():
    selected_mine = get_selected_mine()

    if not selected_mine:
        return jsonify({
            'ok': False,
            'message': 'No mine available'
        }), 404

    readings = (
        SensorReading.query
        .filter_by(mine_id=selected_mine.id)
        .order_by(SensorReading.timestamp.desc())
        .limit(180)
        .all()
    )

    sensors = Sensor.query.filter_by(
        mine_id=selected_mine.id
    )

    alerts = Alert.query.filter_by(
        mine_id=selected_mine.id,
        status='Open'
    ).count()

    latest_by_zone = {}

    for reading in readings:
        if reading.zone not in latest_by_zone:
            latest_by_zone[reading.zone] = reading

    return jsonify({
        'ok': True,
        'mine': {
            'id': selected_mine.id,
            'name': selected_mine.name,
            'location': selected_mine.location,
            'status': selected_mine.status
        },
        'summary': {
            'risk': round(
                sum(r.risk_score for r in readings) / len(readings), 1
            ) if readings else 0,
            'high': sum(
                1 for r in readings if r.risk_score >= 60
            ),
            'critical': sum(
                1 for r in readings if r.risk_score >= 80
            ),
            'alerts': alerts,
            'sensors': sensors.count(),
            'online': sensors.filter_by(
                status='Online'
            ).count(),
            'warning': sensors.filter_by(
                status='Warning'
            ).count()
        },
        'zones': [
            {
                'zone': r.zone,
                'risk_score': round(r.risk_score, 1),
                'risk_level': r.risk_level,
                'displacement_mm': round(
                    r.displacement_mm, 2
                ),
                'factor_of_safety': round(
                    r.fs, 3
                ),
                'reinforcement': round(
                    r.reinforcement, 3
                ),
                'rainfall_mm': round(
                    r.rainfall_mm, 2
                ),
                'slope_angle': round(
                    r.slope_angle, 1
                ),
                'timestamp': r.timestamp.isoformat()
            }
            for r in latest_by_zone.values()
        ]
    })


with app.app_context():
    db.create_all()
    ensure_sensor_schema()
    seed_demo()

if __name__=='__main__':
    app.run(debug=True)