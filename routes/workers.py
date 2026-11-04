from flask import Blueprint, render_template, request, redirect, url_for, flash, send_file
from datetime import datetime, timedelta
from models import db, Worker, Badge, ExposureRecord
from services.excel_service import ExcelService

workers_bp = Blueprint('workers', __name__)

@workers_bp.route('/workers', methods=['GET', 'POST'])
def workers_list():
    """Worker CRUD and directory overview."""
    if request.method == 'POST':
        # Create Worker Form Submission
        worker_code = request.form.get('worker_code', '').strip().upper()
        name = request.form.get('name', '').strip()
        department = request.form.get('department', '').strip()
        role = request.form.get('role', '').strip()
        phone = request.form.get('phone', '').strip()
        badge_code = request.form.get('badge_code', f"BD-{worker_code}").strip().upper()

        if not worker_code or not name or not department or not role:
            flash("Worker Code, Full Name, Department, and Role are mandatory.", "danger")
            return redirect(url_for('workers.workers_list'))

        if Worker.query.filter_by(worker_code=worker_code).first():
            flash(f"Worker Code '{worker_code}' already exists.", "warning")
            return redirect(url_for('workers.workers_list'))

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

            # Create Badge
            badge = Badge(
                badge_code=badge_code,
                worker_id=worker.id,
                activation_date=datetime.utcnow(),
                expiry_date=datetime.utcnow() + timedelta(days=180),
                status='ACTIVE'
            )
            db.session.add(badge)
            db.session.commit()

            try:
                ExcelService.save_workers_excel_to_file()
            except Exception:
                pass

            flash(f"Worker {worker.name} ({worker.worker_code}) and Badge {badge.badge_code} successfully registered.", "success")
            return redirect(url_for('workers.workers_list'))
        except Exception as e:
            db.session.rollback()
            flash(f"Error registering worker: {str(e)}", "danger")

    # Filter & Search
    search = request.args.get('search', '').strip()
    department = request.args.get('department', '').strip()
    status = request.args.get('status', '').strip()

    query = Worker.query
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

    # Get distinct departments for filter dropdown
    departments = [d[0] for d in db.session.query(Worker.department).distinct().all() if d[0]]

    return render_template(
        'workers.html',
        workers=workers,
        departments=departments,
        current_search=search,
        current_dept=department,
        current_status=status
    )

@workers_bp.route('/workers/<int:id>')
def worker_detail(id):
    """Detailed profile view for a single worker."""
    worker = Worker.query.get_or_404(id)
    records = worker.exposure_records.all()
    badges = worker.badges.order_by(Badge.activation_date.desc()).all()
    active_badge = worker.get_active_badge()

    # Calculate status counts for risk distribution doughnut
    status_counts = {'SAFE': 0, 'CAUTION': 0, 'HIGH': 0, 'CRITICAL': 0}
    for r in records:
        if r.status in status_counts:
            status_counts[r.status] += 1

    return render_template(
        'worker_detail.html',
        worker=worker,
        badge=active_badge,
        badges=badges,
        records=records,
        records_json=[r.to_dict() for r in records],
        status_counts=status_counts,
        cumulative_exposure=worker.get_cumulative_exposure()
    )

@workers_bp.route('/workers/<int:id>/status-toggle', methods=['POST'])
def toggle_status(id):
    """Toggle worker active / inactive state."""
    worker = Worker.query.get_or_404(id)
    worker.status = 'INACTIVE' if worker.status == 'ACTIVE' else 'ACTIVE'
    db.session.commit()
    try:
        ExcelService.save_workers_excel_to_file()
    except Exception:
        pass
    flash(f"Status for {worker.worker_code} updated to {worker.status}.", "info")
    return redirect(url_for('workers.workers_list'))

@workers_bp.route('/workers/<int:id>/renew-badge', methods=['POST'])
def renew_badge(id):
    """Issues a new 180-day badge to worker."""
    worker = Worker.query.get_or_404(id)
    new_badge_code = request.form.get('badge_code', f"BD-{worker.worker_code}-R2").strip().upper()
    
    # Revoke current badges
    for b in worker.badges:
        b.status = 'REVOKED'

    new_badge = Badge(
        badge_code=new_badge_code,
        worker_id=worker.id,
        activation_date=datetime.utcnow(),
        expiry_date=datetime.utcnow() + timedelta(days=180),
        status='ACTIVE'
    )
    db.session.add(new_badge)
    db.session.commit()
    try:
        ExcelService.save_workers_excel_to_file()
    except Exception:
        pass
    flash(f"New badge {new_badge.badge_code} successfully issued to {worker.name}.", "success")
    return redirect(url_for('workers.worker_detail', id=worker.id))

@workers_bp.route('/workers/export/excel')
def export_workers_excel():
    """Generates and downloads the full Workforce and Exposure History Excel file."""
    try:
        # Also persist to server exports folder
        ExcelService.save_workers_excel_to_file()
        buf = ExcelService.generate_workers_excel()
        filename = f"h2sense_workers_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.xlsx"
        return send_file(
            buf,
            as_attachment=True,
            download_name=filename,
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
    except Exception as e:
        flash(f"Failed to export Excel report: {str(e)}", "danger")
        return redirect(url_for('workers.workers_list'))
