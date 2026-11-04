from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from models import db, Worker, Badge, ExposureRecord
from datetime import datetime, timedelta
from config import Config

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard')
def admin_dashboard():
    """Renders the comprehensive Administrator / Safety Officer Dashboard."""
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    workers = Worker.query.filter_by(status='ACTIVE').all()
    active_workers_count = len(workers)
    today_scans_count = ExposureRecord.query.filter(ExposureRecord.timestamp >= today_start).count()
    
    # Calculate high risk workers & system total
    high_risk_workers = []
    total_cumulative = 0.0

    for w in workers:
        cum = w.get_cumulative_exposure()
        total_cumulative += cum
        latest = w.get_latest_record()
        if latest and latest.status in ['HIGH', 'CRITICAL']:
            high_risk_workers.append({
                "worker": w,
                "latest": latest,
                "cumulative": cum
            })

    # Recent scans
    recent_scans = ExposureRecord.query.order_by(ExposureRecord.timestamp.desc()).limit(8).all()
    
    # Badges near expiry or expired
    all_badges = Badge.query.all()
    badges_attention = [b for b in all_badges if b.validity_status in ['NEAR EXPIRY', 'EXPIRED']]

    return render_template(
        'dashboard.html',
        active_workers=active_workers_count,
        today_scans=today_scans_count,
        high_risk_count=len(high_risk_workers),
        total_cumulative=round(total_cumulative, 1),
        high_risk_workers=high_risk_workers,
        recent_scans=recent_scans,
        badges_attention=badges_attention
    )

@dashboard_bp.route('/worker-dashboard')
@dashboard_bp.route('/worker-dashboard/<int:id>')
def worker_dashboard(id=None):
    """Renders the dedicated Worker-Oriented Dashboard."""
    all_active_workers = Worker.query.filter_by(status='ACTIVE').order_by(Worker.worker_code.asc()).all()

    # Determine which worker to view based on RBAC
    user_role = session.get('user_role', 'ADMIN')
    
    if user_role == 'WORKER':
        # Enforce sandbox: worker can only see their own dashboard
        logged_in_worker_id = session.get('worker_id')
        current_worker = db.session.get(Worker, logged_in_worker_id)
        
        # Prevent accessing other workers' dashboards
        if id is not None and id != logged_in_worker_id:
            flash("Security Restriction: You are only authorized to view your own exposure details.", "danger")
            return redirect(url_for('dashboard.worker_dashboard'))
    else:
        # ADMIN and SAFETY_OFFICER can view any worker
        if id:
            current_worker = db.session.get(Worker, id)
        elif session.get('worker_id'):
            current_worker = db.session.get(Worker, session.get('worker_id'))
        else:
            # Default presentation fallback
            current_worker = Worker.query.filter_by(worker_code='W104').first() or Worker.query.first()

    if not current_worker and all_active_workers:
        current_worker = all_active_workers[0]

    if not current_worker:
        return redirect(url_for('workers.workers_list'))

    active_badge = current_worker.get_active_badge()
    records = current_worker.exposure_records.all()
    latest_record = current_worker.get_latest_record()

    # Calculate today's shift exposure (sum of shift_exposure for today's scans)
    now = datetime.utcnow()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_records = [r for r in records if r.timestamp >= today_start]
    today_shift_exposure = round(sum(r.shift_exposure for r in today_records), 1)

    # Fallback to latest shift increment if today has none
    if today_shift_exposure == 0.0 and latest_record and latest_record.shift_exposure > 0:
        today_shift_exposure = latest_record.shift_exposure

    cumulative_exposure = current_worker.get_cumulative_exposure()

    return render_template(
        'worker_dashboard.html',
        worker=current_worker,
        badge=active_badge,
        latest_record=latest_record,
        today_shift_exposure=today_shift_exposure,
        cumulative_exposure=cumulative_exposure,
        records=records[:10],
        records_json=[r.to_dict() for r in records[:10]],
        all_workers=all_active_workers
    )
