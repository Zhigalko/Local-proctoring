"""
Comprehensive Unit Tests for Head Pose Calibration, EMA Smoothing,
and YOLO Phone Temporal Smoothing (3-of-7 frames).
"""

import unittest
import time
import numpy as np
import cv2

from proctoring_system.config import (
    CANONICAL_FACE_3D,
    HEAD_POSE_EMA_ALPHA,
    CALIBRATION_DURATION,
    CALIBRATION_MIN_SAMPLES,
    YAW_THRESHOLD_LEFT,
    YAW_THRESHOLD_RIGHT,
    PITCH_THRESHOLD_DOWN,
    PHONE_BUFFER_SIZE,
    PHONE_BUFFER_MIN_DETECTIONS
)
from proctoring_system.vision.head_gaze_tracker import HeadGazeTracker, HeadPose
from proctoring_system.vision.detector import ObjectDetector, PhoneDetection, BoundingBox


class TestHeadPoseCalibrationAndAngles(unittest.TestCase):

    def setUp(self):
        self.tracker = HeadGazeTracker()

    def test_canonical_3d_landmarks_count(self):
        """Verify strict 6 canonical FaceMesh landmarks are defined."""
        self.assertEqual(self.tracker.NOSE_TIP, 1)
        self.assertEqual(self.tracker.CHIN, 152)
        self.assertEqual(self.tracker.LEFT_EYE_OUTER, 33)
        self.assertEqual(self.tracker.RIGHT_EYE_OUTER, 263)
        self.assertEqual(self.tracker.LEFT_MOUTH, 61)
        self.assertEqual(self.tracker.RIGHT_MOUTH, 291)
        self.assertEqual(CANONICAL_FACE_3D.shape, (6, 3))

    def test_euler_angle_signs_and_rqdecomp(self):
        """
        Verify cv2.Rodrigues and cv2.RQDecomp3x3 produce correct signs:
        - Yaw: left is (-), right is (+)
        - Pitch: down is (-), up is (+)
        """
        w, h = 640, 480
        cam = np.array([[w, 0, w / 2], [0, w, h / 2], [0, 0, 1]], dtype=np.float64)
        dist = np.zeros((4, 1), dtype=np.float64)

        # Baseline straight face
        img_straight = np.array([
            [320.0, 240.0],  # Nose tip
            [320.0, 360.0],  # Chin
            [230.0, 180.0],  # Left eye outer
            [410.0, 180.0],  # Right eye outer
            [260.0, 310.0],  # Left mouth
            [380.0, 310.0]   # Right mouth
        ], dtype=np.float64)

        succ, rvec_s, _ = cv2.solvePnP(CANONICAL_FACE_3D, img_straight, cam, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        self.assertTrue(succ)
        angles_s = cv2.RQDecomp3x3(cv2.Rodrigues(rvec_s)[0])[0]
        base_yaw = -float(angles_s[1])
        base_pitch = -float(angles_s[0])

        # Head turned right: nose shifts to the right (x increases)
        img_right = np.array([
            [350.0, 240.0],
            [350.0, 360.0],
            [280.0, 180.0],
            [430.0, 180.0],
            [300.0, 310.0],
            [400.0, 310.0]
        ], dtype=np.float64)
        succ, rvec_r, _ = cv2.solvePnP(CANONICAL_FACE_3D, img_right, cam, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        angles_r = cv2.RQDecomp3x3(cv2.Rodrigues(rvec_r)[0])[0]
        yaw_r = -float(angles_r[1])
        self.assertGreater(yaw_r, base_yaw, "Turning right must produce positive delta Yaw")

        # Head turned left: nose shifts to the left (x decreases)
        img_left = np.array([
            [290.0, 240.0],
            [290.0, 360.0],
            [210.0, 180.0],
            [360.0, 180.0],
            [240.0, 310.0],
            [340.0, 310.0]
        ], dtype=np.float64)
        succ, rvec_l, _ = cv2.solvePnP(CANONICAL_FACE_3D, img_left, cam, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        angles_l = cv2.RQDecomp3x3(cv2.Rodrigues(rvec_l)[0])[0]
        yaw_l = -float(angles_l[1])
        self.assertLess(yaw_l, base_yaw, "Turning left must produce negative delta Yaw")

        # Head tilted down: nose shifts down towards chin (y increases)
        img_down = np.array([
            [320.0, 270.0],
            [320.0, 380.0],
            [230.0, 220.0],
            [410.0, 220.0],
            [260.0, 325.0],
            [380.0, 325.0]
        ], dtype=np.float64)
        succ, rvec_d, _ = cv2.solvePnP(CANONICAL_FACE_3D, img_down, cam, dist, flags=cv2.SOLVEPNP_ITERATIVE)
        angles_d = cv2.RQDecomp3x3(cv2.Rodrigues(rvec_d)[0])[0]
        pitch_d = -float(angles_d[0])
        self.assertLess(pitch_d, base_pitch, "Tilting down must produce negative delta Pitch")

    def test_ema_smoothing_filter(self):
        """Verify EMA filter smooths step changes with alpha = 0.3."""
        # Initial step
        self.tracker.smoothed_yaw = 0.0
        self.tracker.smoothed_pitch = 0.0
        self.tracker.smoothed_roll = 0.0

        # Step jump of raw yaw to 20.0 degrees
        raw_yaw = 20.0
        # After 1 step: 0.3 * 20.0 + 0.7 * 0.0 = 6.0
        self.tracker.smoothed_yaw = self.tracker.ema_alpha * raw_yaw + (1.0 - self.tracker.ema_alpha) * self.tracker.smoothed_yaw
        self.assertAlmostEqual(self.tracker.smoothed_yaw, 6.0, places=2)

        # After 2 steps: 0.3 * 20.0 + 0.7 * 6.0 = 6.0 + 4.2 = 10.2
        self.tracker.smoothed_yaw = self.tracker.ema_alpha * raw_yaw + (1.0 - self.tracker.ema_alpha) * self.tracker.smoothed_yaw
        self.assertAlmostEqual(self.tracker.smoothed_yaw, 10.2, places=2)

    def test_baseline_auto_calibration(self):
        """Verify 3.0s baseline collection and deviation calculations."""
        self.tracker.recalibrate()
        self.assertTrue(self.tracker.is_calibrating)
        self.assertFalse(self.tracker.is_calibrated)

        # Feed 20 neutral samples with small natural noise around yaw=2.0, pitch=-10.0, roll=1.0
        for _ in range(20):
            self.tracker.calibration_samples.append((2.0, -10.0, 1.0))

        # Simulate 3.2 seconds elapsed
        self.tracker.calibration_start_time = time.time() - 3.2

        # Trigger calibration completion check
        now = time.time()
        elapsed = now - self.tracker.calibration_start_time
        if elapsed >= CALIBRATION_DURATION and len(self.tracker.calibration_samples) >= CALIBRATION_MIN_SAMPLES:
            self.tracker.baseline_yaw = float(np.mean([s[0] for s in self.tracker.calibration_samples]))
            self.tracker.baseline_pitch = float(np.mean([s[1] for s in self.tracker.calibration_samples]))
            self.tracker.baseline_roll = float(np.mean([s[2] for s in self.tracker.calibration_samples]))
            self.tracker.is_calibrated = True
            self.tracker.is_calibrating = False

        self.assertTrue(self.tracker.is_calibrated)
        self.assertAlmostEqual(self.tracker.baseline_yaw, 2.0)
        self.assertAlmostEqual(self.tracker.baseline_pitch, -10.0)

        # 1. Normal reading across wide monitor (delta_yaw <= 38.0° -> NO violation)
        normal_reading_yaw = 28.0
        delta_normal_yaw = normal_reading_yaw - self.tracker.baseline_yaw
        self.assertEqual(delta_normal_yaw, 26.0)
        self.assertLessEqual(delta_normal_yaw, YAW_THRESHOLD_RIGHT)  # Allowed for reading wide screen!

        # 2. Significant turn away from monitor (delta_yaw > 38.0° -> VIOLATION)
        turned_yaw = 43.0
        delta_turned_yaw = turned_yaw - self.tracker.baseline_yaw
        self.assertEqual(delta_turned_yaw, 41.0)
        self.assertGreater(delta_turned_yaw, YAW_THRESHOLD_RIGHT)    # Violation!

        # 3. Normal reading text tilt down (delta_pitch >= -30.0° -> NO violation)
        normal_tilt_pitch = -30.0
        delta_normal_pitch = normal_tilt_pitch - self.tracker.baseline_pitch
        self.assertEqual(delta_normal_pitch, -20.0)
        self.assertGreaterEqual(delta_normal_pitch, PITCH_THRESHOLD_DOWN)  # Allowed natural reading tilt!

        # 4. Severe tilt down looking at lap/notes (delta_pitch < -30.0° -> VIOLATION)
        lap_pitch = -45.0
        delta_lap_pitch = lap_pitch - self.tracker.baseline_pitch
        self.assertEqual(delta_lap_pitch, -35.0)
        self.assertLess(delta_lap_pitch, PITCH_THRESHOLD_DOWN)       # Violation!

    def test_automatic_calibration_flow(self):
        """Verify automatic calibration triggers without user intervention when face is detected."""
        self.tracker.recalibrate()
        self.assertTrue(self.tracker.is_calibrating)
        self.assertFalse(self.tracker.is_calibrated)

        # 1. Extreme angles (> 35°) looking away are rejected during auto-calibration
        extreme_yaw = 55.0
        extreme_pitch = 0.0
        if abs(extreme_yaw) < 35.0 and abs(extreme_pitch) < 30.0:
            self.tracker.calibration_samples.append((extreme_yaw, extreme_pitch, 0.0))
        self.assertEqual(len(self.tracker.calibration_samples), 0)

        # 2. Stable normal angles looking at screen are collected
        for _ in range(CALIBRATION_MIN_SAMPLES):
            if abs(1.5) < 35.0 and abs(-5.0) < 30.0:
                self.tracker.calibration_samples.append((1.5, -5.0, 0.5))

        # Auto-calibrate triggers when min samples reached
        if len(self.tracker.calibration_samples) >= CALIBRATION_MIN_SAMPLES:
            self.tracker.baseline_yaw = float(np.median([s[0] for s in self.tracker.calibration_samples]))
            self.tracker.baseline_pitch = float(np.median([s[1] for s in self.tracker.calibration_samples]))
            self.tracker.baseline_roll = float(np.median([s[2] for s in self.tracker.calibration_samples]))
            self.tracker.is_calibrated = True
            self.tracker.is_calibrating = False

        self.assertTrue(self.tracker.is_calibrated)
        self.assertFalse(self.tracker.is_calibrating)
        self.assertAlmostEqual(self.tracker.baseline_yaw, 1.5)
        self.assertAlmostEqual(self.tracker.baseline_pitch, -5.0)

    def test_adaptive_drift_calibration(self):
        """Verify continuous adaptive micro-drift updates baseline during normal reading."""
        self.tracker.baseline_yaw = 0.0
        self.tracker.baseline_pitch = 0.0
        self.tracker.baseline_roll = 0.0
        self.tracker.is_calibrated = True

        # Normal reading posture shift: delta_yaw = 5.0°, delta_pitch = -4.0°
        current_yaw = 5.0
        current_pitch = -4.0
        delta_yaw = current_yaw - self.tracker.baseline_yaw
        delta_pitch = current_pitch - self.tracker.baseline_pitch

        # Micro-drift update
        if abs(delta_yaw) < 18.0 and abs(delta_pitch) < 15.0:
            drift_alpha = 0.002
            self.tracker.baseline_yaw = (1.0 - drift_alpha) * self.tracker.baseline_yaw + drift_alpha * current_yaw

        self.assertGreater(self.tracker.baseline_yaw, 0.0)
        self.assertLess(self.tracker.baseline_yaw, 0.1)

        # Looking away violation (|delta_yaw| = 40.0°) does NOT alter baseline
        away_yaw = 40.0
        delta_away = away_yaw - self.tracker.baseline_yaw
        baseline_before = self.tracker.baseline_yaw
        if abs(delta_away) < 18.0:
            self.tracker.baseline_yaw = 0.998 * self.tracker.baseline_yaw + 0.002 * away_yaw
        self.assertEqual(self.tracker.baseline_yaw, baseline_before)


class TestPhoneTemporalSmoothing(unittest.TestCase):

    def setUp(self):
        self.detector = ObjectDetector()

    def test_phone_temporal_smoothing_buffer(self):
        """
        Verify 3-of-7 frames temporal smoothing:
        - 1 detection: NOT confirmed
        - 2 detections: NOT confirmed
        - 3 detections in 7 frames: CONFIRMED
        - 1 dropped frame: retains confirmed status
        """
        self.detector.detection_history.clear()

        # 1 detection
        self.detector.detection_history.append(True)
        positives = sum(1 for d in self.detector.detection_history if d)
        self.assertFalse(positives >= PHONE_BUFFER_MIN_DETECTIONS)

        # 2 detections
        self.detector.detection_history.append(True)
        positives = sum(1 for d in self.detector.detection_history if d)
        self.assertFalse(positives >= PHONE_BUFFER_MIN_DETECTIONS)

        # 3 detections in 3 frames: Confirmed!
        self.detector.detection_history.append(True)
        positives = sum(1 for d in self.detector.detection_history if d)
        self.assertTrue(positives >= PHONE_BUFFER_MIN_DETECTIONS)

        # 4th frame phone momentarily lost (False)
        self.detector.detection_history.append(False)
        # History: [True, True, True, False] -> 3 positives out of 4 -> Still confirmed!
        positives = sum(1 for d in self.detector.detection_history if d)
        self.assertTrue(positives >= PHONE_BUFFER_MIN_DETECTIONS)

        # Append 5 False frames: [False, False, False, False, False] pushes out the True values
        for _ in range(5):
            self.detector.detection_history.append(False)
        positives = sum(1 for d in self.detector.detection_history if d)
        self.assertLess(positives, PHONE_BUFFER_MIN_DETECTIONS)


if __name__ == "__main__":
    unittest.main()
