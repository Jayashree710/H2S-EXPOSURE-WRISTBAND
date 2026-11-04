from . import db

class CalibrationPoint(db.Model):
    __tablename__ = 'calibration_points'

    id = db.Column(db.Integer, primary_key=True)
    exposure_value = db.Column(db.Float, nullable=False, index=True)
    
    # Expected standard reference RGB & LAB
    r = db.Column(db.Integer, nullable=False)
    g = db.Column(db.Integer, nullable=False)
    b = db.Column(db.Integer, nullable=False)
    lab_l = db.Column(db.Float, nullable=False)
    lab_a = db.Column(db.Float, nullable=False)
    lab_b = db.Column(db.Float, nullable=False)
    
    # Controlled calibration laboratory conditions
    temperature = db.Column(db.Float, default=25.0, nullable=False)
    humidity = db.Column(db.Float, default=50.0, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'exposure_value': self.exposure_value,
            'r': self.r,
            'g': self.g,
            'b': self.b,
            'hex': f"#{self.r:02x}{self.g:02x}{self.b:02x}",
            'lab_l': round(self.lab_l, 2),
            'lab_a': round(self.lab_a, 2),
            'lab_b': round(self.lab_b, 2),
            'temperature': self.temperature,
            'humidity': self.humidity
        }
