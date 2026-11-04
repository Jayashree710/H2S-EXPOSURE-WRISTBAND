from models import db, Worker, Badge

class ValidationService:
    """Centralized validation service for API requests and sensor parameters."""

    @staticmethod
    def validate_rgb(r, g, b):
        try:
            r = int(r)
            g = int(g)
            b = int(b)
            if not (0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255):
                return False, "RGB values must be integers between 0 and 255."
            return True, (r, g, b)
        except (ValueError, TypeError):
            return False, "Invalid RGB format. Values must be integers."

    @staticmethod
    def validate_environment(temperature, humidity):
        try:
            temp = float(temperature)
            hum = float(humidity)
            if not (15.0 <= temp <= 55.0):
                return False, "Temperature must be between 15°C and 55°C."
            if not (0.0 <= hum <= 100.0):
                return False, "Humidity must be between 0% and 100%."
            return True, (temp, hum)
        except (ValueError, TypeError):
            return False, "Temperature and Humidity must be valid numbers."

    @staticmethod
    def validate_worker_and_badge(worker_id, badge_id=None):
        try:
            w_id = int(worker_id)
            worker = db.session.get(Worker, w_id)
            if not worker:
                return False, f"Worker with ID {worker_id} not found."
            if worker.status != 'ACTIVE':
                return False, f"Worker {worker.worker_code} ({worker.name}) is currently INACTIVE."

            badge = None
            if badge_id:
                b_id = int(badge_id)
                badge = db.session.get(Badge, b_id)
                if not badge:
                    return False, f"Badge with ID {badge_id} not found."
                if badge.worker_id != worker.id:
                    return False, f"Badge {badge.badge_code} does not belong to worker {worker.worker_code}."
            else:
                badge = worker.get_active_badge()
                if not badge:
                    return False, f"Worker {worker.worker_code} does not have an active badge assigned."

            # Check badge validity
            if badge.validity_status == 'EXPIRED':
                return False, f"Badge {badge.badge_code} has EXPIRED on {badge.expiry_date.strftime('%Y-%m-%d')}. A replacement badge is required."
            if badge.validity_status == 'REVOKED':
                return False, f"Badge {badge.badge_code} is REVOKED. Scan cannot proceed."

            return True, (worker, badge)
        except (ValueError, TypeError) as e:
            return False, f"Invalid Worker or Badge parameter: {str(e)}"
