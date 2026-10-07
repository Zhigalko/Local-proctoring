"""
Unit tests for SessionReportManager and AdminDashboard logic.
"""

import unittest
import sys
from pathlib import Path
from datetime import datetime

# Ensure project root in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
from proctoring_system.config import REPORTS_DIR
from proctoring_system.reports_manager import SessionReportManager
from proctoring_system.ui.admin_dashboard import AdminDashboardWindow

app = QApplication.instance() or QApplication(sys.argv)


class TestAdminDashboard(unittest.TestCase):

    def test_ensure_demo_sessions_and_list(self):
        SessionReportManager.ensure_demo_sessions()
        sessions = SessionReportManager.list_sessions()
        self.assertGreaterEqual(len(sessions), 3)

        # Check fields of first session
        s0 = sessions[0]
        self.assertIn("student_name", s0)
        self.assertIn("score", s0)
        self.assertIn("status", s0)
        self.assertIn("incidents", s0)

    def test_export_html_and_csv(self):
        sessions = SessionReportManager.list_sessions()
        self.assertTrue(len(sessions) > 0)

        s_dir = Path(sessions[0]["folder_path"])
        html_out = s_dir / "test_export.html"
        csv_out = s_dir / "test_export.csv"

        ok_html = SessionReportManager.export_session_html(s_dir, html_out)
        self.assertTrue(ok_html)
        self.assertTrue(html_out.exists())

        ok_csv = SessionReportManager.export_session_csv(s_dir, csv_out)
        self.assertTrue(ok_csv)
        self.assertTrue(csv_out.exists())

        # Cleanup test files
        if html_out.exists():
            html_out.unlink()
        if csv_out.exists():
            csv_out.unlink()

    def test_admin_dashboard_window_init(self):
        window = AdminDashboardWindow()
        self.assertIsNotNone(window)
        self.assertGreaterEqual(len(window.all_sessions), 3)
        self.assertGreaterEqual(window.sessions_list.count(), 3)
        window.close()


if __name__ == "__main__":
    unittest.main()
