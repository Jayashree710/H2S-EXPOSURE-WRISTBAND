from flask import Blueprint, request, jsonify, send_file
from datetime import datetime, timedelta
from models import db, Worker, Badge, ExposureRecord, CalibrationPoint
from services import (
    ColorDetectorService,
    CalibrationService,
    ExposureService,
    ValidationService,
    ExcelService
)
from config import Config

api_bp = Blueprint('api', __name__, url_prefix='/api')

# -------------------------------------------------------------------
# WORKER APIs
# -------------------------------------------------------------------
@api_bp.route('/workers', methods=['GET'])
def get_workers():
    """Retrieve all workers with optional search and department filtering."""
    query = Worker.query
    search = request.args.get('search', '').strip()
    department = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()

    if search:
        query = query.filter(
            (Worker.worker_code.ilike(f'%{search}%')) |
            (Worker.name.ilike(f'%{search}%')) |
            (Worker.role.ilike(f'%{search}%'))
        )
    if department:
        query = query.filter_by(department=department)
    if status:
        query = query.filter_by(status=status)

    workers = query.order_by(Worker.worker_code.asc()).all()
    return jsonify({
        "success": True,
        "count": len(workers),
        "workers": [w.to_dict() for w in workers]
    })


@api_bp.route('/workers/export', methods=['GET'])
def export_workers():
    """Export all workers and exposure audit logs to Excel (.xlsx)."""
    try:
        saved_path = ExcelService.save_workers_excel_to_file()
        download = request.args.get('download', 'true').lower() in ('true', '1', 'yes')
        if download:
            buf = ExcelService.generate_workers_excel()
            filename = f"h2sense_workers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
            return send_file(
                buf,
                as_attachment=True,
                download_name=filename,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
        return jsonify({
            "success": True,
            "message": "Workers Excel sheet generated successfully.",
            "file_path": saved_path
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/workers', methods=['POST'])
def create_worker():
    """Register a new worker and automatically issue an initial badge."""
    data = request.get_json() or {}
    worker_code = data.get('worker_code', '').strip().upper()
    name = data.get('name', '').strip()
    department = data.get('department', '').strip()
    role = data.get('role', '').strip()
    phone = data.get('phone', '').strip()

    if not worker_code or not name or not department or not role:
        return jsonify({"success": False, "error": "Worker code, name, department, and role are required."}), 400

    if Worker.query.filter_by(worker_code=worker_code).first():
        return jsonify({"success": False, "error": f"Worker code {worker_code} already exists."}), 409

    try:
        worker = Worker(
            worker_code=worker_code,
            name=name,
            department=department,
            role=role,
            phone=phone,
            status='ACTIVE'
        )
        db.session.add(worker)
        db.session.flush()

        # Issue badge automatically (e.g. BD + code or unique)
        badge_code = data.get('badge_code', f"BD-{worker_code}").strip().upper()
        # Verify unique badge code
        existing_badge = Badge.query.filter_by(badge_code=badge_code).first()
        if existing_badge:
            badge_code = f"BD-{worker_code}-{int(datetime.utcnow().timestamp()) % 10000}"

        validity_days = int(data.get('validity_days', 180))
        badge = Badge(
            badge_code=badge_code,
            worker_id=worker.id,
            activation_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=validity_days),
            status='ACTIVE'
        )
        db.session.add(badge)
        db.session.commit()

        try:
            ExcelService.save_workers_excel_to_file()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"Worker {worker.name} ({worker.worker_code}) registered with badge {badge.badge_code}.",
            "worker": worker.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/workers/<int:id>', methods=['GET'])
def get_worker(id):
    """Retrieve single worker detail, active badge, and exposure history."""
    worker = db.session.get(Worker, id)
    if not worker:
        return jsonify({"success": False, "error": f"Worker with ID {id} not found."}), 404

    records = worker.exposure_records.all()
    badges = worker.badges.order_by(Badge.activation_date.desc()).all()

    return jsonify({
        "success": True,
        "worker": worker.to_dict(),
        "badges": [b.to_dict() for b in badges],
        "history": [r.to_dict() for r in records]
    })


@api_bp.route('/workers/<int:id>', methods=['PUT'])
def update_worker(id):
    """Update worker information."""
    worker = db.session.get(Worker, id)
    if not worker:
        return jsonify({"success": False, "error": f"Worker with ID {id} not found."}), 404

    data = request.get_json() or {}
    if 'name' in data and data['name'].strip():
        worker.name = data['name'].strip()
    if 'department' in data and data['department'].strip():
        worker.department = data['department'].strip()
    if 'role' in data and data['role'].strip():
        worker.role = data['role'].strip()
    if 'phone' in data:
        worker.phone = data['phone'].strip()
    if 'status' in data and data['status'] in ['ACTIVE', 'INACTIVE']:
        worker.status = data['status']

    try:
        db.session.commit()
        return jsonify({"success": True, "worker": worker.to_dict()})
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


# -------------------------------------------------------------------
# BADGE APIs
# -------------------------------------------------------------------
@api_bp.route('/badges', methods=['POST'])
def create_badge():
    """Issue a new badge to a worker."""
    data = request.get_json() or {}
    worker_id = data.get('worker_id')
    badge_code = data.get('badge_code', '').strip().upper()
    validity_days = int(data.get('validity_days', 180))

    if not worker_id or not badge_code:
        return jsonify({"success": False, "error": "worker_id and badge_code are required."}), 400

    worker = db.session.get(Worker, worker_id)
    if not worker:
        return jsonify({"success": False, "error": "Worker not found."}), 404

    if Badge.query.filter_by(badge_code=badge_code).first():
        return jsonify({"success": False, "error": f"Badge code {badge_code} already exists."}), 409

    try:
        # Mark previous active badges as REVOKED or superseded if desired
        previous_badges = Badge.query.filter_by(worker_id=worker.id, status='ACTIVE').all()
        for pb in previous_badges:
            pb.status = 'REVOKED'

        badge = Badge(
            badge_code=badge_code,
            worker_id=worker.id,
            activation_date=datetime.utcnow(),
            expiry_date=datetime.utcnow() + timedelta(days=validity_days),
            status='ACTIVE'
        )
        db.session.add(badge)
        db.session.commit()

        return jsonify({"success": True, "badge": badge.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/badges/<int:id>', methods=['GET'])
def get_badge(id):
    badge = db.session.get(Badge, id)
    if not badge:
        return jsonify({"success": False, "error": f"Badge with ID {id} not found."}), 404
    return jsonify({"success": True, "badge": badge.to_dict()})


# -------------------------------------------------------------------
# COLOR DETECTION & EXPOSURE CALCULATION APIs
# -------------------------------------------------------------------
@api_bp.route('/detect-color', methods=['POST'])
def detect_color():
    """
    Extracts sensor color from image upload, base64 capture, or direct RGB.
    Accepts:
    - multipart file (file)
    - json with 'image' (base64)
    - json with 'r', 'g', 'b' (direct simulator input)
    """
    try:
        if 'file' in request.files:
            file = request.files['file']
            if file.filename == '':
                return jsonify({"success": False, "error": "No file selected."}), 400
            color_data = ColorDetectorService.process_image(file.read())
        elif request.is_json:
            data = request.get_json()
            if 'image' in data and data['image']:
                color_data = ColorDetectorService.process_base64(data['image'])
            elif 'r' in data and 'g' in data and 'b' in data:
                is_valid, res = ValidationService.validate_rgb(data['r'], data['g'], data['b'])
                if not is_valid:
                    return jsonify({"success": False, "error": res}), 400
                r, g, b = res
                color_data = ColorDetectorService.process_rgb_direct(r, g, b)
            else:
                return jsonify({"success": False, "error": "No image data or RGB values provided."}), 400
        else:
            return jsonify({"success": False, "error": "Invalid request content type."}), 400

        return jsonify({
            "success": True,
            "color": color_data
        })
    except Exception as e:
        return jsonify({"success": False, "error": f"Computer Vision error: {str(e)}"}), 500


@api_bp.route('/calculate-exposure', methods=['POST'])
def calculate_exposure():
    """
    Performs full calibration curve lookup and environmental correction.
    Body:
    {
        "color": { "r": 234, "g": 179, "b": 8, "lab": { "l": 75.3, "a": 6.2, "b": 76.4 } },
        "temperature": 31.0,
        "humidity": 72.0
    }
    """
    data = request.get_json() or {}
    color_data = data.get('color', {})
    temp = data.get('temperature', 25.0)
    hum = data.get('humidity', 50.0)

    # Validate environment
    valid_env, env_res = ValidationService.validate_environment(temp, hum)
    if not valid_env:
        return jsonify({"success": False, "error": env_res}), 400
    temp_val, hum_val = env_res

    try:
        # 1. Calibration model estimation
        calibration_res = CalibrationService.estimate_exposure(color_data, temp_val, hum_val)
        raw_exposure = calibration_res["exposure"]
        confidence = calibration_res["confidence"]

        # 2. Environmental compensation
        env_correction = ExposureService.calculate_environmental_correction(raw_exposure, temp_val, hum_val)

        # 3. Centralized threshold classification
        corrected_exposure = env_correction["corrected_exposure"]
        classification = ExposureService.classify_exposure(corrected_exposure)

        return jsonify({
            "success": True,
            "raw_exposure": raw_exposure,
            "environmental_correction": env_correction["environmental_correction"],
            "corrected_exposure": corrected_exposure,
            "confidence": confidence,
            "status": classification["status"],
            "classification": classification,
            "environmental_breakdown": env_correction,
            "method": calibration_res["method"],
            "disclaimer": "Prototype calibration demonstration only — not certified occupational H2S measurements."
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@api_bp.route('/record-scan', methods=['POST'])
def record_scan():
    """
    Commits an ENTRY or EXIT exposure scan to the database.
    Body:
    {
        "worker_id": 4,
        "badge_id": 4, # optional, auto-selected if omitted
        "scan_type": "ENTRY" | "EXIT",
        "color": { "r": 249, "g": 115, "b": 22, "lab": { "l": 63.1, "a": 48.2, "b": 65.5 } },
        "temperature": 31.0,
        "humidity": 72.0,
        "raw_exposure": 75.0,
        "confidence": 0.95
    }
    """
    data = request.get_json() or {}
    worker_id = data.get('worker_id')
    badge_id = data.get('badge_id')
    scan_type = data.get('scan_type', 'ENTRY').upper()

    if scan_type not in ['ENTRY', 'EXIT']:
        return jsonify({"success": False, "error": "scan_type must be ENTRY or EXIT."}), 400

    # Validate worker and badge
    valid_wb, wb_res = ValidationService.validate_worker_and_badge(worker_id, badge_id)
    if not valid_wb:
        return jsonify({"success": False, "error": wb_res}), 400
    worker, badge = wb_res

    # Validate environment
    temp = data.get('temperature', 25.0)
    hum = data.get('humidity', 50.0)
    valid_env, env_res = ValidationService.validate_environment(temp, hum)
    if not valid_env:
        return jsonify({"success": False, "error": env_res}), 400
    temp_val, hum_val = env_res

    color_data = data.get('color', {})
    raw_exposure = float(data.get('raw_exposure', 0.0))
    confidence = float(data.get('confidence', 0.95))

    try:
        result = ExposureService.process_scan_record(
            worker_id=worker.id,
            badge_id=badge.id,
            scan_type=scan_type,
            color_data=color_data,
            temperature=temp_val,
            humidity=hum_val,
            raw_exposure=raw_exposure,
            confidence=confidence
        )

        try:
            ExcelService.save_workers_excel_to_file()
        except Exception:
            pass

        return jsonify({
            "success": True,
            "message": f"{scan_type} scan recorded successfully for {worker.name} ({worker.worker_code}).",
            "data": result
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": f"Failed to record scan: {str(e)}"}), 500


@api_bp.route('/exposure/<int:worker_id>', methods=['GET'])
def get_worker_exposure_history(worker_id):
    """Retrieve complete exposure history for a specific worker."""
    worker = db.session.get(Worker, worker_id)
    if not worker:
        return jsonify({"success": False, "error": "Worker not found."}), 404

    records = worker.exposure_records.all()
    return jsonify({
        "success": True,
        "worker": worker.to_dict(),
        "total_records": len(records),
        "cumulative_exposure": worker.get_cumulative_exposure(),
        "records": [r.to_dict() for r in records]
    })


# -------------------------------------------------------------------
# DASHBOARD STATS API
# -------------------------------------------------------------------
@api_bp.route('/dashboard/stats', methods=['GET'])
def get_dashboard_stats():
    """Aggregates all administrative statistics and Chart.js datasets."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 1. High-level metric cards
    active_workers_count = Worker.query.filter_by(status='ACTIVE').count()
    today_scans_count = ExposureRecord.query.filter(ExposureRecord.timestamp >= today_start).count()
    
    # High risk workers: workers whose most recent scan is HIGH or CRITICAL
    all_workers = Worker.query.filter_by(status='ACTIVE').all()
    high_risk_workers = []
    total_cumulative_system_exposure = 0.0

    for w in all_workers:
        cum = w.get_cumulative_exposure()
        total_cumulative_system_exposure += cum
        latest = w.get_latest_record()
        if latest and latest.status in ['HIGH', 'CRITICAL']:
            high_risk_workers.append({
                "id": w.id,
                "worker_code": w.worker_code,
                "name": w.name,
                "department": w.department,
                "status": latest.status,
                "latest_exposure": latest.corrected_exposure,
                "cumulative": cum,
                "timestamp": latest.timestamp.strftime('%H:%M') if latest.timestamp else ''
            })

    # 2. Risk category distribution (SAFE, CAUTION, HIGH, CRITICAL)
    # Based on each worker's latest status
    status_counts = {"SAFE": 0, "CAUTION": 0, "HIGH": 0, "CRITICAL": 0}
    for w in all_workers:
        latest = w.get_latest_record()
        if latest:
            status_counts[latest.status] = status_counts.get(latest.status, 0) + 1
        else:
            status_counts["SAFE"] += 1

    # 3. 7-Day Exposure Trend Chart
    trend_labels = []
    trend_values = []
    for i in range(6, -1, -1):
        day_date = (now - timedelta(days=i)).date()
        day_start = datetime.combine(day_date, datetime.min.time())
        day_end = datetime.combine(day_date, datetime.max.time())
        
        day_records = ExposureRecord.query.filter(
            ExposureRecord.timestamp >= day_start,
            ExposureRecord.timestamp <= day_end
        ).all()
        
        avg_exp = round(sum(r.corrected_exposure for r in day_records) / len(day_records), 1) if day_records else 0.0
        trend_labels.append(day_date.strftime('%b %d'))
        trend_values.append(avg_exp)

    # 4. Worker Cumulative Exposure Comparison (Top 5)
    worker_comp = []
    for w in all_workers:
        worker_comp.append({
            "name": f"{w.worker_code} - {w.name.split()[0]}",
            "cumulative": w.get_cumulative_exposure()
        })
    worker_comp.sort(key=lambda x: x["cumulative"], reverse=True)

    # 5. Badge Health Overview
    all_badges = Badge.query.all()
    badge_health = {
        "valid": sum(1 for b in all_badges if b.validity_status == 'VALID'),
        "near_expiry": sum(1 for b in all_badges if b.validity_status == 'NEAR EXPIRY'),
        "expired": sum(1 for b in all_badges if b.validity_status == 'EXPIRED')
    }

    # 6. Recent Scans Feed (last 10)
    recent_records = ExposureRecord.query.order_by(ExposureRecord.timestamp.desc()).limit(10).all()

    return jsonify({
        "success": True,
        "metrics": {
            "active_workers": active_workers_count,
            "today_scans": today_scans_count,
            "high_risk_count": len(high_risk_workers),
            "total_cumulative_exposure": round(total_cumulative_system_exposure, 1)
        },
        "risk_distribution": status_counts,
        "trend_7day": {
            "labels": trend_labels,
            "values": trend_values
        },
        "worker_comparison": {
            "labels": [item["name"] for item in worker_comp[:6]],
            "values": [item["cumulative"] for item in worker_comp[:6]]
        },
        "badge_health": badge_health,
        "high_risk_list": high_risk_workers,
        "recent_scans": [r.to_dict() for r in recent_records]
    })


# -------------------------------------------------------------------
# CALIBRATION APIs
# -------------------------------------------------------------------
@api_bp.route('/calibration', methods=['GET'])
def get_calibration():
    """Retrieve all active calibration points and configuration."""
    points = CalibrationPoint.query.order_by(CalibrationPoint.exposure_value.asc()).all()
    return jsonify({
        "success": True,
        "points": [p.to_dict() for p in points],
        "configuration": {
            "temp_baseline": Config.TEMP_BASELINE,
            "temp_coefficient": Config.TEMP_COEFFICIENT,
            "humidity_baseline": Config.HUMIDITY_BASELINE,
            "humidity_coefficient": Config.HUMIDITY_COEFFICIENT,
            "threshold_safe": Config.THRESHOLD_SAFE,
            "threshold_caution": Config.THRESHOLD_CAUTION,
            "threshold_high": Config.THRESHOLD_HIGH
        }
    })


@api_bp.route('/calibration', methods=['POST'])
def add_calibration_point():
    """Add or update a calibration reference point."""
    data = request.get_json() or {}
    try:
        exp_val = float(data.get('exposure_value'))
        r = int(data.get('r'))
        g = int(data.get('g'))
        b = int(data.get('b'))
        
        lab_l, lab_a, lab_b = ColorDetectorService.rgb_to_cielab(r, g, b)
        
        point = CalibrationPoint(
            exposure_value=exp_val,
            r=r, g=g, b=b,
            lab_l=lab_l, lab_a=lab_a, lab_b=lab_b,
            temperature=float(data.get('temperature', 25.0)),
            humidity=float(data.get('humidity', 50.0))
        )
        db.session.add(point)
        db.session.commit()
        return jsonify({"success": True, "point": point.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"success": False, "error": str(e)}), 400
