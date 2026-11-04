from flask import Blueprint, render_template, request, redirect, url_for, flash
from models import db, CalibrationPoint
from services.color_detector import ColorDetectorService
from config import Config
from database.seed_data import DEFAULT_CALIBRATION_POINTS

calibration_bp = Blueprint('calibration', __name__)

@calibration_bp.route('/calibration', methods=['GET', 'POST'])
def calibration_view():
    """Calibration reference administration and environmental configuration."""
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'add_point':
            try:
                exp_val = float(request.form.get('exposure_value'))
                r = int(request.form.get('r'))
                g = int(request.form.get('g'))
                b = int(request.form.get('b'))
                temp = float(request.form.get('temperature', 25.0))
                hum = float(request.form.get('humidity', 50.0))

                lab_l, lab_a, lab_b = ColorDetectorService.rgb_to_cielab(r, g, b)

                point = CalibrationPoint(
                    exposure_value=exp_val,
                    r=r, g=g, b=b,
                    lab_l=lab_l, lab_a=lab_a, lab_b=lab_b,
                    temperature=temp,
                    humidity=hum
                )
                db.session.add(point)
                db.session.commit()
                flash(f"Calibration point for {exp_val} ppm added successfully.", "success")
            except Exception as e:
                db.session.rollback()
                flash(f"Failed to add calibration point: {str(e)}", "danger")

        elif action == 'reset_defaults':
            try:
                CalibrationPoint.query.delete()
                for pt in DEFAULT_CALIBRATION_POINTS:
                    point = CalibrationPoint(
                        exposure_value=pt["exposure"],
                        r=pt["r"], g=pt["g"], b=pt["b"],
                        lab_l=pt["lab_l"], lab_a=pt["lab_a"], lab_b=pt["lab_b"],
                        temperature=pt["temp"], humidity=pt["hum"]
                    )
                    db.session.add(point)
                db.session.commit()
                flash("Calibration curve reset to prototype default standards.", "info")
            except Exception as e:
                db.session.rollback()
                flash(f"Error resetting calibration: {str(e)}", "danger")

        elif action == 'update_thresholds':
            try:
                Config.THRESHOLD_SAFE = float(request.form.get('threshold_safe', 25.0))
                Config.THRESHOLD_CAUTION = float(request.form.get('threshold_caution', 50.0))
                Config.THRESHOLD_HIGH = float(request.form.get('threshold_high', 100.0))
                flash("Prototype safety thresholds updated for session.", "success")
            except Exception as e:
                flash(f"Invalid threshold format: {str(e)}", "danger")

        return redirect(url_for('calibration.calibration_view'))

    points = CalibrationPoint.query.order_by(CalibrationPoint.exposure_value.asc()).all()

    return render_template(
        'calibration.html',
        points=points,
        config=Config
    )

@calibration_bp.route('/calibration/<int:id>/delete', methods=['POST'])
def delete_point(id):
    point = CalibrationPoint.query.get_or_404(id)
    db.session.delete(point)
    db.session.commit()
    flash(f"Calibration point {point.exposure_value} ppm removed.", "info")
    return redirect(url_for('calibration.calibration_view'))
