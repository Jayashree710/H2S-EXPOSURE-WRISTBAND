from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from models import Worker, ExposureRecord

main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """Renders the high-impact Industrial Safety Landing Page."""
    active_count = Worker.query.filter_by(status='ACTIVE').count()
    total_scans = ExposureRecord.query.count()
    workers = Worker.query.all()
    total_cumulative_exposure = round(sum(w.get_cumulative_exposure() for w in workers), 1)
    return render_template(
        'landing.html',
        active_count=active_count,
        total_scans=total_scans,
        total_cumulative_exposure=total_cumulative_exposure
    )

@main_bp.route('/login', methods=['GET', 'POST'])
def login():
    """Simple prototype authentication for demonstration."""
    if request.method == 'POST':
        role = request.form.get('role', 'ADMIN').upper()
        worker_code = request.form.get('worker_code', '').strip().upper()
        
        session['user_role'] = role
        session['logged_in'] = True
        
        if role == 'WORKER':
            worker = Worker.query.filter_by(worker_code=worker_code).first() if worker_code else Worker.query.first()
            session['worker_id'] = worker.id if worker else 1
            session['worker_code'] = worker.worker_code if worker else 'W104'
            session['user_name'] = worker.name if worker else 'Worker Demo'
            return redirect(url_for('dashboard.worker_dashboard', id=session['worker_id']))
        elif role == 'SAFETY_OFFICER':
            session['user_name'] = 'Safety Officer Elena Rostova'
            return redirect(url_for('dashboard.admin_dashboard'))
        else:
            session['user_name'] = 'Administrator'
            return redirect(url_for('dashboard.admin_dashboard'))

    return render_template('login.html')

@main_bp.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('main.index'))
