"""
Standalone Entry Point for Admin / Proctor Dashboard.
Allows instructors to inspect exam sessions, violation timelines, evidence screenshots, and export reports.
"""

import sys
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PyQt6.QtWidgets import QApplication
from proctoring_system.ui.admin_dashboard import AdminDashboardWindow


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Proctor Admin Dashboard")
    window = AdminDashboardWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
