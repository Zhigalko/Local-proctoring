"""
Runtime smoke test for the full application.
Launches the proctoring app in windowed mode, runs for 3 seconds, verifies signals, then closes cleanly.
"""

import sys
import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from proctoring_system import config
from proctoring_system.logger import IncidentLogger
from proctoring_system.vision import VisionWorker
from proctoring_system.security import KeyboardLocker
from proctoring_system.ui import MainWindow

def run_smoke_test():
    print("[SmokeTest] Starting application smoke test...")
    app = QApplication(sys.argv)

    config.KIOSK_FULLSCREEN = False
    config.KIOSK_STAYS_ON_TOP = False
    config.ENABLE_MOCK_FALLBACK = True

    logger = IncidentLogger()
    worker = VisionWorker(incident_logger=logger)
    worker.using_mock = True  # Smoke test uses deterministic synthetic generator

    window = MainWindow(vision_worker=worker, incident_logger=logger)
    window.resize(1024, 700)
    window.show()

    frames_received = 0
    def count_frame(q_img):
        nonlocal frames_received
        frames_received += 1

    worker.frame_ready.connect(count_frame)
    worker.start()

    # Test keyboard locker initialization
    locker = KeyboardLocker()
    locker.start()
    time.sleep(0.1)
    locker.stop()
    print("[SmokeTest] Keyboard locker started and stopped cleanly.")

    # Timer to close app after 2.5 seconds
    def auto_close():
        print(f"[SmokeTest] Auto-closing after test period. Total frames received: {frames_received}")
        assert frames_received > 5, f"Expected >5 frames, got {frames_received}"
        worker.stop()
        window.close()
        app.exit(0)

    QTimer.singleShot(2500, auto_close)
    exit_code = app.exec()
    print(f"[SmokeTest] Smoke test completed successfully with exit code: {exit_code}")

if __name__ == "__main__":
    run_smoke_test()
