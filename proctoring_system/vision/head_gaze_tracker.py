"""
Head Pose and Gaze Tracker using MediaPipe FaceMesh, cv2.solvePnP, and cv2.RQDecomp3x3.
Calculates calibrated 3D Head Euler angles (Yaw, Pitch, Roll), 3D XYZ coordinate axes,
Iris Gaze vector, and baseline auto-calibration.
"""

from dataclasses import dataclass
import time
import cv2
import numpy as np
import mediapipe as mp

from proctoring_system.config import (
    CANONICAL_FACE_3D,
    HEAD_POSE_EMA_ALPHA,
    CALIBRATION_DURATION,
    CALIBRATION_MIN_SAMPLES,
    HEAD_YAW_THRESHOLD,
    HEAD_PITCH_DOWN_THRESHOLD,
    HEAD_PITCH_UP_THRESHOLD,
    YAW_THRESHOLD_LEFT,
    YAW_THRESHOLD_RIGHT,
    PITCH_THRESHOLD_DOWN,
    PITCH_THRESHOLD_UP,
    ROLL_THRESHOLD,
    GAZE_RATIO_LEFT,
    GAZE_RATIO_RIGHT,
    GAZE_RATIO_DOWN,
    DRAW_HEAD_AXES_VECTORS,
    DRAW_BOUNDING_BOXES,
    DRAW_FACEMESH_LANDMARKS,
    DRAW_DEBUG_OVERLAYS
)
from proctoring_system.vision.detector import BoundingBox


@dataclass
class HeadPose:
    yaw: float                 # Smoothed absolute Yaw (degrees): (-) left, (+) right
    pitch: float               # Smoothed absolute Pitch (degrees): (-) down, (+) up
    roll: float                # Smoothed absolute Roll (degrees)
    delta_yaw: float           # Relative deviation from baseline (current_yaw - baseline_yaw)
    delta_pitch: float         # Relative deviation from baseline (current_pitch - baseline_pitch)
    delta_roll: float          # Relative deviation from baseline (current_roll - baseline_roll)
    nose_2d: tuple[int, int]
    axis_x_2d: tuple[int, int] # End of 3D X vector (Red, pointing right)
    axis_y_2d: tuple[int, int] # End of 3D Y vector (Green, pointing down)
    axis_z_2d: tuple[int, int] # End of 3D Z vector (Blue/Forward gaze vector)
    nose_proj_2d: tuple[int, int]  # Backward compatibility synonym for axis_z_2d
    is_looking_away: bool      # Head turned left or right beyond threshold
    is_looking_down: bool      # Head tilted down beyond threshold
    is_calibrated: bool        # Whether baseline calibration is completed


@dataclass
class GazeState:
    horizontal_ratio: float
    vertical_ratio: float
    direction: str          # "CENTER", "LEFT", "RIGHT", "DOWN", "UP"
    is_gaze_diverted: bool


@dataclass
class FaceTrackingResult:
    face_count: int
    faces_boxes: list[BoundingBox]
    head_pose: HeadPose | None
    gaze: GazeState | None
    is_no_face: bool
    is_multiple_faces: bool
    is_calibrated: bool = False
    is_calibrating: bool = False
    calibration_progress: float = 0.0
    landmarks_points: list[tuple[int, int]] | None = None


