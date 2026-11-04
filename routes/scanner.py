from flask import Blueprint, render_template, request, session
from models import Worker, Badge
from config import Config

scanner_bp = Blueprint('scanner', __name__)

@scanner_bp.route('/scanner')
def scanner_view():
    """Renders the Color Detection Scanner workstation."""
    workers = Worker.query.filter_by(status='ACTIVE').order_by(Worker.worker_code.asc()).all()
    
    # Pre-filled query parameters from simulator bridge if available
    prefill_r = request.args.get('r', '')
    prefill_g = request.args.get('g', '')
    prefill_b = request.args.get('b', '')
    prefill_exp = request.args.get('exposure', '')

    return render_template(
        'scanner.html',
        workers=workers,
        prefill_r=prefill_r,
        prefill_g=prefill_g,
        prefill_b=prefill_b,
        prefill_exp=prefill_exp,
        config=Config,
        user_role=session.get('user_role', 'ADMIN'),
        logged_in_worker_id=session.get('worker_id')
    )
