from datetime import datetime, timedelta
import random
from models import db, Worker, Badge, ExposureRecord, CalibrationPoint
from config import Config

# Standard prototype colorimetric points for H2S color change:
# Safe (Green) -> Caution (Yellow) -> High (Orange) -> Critical (Red/Brown)
DEFAULT_CALIBRATION_POINTS = [
    {"exposure": 0.0,   "r": 34,  "g": 197, "b": 94,  "lab_l": 70.5, "lab_a": -60.2, "lab_b": 41.5, "temp": 25.0, "hum": 50.0},
    {"exposure": 10.0,  "r": 95,  "g": 207, "b": 72,  "lab_l": 74.2, "lab_a": -49.6, "lab_b": 53.1, "temp": 25.0, "hum": 50.0},
    {"exposure": 25.0,  "r": 163, "g": 230, "b": 53,  "lab_l": 83.1, "lab_a": -38.4, "lab_b": 68.2, "temp": 25.0, "hum": 50.0},
    {"exposure": 50.0,  "r": 234, "g": 179, "b": 8,   "lab_l": 75.3, "lab_a": 6.2,   "lab_b": 76.4, "temp": 25.0, "hum": 50.0},
    {"exposure": 75.0,  "r": 249, "g": 115, "b": 22,  "lab_l": 63.1, "lab_a": 48.2,  "lab_b": 65.5, "temp": 25.0, "hum": 50.0},
    {"exposure": 100.0, "r": 239, "g": 68,  "b": 68,  "lab_l": 53.2, "lab_a": 67.1,  "lab_b": 48.8, "temp": 25.0, "hum": 50.0},
    {"exposure": 150.0, "r": 185, "g": 28,  "b": 28,  "lab_l": 37.4, "lab_a": 61.5,  "lab_b": 43.2, "temp": 25.0, "hum": 50.0},
    {"exposure": 200.0, "r": 127, "g": 29,  "b": 29,  "lab_l": 26.8, "lab_a": 44.9,  "lab_b": 28.6, "temp": 25.0, "hum": 50.0},
]

DEMO_WORKERS = [
    {
        "worker_code": "W101",
        "name": "Marcus Vance",
        "department": "Refinery Operations",
        "role": "Senior Distillation Lead",
        "phone": "+1 (555) 234-5678",
        "status": "ACTIVE",
        "badge_code": "BD101",
        "expiry_days": 180
    },
    {
        "worker_code": "W102",
        "name": "Elena Rostova",
        "department": "Inspection & QA",
        "role": "Industrial Hygienist",
        "phone": "+1 (555) 345-6789",
        "status": "ACTIVE",
        "badge_code": "BD102",
        "expiry_days": 90
    },
    {
        "worker_code": "W103",
        "name": "David Chen",
        "department": "Maintenance",
        "role": "Valves & Pipefittings Tech",
        "phone": "+1 (555) 456-7890",
        "status": "ACTIVE",
        "badge_code": "BD103",
        "expiry_days": 4  # NEAR EXPIRY test case
    },
    {
        "worker_code": "W104",
        "name": "Sarah Jenkins",
        "department": "Production",
        "role": "Hydrocracker Operator",
        "phone": "+1 (555) 567-8901",
        "status": "ACTIVE",
        "badge_code": "BD104",
        "expiry_days": 150
    },
    {
        "worker_code": "W105",
        "name": "Tariq Al-Mansoor",
        "department": "Plant Safety",
        "role": "Hazard Containment Auditor",
        "phone": "+1 (555) 678-9012",
        "status": "ACTIVE",
        "badge_code": "BD105",
        "expiry_days": 240
    }
]

