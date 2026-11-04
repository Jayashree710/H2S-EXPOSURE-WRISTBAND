import math
import numpy as np
from models.calibration import CalibrationPoint

class CalibrationService:
    """
    Reference Calibration Model Service.
    
    Translates extracted color metrics (RGB & CIELAB) to estimated exposure (units/ppm)
    using inverse-distance-weighted interpolation and piecewise linear regression
    against calibrated reference points.
    """

    # Fallback calibration reference points if database is temporarily uninitialized
    DEFAULT_CURVE = [
        {"exposure": 0.0,   "r": 34,  "g": 197, "b": 94,  "lab_l": 70.5, "lab_a": -60.2, "lab_b": 41.5},
        {"exposure": 10.0,  "r": 95,  "g": 207, "b": 72,  "lab_l": 74.2, "lab_a": -49.6, "lab_b": 53.1},
        {"exposure": 25.0,  "r": 163, "g": 230, "b": 53,  "lab_l": 83.1, "lab_a": -38.4, "lab_b": 68.2},
        {"exposure": 50.0,  "r": 234, "g": 179, "b": 8,   "lab_l": 75.3, "lab_a": 6.2,   "lab_b": 76.4},
        {"exposure": 75.0,  "r": 249, "g": 115, "b": 22,  "lab_l": 63.1, "lab_a": 48.2,  "lab_b": 65.5},
        {"exposure": 100.0, "r": 239, "g": 68,  "b": 68,  "lab_l": 53.2, "lab_a": 67.1,  "lab_b": 48.8},
        {"exposure": 150.0, "r": 185, "g": 28,  "b": 28,  "lab_l": 37.4, "lab_a": 61.5,  "lab_b": 43.2},
        {"exposure": 200.0, "r": 127, "g": 29,  "b": 29,  "lab_l": 26.8, "lab_a": 44.9,  "lab_b": 28.6},
    ]

    @classmethod
    def get_calibration_points(cls):
        """Retrieves calibration points from MySQL database, falling back to default curve."""
        try:
            points = CalibrationPoint.query.order_by(CalibrationPoint.exposure_value.asc()).all()
            if points and len(points) >= 2:
                return [p.to_dict() for p in points]
        except Exception:
            pass
        return cls.DEFAULT_CURVE

    @staticmethod
    def delta_e_cie76(l1, a1, b1, l2, a2, b2):
        """Calculates standard Euclidean distance in CIELAB space."""
        return math.sqrt((l1 - l2)**2 + (a1 - a2)**2 + (b1 - b2)**2)

    @classmethod
    def estimate_exposure(cls, color_features: dict, temperature: float = 25.0, humidity: float = 50.0):
        """
        Estimates exposure from extracted color features (RGB and LAB).
        Uses inverse distance weighting across closest reference points in CIELAB space.
        
        Returns:
        {
            "exposure": float,
            "confidence": float,
            "status": str,
            "method": str
        }
        """
        lab = color_features.get('lab', {})
        target_l = float(lab.get('l', 70.0))
        target_a = float(lab.get('a', -50.0))
        target_b = float(lab.get('b', 50.0))

        points = cls.get_calibration_points()

        # Calculate Delta E to each reference point
        distances = []
        for pt in points:
            d_e = cls.delta_e_cie76(
                target_l, target_a, target_b,
                float(pt['lab_l']), float(pt['lab_a']), float(pt['lab_b'])
            )
            distances.append((d_e, float(pt['exposure_value'] if 'exposure_value' in pt else pt['exposure'])))

        # Sort by distance
        distances.sort(key=lambda x: x[0])

        min_distance = distances[0][0]

        # Exact or virtually exact match
        if min_distance < 0.5:
            estimated_raw = distances[0][1]
            confidence = 0.98
        else:
            # Weighted interpolation between top 3 closest reference points
            k = min(3, len(distances))
            weights = []
            values = []
            
            for d, exp_val in distances[:k]:
                # Inverse distance weighting with power 2
                w = 1.0 / (max(d, 0.1) ** 2)
                weights.append(w)
                values.append(exp_val)
            
            estimated_raw = sum(w * v for w, v in zip(weights, values)) / sum(weights)
            
            # Confidence decreases smoothly if distance is large
            confidence = max(0.50, min(0.99, round(1.0 - (min_distance / 120.0), 2)))

        estimated_raw = max(0.0, round(estimated_raw, 1))

        # Classify status based on standard prototype thresholds
        if estimated_raw <= 25.0:
            status = 'SAFE'
        elif estimated_raw <= 50.0:
            status = 'CAUTION'
        elif estimated_raw <= 100.0:
            status = 'HIGH'
        else:
            status = 'CRITICAL'

        return {
            "exposure": estimated_raw,
            "confidence": confidence,
            "status": status,
            "method": "prototype_cielab_interpolation"
        }
