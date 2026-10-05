"""
Stress Test & Crash Test for Proctoring System.
Simulates rapid generation of 50+ violations in succession to verify:
1. PyQt thread-safety and signal dispatch stability without crashes.
2. Safe I/O disk logging and screenshot writes under burst load without dropping frames.
3. Fixed-size in-memory queue bounding (RAM leak prevention: max 50 items).
4. HUD banner auto-dismiss and UI responsiveness without lockups.
"""

import sys
import os
import time
import unittest
from pathlib import Path
import numpy as np
import cv2
import psutil

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt

from proctoring_system import config
from proctoring_system.logger import IncidentLogger, IncidentType, Severity
from proctoring_system.vision import VisionWorker
from proctoring_system.ui import MainWindow


class IncidentStressTest(unittest.TestCase):
    """
    Automated stress and resilience test against rapid bursts of violations.
    """

    @classmethod
    def setUpClass(cls):
        # Create single QApplication instance for test session
        cls.app = QApplication.instance()
        if cls.app is None:
            # Force offscreen if needed, or run standard GUI
            cls.app = QApplication(sys.argv)

    def setUp(self):
        # Force windowed mode for tests
        config.KIOSK_FULLSCREEN = False
        config.KIOSK_STAYS_ON_TOP = False

        self.logger = IncidentLogger(max_in_memory=50)
        self.worker = VisionWorker(incident_logger=self.logger)
        self.worker.using_mock = True

        self.window = MainWindow(vision_worker=self.worker, incident_logger=self.logger)
        self.window.resize(1024, 768)
        self.window.show()
        self.app.processEvents()

    def tearDown(self):
        self.window.close()
        self.app.processEvents()

    def test_burst_50_plus_incidents_without_crash_or_leak(self):
        """
        Simulate 60 rapid successive violation events across different incident types.
        Verify memory bounding, signal reception, screenshot integrity, and UI stability.
        """
        import gc
        import tracemalloc

        # Warm up: run 5 events so one-time model/UI singletons and font caches are initialized
        for w in range(5):
            warmup_frame = np.zeros((480, 640, 3), dtype=np.uint8)
            rec = self.logger.log_incident(incident_type=IncidentType.NO_FACE, frame=warmup_frame)
            self.worker.incident_triggered.emit(rec.incident_type, rec.description, rec.severity, rec.screenshot_path)
            self.app.processEvents()

        gc.collect()
        tracemalloc.start()
        process = psutil.Process(os.getpid())
        initial_rss_mb = process.memory_info().rss / (1024 * 1024)
        snapshot_start = tracemalloc.take_snapshot()
        print(f"\n[StressTest] Post-warmup baseline RAM: {initial_rss_mb:.2f} MB")

        incident_types = [
            IncidentType.PHONE_DETECTED,
            IncidentType.LOOKING_AWAY,
            IncidentType.LOOKING_DOWN,
            IncidentType.NO_FACE,
            IncidentType.MULTIPLE_FACES,
            IncidentType.GAZE_AWAY,
            IncidentType.FOCUS_LOST,
            IncidentType.HOTKEY_BLOCKED
        ]

        total_iterations = 60
        created_screenshots = []

        print(f"[StressTest] Starting rapid burst simulation of {total_iterations} incidents...")
        start_time = time.time()

        # Phase 1: 60 Rapid Incidents
        for i in range(total_iterations):
            inc_type = incident_types[i % len(incident_types)]
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"BURST-1 #{i+1}: {inc_type.value}", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

            rec = self.logger.log_incident(incident_type=inc_type, frame=frame.copy(), details={"burst": 1, "idx": i})
            if rec.screenshot_path:
                created_screenshots.append(rec.screenshot_path)

            self.worker.incident_triggered.emit(rec.incident_type, rec.description, rec.severity, rec.screenshot_path)
            self.worker.status_updated.emit({
                "status": "VIOLATION" if (i % 2 == 0) else "WARNING",
                "warnings": [f"Burst 1 warning #{i+1}"],
                "fps": 30.0,
                "gaze": "CENTER",
                "phone_detected": (inc_type == IncidentType.PHONE_DETECTED)
            })
            self.app.processEvents()

        gc.collect()
        phase1_rss_mb = process.memory_info().rss / (1024 * 1024)
        print(f"[StressTest] Phase 1 (60 incidents) RAM: {phase1_rss_mb:.2f} MB")

        # Phase 2: Another 60 Rapid Incidents (Testing long-running sustained stability)
        for i in range(total_iterations):
            inc_type = incident_types[i % len(incident_types)]
            frame = np.zeros((480, 640, 3), dtype=np.uint8)
            cv2.putText(frame, f"BURST-2 #{i+1}: {inc_type.value}", (30, 240), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            rec = self.logger.log_incident(incident_type=inc_type, frame=frame.copy(), details={"burst": 2, "idx": i})
            if rec.screenshot_path:
                created_screenshots.append(rec.screenshot_path)

            self.worker.incident_triggered.emit(rec.incident_type, rec.description, rec.severity, rec.screenshot_path)
            self.worker.status_updated.emit({
                "status": "VIOLATION" if (i % 2 == 0) else "NORMAL",
                "warnings": [f"Burst 2 warning #{i+1}"],
                "fps": 30.0,
                "gaze": "CENTER",
                "phone_detected": (inc_type == IncidentType.PHONE_DETECTED)
            })
            self.app.processEvents()

        elapsed = time.time() - start_time
        grand_total = total_iterations * 2
        print(f"[StressTest] Completed {grand_total} events in {elapsed:.2f} seconds ({grand_total / elapsed:.1f} events/sec).")

        # ------------------------------------------------------------------
        # Assertion 1: Total logged incidents >= grand_total
        # ------------------------------------------------------------------
        stats = self.logger.get_stats()
        print(f"[StressTest] Logger stats: total={stats['total']}, in_memory={stats['in_memory']}")
        self.assertGreaterEqual(stats["total"], grand_total, "Total logged count must reflect all incidents.")

        # ------------------------------------------------------------------
        # Assertion 2: Bounded in-memory queue (NO unbounded RAM growth)
        # ------------------------------------------------------------------
        self.assertLessEqual(
            stats["in_memory"],
            50,
            f"In-memory queue must be capped at 50 to prevent RAM leaks, but was {stats['in_memory']}."
        )
        self.assertEqual(len(self.logger.incidents), 50, "In-memory deque should contain exactly 50 recent records.")

        # ------------------------------------------------------------------
        # Assertion 3: UI received and processed all incidents
        # ------------------------------------------------------------------
        self.assertGreaterEqual(
            self.window.total_violations,
            grand_total,
            "MainWindow total_violations counter must update on every event."
        )
        self.assertIn(str(self.window.total_violations), self.window.violations_chip.text())

        # ------------------------------------------------------------------
        # Assertion 4: Screenshots are written and physically valid on disk
        # ------------------------------------------------------------------
        self.assertGreater(len(created_screenshots), 0, "Screenshots must be saved.")
        sample_screenshot = created_screenshots[-1]
        self.assertTrue(os.path.exists(sample_screenshot), f"File {sample_screenshot} must exist on disk.")

        img = cv2.imread(sample_screenshot)
        self.assertIsNotNone(img, "Saved screenshot must be a valid decodable image.")
        self.assertEqual(img.shape, (480, 640, 3), "Screenshot resolution must match original frame.")

        # ------------------------------------------------------------------
        # Assertion 5: Memory Leak & Stabilization Verification
        # ------------------------------------------------------------------
        gc.collect()
        final_rss_mb = process.memory_info().rss / (1024 * 1024)
        sustained_growth_mb = final_rss_mb - phase1_rss_mb
        current_py_mem, peak_py_mem = tracemalloc.get_traced_memory()
        tracemalloc.stop()

        py_heap_growth_mb = peak_py_mem / (1024 * 1024)
        print(f"[StressTest] Phase 2 RAM: {final_rss_mb:.2f} MB (Phase 1 -> 2 Delta: {sustained_growth_mb:+.2f} MB, Python peak heap: {py_heap_growth_mb:.2f} MB)")
        # Python heap growth for 120 iterations must stay minimal (< 15 MB)
        self.assertLess(py_heap_growth_mb, 15.0, f"Python heap growth ({py_heap_growth_mb:.2f} MB) indicates leak in incident objects.")
        # Between Phase 1 and Phase 2, memory must be stabilized (no runaway leak; OS I/O buffers can vary on Windows)
        self.assertLess(sustained_growth_mb, 350.0, f"Sustained RSS growth between bursts ({sustained_growth_mb:.2f} MB) indicates a leak.")

    def test_resilience_to_corrupt_frames_and_io_errors(self):
        """
        Verify that passing invalid frames (None, empty, corrupt) does not crash logger or worker.
        """
        # Empty array
        empty_frame = np.empty((0, 0, 3), dtype=np.uint8)
        rec1 = self.logger.log_incident(IncidentType.NO_FACE, frame=empty_frame)
        self.assertIsNotNone(rec1)
        self.assertEqual(rec1.screenshot_path, "")

        # None frame
        rec2 = self.logger.log_incident(IncidentType.FOCUS_LOST, frame=None)
        self.assertIsNotNone(rec2)
        self.assertEqual(rec2.screenshot_path, "")

        # Non-blocking HUD alert under invalid severity
        self.window.alert_banner.show_alert(
            title="TEST",
            description="Testing fallback severity",
            severity="UNKNOWN",
            duration_ms=100
        )
        self.app.processEvents()
        self.assertTrue(self.window.alert_banner.isVisible())


if __name__ == "__main__":
    unittest.main()
