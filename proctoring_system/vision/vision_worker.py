"""
Vision Worker QThread for real-time video capture, inference, and temporal anomaly detection.
Runs asynchronously at 25-30 FPS, keeping GUI responsive.
"""

import time
from dataclasses import dataclass, field
import cv2
import numpy as np
from PyQt6.QtCore import QThread, pyqtSignal
from PyQt6.QtGui import QImage

from PIL import Image, ImageDraw, ImageFont

from proctoring_system.config import (
    CAMERA_INDEX,
    CAMERA_WIDTH,
    CAMERA_HEIGHT,
    TARGET_FPS,
    VIOLATION_DURATION_THRESHOLD,
    DURATION_NO_FACE,
    DURATION_MULTIPLE_FACES,
    DURATION_LOOKING_AWAY,
    DURATION_LOOKING_DOWN,
    DURATION_GAZE_AWAY,
    DURATION_PHONE_DETECTED,
    INCIDENT_LOG_COOLDOWN,
    ENABLE_MOCK_FALLBACK,
    DRAW_DEBUG_OVERLAYS
)
from proctoring_system.logger import IncidentLogger, IncidentType
from proctoring_system.vision.detector import ObjectDetector
from proctoring_system.vision.head_gaze_tracker import HeadGazeTracker, FaceTrackingResult


@dataclass
class AnomalyTimers:
    """Tracks start timestamps for sustained behavioral anomalies."""
    no_face_start: float | None = None
    multiple_faces_start: float | None = None

    # Continuous head turn tracking (Yaw / Pitch)
    head_turn_start: float | None = None
    head_turn_logged: bool = False
    head_turn_last_log_time: float = 0.0
    head_turn_type: str | None = None

    gaze_away_start: float | None = None
    phone_start: float | None = None

    # Track last log timestamp per incident type to apply cooldown
    last_logged_time: dict[str, float] = field(default_factory=dict)


