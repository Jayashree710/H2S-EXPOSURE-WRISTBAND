from datetime import datetime
from . import db

class Worker(db.Model):
    __tablename__ = 'workers'

    id = db.Column(db.Integer, primary_key=True)
    worker_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    name = db.Column(db.String(128), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(32), nullable=True)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE / INACTIVE
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    badges = db.relationship('Badge', backref='worker', lazy='dynamic', cascade='all, delete-orphan')
    exposure_records = db.relationship(
        'ExposureRecord', 
        backref='worker', 
        lazy='dynamic', 
        cascade='all, delete-orphan',
        order_by='ExposureRecord.timestamp.desc()'
    )

    def get_active_badge(self):
        """Returns the currently active badge or the most recent badge."""
        return self.badges.filter_by(status='ACTIVE').order_by(db.desc('id')).first()

    def get_latest_record(self):
        """Returns the most recent exposure record."""
        return self.exposure_records.first()

    def get_cumulative_exposure(self):
        """Returns the cumulative exposure computed from all valid shift increments."""
        from .exposure import ExposureRecord
        records = self.exposure_records.filter(ExposureRecord.shift_exposure > 0).all()
        return round(sum(r.shift_exposure for r in records), 2)

    def to_dict(self):
        active_badge = self.get_active_badge()
        latest_record = self.get_latest_record()
        return {
            'id': self.id,
            'worker_code': self.worker_code,
            'name': self.name,
            'department': self.department,
            'role': self.role,
            'phone': self.phone or '',
            'status': self.status,
            'created_at': self.created_at.strftime('%Y-%m-%d %H:%M:%S') if self.created_at else '',
            'active_badge': active_badge.to_dict() if active_badge else None,
            'latest_exposure': latest_record.corrected_exposure if latest_record else 0.0,
            'latest_status': latest_record.status if latest_record else 'SAFE',
            'cumulative_exposure': self.get_cumulative_exposure()
        }
