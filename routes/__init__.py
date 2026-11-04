from .main import main_bp
from .simulator import simulator_bp
from .scanner import scanner_bp
from .dashboard import dashboard_bp
from .workers import workers_bp
from .calibration import calibration_bp
from .api import api_bp

__all__ = [
    'main_bp',
    'simulator_bp',
    'scanner_bp',
    'dashboard_bp',
    'workers_bp',
    'calibration_bp',
    'api_bp'
]