def seed_database():
    """Populates calibration points, demo workers, badges, and realistic historical scans."""
    # 1. Seed Calibration Points if empty
    if CalibrationPoint.query.count() == 0:
        for pt in DEFAULT_CALIBRATION_POINTS:
            point = CalibrationPoint(
                exposure_value=pt["exposure"],
                r=pt["r"],
                g=pt["g"],
                b=pt["b"],
                lab_l=pt["lab_l"],
                lab_a=pt["lab_a"],
                lab_b=pt["lab_b"],
                temperature=pt["temp"],
                humidity=pt["hum"]
            )
            db.session.add(point)
        db.session.commit()

    # 2. Seed Workers and Badges if empty
    if Worker.query.count() == 0:
        now = datetime.utcnow()
        created_workers = []

        for w_info in DEMO_WORKERS:
            worker = Worker(
                worker_code=w_info["worker_code"],
                name=w_info["name"],
                department=w_info["department"],
                role=w_info["role"],
                phone=w_info["phone"],
                status=w_info["status"],
                created_at=now - timedelta(days=60)
            )
            db.session.add(worker)
            db.session.flush()

            badge = Badge(
                badge_code=w_info["badge_code"],
                worker_id=worker.id,
                activation_date=now - timedelta(days=30),
                expiry_date=now + timedelta(days=w_info["expiry_days"]),
                status="ACTIVE"
            )
            db.session.add(badge)
            db.session.flush()
            created_workers.append((worker, badge))

        db.session.commit()

        # 3. Generate Historical Exposure Records for past shifts
        # Simulating ENTRY and EXIT shifts over recent days
        for worker, badge in created_workers:
            cumulative_total = 0.0
            
            # Create 3 past shifts
            for days_ago in [3, 2, 1]:
                shift_date = now - timedelta(days=days_ago)
                entry_time = shift_date.replace(hour=8, minute=random.randint(0, 15), second=0)
                exit_time = shift_date.replace(hour=17, minute=random.randint(30, 55), second=0)
                
                # Base entry reading (sensor baseline / residual)
                entry_reading = round(random.uniform(2.0, 12.0), 1)
                temp_entry = round(random.uniform(23.0, 26.0), 1)
                hum_entry = round(random.uniform(45.0, 55.0), 1)
                
                # Entry record
                entry_record = ExposureRecord(
                    worker_id=worker.id,
                    badge_id=badge.id,
                    timestamp=entry_time,
                    scan_type='ENTRY',
                    r=34, g=197, b=94,
                    lab_l=70.5, lab_a=-60.2, lab_b=41.5,
                    temperature=temp_entry,
                    humidity=hum_entry,
                    raw_exposure=entry_reading,
                    corrected_exposure=entry_reading,
                    shift_exposure=0.0,
                    cumulative_exposure=cumulative_total,
                    status='SAFE',
                    confidence=0.96
                )
                db.session.add(entry_record)

                # Exit reading
                # Give W104 higher exposure as a realistic example of high exposure monitoring
                if worker.worker_code == 'W104':
                    exit_raw = round(random.uniform(70.0, 85.0), 1)
                    temp_exit = 31.0
                    hum_exit = 72.0
                    # Environmental correction: (31-25)*0.35 + (72-50)*0.15 = 2.1 + 3.3 = 5.4
                    exit_corrected = round(exit_raw + 5.4, 1)
                    status = 'HIGH' if exit_corrected <= 100 else 'CRITICAL'
                elif worker.worker_code == 'W103':
                    exit_raw = round(random.uniform(35.0, 48.0), 1)
                    temp_exit = 27.5
                    hum_exit = 60.0
                    exit_corrected = round(exit_raw + 2.3, 1)
                    status = 'CAUTION'
                else:
                    exit_raw = round(random.uniform(12.0, 24.0), 1)
                    temp_exit = 25.0
                    hum_exit = 52.0
                    exit_corrected = round(exit_raw + 0.3, 1)
                    status = 'SAFE'

                shift_inc = max(0.0, round(exit_corrected - entry_reading, 1))
                cumulative_total = round(cumulative_total + shift_inc, 1)

                exit_record = ExposureRecord(
                    worker_id=worker.id,
                    badge_id=badge.id,
                    timestamp=exit_time,
                    scan_type='EXIT',
                    r=249 if status == 'HIGH' else (234 if status == 'CAUTION' else 34),
                    g=115 if status == 'HIGH' else (179 if status == 'CAUTION' else 197),
                    b=22 if status == 'HIGH' else (8 if status == 'CAUTION' else 94),
                    lab_l=63.1 if status == 'HIGH' else 75.3,
                    lab_a=48.2 if status == 'HIGH' else 6.2,
                    lab_b=65.5 if status == 'HIGH' else 76.4,
                    temperature=temp_exit,
                    humidity=hum_exit,
                    raw_exposure=exit_raw,
                    corrected_exposure=exit_corrected,
                    shift_exposure=shift_inc,
                    cumulative_exposure=cumulative_total,
                    status=status,
                    confidence=0.94
                )
                db.session.add(exit_record)

        db.session.commit()
