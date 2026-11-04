from datetime import datetime
from . import db

class ExposureRecord(db.Model):
    __tablename__ = 'exposure_records'

    id = db.Column(db.Integer, primary_key=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False, index=True)
    badge_id = db.Column(db.Integer, db.ForeignKey('badges.id', ondelete='CASCADE'), nullable=False, index=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    scan_type = db.Column(db.String(10), nullable=False)  # 'ENTRY' or 'EXIT'
    
    # Measured Color Data
    r = db.Column(db.Integer, nullable=False)
    g = db.Column(db.Integer, nullable=False)
    b = db.Column(db.Integer, nullable=False)
    lab_l = db.Column(db.Float, nullable=False)
    lab_a = db.Column(db.Float, nullable=False)
    lab_b = db.Column(db.Float, nullable=False)
    
    # Environmental Data
    temperature = db.Column(db.Float, default=25.0, nullable=False)
    humidity = db.Column(db.Float, default=50.0, nullable=False)
    
    # Computed Exposure Metrics
    raw_exposure = db.Column(db.Float, nullable=False)
    corrected_exposure = db.Column(db.Float, nullable=False)
    shift_exposure = db.Column(db.Float, default=0.0, nullable=False)
    cumulative_exposure = db.Column(db.Float, default=0.0, nullable=False)
    
    # Risk & Quality
    status = db.Column(db.String(20), nullable=False)  # SAFE / CAUTION / HIGH / CRITICAL
    confidence = db.Column(db.Float, default=0.95, nullable=False)

    def to_dict(self):
        return {
            'id': self.id,
            'worker_id': self.worker_id,
            'worker_code': self.worker.worker_code if self.worker else '',
            'worker_name': self.worker.name if self.worker else '',
            'badge_id': self.badge_id,
            'badge_code': self.badge.badge_code if self.badge else '',
            'timestamp': self.timestamp.strftime('%Y-%m-%d %H:%M:%S') if self.timestamp else '',
            'time_only': self.timestamp.strftime('%H:%M') if self.timestamp else '',
            'date_only': self.timestamp.strftime('%Y-%m-%d') if self.timestamp else '',
            'scan_type': self.scan_type,
            'color': {
                'r': self.r,
                'g': self.g,
                'b': self.b,
                'hex': f"#{self.r:02x}{self.g:02x}{self.b:02x}",
                'lab_l': round(self.lab_l, 2),
                'lab_a': round(self.lab_a, 2),
                'lab_b': round(self.lab_b, 2)
            },
            'temperature': round(self.temperature, 1),
            'humidity': round(self.humidity, 1),
            'raw_exposure': round(self.raw_exposure, 1),
            'corrected_exposure': round(self.corrected_exposure, 1),
            'shift_exposure': round(self.shift_exposure, 1),
            'cumulative_exposure': round(self.cumulative_exposure, 1),
            'status': self.status,
            'confidence': round(self.confidence * 100, 1)
        }
