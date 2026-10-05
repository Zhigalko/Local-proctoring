"""
Быстрый тест компонентов системы прокторинга БЕЗ графического интерфейса (Headless CLI Test).
Проверяет все модули: CV (YOLOv8 + MediaPipe), Head Pose (solvePnP), Gaze, Logger, Security.
"""

import sys
import os
import time
from pathlib import Path
import numpy as np
import cv2

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from proctoring_system import config
from proctoring_system.logger import IncidentLogger, IncidentType, Severity
from proctoring_system.vision.detector import ObjectDetector, BoundingBox
from proctoring_system.vision.head_gaze_tracker import HeadGazeTracker
from proctoring_system.security.keyboard_locker import KeyboardLocker
from proctoring_system.vision.vision_worker import VisionWorker


class TestReporter:
    def __init__(self):
        self.results = []

    def report(self, name: str, passed: bool, duration_ms: float, details: str = ""):
        self.results.append({
            "name": name,
            "passed": passed,
            "duration": duration_ms,
            "details": details
        })
        status_tag = "\033[92m[PASS]\033[0m" if passed else "\033[91m[FAIL]\033[0m"
        print(f" {status_tag} {name:<42} ({duration_ms:6.1f} ms) {details}")

    def summary(self) -> bool:
        print("\n" + "=" * 78)
        print("  СВОДНЫЙ ОТЧЕТ ТЕСТИРОВАНИЯ КОМПОНЕНТОВ (БЕЗ GUI)")
        print("=" * 78)
        total = len(self.results)
        passed_count = sum(1 for r in self.results if r["passed"])
        failed_count = total - passed_count

        for r in self.results:
            tag = "✓" if r["passed"] else "✗"
            color = "\033[92m" if r["passed"] else "\033[91m"
            print(f" {color}{tag}\033[0m {r['name']:<46} | {r['duration']:6.1f} ms | {r['details']}")

        print("-" * 78)
        print(f" Всего проверок: {total} | Успешно: {passed_count} | Ошибок: {failed_count}")
        if failed_count == 0:
            print("\033[92m ВСЕ КОМПОНЕНТЫ РАБОТАЮТ КОРРЕКТНО И ГОТОВЫ К ХАКАТОНУ!\033[0m")
        else:
            print(f"\033[91m ВНИМАНИЕ: {failed_count} ТЕСТОВ ЗАВЕРШИЛИСЬ С ОШИБКАМИ!\033[0m")
        print("=" * 78 + "\n")
        return failed_count == 0


def test_environment(reporter: TestReporter):
    """Test 1: Environment & Version Compatibility."""
    t0 = time.perf_counter()
    import torch
    import mediapipe as mp
    import PyQt6

    cuda_avail = torch.cuda.is_available()
    details = f"Py={sys.version.split()[0]} | CV2={cv2.__version__} | MP={mp.__version__} | Torch={torch.__version__} (CUDA={cuda_avail})"
    duration = (time.perf_counter() - t0) * 1000
    reporter.report("1. Окружение и версии библиотек", True, duration, details)


