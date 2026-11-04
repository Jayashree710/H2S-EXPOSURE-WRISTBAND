from flask import Blueprint, render_template
from models.calibration import CalibrationPoint
from services.calibration_service import CalibrationService

simulator_bp = Blueprint('simulator', __name__)

@simulator_bp.route('/simulator')
def simulator_view():
    """Renders the Digital H2S Sensor Simulator interface."""
    points = CalibrationService.get_calibration_points()
    return render_template('simulator.html', calibration_points=points)
