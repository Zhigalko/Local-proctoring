"""
Unit and Integration Tests for the Proctoring CV + Security System.
"""

import unittest
import numpy as np
import cv2
from pathlib import Path

from proctoring_system.config import (
    CANONICAL_FACE_3D,
    YAW_THRESHOLD_LEFT,
    YAW_THRESHOLD_RIGHT,
    PITCH_THRESHOLD_DOWN,
    INCIDENTS_JSON,
    INCIDENTS_CSV
)
from proctoring_system.logger import IncidentLogger, IncidentType, Severity
from proctoring_system.vision.detector import ObjectDetector, BoundingBox
from proctoring_system.vision.head_gaze_tracker import HeadGazeTracker
from proctoring_system.security.keyboard_locker import KeyboardLocker


class TestIncidentLogger(unittest.TestCase):

    def setUp(self):
        self.logger = IncidentLogger()

    def test_log_incident_and_screenshot(self):
        dummy_frame = np.zeros((240, 320, 3), dtype=np.uint8)
        cv2.putText(dummy_frame, "TEST INCIDENT", (20, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        record = self.logger.log_incident(
            incident_type=IncidentType.PHONE_DETECTED,
            frame=dummy_frame,
            details={"confidence": 0.92, "source": "unit_test"}
        )

        self.assertEqual(record.incident_type, IncidentType.PHONE_DETECTED.value)
        self.assertEqual(record.severity, Severity.CRITICAL.value)
        self.assertTrue(Path(record.screenshot_path).exists())

        stats = self.logger.get_stats()
        self.assertGreaterEqual(stats["total"], 1)
        self.assertIn(IncidentType.PHONE_DETECTED.value, stats["by_type"])


class TestObjectDetector(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.detector = ObjectDetector()

    def test_detector_inference_on_blank(self):
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        res = self.detector.detect(blank)
        self.assertFalse(res.is_phone_violation)
        self.assertEqual(len(res.phones), 0)

    def test_bounding_box_geometry(self):
        bbox = BoundingBox(100, 150, 300, 350)
        self.assertEqual(bbox.center, (200, 250))
        self.assertEqual(bbox.width, 200)
        self.assertEqual(bbox.height, 200)
        self.assertEqual(bbox.area, 40000)


class TestHeadGazeTracker(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.tracker = HeadGazeTracker()

    def test_tracker_on_blank_frame(self):
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        res = self.tracker.process(blank)
        self.assertTrue(res.is_no_face)
        self.assertEqual(res.face_count, 0)
        self.assertIsNone(res.head_pose)

    def test_canonical_face_geometry(self):
        self.assertEqual(CANONICAL_FACE_3D.shape, (6, 3))


class TestHeadTurnTimer(unittest.TestCase):

    def test_head_turn_continuous_timer_and_reset(self):
        """Verify continuous 3.0s timer, instant reset upon return, and anti-spam."""
        from proctoring_system.vision.vision_worker import VisionWorker
        from proctoring_system.vision.head_gaze_tracker import HeadPose
        import time

        logger = IncidentLogger()
        worker = VisionWorker(incident_logger=logger)
        worker.using_mock = True

        dummy_frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # 1. Simulate turned head for 0.8s (less than 1.5s)
        worker.sim_anomaly_mode = "LOOKING_AWAY"
        worker._process_frame(dummy_frame)
        worker.timers.head_turn_start = time.time() - 0.8
        _, m_warn = worker._process_frame(dummy_frame)
        self.assertIsNotNone(worker.timers.head_turn_start)
        self.assertFalse(worker.timers.head_turn_logged)
        self.assertEqual(m_warn["status"], "WARNING")

        # 2. Return head to center before 1.5s -> timer MUST reset to 0
        worker.sim_anomaly_mode = None
        worker._process_frame(dummy_frame)
        self.assertIsNone(worker.timers.head_turn_start)
        self.assertFalse(worker.timers.head_turn_logged)

        # 3. Simulate continuous turn >= 1.5s (e.g. 1.6s)
        worker.sim_anomaly_mode = "LOOKING_AWAY"
        worker._process_frame(dummy_frame)
        worker.timers.head_turn_start = time.time() - 1.6

        incidents_before = len(logger.incidents)
        _, metrics = worker._process_frame(dummy_frame)

        self.assertEqual(metrics["status"], "VIOLATION")
        self.assertTrue(worker.timers.head_turn_logged)
        self.assertEqual(len(logger.incidents), incidents_before + 1)
        self.assertIn("НАРУШЕНИЕ: Отвод головы зафиксирован!", metrics["warnings"])

        # 4. Anti-spam check: next frame while still turned must NOT create duplicate log entry
        _, metrics2 = worker._process_frame(dummy_frame)
        self.assertEqual(len(logger.incidents), incidents_before + 1)  # No duplicates!

        # 5. Return to center: resets timer
        worker.sim_anomaly_mode = None
        worker._process_frame(dummy_frame)
        self.assertIsNone(worker.timers.head_turn_start)
        self.assertFalse(worker.timers.head_turn_logged)


if __name__ == "__main__":
    unittest.main()
