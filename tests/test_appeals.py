"""
Tests for Student Appeals System and Teacher Review Workflow in Local Proctoring.
"""

import unittest
import tempfile
import json
import shutil
from pathlib import Path
from datetime import datetime

from PyQt6.QtWidgets import QApplication

from proctoring_system.reports_manager import SessionReportManager
from proctoring_system.ui.admin_dashboard import AdminDashboardWindow, ImagePreviewModal


class TestAppealsSystem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])

    def setUp(self):
        self.test_dir = Path(tempfile.mkdtemp(prefix="test_proctor_appeals_"))
        self.orig_reports_dir = SessionReportManager

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_submit_appeal_and_schema(self):
        """Verifies incident structure and student appeal submission in summary.json."""
        start = datetime.now()
        end = datetime.now()

        incidents = [
            {
                "incident_type": "PHONE_DETECTED",
                "severity": "CRITICAL",
                "description": "Обнаружен смартфон в рабочей зоне",
                "timestamp": start.isoformat(),
                "details": {"duration": 2.2},
                "screenshot_path": ""
            }
        ]

        # Temporarily point REPORTS_DIR to our isolated test directory
        from proctoring_system import reports_manager
        orig_dir = reports_manager.REPORTS_DIR
        reports_manager.REPORTS_DIR = self.test_dir

        try:
            session_dir = SessionReportManager.save_session(
                student_name="Кузнецов Иван Петрович",
                start_time=start,
                end_time=end,
                correct_count=9,
                total_count=10,
                score_pct=90,
                time_spent="08:15",
                incidents=incidents
            )

            # Check initial summary.json
            with open(session_dir / "summary.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            self.assertEqual(len(data["incidents"]), 1)
            inc = data["incidents"][0]
            self.assertEqual(inc["incident_id"], "inc_001")
            self.assertEqual(inc["type"], "PHONE_DETECTED")
            self.assertIn(":", inc["timestamp"])
            self.assertIsNone(inc.get("appeal"))

            # Submit student appeal
            appeal_res = SessionReportManager.submit_appeal(
                session_dir,
                "inc_001",
                "Ложное срабатывание (в руке был предмет, а не телефон)",
                "В руке был калькулятор Casio, решал задачу по матрице камеры."
            )

            self.assertIsNotNone(appeal_res)
            self.assertEqual(appeal_res["status"], "pending")
            self.assertEqual(appeal_res["reason"], "Ложное срабатывание (в руке был предмет, а не телефон)")
            self.assertIn("калькулятор", appeal_res["comment"])

            # Verify saved on disk
            with open(session_dir / "summary.json", "r", encoding="utf-8") as f:
                updated_data = json.load(f)

            saved_appeal = updated_data["incidents"][0]["appeal"]
            self.assertIsNotNone(saved_appeal)
            self.assertEqual(saved_appeal["status"], "pending")
            self.assertEqual(saved_appeal["reason"], "Ложное срабатывание (в руке был предмет, а не телефон)")
            self.assertEqual(saved_appeal["teacher_comment"], "")
        finally:
            reports_manager.REPORTS_DIR = orig_dir

    def test_review_appeal_approved(self):
        """Verifies instructor approving an appeal and recalculating session status."""
        from proctoring_system import reports_manager
        orig_dir = reports_manager.REPORTS_DIR
        reports_manager.REPORTS_DIR = self.test_dir

        try:
            start = datetime.now()
            end = datetime.now()
            incidents = [
                {
                    "incident_type": "LOOKING_AWAY",
                    "severity": "HIGH",
                    "description": "Отвод головы вправо",
                    "timestamp": start.isoformat(),
                    "details": {"duration": 1.7},
                    "screenshot_path": ""
                }
            ]

            session_dir = SessionReportManager.save_session(
                student_name="Сергеева Ольга",
                start_time=start,
                end_time=end,
                correct_count=8,
                total_count=10,
                score_pct=80,
                time_spent="10:00",
                incidents=incidents
            )

            SessionReportManager.submit_appeal(
                session_dir,
                "inc_001",
                "Посмотрел на клавиатуру / в черновик",
                "Сверял записи в черновике."
            )

            # Instructor approves appeal
            ok = SessionReportManager.review_appeal(
                session_dir,
                "inc_001",
                "approved",
                "Нарушение аннулировано: движение взгляда обосновано."
            )
            self.assertTrue(ok)

            with open(session_dir / "summary.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            app = data["incidents"][0]["appeal"]
            self.assertEqual(app["status"], "approved")
            self.assertEqual(app["teacher_comment"], "Нарушение аннулировано: движение взгляда обосновано.")
            self.assertEqual(data["effective_violations"], 0)
            self.assertEqual(data["status"], "CLEAN")
            self.assertEqual(data["status_ru"], "Чисто")
        finally:
            reports_manager.REPORTS_DIR = orig_dir

    def test_review_appeal_rejected(self):
        """Verifies instructor rejecting an appeal with comments."""
        from proctoring_system import reports_manager
        orig_dir = reports_manager.REPORTS_DIR
        reports_manager.REPORTS_DIR = self.test_dir

        try:
            start = datetime.now()
            end = datetime.now()
            incidents = [
                {
                    "incident_type": "PHONE_DETECTED",
                    "severity": "CRITICAL",
                    "description": "Обнаружен телефон",
                    "timestamp": start.isoformat(),
                    "details": {"duration": 3.0},
                    "screenshot_path": ""
                }
            ]

            session_dir = SessionReportManager.save_session(
                student_name="Ковалев Артем",
                start_time=start,
                end_time=end,
                correct_count=6,
                total_count=10,
                score_pct=60,
                time_spent="05:30",
                incidents=incidents
            )

            SessionReportManager.submit_appeal(
                session_dir,
                "inc_001",
                "Ложное срабатывание (в руке был предмет, а не телефон)",
                "В руке был блокнот."
            )

            ok = SessionReportManager.review_appeal(
                session_dir,
                "inc_001",
                "rejected",
                "Отклонено. На снимке четко виден экран мобильного устройства."
            )
            self.assertTrue(ok)

            with open(session_dir / "summary.json", "r", encoding="utf-8") as f:
                data = json.load(f)

            app = data["incidents"][0]["appeal"]
            self.assertEqual(app["status"], "rejected")
            self.assertEqual(app["teacher_comment"], "Отклонено. На снимке четко виден экран мобильного устройства.")
            self.assertEqual(data["effective_violations"], 1)
        finally:
            reports_manager.REPORTS_DIR = orig_dir

    def test_exports_contain_appeal_data(self):
        """Verifies HTML and CSV reports include appeal information."""
        from proctoring_system import reports_manager
        orig_dir = reports_manager.REPORTS_DIR
        reports_manager.REPORTS_DIR = self.test_dir

        try:
            start = datetime.now()
            end = datetime.now()
            incidents = [
                {
                    "incident_type": "PHONE_DETECTED",
                    "severity": "CRITICAL",
                    "description": "Телефон в кадре",
                    "timestamp": start.isoformat(),
                    "details": {"duration": 2.0},
                    "screenshot_path": ""
                }
            ]

            session_dir = SessionReportManager.save_session(
                student_name="Тестовый Студент",
                start_time=start,
                end_time=end,
                correct_count=7,
                total_count=10,
                score_pct=70,
                time_spent="07:00",
                incidents=incidents
            )

            SessionReportManager.submit_appeal(
                session_dir,
                "inc_001",
                "Ложное срабатывание (в руке был предмет, а не телефон)",
                "Держал футляр от очков."
            )

            # Export HTML
            html_file = self.test_dir / "report.html"
            ok_html = SessionReportManager.export_session_html(session_dir, html_file)
            self.assertTrue(ok_html)
            html_text = html_file.read_text(encoding="utf-8")
            self.assertIn("На рассмотрении", html_text)
            self.assertIn("футляр от очков", html_text)

            # Export CSV
            csv_file = self.test_dir / "report.csv"
            ok_csv = SessionReportManager.export_session_csv(session_dir, csv_file)
            self.assertTrue(ok_csv)
            csv_text = csv_file.read_text(encoding="utf-8")
            self.assertIn("AppealStatus", csv_text)
            self.assertIn("pending", csv_text)
            self.assertIn("футляр от очков", csv_text)
        finally:
            reports_manager.REPORTS_DIR = orig_dir


if __name__ == "__main__":
    unittest.main()
