"""
End-to-End Verification Test Script for H₂SENSE
Validates Computer Vision, Calibration, Environmental Compensation,
Shift Calculation, Persistence, and REST APIs.
"""

import unittest
import json
from app import app
from models import db, Worker, Badge, ExposureRecord, CalibrationPoint
from services import ColorDetectorService, CalibrationService, ExposureService, ValidationService

class H2SenseVerificationTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app
        self.client = self.app.test_client()
        self.ctx = self.app.app_context()
        self.ctx.push()

    def tearDown(self):
        self.ctx.pop()

    def test_01_models_and_database_counts(self):
        """Verify seeded database contents."""
        workers_count = Worker.query.count()
        badges_count = Badge.query.count()
        cal_points_count = CalibrationPoint.query.count()
        records_count = ExposureRecord.query.count()

        print(f"\n[PASS] Verified Database: {workers_count} workers, {badges_count} badges, {cal_points_count} calibration points, {records_count} exposure records.")
        self.assertGreaterEqual(workers_count, 5)
        self.assertGreaterEqual(cal_points_count, 8)
        self.assertGreaterEqual(records_count, 10)

    def test_02_color_detector_service(self):
        """Test OpenCV RGB to CIELAB and HSV conversions."""
        r, g, b = 34, 197, 94
        lab_l, lab_a, lab_b = ColorDetectorService.rgb_to_cielab(r, g, b)
        h, s, v = ColorDetectorService.rgb_to_hsv(r, g, b)

        self.assertTrue(0 <= lab_l <= 100)
        self.assertTrue(-128 <= lab_a <= 128)
        self.assertTrue(-128 <= lab_b <= 128)
        self.assertTrue(0 <= h <= 360)
        print(f"[PASS] ColorDetectorService: RGB({r},{g},{b}) -> CIELAB(L*={lab_l}, a*={lab_a}, b*={lab_b}) HSV(H={h}, S={s}%, V={v}%)")

        # Test Direct RGB Swatch Generation
        direct_res = ColorDetectorService.process_rgb_direct(r, g, b)
        self.assertEqual(direct_res["hex"], "#22c55e")
        self.assertTrue(direct_res["annotated_image"].startswith("data:image/jpeg;base64,"))
        print("[PASS] ColorDetectorService: Swatch generation successful.")

    def test_03_calibration_and_environmental_compensation(self):
        """Test CIELAB calibration curve lookup and environmental correction."""
        # 75 ppm prototype color: RGB(249, 115, 22)
        color_features = {
            "r": 249, "g": 115, "b": 22,
            "lab": { "l": 63.1, "a": 48.2, "b": 65.5 }
        }
        
        # Test calibration estimate
        est = CalibrationService.estimate_exposure(color_features, 25.0, 50.0)
        self.assertAlmostEqual(est["exposure"], 75.0, delta=5.0)
        self.assertEqual(est["status"], "HIGH")
        print(f"[PASS] CalibrationService: Estimated {est['exposure']} ppm (Status: {est['status']}, Confidence: {est['confidence']})")

        # Test Environmental compensation: T=31°C, H=72%
        # baseline: T=25, H=50, coefficients: c_T=0.35, c_H=0.15
        # Expected correction: (31-25)*0.35 + (72-50)*0.15 = 2.1 + 3.3 = +5.4
        env = ExposureService.calculate_environmental_correction(est["exposure"], 31.0, 72.0)
        expected_corr = round((31.0 - 25.0)*0.35 + (72.0 - 50.0)*0.15, 1)
        self.assertEqual(env["environmental_correction"], expected_corr)
        self.assertEqual(env["corrected_exposure"], round(est["exposure"] + expected_corr, 1))
        print(f"[PASS] ExposureService: Environmental compensation raw {env['raw_exposure']} + ({env['environmental_correction']}) = {env['corrected_exposure']} ppm.")

    def test_04_shift_entry_exit_workflow(self):
        """Test complete ENTRY -> EXIT scan sequence with shift exposure delta."""
        w104 = Worker.query.filter_by(worker_code="W104").first()
        self.assertIsNotNone(w104)
        badge = w104.get_active_badge()
        self.assertIsNotNone(badge)

        prev_cumulative = w104.get_cumulative_exposure()

        # Step A: Record ENTRY Scan (e.g. 10.0 ppm)
        entry_payload = {
            "worker_id": w104.id,
            "badge_id": badge.id,
            "scan_type": "ENTRY",
            "color": { "r": 95, "g": 207, "b": 72, "lab": { "l": 74.2, "a": -49.6, "b": 53.1 } },
            "temperature": 25.0,
            "humidity": 50.0,
            "raw_exposure": 10.0,
            "confidence": 0.96
        }
        res_entry = self.client.post('/api/record-scan', data=json.dumps(entry_payload), content_type='application/json')
        self.assertEqual(res_entry.status_code, 201)
        entry_data = json.loads(res_entry.data)
        self.assertEqual(entry_data["data"]["record"]["scan_type"], "ENTRY")
        self.assertEqual(entry_data["data"]["record"]["shift_exposure"], 0.0)
        print(f"[PASS] Workflow Step 1: ENTRY scan recorded for {w104.worker_code} (Reading: {entry_data['data']['record']['corrected_exposure']}).")

        # Step B: Record EXIT Scan (e.g. 75.0 ppm raw + 5.4 env = 80.4 ppm)
        exit_payload = {
            "worker_id": w104.id,
            "badge_id": badge.id,
            "scan_type": "EXIT",
            "color": { "r": 249, "g": 115, "b": 22, "lab": { "l": 63.1, "a": 48.2, "b": 65.5 } },
            "temperature": 31.0,
            "humidity": 72.0,
            "raw_exposure": 75.0,
            "confidence": 0.94
        }
        res_exit = self.client.post('/api/record-scan', data=json.dumps(exit_payload), content_type='application/json')
        self.assertEqual(res_exit.status_code, 201)
        exit_data = json.loads(res_exit.data)
        exit_record = exit_data["data"]["record"]
        
        # Shift delta must equal Exit Corrected - Entry Corrected
        expected_shift = round(exit_record["corrected_exposure"] - entry_data["data"]["record"]["corrected_exposure"], 1)
        self.assertEqual(exit_record["shift_exposure"], expected_shift)
        self.assertEqual(exit_record["cumulative_exposure"], round(prev_cumulative + expected_shift, 1))
        print(f"[PASS] Workflow Step 2: EXIT scan recorded. Shift delta = {expected_shift} ppm. Cumulative total = {exit_record['cumulative_exposure']} ppm.")

    def test_05_insufficient_change_safe_handling(self):
        """Verify that when Exit reading < Entry reading, it is handled safely without negative exposure."""
        w101 = Worker.query.filter_by(worker_code="W101").first()
        badge = w101.get_active_badge()

        # Record high entry scan
        entry_payload = {
            "worker_id": w101.id,
            "badge_id": badge.id,
            "scan_type": "ENTRY",
            "color": { "r": 249, "g": 115, "b": 22, "lab": { "l": 63.1, "a": 48.2, "b": 65.5 } },
            "temperature": 25.0,
            "humidity": 50.0,
            "raw_exposure": 80.0,
            "confidence": 0.95
        }
        self.client.post('/api/record-scan', data=json.dumps(entry_payload), content_type='application/json')

        # Record lower exit scan (e.g. 50.0 ppm)
        exit_payload = {
            "worker_id": w101.id,
            "badge_id": badge.id,
            "scan_type": "EXIT",
            "color": { "r": 234, "g": 179, "b": 8, "lab": { "l": 75.3, "a": 6.2, "b": 76.4 } },
            "temperature": 25.0,
            "humidity": 50.0,
            "raw_exposure": 50.0,
            "confidence": 0.95
        }
        res = self.client.post('/api/record-scan', data=json.dumps(exit_payload), content_type='application/json')
        self.assertEqual(res.status_code, 201)
        data = json.loads(res.data)
        
        self.assertEqual(data["data"]["record"]["shift_exposure"], 0.0)
        self.assertIn("insufficient", data["data"]["warning"].lower())
        print(f"[PASS] Safe Non-Negative Handling: Warning returned = '{data['data']['warning']}'")

    def test_06_dashboard_and_html_views(self):
        """Verify all HTML web routes return HTTP 200."""
        routes = [
            '/',
            '/simulator',
            '/scanner',
            '/dashboard',
            '/worker-dashboard',
            '/workers',
            '/calibration',
            '/login'
        ]
        for route in routes:
            response = self.client.get(route)
            self.assertEqual(response.status_code, 200, f"Route {route} failed with status {response.status_code}")
            print(f"[PASS] HTTP 200: {route}")

    def test_07_api_dashboard_stats(self):
        """Verify aggregated telemetry endpoint."""
        res = self.client.get('/api/dashboard/stats')
        self.assertEqual(res.status_code, 200)
        data = json.loads(res.data)
        self.assertTrue(data["success"])
        self.assertIn("active_workers", data["metrics"])
        self.assertIn("risk_distribution", data)
        self.assertIn("trend_7day", data)
        self.assertIn("worker_comparison", data)
        print(f"[PASS] /api/dashboard/stats: Telemetry JSON verified with 7-day trend ({len(data['trend_7day']['labels'])} days).")

    def test_08_worker_dashboard_by_id(self):
        """Verify dedicated worker dashboard with explicit ID (e.g. /worker-dashboard/4)."""
        workers = Worker.query.all()
        for w in workers:
            res = self.client.get(f'/worker-dashboard/{w.id}')
            self.assertEqual(res.status_code, 200, f"Failed for worker ID {w.id}")
        print(f"[PASS] Verified /worker-dashboard/<id> for all {len(workers)} workers.")

    def test_09_excel_export(self):
        """Verify worker details export to Excel sheet (.xlsx)."""
        from services import ExcelService
        import os
        
        # Test direct generation & persistence
        path = ExcelService.save_workers_excel_to_file()
        self.assertTrue(os.path.exists(path))
        self.assertGreater(os.path.getsize(path), 1000)

        # Test Web route
        res_web = self.client.get('/workers/export/excel')
        self.assertEqual(res_web.status_code, 200)
        self.assertEqual(res_web.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

        # Test API route
        res_api = self.client.get('/api/workers/export')
        self.assertEqual(res_api.status_code, 200)
        self.assertEqual(res_api.content_type, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        print("[PASS] Verified Excel export feature (Workbook generated, persisted to disk, and downloaded via Web and REST API).")

if __name__ == '__main__':
    unittest.main()