class VisionWorker(QThread):
    """
    Background worker thread performing OpenCV capture, YOLO inference,
    MediaPipe FaceMesh tracking, head pose estimation, and temporal violation detection.
    """

    frame_ready = pyqtSignal(QImage)
    incident_triggered = pyqtSignal(str, str, str, str)  # type, desc, severity, screenshot_path
    status_updated = pyqtSignal(dict)                   # metrics dict for HUD

    def __init__(self, incident_logger: IncidentLogger):
        super().__init__()
        self.logger = incident_logger
        self.is_running = False

        self.cap: cv2.VideoCapture | None = None
        self.using_mock = False
        self.silence_incidents = False

        # Vision sub-modules
        self.detector = ObjectDetector()
        self.tracker = HeadGazeTracker()

        self.timers = AnomalyTimers()
        self.fps = 0.0
        self._frame_count = 0
        self._fps_start_time = time.time()

        # Cache PIL fonts for crisp Russian text overlays
        try:
            self._font_bold = ImageFont.truetype("arialbd.ttf", 15)
            self._font_regular = ImageFont.truetype("arial.ttf", 13)
        except Exception:
            self._font_bold = ImageFont.load_default()
            self._font_regular = self._font_bold

        # Mock simulation state variables (for testing without camera or testing simulations)
        self.sim_anomaly_mode: str | None = None  # None, "NO_FACE", "PHONE", "LOOKING_AWAY", "LOOKING_DOWN", "MULTIPLE_FACES"

    def run(self):
        """Main capture and inference loop."""
        self.is_running = True
        self._init_camera()

        interval = 1.0 / TARGET_FPS

        while self.is_running:
            loop_start = time.time()

            frame = self._read_frame()
            if frame is None or frame.size == 0:
                time.sleep(0.02)
                continue

            # Process frame with exception safety
            try:
                annotated_frame, metrics = self._process_frame(frame)
            except Exception as e:
                print(f"[VisionWorker] Error processing frame: {e}")
                annotated_frame = frame.copy()
                metrics = {
                    "status": "NORMAL",
                    "warnings": [],
                    "face_count": 1,
                    "phones_count": 0,
                    "phone_detected": False,
                    "head_pose": None,
                    "is_calibrated": True,
                    "calibration_progress": 1.0,
                    "gaze": "CENTER",
                    "fps": round(self.fps, 1),
                    "is_mock": self.using_mock
                }

            # FPS calculation
            self._frame_count += 1
            now = time.time()
            if now - self._fps_start_time >= 1.0:
                self.fps = self._frame_count / (now - self._fps_start_time)
                self._frame_count = 0
                self._fps_start_time = now

            metrics["fps"] = round(self.fps, 1)

            # Convert to QImage and emit
            try:
                q_img = self._cv2_to_qimage(annotated_frame)
                self.frame_ready.emit(q_img)
                self.status_updated.emit(metrics)
            except Exception as e:
                print(f"[VisionWorker] Error emitting frame/metrics: {e}")

            # Frame rate pacing
            elapsed = time.time() - loop_start
            sleep_time = max(0.001, interval - elapsed)
            time.sleep(sleep_time)

        self._release_camera()

    def stop(self):
        """Signal thread to terminate, release camera, and wait."""
        self.is_running = False
        self._release_camera()
        self.wait(1000)

    def trigger_simulation_mode(self, mode: str | None):
        """Allows testing anomaly scenarios on demand."""
        self.sim_anomaly_mode = mode

    def recalibrate(self):
        """Trigger manual baseline recalibration (e.g. from hotkey 'C' or UI button)."""
        self.tracker.recalibrate()

    def _init_camera(self):
        """Initialize camera device or fallback."""
        if self.using_mock:
            print("[VisionWorker] Using mock synthetic generator as requested.")
            return

        print(f"[VisionWorker] Opening camera index {CAMERA_INDEX}...")
        self.cap = cv2.VideoCapture(CAMERA_INDEX, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(CAMERA_INDEX)

        if self.cap.isOpened():
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
            self.using_mock = False
            print("[VisionWorker] Camera opened successfully.")
        else:
            if ENABLE_MOCK_FALLBACK:
                print("[VisionWorker] No physical camera found. Initializing high-fidelity mock video generator.")
                self.using_mock = True
            else:
                print("[VisionWorker] Camera failed to open.")

    def _release_camera(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()
            self.cap = None

    def _read_frame(self) -> np.ndarray | None:
        """Fetch next frame from webcam or simulator."""
        if not self.using_mock and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret and frame is not None:
                # Mirror frame horizontally for natural selfie view
                return cv2.flip(frame, 1)

        # Fallback synthetic frame generator
        return self._generate_synthetic_frame()

    def _process_frame(self, frame: np.ndarray) -> tuple[np.ndarray, dict]:
        """
        Run inference pipelines, temporal debouncing, anomaly logging, and overlay rendering.
        """
        now = time.time()
        display_frame = frame.copy()

        # Step 1: Head Pose & Face Tracking
        face_result = self.tracker.process(frame)

        # Step 2: YOLO Object Detection (pass face bounding boxes for risk proximity)
        det_result = self.detector.detect(frame, face_boxes=face_result.faces_boxes)

        # Active warnings for this frame
        active_warnings: list[str] = []
        overall_status = "NORMAL"  # "NORMAL", "WARNING", "VIOLATION"

        if getattr(self, "silence_incidents", False):
            # Exam finished: do not trigger any warnings or incidents
            return display_frame, {
                "status": "NORMAL",
                "warnings": [],
                "face_count": face_result.face_count,
                "phones_count": 0,
                "phone_detected": False,
                "head_pose": None,
                "is_calibrated": True,
                "calibration_progress": 1.0,
                "gaze": "CENTER",
                "is_mock": self.using_mock,
                "fps": self.fps
            }

        # ----------------------------------------------------
        # Simulation override for Demo mode (if active)
        # ----------------------------------------------------
        if self.sim_anomaly_mode == "NO_FACE":
            face_result.is_no_face = True
            face_result.face_count = 0
            face_result.head_pose = None
        elif self.sim_anomaly_mode == "MULTIPLE_FACES":
            face_result.is_no_face = False
            face_result.is_multiple_faces = True
            face_result.face_count = 2
        elif self.sim_anomaly_mode == "LOOKING_AWAY" and (face_result.head_pose is None or not face_result.head_pose.is_looking_away):
            from proctoring_system.vision.head_gaze_tracker import HeadPose
            face_result.is_no_face = False
            face_result.head_pose = HeadPose(
                yaw=45.0, pitch=0.0, roll=0.0,
                delta_yaw=45.0, delta_pitch=0.0, delta_roll=0.0,
                nose_2d=(320, 240),
                axis_x_2d=(380, 240), axis_y_2d=(320, 300), axis_z_2d=(430, 240),
                nose_proj_2d=(430, 240),
                is_looking_away=True, is_looking_down=False,
                is_calibrated=True
            )
        elif self.sim_anomaly_mode == "LOOKING_DOWN" and (face_result.head_pose is None or not face_result.head_pose.is_looking_down):
            from proctoring_system.vision.head_gaze_tracker import HeadPose
            face_result.is_no_face = False
            face_result.head_pose = HeadPose(
                yaw=0.0, pitch=-35.0, roll=0.0,
                delta_yaw=0.0, delta_pitch=-35.0, delta_roll=0.0,
                nose_2d=(320, 240),
                axis_x_2d=(380, 240), axis_y_2d=(320, 300), axis_z_2d=(320, 340),
                nose_proj_2d=(320, 340),
                is_looking_away=False, is_looking_down=True,
                is_calibrated=True
            )
        elif self.sim_anomaly_mode == "PHONE":
            det_result.is_phone_violation = True
            det_result.max_phone_conf = 0.92

        # ----------------------------------------------------
        # Anomaly 1: No Face Detected (Student left desk)
        # ----------------------------------------------------
        if face_result.is_no_face:
            if self.timers.no_face_start is None:
                self.timers.no_face_start = now
            duration = now - self.timers.no_face_start
            if duration >= DURATION_NO_FACE:
                overall_status = "VIOLATION"
                active_warnings.append(f"ЛИЦО НЕ НАЙДЕНО ({duration:.1f}с)")
                self._check_and_log_incident(
                    IncidentType.NO_FACE,
                    display_frame,
                    details={"duration": round(duration, 1)}
                )
            else:
                overall_status = "WARNING" if overall_status != "VIOLATION" else overall_status
                active_warnings.append(f"Поиск лица... ({duration:.1f}с)")
        else:
            self.timers.no_face_start = None

        # ----------------------------------------------------
        # Anomaly 2: Multiple Faces in Frame
        # ----------------------------------------------------
        if face_result.is_multiple_faces:
            if self.timers.multiple_faces_start is None:
                self.timers.multiple_faces_start = now
            duration = now - self.timers.multiple_faces_start
            if duration >= DURATION_MULTIPLE_FACES:
                overall_status = "VIOLATION"
                active_warnings.append(f"ПОСТОРОННЕЕ ЛИЦО В КАДРЕ ({face_result.face_count})")
                self._check_and_log_incident(
                    IncidentType.MULTIPLE_FACES,
                    display_frame,
                    details={"faces_count": face_result.face_count}
                )
            else:
                overall_status = "WARNING" if overall_status != "VIOLATION" else overall_status
        else:
            self.timers.multiple_faces_start = None

        # ----------------------------------------------------
        # Anomaly 3: Head Pose Tracking (Yaw > 25° / < -25° or Pitch < -20°)
        # Continuous timer with 3.0s threshold, instant reset on return, anti-spam cooldown
        # ----------------------------------------------------
        is_head_deviated = False
        head_incident_type = None

        if face_result.head_pose is not None:
            hp = face_result.head_pose
            if hp.is_looking_away:
                is_head_deviated = True
                head_incident_type = IncidentType.LOOKING_AWAY
            elif hp.is_looking_down:
                is_head_deviated = True
                head_incident_type = IncidentType.LOOKING_DOWN

        if is_head_deviated and head_incident_type is not None:
            if self.timers.head_turn_start is None:
                # 2. Как только зафиксирован поворот — запускаем таймер
                self.timers.head_turn_start = now
                self.timers.head_turn_logged = False
                self.timers.head_turn_type = head_incident_type.value

            duration = now - self.timers.head_turn_start

            if duration < DURATION_LOOKING_AWAY:
                # 4. Пока голова повернута и идёт отсчёт: выводить жёлтый статус с таймером
                # Например: "Внимание: отвод головы (Таймер: 0.8 / 1.5 сек)"
                overall_status = "WARNING" if overall_status != "VIOLATION" else overall_status
                active_warnings.append(f"Внимание: отвод головы (Таймер: {duration:.1f} / {DURATION_LOOKING_AWAY:.1f} сек)")
            else:
                # Когда прошло >= 1.5 секунды: красный статус "НАРУШЕНИЕ: Отвод головы зафиксирован!"
                overall_status = "VIOLATION"
                active_warnings.append("НАРУШЕНИЕ: Отвод головы зафиксирован!")

                # 3. Защита от спама: после срабатывания алерта на 3-й секунде не дублировать
                # запись каждый кадр. Следующая фиксация возможна либо после возврата головы
                # в центр, либо с интервалом (кулдауном).
                time_since_last_log = now - self.timers.head_turn_last_log_time
                if (not self.timers.head_turn_logged) or (time_since_last_log >= INCIDENT_LOG_COOLDOWN):
                    self.timers.head_turn_logged = True
                    self.timers.head_turn_last_log_time = now
                    details = {
                        "yaw": face_result.head_pose.yaw,
                        "pitch": face_result.head_pose.pitch,
                        "roll": face_result.head_pose.roll,
                        "delta_yaw": face_result.head_pose.delta_yaw,
                        "delta_pitch": face_result.head_pose.delta_pitch,
                        "duration": round(duration, 1),
                        "threshold": DURATION_LOOKING_AWAY
                    }
                    record = self.logger.log_incident(
                        incident_type=head_incident_type,
                        frame=display_frame.copy(),
                        details=details,
                        custom_desc=f"Непрерывный отвод головы: {duration:.1f}с (порог {DURATION_LOOKING_AWAY:.1f}с)"
                    )
                    if record:
                        self.incident_triggered.emit(
                            record.incident_type,
                            record.description,
                            record.severity,
                            record.screenshot_path
                        )
        else:
            # 2. Если голова возвращается в нормальное положение раньше, чем прошло 3.0 секунды
            # (или возвращается в центр после зафиксированного нарушения) —
            # полностью сбрасываем таймер в 0 без фиксации нарушения.
            self.timers.head_turn_start = None
            self.timers.head_turn_logged = False
            self.timers.head_turn_type = None

        # ----------------------------------------------------
        # Anomaly 4: Gaze Diverted (Eyes diverted from screen)
        # ----------------------------------------------------
        if face_result.gaze and face_result.gaze.is_gaze_diverted and not is_head_deviated:
            if self.timers.gaze_away_start is None:
                self.timers.gaze_away_start = now
            duration = now - self.timers.gaze_away_start
            if duration < DURATION_GAZE_AWAY:
                overall_status = "WARNING" if overall_status != "VIOLATION" else overall_status
                active_warnings.append(f"Внимание: отвод глаз (Таймер: {duration:.1f} / {DURATION_GAZE_AWAY:.1f} сек)")
            else:
                overall_status = "VIOLATION"
                active_warnings.append("НАРУШЕНИЕ: Отвод взгляда зафиксирован!")
                self._check_and_log_incident(
                    IncidentType.GAZE_AWAY,
                    display_frame,
                    details={"direction": face_result.gaze.direction, "duration": round(duration, 1), "threshold": DURATION_GAZE_AWAY}
                )
        else:
            self.timers.gaze_away_start = None

        # ----------------------------------------------------
        # Anomaly 5: Phone / Foreign Object Detected
        # ----------------------------------------------------
        if det_result.is_phone_violation:
            if self.timers.phone_start is None:
                self.timers.phone_start = now
            duration = now - self.timers.phone_start
            if duration < DURATION_PHONE_DETECTED:
                overall_status = "WARNING" if overall_status != "VIOLATION" else overall_status
                active_warnings.append(f"Внимание: смартфон в кадре (Таймер: {duration:.1f} / {DURATION_PHONE_DETECTED:.1f} сек)")
            else:
                overall_status = "VIOLATION"
                active_warnings.append(f"НАРУШЕНИЕ: ОБНАРУЖЕН СМАРТФОН! ({det_result.max_phone_conf:.0%})")
                self._check_and_log_incident(
                    IncidentType.PHONE_DETECTED,
                    display_frame,
                    details={"confidence": round(det_result.max_phone_conf, 2), "duration": round(duration, 1), "threshold": DURATION_PHONE_DETECTED}
                )
        else:
            self.timers.phone_start = None

        # ----------------------------------------------------
        # Draw Overlays on Display Frame (Clean view: vectors, boxes, and mesh disabled)
        # ----------------------------------------------------
        if DRAW_DEBUG_OVERLAYS:
            display_frame = self.tracker.draw_overlays(display_frame, face_result)
            display_frame = self.detector.draw_overlays(display_frame, det_result)

        # Draw HUD status & countdown timer banner on the frame itself
        self._render_frame_hud(display_frame, overall_status, active_warnings)

        metrics = {
            "status": overall_status,
            "warnings": active_warnings,
            "face_count": face_result.face_count,
            "phones_count": len(det_result.phones),
            "phone_detected": det_result.is_phone_violation,
            "head_pose": {
                "yaw": face_result.head_pose.yaw,
                "pitch": face_result.head_pose.pitch,
                "roll": face_result.head_pose.roll,
                "delta_yaw": face_result.head_pose.delta_yaw,
                "delta_pitch": face_result.head_pose.delta_pitch,
                "delta_roll": face_result.head_pose.delta_roll,
                "is_calibrated": face_result.head_pose.is_calibrated
            } if face_result.head_pose else None,
            "is_calibrated": face_result.is_calibrated,
            "calibration_progress": face_result.calibration_progress,
            "gaze": face_result.gaze.direction if face_result.gaze else "NONE",
            "is_mock": self.using_mock
        }

        return display_frame, metrics

    def _check_and_log_incident(self, incident_type: IncidentType, frame: np.ndarray | None, details: dict):
        """
        Logs an incident if cooldown has elapsed.
        Always passes an independent copy of the frame to prevent concurrent access issues.
        """
        if getattr(self, "silence_incidents", False):
            return
        try:
            now = time.time()
            last_time = self.timers.last_logged_time.get(incident_type.value, 0.0)

            if (now - last_time) >= INCIDENT_LOG_COOLDOWN:
                self.timers.last_logged_time[incident_type.value] = now
                frame_copy = frame.copy() if (frame is not None and frame.size > 0) else None
                record = self.logger.log_incident(incident_type=incident_type, frame=frame_copy, details=details)
                if record:
                    self.incident_triggered.emit(
                        record.incident_type,
                        record.description,
                        record.severity,
                        record.screenshot_path
                    )
        except Exception as e:
            print(f"[VisionWorker] Error in _check_and_log_incident: {e}")

    def _render_frame_hud(self, frame: np.ndarray, status: str, warnings: list[str]):
        """Renders visual status indicator and alert banners directly on webcam feed."""
        try:
            h, w = frame.shape[:2]

            # Status badge color
            if status == "VIOLATION":
                top_bar_color = (0, 0, 220)      # Bright Red
                status_text = "VIOLATION DETECTED"
                chip_color = (0, 0, 220)
            elif status == "WARNING":
                top_bar_color = (0, 180, 240)    # Amber/Yellow
                status_text = "WARNING"
                chip_color = (0, 180, 240)
            else:
                top_bar_color = (0, 200, 50)     # Neon Green
                status_text = "SECURE / NORMAL"
                chip_color = (0, 200, 50)

            # Top border / indicator bar
            cv2.rectangle(frame, (0, 0), (w, 4), top_bar_color, -1)

            # Continuous Violation Progress Bar & Countdown Timer (Head turn, Gaze away, Phone)
            active_timer_start = None
            active_timer_limit = VIOLATION_DURATION_THRESHOLD

            if self.timers.head_turn_start is not None:
                active_timer_start = self.timers.head_turn_start
                active_timer_limit = DURATION_LOOKING_AWAY
            elif self.timers.gaze_away_start is not None:
                active_timer_start = self.timers.gaze_away_start
                active_timer_limit = DURATION_GAZE_AWAY
            elif self.timers.phone_start is not None:
                active_timer_start = self.timers.phone_start
                active_timer_limit = DURATION_PHONE_DETECTED

            if active_timer_start is not None:
                elapsed = time.time() - active_timer_start
                ratio = min(1.0, elapsed / active_timer_limit)
                bar_w = 180
                bar_h = 8
                bx, by = 10, 38

                # Progress bar frame & fill
                cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (25, 25, 25), -1)
                fill_color = (0, 180, 255) if ratio < 1.0 else (0, 0, 230)
                cv2.rectangle(frame, (bx, by), (bx + int(bar_w * ratio), by + bar_h), fill_color, -1)
                cv2.rectangle(frame, (bx, by), (bx + bar_w, by + bar_h), (80, 80, 80), 1)

                # Text: "Таймер: {elapsed:.1f} / 1.5 сек"
                timer_text = f"Таймер: {elapsed:.1f} / {active_timer_limit:.1f} сек"
                cv2.putText(frame, timer_text, (bx + bar_w + 8, by + 7), cv2.FONT_HERSHEY_SIMPLEX, 0.40, (255, 255, 255), 1, cv2.LINE_AA)

            # Render Cyrillic warning alerts banner if any
            if warnings:
                pil_img = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                draw = ImageDraw.Draw(pil_img)
                y_offset = 54 if active_timer_start is not None else 42

                for msg in warnings[:2]:
                    is_violation_msg = ("НАРУШЕНИЕ" in msg or "ОБНАРУЖЕН" in msg or "НЕ НАЙДЕНО" in msg)
                    # Yellow/Amber for warning, Red for violation
                    bg_color = (210, 20, 20) if is_violation_msg else (230, 140, 0)

                    bbox = self._font_bold.getbbox(msg)
                    tw = bbox[2] - bbox[0]
                    th = bbox[3] - bbox[1]

                    pill_x1 = 10
                    pill_y1 = y_offset
                    pill_x2 = 10 + tw + 20
                    pill_y2 = y_offset + th + 12

                    draw.rounded_rectangle([pill_x1, pill_y1, pill_x2, pill_y2], radius=6, fill=bg_color)
                    draw.text((pill_x1 + 10, pill_y1 + 5), msg, font=self._font_bold, fill=(255, 255, 255))
                    y_offset += (th + 18)

                frame[:] = cv2.cvtColor(np.asarray(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            print(f"[VisionWorker] Error rendering frame HUD: {e}")

    def _cv2_to_qimage(self, frame: np.ndarray) -> QImage:
        """Convert BGR OpenCV frame to QImage for Qt rendering safely."""
        try:
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, ch = rgb.shape
            bytes_per_line = ch * w
            q_img = QImage(rgb.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
            return q_img.copy()
        except Exception as e:
            print(f"[VisionWorker] Error converting frame to QImage: {e}")
            return QImage()

    def _generate_synthetic_frame(self) -> np.ndarray:
        """
        Creates a high-fidelity synthetic camera frame for simulation/demo mode
        if real camera is not available.
        """
        w, h = CAMERA_WIDTH, CAMERA_HEIGHT
        frame = np.full((h, w, 3), 40, dtype=np.uint8)

        # Office background room
        cv2.rectangle(frame, (0, int(h * 0.65)), (w, h), (60, 50, 45), -1)  # Desk
        cv2.rectangle(frame, (50, 50), (180, 200), (30, 30, 35), -1)        # Poster/window
        cv2.putText(frame, "PROCTORING LAB", (60, 80), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (120, 120, 120), 1)

        t = time.time()
        # Natural subtle head sway
        sway_x = int(np.sin(t * 1.5) * 8)
        sway_y = int(np.cos(t * 1.0) * 4)

        cx, cy = w // 2 + sway_x, h // 2 - 10 + sway_y

        # If simulation mode is active, simulate behaviors
        if self.sim_anomaly_mode == "NO_FACE":
            # Empty desk
            cv2.putText(frame, "[SIMULATION: NO STUDENT AT DESK]", (w // 2 - 160, h // 2),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
            return frame

        # Draw head / silhouette
        cv2.ellipse(frame, (cx, cy + 130), (110, 80), 0, 0, 360, (70, 70, 80), -1) # Shoulders
        cv2.ellipse(frame, (cx, cy), (65, 85), 0, 0, 360, (210, 180, 150), -1)     # Face

        # Eyes & mouth
        eye_y = cy - 15
        mouth_y = cy + 45
        eye_offset = 25

        if self.sim_anomaly_mode == "LOOKING_AWAY":
            eye_offset += 15
            cx_face = cx + 30
            cv2.putText(frame, "[SIMULATION: LOOKING RIGHT]", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)
        elif self.sim_anomaly_mode == "LOOKING_DOWN":
            eye_y += 18
            mouth_y += 15
            cv2.putText(frame, "[SIMULATION: LOOKING DOWN AT LAP]", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 2)

        # Draw eyes
        cv2.circle(frame, (cx - eye_offset, eye_y), 7, (255, 255, 255), -1)
        cv2.circle(frame, (cx + eye_offset, eye_y), 7, (255, 255, 255), -1)
        cv2.circle(frame, (cx - eye_offset, eye_y), 3, (50, 40, 30), -1)
        cv2.circle(frame, (cx + eye_offset, eye_y), 3, (50, 40, 30), -1)

        # Nose & mouth
        cv2.line(frame, (cx, cy), (cx, cy + 20), (180, 150, 120), 2)
        cv2.line(frame, (cx - 15, mouth_y), (cx + 15, mouth_y), (160, 80, 80), 3)

        # If multiple faces simulation
        if self.sim_anomaly_mode == "MULTIPLE_FACES":
            cx2, cy2 = w - 100, h // 2 - 40
            cv2.ellipse(frame, (cx2, cy2), (40, 55), 0, 0, 360, (190, 160, 130), -1)
            cv2.circle(frame, (cx2 - 12, cy2 - 10), 4, (40, 40, 40), -1)
            cv2.circle(frame, (cx2 + 12, cy2 - 10), 4, (40, 40, 40), -1)
            cv2.putText(frame, "[SIMULATION: SECOND PERSON]", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        # If phone simulation
        if self.sim_anomaly_mode == "PHONE":
            px, py = cx + 80, cy + 60
            cv2.rectangle(frame, (px, py), (px + 50, py + 95), (20, 20, 20), -1)
            cv2.rectangle(frame, (px + 4, py + 8), (px + 46, py + 87), (200, 230, 255), -1)
            cv2.putText(frame, "[SIMULATION: PHONE IN VIEW]", (20, h - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        return frame
