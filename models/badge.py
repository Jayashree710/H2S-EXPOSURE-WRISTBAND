from datetime import datetime, timedelta
from . import db

class Badge(db.Model):
    __tablename__ = 'badges'

    id = db.Column(db.Integer, primary_key=True)
    badge_code = db.Column(db.String(32), unique=True, nullable=False, index=True)
    worker_id = db.Column(db.Integer, db.ForeignKey('workers.id', ondelete='CASCADE'), nullable=False)
    activation_date = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    expiry_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='ACTIVE')  # ACTIVE / EXPIRED / REVOKED

    # Relationship
    exposure_records = db.relationship(
        'ExposureRecord', 
        backref='badge', 
        lazy='dynamic', 
        cascade='all, delete-orphan',
        order_by='ExposureRecord.timestamp.desc()'
    )

    @property
    def badge_age_days(self):
        """Calculates badge age in days since activation."""
        if not self.activation_date:
            return 0
        delta = datetime.utcnow() - self.activation_date
        return max(0, delta.days)

    @property
    def validity_status(self):
        """Calculates dynamic badge validity: VALID, NEAR EXPIRY, or EXPIRED."""
        if self.status == 'REVOKED':
            return 'REVOKED'
        
        now = datetime.utcnow()
        if now > self.expiry_date:
            return 'EXPIRED'
        
        # Near expiry if within 7 days of expiration
        if self.expiry_date - now <= timedelta(days=7):
            return 'NEAR EXPIRY'
        
        return 'VALID'

    @property
    def days_remaining(self):
        """Remaining days of validity."""
        now = datetime.utcnow()
        delta = self.expiry_date - now
        return max(0, delta.days)

    def to_dict(self):
        return {
            'id': self.id,
            'badge_code': self.badge_code,
            'worker_id': self.worker_id,
            'worker_code': self.worker.worker_code if self.worker else '',
            'worker_name': self.worker.name if self.worker else '',
            'activation_date': self.activation_date.strftime('%Y-%m-%d %H:%M:%S') if self.activation_date else '',
            'expiry_date': self.expiry_date.strftime('%Y-%m-%d %H:%M:%S') if self.expiry_date else '',
            'status': self.status,
            'validity_status': self.validity_status,
            'badge_age_days': self.badge_age_days,
            'days_remaining': self.days_remaining
        }
