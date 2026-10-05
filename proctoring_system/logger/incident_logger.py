"""
Incident Logger for Proctoring System.
Handles structured logging (JSONL/CSV), safe screenshot capture,
bounded in-memory queue to prevent memory leaks, and thread-safe operations.
"""

from dataclasses import dataclass, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from collections import deque
import json
import csv
import os
import threading
import cv2
import numpy as np

from proctoring_system.config import INCIDENTS_DIR, INCIDENTS_JSON, INCIDENTS_CSV


class IncidentType(str, Enum):
    PHONE_DETECTED = "PHONE_DETECTED"
    LOOKING_DOWN = "LOOKING_DOWN"
    LOOKING_AWAY = "LOOKING_AWAY"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    NO_FACE = "NO_FACE"
    GAZE_DEVIATION = "GAZE_DEVIATION"
    GAZE_AWAY = "GAZE_AWAY"
    HOTKEY_BLOCKED = "HOTKEY_BLOCKED"
    FOCUS_LOST = "FOCUS_LOST"


class Severity(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


@dataclass
class IncidentRecord:
    timestamp: str
    incident_type: str
    severity: str
    description: str
    details: dict
    screenshot_path: str = ""

    def to_dict(self):
        return asdict(self)


class IncidentLogger:
    """
    Thread-safe logger for proctoring violation incidents.
    Saves screenshot artifacts safely without crashing on disk errors,
    and maintains bounded in-memory queue (max 50) to prevent RAM leaks.
    """

    MAX_IN_MEMORY_INCIDENTS = 50

    RUSSIAN_DESCRIPTIONS = {
        IncidentType.PHONE_DETECTED: "Обнаружен смартфон в рабочей зоне",
        IncidentType.LOOKING_DOWN: "Взгляд опущен вниз (подозрение на телефон/шпаргалку)",
        IncidentType.LOOKING_AWAY: "Поворот головы в сторону (подозрение на второй экран)",
        IncidentType.MULTIPLE_FACES: "Обнаружено несколько лиц в кадре",
        IncidentType.NO_FACE: "Студент покинул рабочее место (лицо не найдено)",
        IncidentType.GAZE_DEVIATION: "Взгляд отведён от экрана тестирования",
        IncidentType.GAZE_AWAY: "Взгляд отведён от экрана тестирования",
        IncidentType.HOTKEY_BLOCKED: "Попытка использования запрещённой комбинации клавиш",
        IncidentType.FOCUS_LOST: "Потеря фокуса окна тестирования (попытка переключения)"
    }

    SEVERITY_MAP = {
        IncidentType.PHONE_DETECTED: Severity.CRITICAL,
        IncidentType.LOOKING_DOWN: Severity.HIGH,
        IncidentType.LOOKING_AWAY: Severity.HIGH,
        IncidentType.MULTIPLE_FACES: Severity.CRITICAL,
        IncidentType.NO_FACE: Severity.HIGH,
        IncidentType.GAZE_DEVIATION: Severity.MEDIUM,
        IncidentType.GAZE_AWAY: Severity.MEDIUM,
        IncidentType.HOTKEY_BLOCKED: Severity.HIGH,
        IncidentType.FOCUS_LOST: Severity.CRITICAL
    }

    def __init__(self, max_in_memory: int = MAX_IN_MEMORY_INCIDENTS):
        self._lock = threading.Lock()
        # Bounded in-memory history to avoid RAM leaks
        self.max_in_memory = max_in_memory
        self.incidents: deque[IncidentRecord] = deque(maxlen=max_in_memory)
        self.total_count = 0
        self.by_type_counts: dict[str, int] = {}
        self._ensure_directories()
        self._init_csv()

    def _ensure_directories(self):
        """Ensure incidents directories exist."""
        try:
            os.makedirs(str(INCIDENTS_DIR), exist_ok=True)
            if INCIDENTS_JSON.parent:
                os.makedirs(str(INCIDENTS_JSON.parent), exist_ok=True)
        except Exception as e:
            print(f"[IncidentLogger] Error creating directories: {e}")

    def _init_csv(self):
        """Ensure CSV file exists with appropriate header."""
        try:
            self._ensure_directories()
            if not INCIDENTS_CSV.exists() or INCIDENTS_CSV.stat().st_size == 0:
                with open(INCIDENTS_CSV, mode="w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(["Timestamp", "Type", "Severity", "Description", "Details", "Screenshot"])
        except Exception as e:
            print(f"[IncidentLogger] Error initializing CSV: {e}")

    def log_incident(
        self,
        incident_type: IncidentType | str,
        frame: np.ndarray | None = None,
        details: dict | None = None,
        custom_desc: str | None = None
    ) -> IncidentRecord:
        """
        Record a violation incident, save an independent frame screenshot copy,
        and persist to disk without crashing under I/O errors.
        """
        try:
            if isinstance(incident_type, str):
                try:
                    incident_type = IncidentType(incident_type)
                except ValueError:
                    pass

            now = datetime.now()
            timestamp_str = now.isoformat()
            file_timestamp = now.strftime("%Y%m%d_%H%M%S_%f")[:19]

            type_str = incident_type.value if isinstance(incident_type, IncidentType) else str(incident_type)
            severity = self.SEVERITY_MAP.get(incident_type, Severity.MEDIUM).value
            description = custom_desc or self.RUSSIAN_DESCRIPTIONS.get(incident_type, "Нарушение регламента тестирования")
            details = details or {}

            # 2. Безопасное сохранение скриншота:
            screenshot_path_str = ""
            if frame is not None and frame.size > 0:
                try:
                    self._ensure_directories()
                    # Делаем независимую копию кадра перед сохранением
                    save_frame = frame.copy()
                    screenshot_filename = f"{file_timestamp}_{type_str}.jpg"
                    screenshot_full_path = INCIDENTS_DIR / screenshot_filename
                    success = cv2.imwrite(str(screenshot_full_path), save_frame)
                    if success:
                        screenshot_path_str = str(screenshot_full_path)
                    else:
                        print(f"[IncidentLogger] cv2.imwrite returned False for {screenshot_full_path}")
                except Exception as e:
                    print(f"[IncidentLogger] Error saving screenshot to disk: {e}")

            record = IncidentRecord(
                timestamp=timestamp_str,
                incident_type=type_str,
                severity=severity,
                description=description,
                details=details,
                screenshot_path=screenshot_path_str
            )

            # 3. Очистка памяти: сохраняем в ограниченную очередь
            with self._lock:
                self.incidents.append(record)
                self.total_count += 1
                self.by_type_counts[type_str] = self.by_type_counts.get(type_str, 0) + 1
                self._write_jsonl(record)
                self._write_csv(record)

            print(f"[SECURITY ALERT] {record.severity}: {record.incident_type} - {record.description}")
            return record

        except Exception as e:
            print(f"[IncidentLogger] Error in log_incident: {e}")
            # Fallback record so caller doesn't fail
            return IncidentRecord(
                timestamp=datetime.now().isoformat(),
                incident_type=str(incident_type),
                severity=Severity.HIGH.value,
                description="Ошибка записи инцидента",
                details=details or {},
                screenshot_path=""
            )

    def _write_jsonl(self, record: IncidentRecord):
        try:
            with open(INCIDENTS_JSON, mode="a", encoding="utf-8") as f:
                f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[IncidentLogger] Error writing JSONL: {e}")

    def _write_csv(self, record: IncidentRecord):
        try:
            with open(INCIDENTS_CSV, mode="a", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow([
                    record.timestamp,
                    record.incident_type,
                    record.severity,
                    record.description,
                    json.dumps(record.details, ensure_ascii=False),
                    record.screenshot_path
                ])
        except Exception as e:
            print(f"[IncidentLogger] Error writing CSV: {e}")

    def get_stats(self) -> dict:
        """Returns statistics on logged violations."""
        with self._lock:
            return {
                "total": self.total_count,
                "in_memory": len(self.incidents),
                "by_type": dict(self.by_type_counts)
            }

    def get_recent(self, limit: int = 20) -> list[IncidentRecord]:
        """Returns recent incident records."""
        with self._lock:
            return list(self.incidents)[-limit:]