class HeadGazeTracker:
    """
    Analyzes face geometry, solves Perspective-n-Point (PnP) for Head Pose using
    strict 6 canonical MediaPipe FaceMesh landmarks, filters with Exponential Moving Average (EMA),
    auto-calibrates neutral baseline gaze, and estimates pupil iris gaze deviation.
    """

    # Strict 6 canonical MediaPipe FaceMesh landmark indices:
    NOSE_TIP = 1
    CHIN = 152
    LEFT_EYE_OUTER = 33
    RIGHT_EYE_OUTER = 263
    LEFT_MOUTH = 61
    RIGHT_MOUTH = 291

    # Iris landmarks (available when refine_landmarks=True)
    LEFT_IRIS_CENTER = 468
    RIGHT_IRIS_CENTER = 473
    LEFT_EYE_INNER = 133
    RIGHT_EYE_INNER = 362
    LEFT_EYE_TOP = 159
    LEFT_EYE_BOTTOM = 145
    RIGHT_EYE_TOP = 386
    RIGHT_EYE_BOTTOM = 374

    def __init__(self, max_faces: int = 4):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=max_faces,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        # EMA smoothing filter state (alpha = 0.3)
        self.ema_alpha = HEAD_POSE_EMA_ALPHA
        self.smoothed_yaw: float | None = None
        self.smoothed_pitch: float | None = None
        self.smoothed_roll: float | None = None

        # Baseline Auto-calibration state
        self.is_calibrated = False
        self.is_calibrating = True
        self.calibration_start_time = time.time()
        self.calibration_samples: list[tuple[float, float, float]] = []
        self.baseline_yaw = 0.0
        self.baseline_pitch = 0.0
        self.baseline_roll = 0.0

    def recalibrate(self):
        """
        Trigger manual baseline recalibration (e.g., when pressing 'C' or clicking button).
        Collects 3.0 seconds of neutral gaze samples to establish calibrated zero.
        """
        self.is_calibrated = False
        self.is_calibrating = True
        self.calibration_samples.clear()
        self.calibration_start_time = time.time()

    def process(self, frame: np.ndarray) -> FaceTrackingResult:
        """
        Process a BGR video frame to extract face count, head pose angles, and gaze.
        """
        if frame is None or frame.size == 0:
            return FaceTrackingResult(
                face_count=0,
                faces_boxes=[],
                head_pose=None,
                gaze=None,
                is_no_face=True,
                is_multiple_faces=False,
                is_calibrated=self.is_calibrated,
                is_calibrating=self.is_calibrating,
                calibration_progress=self._get_calibration_progress()
            )

        h, w = frame.shape[:2]
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        rgb_frame.flags.writeable = False
        results = self.face_mesh.process(rgb_frame)

        if not results.multi_face_landmarks:
            return FaceTrackingResult(
                face_count=0,
                faces_boxes=[],
                head_pose=None,
                gaze=None,
                is_no_face=True,
                is_multiple_faces=False,
                is_calibrated=self.is_calibrated,
                is_calibrating=self.is_calibrating,
                calibration_progress=self._get_calibration_progress()
            )

        face_count = len(results.multi_face_landmarks)
        faces_boxes: list[BoundingBox] = []

        for landmarks in results.multi_face_landmarks:
            xs = [int(p.x * w) for p in landmarks.landmark]
            ys = [int(p.y * h) for p in landmarks.landmark]
            margin_x = int((max(xs) - min(xs)) * 0.15)
            margin_y = int((max(ys) - min(ys)) * 0.15)
            faces_boxes.append(BoundingBox(
                x1=max(0, min(xs) - margin_x),
                y1=max(0, min(ys) - margin_y),
                x2=min(w, max(xs) + margin_x),
                y2=min(h, max(ys) + margin_y)
            ))

        # We analyze primary face (largest bbox or first detected)
        primary_idx = 0
        if face_count > 1:
            primary_idx = max(range(face_count), key=lambda i: faces_boxes[i].area)

        primary_landmarks = results.multi_face_landmarks[primary_idx]
        lm = primary_landmarks.landmark

        # Extract 2D points for 6 canonical landmarks for solvePnP
        p2d_nose = (int(lm[self.NOSE_TIP].x * w), int(lm[self.NOSE_TIP].y * h))
        p2d_chin = (int(lm[self.CHIN].x * w), int(lm[self.CHIN].y * h))
        p2d_left_eye = (int(lm[self.LEFT_EYE_OUTER].x * w), int(lm[self.LEFT_EYE_OUTER].y * h))
        p2d_right_eye = (int(lm[self.RIGHT_EYE_OUTER].x * w), int(lm[self.RIGHT_EYE_OUTER].y * h))
        p2d_left_mouth = (int(lm[self.LEFT_MOUTH].x * w), int(lm[self.LEFT_MOUTH].y * h))
        p2d_right_mouth = (int(lm[self.RIGHT_MOUTH].x * w), int(lm[self.RIGHT_MOUTH].y * h))

        image_points = np.array([
            p2d_nose,
            p2d_chin,
            p2d_left_eye,
            p2d_right_eye,
            p2d_left_mouth,
            p2d_right_mouth
        ], dtype=np.float64)

        # Standard camera intrinsic matrix:
        # fx = fy = frame_width, cx = frame_width/2, cy = frame_height/2
        focal_length = float(w)
        center_x = float(w / 2.0)
        center_y = float(h / 2.0)
        camera_matrix = np.array([
            [focal_length, 0, center_x],
            [0, focal_length, center_y],
            [0, 0, 1]
        ], dtype=np.float64)

        dist_coeffs = np.zeros((4, 1), dtype=np.float64)

        # Solve Perspective-n-Point with SOLVEPNP_ITERATIVE
        success, rvec, tvec = False, None, None
        try:
            success, rvec, tvec = cv2.solvePnP(
                CANONICAL_FACE_3D,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )
        except Exception:
            success = False

        head_pose = None
        if success and rvec is not None and tvec is not None:
            # Convert rotation vector to rotation matrix
            rmat, _ = cv2.Rodrigues(rvec)

            # Compute Euler angles via cv2.RQDecomp3x3
            # angles = (pitch, yaw, roll) in degrees
            angles = cv2.RQDecomp3x3(rmat)[0]
            pitch_raw, yaw_raw, roll_raw = angles

            # Coordinate orientation:
            # Yaw: turning head left is (-), turning right is (+)
            # Pitch: tilting down is (-), tilting up is (+)
            # Roll: tilt towards shoulder
            raw_yaw = -float(yaw_raw)
            raw_pitch = -float(pitch_raw)
            raw_roll = float(roll_raw)

            # 3. Exponential Moving Average (EMA) smoothing (alpha = 0.3)
            if self.smoothed_yaw is None:
                self.smoothed_yaw = raw_yaw
                self.smoothed_pitch = raw_pitch
                self.smoothed_roll = raw_roll
            else:
                self.smoothed_yaw = self.ema_alpha * raw_yaw + (1.0 - self.ema_alpha) * self.smoothed_yaw
                self.smoothed_pitch = self.ema_alpha * raw_pitch + (1.0 - self.ema_alpha) * self.smoothed_pitch
                self.smoothed_roll = self.ema_alpha * raw_roll + (1.0 - self.ema_alpha) * self.smoothed_roll

            # 4. Baseline Auto-Calibration & Adaptive Drift
            now = time.time()
            if self.is_calibrating:
                # If calibration was just initiated or no samples yet, anchor start time to first detected face
                if len(self.calibration_samples) == 0:
                    self.calibration_start_time = now

                # Only collect calibration samples when face is looking roughly at the monitor
                # (|raw_yaw| < 35.0° and |raw_pitch| < 30.0°) to avoid locking in an off-screen pose
                if abs(raw_yaw) < 35.0 and abs(raw_pitch) < 30.0:
                    self.calibration_samples.append((self.smoothed_yaw, self.smoothed_pitch, self.smoothed_roll))

                elapsed = now - (self.calibration_start_time or now)
                # Auto-calibrate as soon as sufficient stable frames are collected (min 15 frames)
                if len(self.calibration_samples) >= CALIBRATION_MIN_SAMPLES:
                    self.baseline_yaw = float(np.median([s[0] for s in self.calibration_samples]))
                    self.baseline_pitch = float(np.median([s[1] for s in self.calibration_samples]))
                    self.baseline_roll = float(np.median([s[2] for s in self.calibration_samples]))
                    self.is_calibrated = True
                    self.is_calibrating = False

            elif self.is_calibrated:
                # Continuous adaptive micro-calibration:
                # Slowly and seamlessly adapt baseline to subtle natural posture shifts while reading normally
                # (Only when delta is well within normal safe reading bounds: |delta_yaw| < 18° and |delta_pitch| < 15°)
                delta_yaw_temp = self.smoothed_yaw - self.baseline_yaw
                delta_pitch_temp = self.smoothed_pitch - self.baseline_pitch
                if abs(delta_yaw_temp) < 18.0 and abs(delta_pitch_temp) < 15.0:
                    drift_alpha = 0.002
                    self.baseline_yaw = (1.0 - drift_alpha) * self.baseline_yaw + drift_alpha * self.smoothed_yaw
                    self.baseline_pitch = (1.0 - drift_alpha) * self.baseline_pitch + drift_alpha * self.smoothed_pitch
                    self.baseline_roll = (1.0 - drift_alpha) * self.baseline_roll + drift_alpha * self.smoothed_roll

            # Deviation relative to calibrated baseline:
            # delta_yaw = current_yaw - baseline_yaw
            # delta_pitch = current_pitch - baseline_pitch
            if self.is_calibrated:
                delta_yaw = self.smoothed_yaw - self.baseline_yaw
                delta_pitch = self.smoothed_pitch - self.baseline_pitch
                delta_roll = self.smoothed_roll - self.baseline_roll
            else:
                delta_yaw = 0.0
                delta_pitch = 0.0
                delta_roll = 0.0

            # 3D Coordinate axes projection (X Red, Y Green, Z Blue from nose tip)
            axis_len = 80.0
            axes_3d = np.array([
                (axis_len, 0.0, 0.0),        # Axis X (Person's right, Red)
                (0.0, axis_len, 0.0),        # Axis Y (Person's down/chin, Green)
                (0.0, 0.0, -axis_len * 1.5)  # Axis Z (Forward gaze vector, Blue)
            ], dtype=np.float64)

            proj_axes, _ = cv2.projectPoints(axes_3d, rvec, tvec, camera_matrix, dist_coeffs)
            axis_x = (int(proj_axes[0][0][0]), int(proj_axes[0][0][1]))
            axis_y = (int(proj_axes[1][0][0]), int(proj_axes[1][0][1]))
            axis_z = (int(proj_axes[2][0][0]), int(proj_axes[2][0][1]))

            # Head pose threshold violations (calibrated relative to neutral monitor center)
            if self.is_calibrated:
                is_looking_away = (abs(delta_yaw) > HEAD_YAW_THRESHOLD) or (delta_pitch > HEAD_PITCH_UP_THRESHOLD)
                is_looking_down = (delta_pitch < HEAD_PITCH_DOWN_THRESHOLD)
            else:
                # Do not trigger false violations while calibrating initial baseline
                is_looking_away = False
                is_looking_down = False

            head_pose = HeadPose(
                yaw=round(self.smoothed_yaw, 1),
                pitch=round(self.smoothed_pitch, 1),
                roll=round(self.smoothed_roll, 1),
                delta_yaw=round(delta_yaw, 1),
                delta_pitch=round(delta_pitch, 1),
                delta_roll=round(delta_roll, 1),
                nose_2d=p2d_nose,
                axis_x_2d=axis_x,
                axis_y_2d=axis_y,
                axis_z_2d=axis_z,
                nose_proj_2d=axis_z,
                is_looking_away=is_looking_away,
                is_looking_down=is_looking_down,
                is_calibrated=self.is_calibrated
            )

        # Gaze tracking via Iris landmarks
        gaze = self._calculate_gaze(lm, w, h)

        return FaceTrackingResult(
            face_count=face_count,
            faces_boxes=faces_boxes,
            head_pose=head_pose,
            gaze=gaze,
            is_no_face=False,
            is_multiple_faces=(face_count > 1),
            is_calibrated=self.is_calibrated,
            is_calibrating=self.is_calibrating,
            calibration_progress=self._get_calibration_progress()
        )

    def _get_calibration_progress(self) -> float:
        """Returns 0.0 to 1.0 progress of the auto-calibration phase."""
        if self.is_calibrated:
            return 1.0
        if not self.is_calibrating:
            return 0.0
        sample_progress = len(self.calibration_samples) / max(1, CALIBRATION_MIN_SAMPLES)
        return min(1.0, max(0.0, sample_progress))

    def _calculate_gaze(self, lm, w: int, h: int) -> GazeState:
        """
        Estimate gaze vector from iris position relative to eye corners.
        """
        try:
            # Left Eye: outer (33), inner (133), iris (468)
            lx_outer = lm[self.LEFT_EYE_OUTER].x * w
            lx_inner = lm[self.LEFT_EYE_INNER].x * w
            lx_iris = lm[self.LEFT_IRIS_CENTER].x * w
            ly_top = lm[self.LEFT_EYE_TOP].y * h
            ly_bottom = lm[self.LEFT_EYE_BOTTOM].y * h
            ly_iris = lm[self.LEFT_IRIS_CENTER].y * h

            # Right Eye: inner (362), outer (263), iris (473)
            rx_inner = lm[self.RIGHT_EYE_INNER].x * w
            rx_outer = lm[self.RIGHT_EYE_OUTER].x * w
            rx_iris = lm[self.RIGHT_IRIS_CENTER].x * w
            ry_top = lm[self.RIGHT_EYE_TOP].y * h
            ry_bottom = lm[self.RIGHT_EYE_BOTTOM].y * h
            ry_iris = lm[self.RIGHT_IRIS_CENTER].y * h

            # Horizontal gaze ratio (0.0: looking left, 1.0: looking right)
            left_width = max(1.0, abs(lx_inner - lx_outer))
            right_width = max(1.0, abs(rx_outer - rx_inner))

            left_ratio = (lx_iris - min(lx_outer, lx_inner)) / left_width
            right_ratio = (rx_iris - min(rx_inner, rx_outer)) / right_width
            h_ratio = float((left_ratio + right_ratio) / 2.0)

            # Vertical gaze ratio (0.0: looking up, 1.0: looking down)
            left_h = max(1.0, abs(ly_bottom - ly_top))
            right_h = max(1.0, abs(ry_bottom - ry_top))
            v_ratio = float(((ly_iris - ly_top) / left_h + (ry_iris - ry_top) / right_h) / 2.0)

            direction = "CENTER"
            if h_ratio < GAZE_RATIO_LEFT:
                direction = "LEFT"
            elif h_ratio > GAZE_RATIO_RIGHT:
                direction = "RIGHT"
            elif v_ratio > GAZE_RATIO_DOWN:
                direction = "DOWN"
            elif v_ratio < 0.25:
                direction = "UP"

            is_diverted = (direction != "CENTER")

            return GazeState(
                horizontal_ratio=round(h_ratio, 2),
                vertical_ratio=round(v_ratio, 2),
                direction=direction,
                is_gaze_diverted=is_diverted
            )
        except Exception:
            return GazeState(0.5, 0.5, "CENTER", False)

    def draw_overlays(self, frame: np.ndarray, result: FaceTrackingResult) -> np.ndarray:
        """
        Visual overlays for face tracking.
        Clean video feed for student: 3D vectors, face bounding boxes, and landmark meshes are disabled.
        All math, head pose, and gaze tracking continue running uninterrupted in the background.
        """
        if not DRAW_DEBUG_OVERLAYS:
            # Clean camera view: return original frame without clutter
            return frame

        h, w = frame.shape[:2]

        # 1. Face bounding boxes (disabled by default)
        if DRAW_BOUNDING_BOXES:
            for i, fb in enumerate(result.faces_boxes):
                is_primary = (i == 0)
                color = (0, 255, 0) if is_primary and not result.is_multiple_faces else (0, 0, 255)
                cv2.rectangle(frame, (fb.x1, fb.y1), (fb.x2, fb.y2), color, 2)
                tag = "Student" if is_primary else f"Unauthorized Face #{i+1}"
                cv2.putText(frame, tag, (fb.x1, max(15, fb.y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1)

        # 2. 3D Head Pose Axes Vectors (disabled by default)
        if DRAW_HEAD_AXES_VECTORS and result.head_pose:
            hp = result.head_pose
            p_nose = hp.nose_2d
            z_color = (0, 0, 255) if (hp.is_looking_away or hp.is_looking_down) else (255, 120, 0)
            cv2.arrowedLine(frame, p_nose, hp.axis_x_2d, (0, 0, 255), 2, tipLength=0.2)
            cv2.putText(frame, "X", hp.axis_x_2d, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 255), 1)
            cv2.arrowedLine(frame, p_nose, hp.axis_y_2d, (0, 255, 0), 2, tipLength=0.2)
            cv2.putText(frame, "Y", hp.axis_y_2d, cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)
            cv2.arrowedLine(frame, p_nose, hp.axis_z_2d, z_color, 3, tipLength=0.25)
            cv2.putText(frame, "Z", hp.axis_z_2d, cv2.FONT_HERSHEY_SIMPLEX, 0.45, z_color, 1)
            cv2.circle(frame, p_nose, 4, (0, 255, 255), -1)

        return frame
