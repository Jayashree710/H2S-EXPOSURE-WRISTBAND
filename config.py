import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'h2sense-dev-secret-key-98765')
    
    # MySQL Database credentials
    DB_USER = os.getenv('DB_USER', 'root')
    DB_PASSWORD = os.getenv('DB_PASSWORD', '')
    DB_HOST = os.getenv('DB_HOST', '127.0.0.1')
    DB_PORT = os.getenv('DB_PORT', '3306')
    DB_NAME = os.getenv('DB_NAME', 'h2sense')

    # Construct SQLAlchemy Database URI
    # Supports MySQL with PyMySQL driver
    if DB_PASSWORD:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )
    else:
        SQLALCHEMY_DATABASE_URI = (
            f"mysql+pymysql://{DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}?charset=utf8mb4"
        )

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_recycle': 280,
        'pool_pre_ping': True,
    }

    # Environmental baseline & compensation factors
    TEMP_BASELINE = float(os.getenv('TEMP_BASELINE', 25.0))
    TEMP_COEFFICIENT = float(os.getenv('TEMP_COEFFICIENT', 0.35))
    HUMIDITY_BASELINE = float(os.getenv('HUMIDITY_BASELINE', 50.0))
    HUMIDITY_COEFFICIENT = float(os.getenv('HUMIDITY_COEFFICIENT', 0.15))

    # Prototype Risk Thresholds
    THRESHOLD_SAFE = float(os.getenv('THRESHOLD_SAFE', 25.0))
    THRESHOLD_CAUTION = float(os.getenv('THRESHOLD_CAUTION', 50.0))
    THRESHOLD_HIGH = float(os.getenv('THRESHOLD_HIGH', 100.0))

    # File uploads & exports
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    EXPORTS_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'exports')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 MB max image upload
