from extensions import db

class Mine(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),nullable=False)
    location=db.Column(db.String(200))
    status=db.Column(db.String(30),default='Operational')

class Sensor(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    code=db.Column(db.String(30),unique=True,nullable=False)
    zone=db.Column(db.String(100))
    sensor_type=db.Column(db.String(50))
    status=db.Column(db.String(30),default='Online')
    mine_id=db.Column(db.Integer,db.ForeignKey('mine.id'))

class SensorReading(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    timestamp=db.Column(db.DateTime,nullable=False)
    sensor_code=db.Column(db.String(30),db.ForeignKey('sensor.code'),nullable=True,index=True)
    zone=db.Column(db.String(100))
    fs=db.Column(db.Float,nullable=False)
    reinforcement=db.Column(db.Float,nullable=False)
    displacement_mm=db.Column(db.Float,default=0)
    rainfall_mm=db.Column(db.Float,default=0)
    slope_angle=db.Column(db.Float,default=55)
    risk_score=db.Column(db.Float,default=0)
    risk_level=db.Column(db.String(30),default='Low')
    mine_id=db.Column(db.Integer,db.ForeignKey('mine.id'))

class Alert(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    title=db.Column(db.String(160))
    zone=db.Column(db.String(100))
    severity=db.Column(db.String(30))
    status=db.Column(db.String(30),default='Open')
    message=db.Column(db.Text)
    created_at=db.Column(db.DateTime,nullable=False)
    mine_id=db.Column(db.Integer,db.ForeignKey('mine.id'))

class Worker(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120),nullable=False)
    role=db.Column(db.String(100))
    zone=db.Column(db.String(100))
    status=db.Column(db.String(30),default='Active')

class Prediction(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    timestamp=db.Column(db.DateTime,nullable=False)
    fs=db.Column(db.Float)
    reinforcement=db.Column(db.Float)
    displacement_mm=db.Column(db.Float)
    rainfall_mm=db.Column(db.Float)
    slope_angle=db.Column(db.Float)
    risk_score=db.Column(db.Float)
    risk_level=db.Column(db.String(30))
    source=db.Column(db.String(50))

class Scenario(db.Model):
    id=db.Column(db.Integer,primary_key=True)
    name=db.Column(db.String(120))
    created_at=db.Column(db.DateTime)
