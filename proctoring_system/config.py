"""
Configuration settings for the Proctoring CV + Security System.
Contains thresholds, model configurations, hotkeys, paths, and operational parameters.
"""

from pathlib import Path
import numpy as np

# Base directory paths
BASE_DIR = Path(__file__).resolve().parent.parent
LOGS_DIR = BASE_DIR / "logs"
INCIDENTS_DIR = LOGS_DIR / "incidents"
INCIDENTS_JSON = LOGS_DIR / "incidents.jsonl"
INCIDENTS_CSV = LOGS_DIR / "incidents.csv"
YOLO_MODEL_PATH = str(BASE_DIR / "yolov8n.pt")

# Ensure required directories exist
LOGS_DIR.mkdir(parents=True, exist_ok=True)
INCIDENTS_DIR.mkdir(parents=True, exist_ok=True)

# Camera / Video stream configuration
CAMERA_INDEX = 0
CAMERA_WIDTH = 640
CAMERA_HEIGHT = 480
TARGET_FPS = 30
ENABLE_MOCK_FALLBACK = True  # If no webcam is physically present, use synthetic simulator

# YOLO Object Detection Configuration
YOLO_CONFIDENCE_THRESHOLD = 0.28  # Optimized to 0.28 to detect phones held at angles/in hand
YOLO_PHONE_CLASS_ID = 67          # COCO class 'cell phone'
YOLO_PERSON_CLASS_ID = 0          # COCO class 'person'
YOLO_IMGSZ = 640                  # High-accuracy inference frame size (640px)
PHONE_BUFFER_SIZE = 7             # Sliding temporal buffer window length
PHONE_BUFFER_MIN_DETECTIONS = 3   # Must be detected in at least 3 of last 7 frames

# Risk Zone for Phone Detection
# (phone bounding box center in upper 65% of screen or in proximity to face)
PHONE_RISK_ROI_MAX_Y = 0.70

# Head Pose Estimation & Smoothing (EMA filter & Baseline Calibration)
HEAD_POSE_EMA_ALPHA = 0.3         # Exponential Moving Average smoothing factor
CALIBRATION_DURATION = 3.0        # Baseline calibration window in seconds
CALIBRATION_MIN_SAMPLES = 15      # Minimum frames required to compute baseline

# Visual Overlays Configuration (Clean Video Feed for Student)
DRAW_HEAD_AXES_VECTORS = False    # Disable 3D axes/lines/arrows overlay on camera feed
DRAW_BOUNDING_BOXES = False       # Disable bounding boxes around face and objects
DRAW_FACEMESH_LANDMARKS = False   # Disable face mesh landmark points
DRAW_DEBUG_OVERLAYS = False       # Clean video stream view for user (no vectors, boxes, or mesh)

# Head Pose Estimation Thresholds (Euler angles in degrees)
# Permissible head movement calibrated relative to monitor center
HEAD_YAW_THRESHOLD = 38.0              # Permissible horizontal head turn (|delta_yaw| > 38.0° triggers violation)
HEAD_PITCH_DOWN_THRESHOLD = -30.0      # Permissible downward tilt (delta_pitch < -30.0° triggers violation)
HEAD_PITCH_UP_THRESHOLD = 30.0         # Permissible upward tilt (delta_pitch > 30.0° triggers violation)
ROLL_THRESHOLD = 25.0

# Aliases for backward compatibility
YAW_THRESHOLD_LEFT = -HEAD_YAW_THRESHOLD
YAW_THRESHOLD_RIGHT = HEAD_YAW_THRESHOLD
PITCH_THRESHOLD_DOWN = HEAD_PITCH_DOWN_THRESHOLD
PITCH_THRESHOLD_UP = HEAD_PITCH_UP_THRESHOLD

# Gaze Estimation Thresholds
# Iris horizontal displacement ratio: normal is ~0.45 - 0.55
GAZE_RATIO_LEFT = 0.35
GAZE_RATIO_RIGHT = 0.65
GAZE_RATIO_DOWN = 0.65

# Universal sustained violation threshold in seconds (head pose, gaze, device detection)
VIOLATION_DURATION_THRESHOLD = 1.5

# Temporal Incident Timers (seconds of sustained violation before alert triggers)
DURATION_NO_FACE = 1.5                                    # Time without any face in frame
DURATION_MULTIPLE_FACES = 0.8                             # Time with >1 face in frame
DURATION_LOOKING_AWAY = VIOLATION_DURATION_THRESHOLD      # Time looking left/right (Head Pose Yaw: 1.5s)
DURATION_LOOKING_DOWN = VIOLATION_DURATION_THRESHOLD      # Time looking down (Head Pose Pitch: 1.5s)
DURATION_GAZE_AWAY = VIOLATION_DURATION_THRESHOLD         # Time eyes diverted away from screen (1.5s)
DURATION_PHONE_DETECTED = VIOLATION_DURATION_THRESHOLD    # Time phone must persist (1.5s)

# Incident Cooldown (seconds between logging the same recurring incident to avoid log spam)
INCIDENT_LOG_COOLDOWN = 5.0

# Canonical 3D Face Model Points for solvePnP (in millimeters)
# 6 standard facial landmarks:
# 1: Nose tip
# 152: Chin
# 33: Left eye outer corner
# 263: Right eye outer corner
# 61: Left mouth corner
# 291: Right mouth corner
CANONICAL_FACE_3D = np.array([
    (0.0, 0.0, 0.0),             # Nose tip (landmark 1)
    (0.0, 330.0, -65.0),         # Chin (landmark 152) - down (+Y)
    (-225.0, -170.0, -135.0),    # Left eye outer corner (landmark 33) - image left (-X), up (-Y)
    (225.0, -170.0, -135.0),     # Right eye outer corner (landmark 263) - image right (+X), up (-Y)
    (-150.0, 150.0, -125.0),     # Left mouth corner (landmark 61) - image left (-X), down (+Y)
    (150.0, 150.0, -125.0)       # Right mouth corner (landmark 291) - image right (+X), down (+Y)
], dtype=np.float64)

# Security & Kiosk Mode Settings
KIOSK_FULLSCREEN = True
KIOSK_STAYS_ON_TOP = True
ADMIN_UNLOCK_PASSWORD = "proctor2026"
ADMIN_EMERGENCY_HOTKEY = "Ctrl+Alt+Shift+F12"

# Blocked Key Names and Win32 Virtual Key Codes
# Used by KeyboardLocker
BLOCKED_KEYS_INFO = [
    {"name": "Alt+Tab", "desc": "Switch application"},
    {"name": "Win Key", "desc": "Windows start menu"},
    {"name": "Ctrl+C", "desc": "Copy to clipboard"},
    {"name": "Ctrl+V", "desc": "Paste from clipboard"},
    {"name": "Ctrl+X", "desc": "Cut to clipboard"},
    {"name": "Alt+F4", "desc": "Close application"},
    {"name": "PrintScreen", "desc": "Screenshot capture"},
    {"name": "Ctrl+Shift+Esc", "desc": "Task Manager shortcut"},
    {"name": "Ctrl+Esc", "desc": "Start menu alternative"}
]
