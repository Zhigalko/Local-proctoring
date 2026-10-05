"""
YOLO Object Detector for Proctoring System.
Specialized in high-speed detection of smartphones and foreign objects with anti-flicker debouncing.
"""

from dataclasses import dataclass
from collections import deque
import cv2
import numpy as np
from ultralytics import YOLO

from proctoring_system.config import (
    YOLO_MODEL_PATH,
    YOLO_CONFIDENCE_THRESHOLD,
    YOLO_PHONE_CLASS_ID,
    YOLO_IMGSZ,
    PHONE_BUFFER_SIZE,
    PHONE_BUFFER_MIN_DETECTIONS,
    PHONE_RISK_ROI_MAX_Y,
    DRAW_BOUNDING_BOXES,
    DRAW_DEBUG_OVERLAYS
)


@dataclass
class BoundingBox:
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def center(self) -> tuple[int, int]:
        return ((self.x1 + self.x2) // 2, (self.y1 + self.y2) // 2)

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return max(0, self.width) * max(0, self.height)


@dataclass
class PhoneDetection:
    bbox: BoundingBox
    confidence: float
    in_risk_zone: bool
    is_confirmed: bool  # True when temporal smoothing threshold (3/7) reached
    persistence_count: int


@dataclass
class DetectionResult:
    phones: list[PhoneDetection]
    persons_count: int
    is_phone_violation: bool
    max_phone_conf: float


class ObjectDetector:
    """
    Wraps Ultralytics YOLOv8 for cell phone detection with optimized confidence,
    640px resolution, target class filtering (classes=[67]), and temporal smoothing.
    """

    def __init__(self, model_path: str = YOLO_MODEL_PATH, conf_threshold: float = YOLO_CONFIDENCE_THRESHOLD):
        self.conf_threshold = conf_threshold
        print(f"[ObjectDetector] Loading YOLO model from {model_path} (conf={self.conf_threshold}, imgsz={YOLO_IMGSZ})...")
        self.model = YOLO(model_path)
        # Warmup model once with target class
        _blank = np.zeros((320, 320, 3), dtype=np.uint8)
        self.model(_blank, classes=[YOLO_PHONE_CLASS_ID], verbose=False)
        print("[ObjectDetector] YOLO model initialized and warmed up.")

        # Temporal smoothing history queue (stores boolean: was phone detected in frame?)
        self.detection_history = deque(maxlen=PHONE_BUFFER_SIZE)
        self.last_detected_phones: list[PhoneDetection] = []

    def detect(self, frame: np.ndarray, face_boxes: list[BoundingBox] | None = None) -> DetectionResult:
        """
        Run inference on frame, detect cell phones with target class 67, imgsz=640, conf=0.28,
        and apply 3-of-7 temporal smoothing.
        """
        if frame is None or frame.size == 0:
            return DetectionResult(phones=[], persons_count=0, is_phone_violation=False, max_phone_conf=0.0)

        h, w = frame.shape[:2]
        # Target class: cell phone (67), imgsz=640, conf=0.28
        results = self.model(
            frame,
            classes=[YOLO_PHONE_CLASS_ID],
            conf=self.conf_threshold,
            imgsz=YOLO_IMGSZ,
            verbose=False
        )

        raw_phones: list[tuple[BoundingBox, float]] = []

        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                cls_id = int(box.cls[0].item())
                conf = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().astype(int)
                bbox = BoundingBox(x1=int(xyxy[0]), y1=int(xyxy[1]), x2=int(xyxy[2]), y2=int(xyxy[3]))

                if cls_id == YOLO_PHONE_CLASS_ID:
                    raw_phones.append((bbox, conf))

        phone_found_in_frame = len(raw_phones) > 0
        self.detection_history.append(phone_found_in_frame)

        # Temporal smoothing criteria:
        # If phone is detected in at least 3 of the last 7 frames, consider device present!
        recent_positives = sum(1 for d in self.detection_history if d)
        is_temporally_confirmed = (recent_positives >= PHONE_BUFFER_MIN_DETECTIONS)

        phones: list[PhoneDetection] = []
        max_conf = 0.0

        if phone_found_in_frame:
            for bbox, conf in raw_phones:
                max_conf = max(max_conf, conf)
                center_x, center_y = bbox.center

                # Risk Zone Analysis:
                # 1. Vertical position: is the phone held up in view (upper/middle screen)?
                in_vertical_risk = (center_y / h) <= PHONE_RISK_ROI_MAX_Y

                # 2. Proximity to face: is phone close to head/face area?
                near_face = False
                if face_boxes:
                    for fb in face_boxes:
                        fc_x, fc_y = fb.center
                        dist = np.hypot(center_x - fc_x, center_y - fc_y)
                        if dist < (fb.width * 1.6):
                            near_face = True
                            break

                in_risk = in_vertical_risk or near_face

                phones.append(
                    PhoneDetection(
                        bbox=bbox,
                        confidence=conf,
                        in_risk_zone=in_risk,
                        is_confirmed=is_temporally_confirmed,
                        persistence_count=recent_positives
                    )
                )
            self.last_detected_phones = phones
        elif is_temporally_confirmed and self.last_detected_phones:
            # Phone momentarily occluded for 1-2 frames: maintain smoothed presence
            phones = self.last_detected_phones
            max_conf = max((p.confidence for p in phones), default=self.conf_threshold)
        else:
            self.last_detected_phones = []

        is_violation = is_temporally_confirmed and len(phones) > 0
        persons_detected = len(face_boxes) if face_boxes else 0

        return DetectionResult(
            phones=phones,
            persons_count=persons_detected,
            is_phone_violation=is_violation,
            max_phone_conf=max_conf
        )

    def draw_overlays(self, frame: np.ndarray, result: DetectionResult) -> np.ndarray:
        """
        Visual overlays for detected objects.
        Clean video feed for student: bounding boxes and labels are disabled.
        All math and YOLO detection continue running uninterrupted in the background.
        """
        if not DRAW_DEBUG_OVERLAYS or not DRAW_BOUNDING_BOXES:
            # Clean camera view: return original frame without clutter
            return frame

        for phone in result.phones:
            bbox = phone.bbox
            color = (0, 0, 255) if phone.is_confirmed else (0, 165, 255)  # Red if confirmed, orange if debouncing
            thickness = 3 if phone.is_confirmed else 2

            cv2.rectangle(frame, (bbox.x1, bbox.y1), (bbox.x2, bbox.y2), color, thickness)

            status_tag = "PHONE DETECTED!" if phone.is_confirmed else f"Debouncing ({phone.persistence_count}/{PHONE_BUFFER_MIN_DETECTIONS})"
            label = f"{status_tag} {phone.confidence:.0%}"

            # Text background pill
            (txt_w, txt_h), baseline = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.55, 2)
            cv2.rectangle(
                frame,
                (bbox.x1, max(0, bbox.y1 - txt_h - 10)),
                (bbox.x1 + txt_w + 10, bbox.y1),
                color,
                -1
            )
            cv2.putText(
                frame,
                label,
                (bbox.x1 + 5, bbox.y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )

        return frame
