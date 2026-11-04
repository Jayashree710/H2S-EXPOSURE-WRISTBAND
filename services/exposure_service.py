from config import Config
from models import db, ExposureRecord, Worker, Badge

class ExposureService:
    """
    Centralized Exposure Calculation and Environmental Compensation Service.
    
    Handles:
    - Prototype environmental correction (Temperature & Humidity compensation)
    - Shift exposure delta calculation (Exit - Entry, handling non-positive deltas safely)
    - Cumulative worker/badge exposure aggregation
    - Centralized risk classification with semantic CSS classes and advisory alerts
    """

    @classmethod
    def calculate_environmental_correction(cls, raw_exposure: float, temperature: float, humidity: float):
        """
        Applies prototype environmental compensation.
        Formula:
        delta_env = c_T * (T - T_baseline) + c_H * (H - H_baseline)
        corrected = max(0, raw_exposure + delta_env)
        """
        temp_delta = float(temperature) - Config.TEMP_BASELINE
        hum_delta = float(humidity) - Config.HUMIDITY_BASELINE

        # Prototype correction factors
        temp_effect = Config.TEMP_COEFFICIENT * temp_delta
        hum_effect = Config.HUMIDITY_COEFFICIENT * hum_delta
        
        correction = round(temp_effect + hum_effect, 1)
        corrected = max(0.0, round(raw_exposure + correction, 1))

        return {
            "raw_exposure": round(float(raw_exposure), 1),
            "environmental_correction": correction,
            "corrected_exposure": corrected,
            "baseline_temp": Config.TEMP_BASELINE,
            "baseline_hum": Config.HUMIDITY_BASELINE,
            "temperature_used": temperature,
            "humidity_used": humidity,
            "formula_note": "Prototype environmental compensation: delta = 0.35*(T-25) + 0.15*(H-50)"
        }

    @classmethod
    def classify_exposure(cls, value: float):
        """
        Centralized risk classification based on prototype thresholds.
        Returns:
        {
            "status": "SAFE" | "CAUTION" | "HIGH" | "CRITICAL",
            "label": str,
            "severity": int,
            "display_message": str,
            "css_class": str
        }
        """
        val = float(value)
        if val <= Config.THRESHOLD_SAFE:
            return {
                "status": "SAFE",
                "label": "Safe / Baseline",
                "severity": 1,
                "display_message": "Exposure within acceptable prototype baseline limit (< 25 ppm).",
                "css_class": "status-safe",
                "badge_class": "badge-safe",
                "color_code": "#22c55e"
            }
        elif val <= Config.THRESHOLD_CAUTION:
            return {
                "status": "CAUTION",
                "label": "Caution / Elevated",
                "severity": 2,
                "display_message": "Moderate exposure detected (25–50 ppm). Monitor worker closely.",
                "css_class": "status-caution",
                "badge_class": "badge-caution",
                "color_code": "#eab308"
            }
        elif val <= Config.THRESHOLD_HIGH:
            return {
                "status": "HIGH",
                "label": "High Risk Exposure",
                "severity": 3,
                "display_message": "High exposure detected (50–100 ppm). Mandatory safety review required.",
                "css_class": "status-high",
                "badge_class": "badge-high",
                "color_code": "#f97316"
            }
        else:
            return {
                "status": "CRITICAL",
                "label": "Critical Danger Level",
                "severity": 4,
                "display_message": "CRITICAL: Severe exposure (> 100 ppm). Evacuation protocol recommended.",
                "css_class": "status-critical",
                "badge_class": "badge-critical",
                "color_code": "#ef4444"
            }

    @classmethod
    def get_latest_entry_scan(cls, worker_id: int):
        """Finds the most recent ENTRY scan for this worker."""
        return ExposureRecord.query.filter_by(
            worker_id=worker_id, 
            scan_type='ENTRY'
        ).order_by(ExposureRecord.timestamp.desc()).first()

    @classmethod
    def process_scan_record(cls, worker_id: int, badge_id: int, scan_type: str, 
                            color_data: dict, temperature: float, humidity: float, 
                            raw_exposure: float, confidence: float):
        """
        Records a new ENTRY or EXIT scan, computes shift increment,
        updates cumulative exposure, and persists the record.
        """
        # Environmental correction
        env_result = cls.calculate_environmental_correction(raw_exposure, temperature, humidity)
        corrected_exposure = env_result["corrected_exposure"]

        # Classification
        class_info = cls.classify_exposure(corrected_exposure)

        # Cumulative calculation: get previous total
        previous_records = ExposureRecord.query.filter_by(worker_id=worker_id).all()
        current_cumulative = sum(r.shift_exposure for r in previous_records if r.shift_exposure > 0)

        shift_exposure = 0.0
        warning_message = None

        if scan_type == 'EXIT':
            latest_entry = cls.get_latest_entry_scan(worker_id)
            if latest_entry:
                entry_val = latest_entry.corrected_exposure
                if corrected_exposure < entry_val:
                    # Reading decreased or insufficient change
                    shift_exposure = 0.0
                    warning_message = "Reading change is insufficient to calculate a valid shift increment."
                else:
                    shift_exposure = round(corrected_exposure - entry_val, 1)
            else:
                # No prior entry scan recorded today; treat whole reading as shift estimate
                shift_exposure = corrected_exposure
                warning_message = "No prior ENTRY scan found for this shift. Current reading recorded as shift estimate."

            new_cumulative = round(current_cumulative + shift_exposure, 1)
        else:
            # ENTRY scan sets the baseline for the shift; shift exposure is 0
            shift_exposure = 0.0
            new_cumulative = round(current_cumulative, 1)

        # Create record
        record = ExposureRecord(
            worker_id=worker_id,
            badge_id=badge_id,
            scan_type=scan_type,
            r=color_data.get('r', 0),
            g=color_data.get('g', 0),
            b=color_data.get('b', 0),
            lab_l=color_data.get('lab', {}).get('l', 0.0),
            lab_a=color_data.get('lab', {}).get('a', 0.0),
            lab_b=color_data.get('lab', {}).get('b', 0.0),
            temperature=temperature,
            humidity=humidity,
            raw_exposure=raw_exposure,
            corrected_exposure=corrected_exposure,
            shift_exposure=shift_exposure,
            cumulative_exposure=new_cumulative,
            status=class_info["status"],
            confidence=confidence
        )

        db.session.add(record)
        db.session.commit()

        return {
            "record": record.to_dict(),
            "warning": warning_message,
            "classification": class_info,
            "env_breakdown": env_result
        }