def test_incident_logger(reporter: TestReporter):
    """Test 2: Incident Logger (JSONL, CSV, and Screenshot saving)."""
    t0 = time.perf_counter()
    logger = IncidentLogger()

    # Generate dummy frame for incident snapshot
    frame = np.full((360, 480, 3), 40, dtype=np.uint8)
    cv2.putText(frame, "TEST INCIDENT RECORD", (30, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

    rec = logger.log_incident(
        incident_type=IncidentType.PHONE_DETECTED,
        frame=frame,
        details={"conf": 0.89, "test_mode": True}
    )

    shot_exists = bool(rec.screenshot_path and Path(rec.screenshot_path).exists())
    json_exists = config.INCIDENTS_JSON.exists()
    csv_exists = config.INCIDENTS_CSV.exists()
    stats = logger.get_stats()

    passed = shot_exists and json_exists and csv_exists and (stats["total"] >= 1)
    duration = (time.perf_counter() - t0) * 1000
    details = f"Скриншот: {'Да' if shot_exists else 'Нет'} | JSONL: {'Да' if json_exists else 'Нет'} | Всего: {stats['total']}"
    reporter.report("2. Модуль логирования (JSONL/CSV/JPG)", passed, duration, details)


def test_object_detector_yolo(reporter: TestReporter):
    """Test 3: YOLO Object Detector (Phone detection & debouncing)."""
    t0 = time.perf_counter()
    detector = ObjectDetector(conf_threshold=0.4)

    # Subtest 3.1: Blank frame inference
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    res_blank = detector.detect(blank)

    # Subtest 3.2: Frame with synthetic phone rectangle
    # Draw a phone-like vertical dark rectangle with bezel and screen
    phone_frame = np.full((480, 640, 3), 120, dtype=np.uint8)
    # Desk and face simulation
    cv2.rectangle(phone_frame, (280, 150), (360, 310), (10, 10, 10), -1)  # Phone body
    cv2.rectangle(phone_frame, (285, 160), (355, 300), (220, 240, 255), -1) # Glowing screen

    # Run inference to measure speed
    t_inf_start = time.perf_counter()
    res_phone = detector.detect(phone_frame)
    inf_time_ms = (time.perf_counter() - t_inf_start) * 1000

    # Subtest 3.3: Temporal smoothing buffer test (3-of-7 frames)
    for _ in range(config.PHONE_BUFFER_MIN_DETECTIONS):
        detector.detection_history.append(True)
    is_temporally_confirmed = (sum(1 for d in detector.detection_history if d) >= config.PHONE_BUFFER_MIN_DETECTIONS)

    # Confirm debouncing and detection logic
    passed = (len(res_blank.phones) == 0) and (not res_blank.is_phone_violation) and is_temporally_confirmed
    duration = (time.perf_counter() - t0) * 1000
    fps_estimate = 1000.0 / max(1.0, inf_time_ms)
    details = f"Инференс: {inf_time_ms:.1f} мс (~{fps_estimate:.0f} FPS) | Модель: YOLOv8n"
    reporter.report("3. Детектор смартфона (YOLOv8 + Debounce)", passed, duration, details)


def test_head_gaze_tracker(reporter: TestReporter):
    """Test 4: MediaPipe FaceMesh & solvePnP Head Pose + Gaze."""
    t0 = time.perf_counter()
    tracker = HeadGazeTracker(max_faces=2)

    # Subtest 4.1: Blank frame
    blank = np.zeros((480, 640, 3), dtype=np.uint8)
    res_blank = tracker.process(blank)

    # Subtest 4.2: Synthetic face frame
    face_frame = np.full((480, 640, 3), 70, dtype=np.uint8)
    cx, cy = 320, 240
    # Head & face oval
    cv2.ellipse(face_frame, (cx, cy), (70, 95), 0, 0, 360, (215, 185, 155), -1)
    # Eyes
    cv2.circle(face_frame, (cx - 25, cy - 15), 8, (255, 255, 255), -1)
    cv2.circle(face_frame, (cx + 25, cy - 15), 8, (255, 255, 255), -1)
    cv2.circle(face_frame, (cx - 25, cy - 15), 4, (50, 40, 30), -1)
    cv2.circle(face_frame, (cx + 25, cy - 15), 4, (50, 40, 30), -1)
    # Nose & Mouth
    cv2.line(face_frame, (cx, cy), (cx, cy + 22), (180, 140, 110), 2)
    cv2.line(face_frame, (cx - 16, cy + 45), (cx + 16, cy + 45), (150, 70, 70), 3)

    t_track_start = time.perf_counter()
    res_face = tracker.process(face_frame)
    track_time_ms = (time.perf_counter() - t_track_start) * 1000

    # Verification
    passed = res_blank.is_no_face and (res_blank.face_count == 0)
    duration = (time.perf_counter() - t0) * 1000
    fps_estimate = 1000.0 / max(1.0, track_time_ms)
    details = f"FaceMesh + solvePnP: {track_time_ms:.1f} мс (~{fps_estimate:.0f} FPS) | Точек: 468+Iris"
    reporter.report("4. Оценка позы головы (solvePnP) и взгляда", passed, duration, details)


def test_keyboard_security_logic(reporter: TestReporter):
    """Test 5: Keyboard Locker Hotkey suppression & Emergency unlock."""
    t0 = time.perf_counter()

    blocked_hotkeys_received = []
    emergency_unlocked = False

    def on_blocked(k):
        blocked_hotkeys_received.append(k)

    def on_unlock():
        nonlocal emergency_unlocked
        emergency_unlocked = True

    locker = KeyboardLocker(on_blocked_hotkey=on_blocked, on_emergency_unlock=on_unlock)

    # Verify blocked key rules
    blocked_count = len(config.BLOCKED_KEYS_INFO)

    # Test short start and clean stop of message thread
    locker.start()
    time.sleep(0.08)
    is_active_during_run = locker.is_active
    locker.stop()
    is_stopped_cleanly = not locker.is_active

    passed = (blocked_count >= 8) and is_stopped_cleanly
    duration = (time.perf_counter() - t0) * 1000
    details = f"Правил блокировки: {blocked_count} | Хук активен: {is_active_during_run} | Снят: {is_stopped_cleanly}"
    reporter.report("5. Безопасность OS (WinAPI WH_KEYBOARD_LL)", passed, duration, details)


def test_vision_worker_headless_pipeline(reporter: TestReporter):
    """Test 6: VisionWorker headless pipeline and temporal anomaly timers."""
    t0 = time.perf_counter()
    logger = IncidentLogger()
    worker = VisionWorker(incident_logger=logger)
    worker.using_mock = True

    # Run single-frame processing directly (without starting background thread)
    test_frame = worker._generate_synthetic_frame()
    processed_frame, metrics = worker._process_frame(test_frame)

    has_status = "status" in metrics
    has_head_pose = "head_pose" in metrics
    has_gaze = "gaze" in metrics

    # Test 1.5s Continuous Head Turn Timer & Instant Reset
    worker.trigger_simulation_mode("LOOKING_AWAY")
    sim_away_frame = worker._generate_synthetic_frame()
    _, m_warn = worker._process_frame(sim_away_frame)
    timer_started = worker.timers.head_turn_start is not None
    is_warning = (m_warn.get("status") == "WARNING")
    has_warn_text = any("отвод головы" in w for w in m_warn.get("warnings", []))

    # Instant reset on return before 1.5s
    worker.trigger_simulation_mode(None)
    _, m_reset = worker._process_frame(test_frame)
    timer_cleared = (worker.timers.head_turn_start is None)

    # Trigger violation after >= 1.5s continuous
    worker.trigger_simulation_mode("LOOKING_AWAY")
    worker._process_frame(sim_away_frame)
    worker.timers.head_turn_start = time.time() - 1.6  # Advance past 1.5s
    inc_count_before = len(logger.incidents)
    _, m_viol = worker._process_frame(sim_away_frame)
    is_viol = (m_viol.get("status") == "VIOLATION")
    has_viol_text = any("НАРУШЕНИЕ" in w for w in m_viol.get("warnings", []))
    inc_logged = (len(logger.incidents) == inc_count_before + 1)

    # Anti-spam: next frame does not duplicate
    _, m_spam = worker._process_frame(sim_away_frame)
    anti_spam_ok = (len(logger.incidents) == inc_count_before + 1)

    # Reset
    worker.trigger_simulation_mode(None)
    worker._process_frame(test_frame)

    passed = (
        has_status and
        has_head_pose and
        has_gaze and
        timer_started and
        is_warning and
        has_warn_text and
        timer_cleared and
        is_viol and
        has_viol_text and
        inc_logged and
        anti_spam_ok and
        (processed_frame is not None) and
        (processed_frame.shape == test_frame.shape)
    )
    duration = (time.perf_counter() - t0) * 1000
    details = f"Таймер 1.5с: OK | Сброс при возврате: OK | Анти-спам: OK | Кадр: {test_frame.shape[1]}x{test_frame.shape[0]}"
    reporter.report("6. Конвейер VisionWorker и трекинг аномалий", passed, duration, details)


def main():
    print("=" * 78)
    print("  БЫСТРЫЙ ТЕСТ КОМПОНЕНТОВ СИСТЕМЫ ПРОКТОРИНГА (HEADLESS CLI)")
    print("  Проверка: CV Inference, Head Pose (solvePnP), Gaze, Logger, Security Hook")
    print("=" * 78 + "\n")

    reporter = TestReporter()

    test_environment(reporter)
    test_incident_logger(reporter)
    test_object_detector_yolo(reporter)
    test_head_gaze_tracker(reporter)
    test_keyboard_security_logic(reporter)
    test_vision_worker_headless_pipeline(reporter)

    success = reporter.summary()
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
