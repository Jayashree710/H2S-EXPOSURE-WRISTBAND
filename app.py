import os
from flask import Flask, render_template, jsonify
from flask_cors import CORS
from config import Config
from models import db
from database.seed_data import seed_database
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('h2sense')

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Enable CORS for APIs
    CORS(app)

    # Initialize SQLAlchemy
    db.init_app(app)

    # Ensure upload and export directories exist
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    os.makedirs(app.config.get('EXPORTS_FOLDER', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')), exist_ok=True)

    # Register Blueprints
    from routes import (
        main_bp,
        simulator_bp,
        scanner_bp,
        dashboard_bp,
        workers_bp,
        calibration_bp,
        api_bp
    )

    app.register_blueprint(main_bp)
    app.register_blueprint(simulator_bp)
    app.register_blueprint(scanner_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(workers_bp)
    app.register_blueprint(calibration_bp)
    app.register_blueprint(api_bp)

    # Global Context Processor
    @app.context_processor
    def inject_global_context():
        return {
            'app_name': 'H₂SENSE',
            'tagline': 'Know Your Exposure. Protect Your Workforce.',
            'prototype_disclaimer': (
                'Prototype demonstration: exposure values shown in this application are simulated/'
                'calibration-demo values and are not certified occupational H₂S measurements. '
                'Real-world deployment requires controlled chemical calibration, environmental validation, '
                'shelf-life testing, and safety certification.'
            )
        }

    # Error Handlers
    @app.errorhandler(404)
    def page_not_found(e):
        return render_template('base.html', error_title="404 - Page Not Found", error_msg="The requested safety portal resource was not found."), 404

    @app.errorhandler(500)
    def internal_server_error(e):
        logger.error(f"Internal server error: {e}")
        return render_template('base.html', error_title="500 - System Service Warning", error_msg="An internal processing error occurred. Please verify sensor input parameters or check server logs."), 500

    # Auto-initialize database tables and seed data
    with app.app_context():
        try:
            logger.info("Initializing database tables...")
            db.create_all()
            logger.info("Database tables verified. Checking seed data...")
            seed_database()
            logger.info("Seed data verified.")
            try:
                from services.excel_service import ExcelService
                excel_path = ExcelService.save_workers_excel_to_file()
                logger.info(f"Workers Excel master sheet synchronized at: {excel_path}")
            except Exception as ex_err:
                logger.warning(f"Could not initialize workers Excel sheet: {ex_err}")
        except Exception as e:
            logger.error(f"Database initialization error (Check MySQL / WAMP server): {e}")
            # Try SQLite fallback if MySQL is down
            fallback_sqlite = "sqlite:///" + os.path.join(os.path.dirname(os.path.abspath(__file__)), "h2sense_fallback.db")
            logger.warning(f"Attempting SQLite fallback at {fallback_sqlite}...")
            try:
                app.config['SQLALCHEMY_DATABASE_URI'] = fallback_sqlite
                db.init_app(app)
                db.create_all()
                seed_database()
                logger.info("Successfully connected to SQLite fallback.")
            except Exception as sqlite_err:
                logger.critical(f"Failed fallback: {sqlite_err}")

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    debug = os.getenv('DEBUG', 'True').lower() in ('true', '1', 't')
    logger.info(f"Starting H2SENSE Industrial Exposure System on http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=debug)
