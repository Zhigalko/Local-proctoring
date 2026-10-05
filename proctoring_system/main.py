"""
Entry Point for the Local Proctoring System ("Proctoring CV + Security").
Initializes UI, starts Computer Vision worker thread, installs low-level OS security hooks,
and coordinates incident response.
"""

import sys
import argparse
from pathlib import Path

# Ensure project root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt, QObject, pyqtSignal

from proctoring_system import config
from proctoring_system.logger import IncidentLogger, IncidentType
from proctoring_system.security import KeyboardLocker
from proctoring_system.vision import VisionWorker
from proctoring_system.ui import MainWindow


class KeyboardHookBridge(QObject):
    """Bridge for thread-safe cross-thread signal emission from keyboard hook to GUI."""
    blocked_key_signal = pyqtSignal(str)
    emergency_unlock_signal = pyqtSignal()


def parse_arguments():
    parser = argparse.ArgumentParser(description="Local proctoring (CV + Security)")
    parser.add_argument("--windowed", action="store_true", help="Запуск в оконном режиме (для отладки)")
    parser.add_argument("--camera", type=int, default=config.CAMERA_INDEX, help="Индекс камеры (по умолчанию 0)")
    parser.add_argument("--mock", action="store_true", help="Принудительный запуск синтетического симулятора камеры")
    parser.add_argument("--no-hook", action="store_true", help="Отключить системный хук клавиатуры")
    return parser.parse_args()


def main():
    args = parse_arguments()

    print("=" * 65)
    print("  LOCAL PROCTORING (CV + DESKTOP SECURITY)")
    print("  Ultralytics YOLOv8 + MediaPipe FaceMesh + Windows Kiosk")
    print("=" * 65)

    # 1. Initialize Qt Application
    app = QApplication(sys.argv)
    app.setApplicationName("Local proctoring")

    # 2. Initialize Incident Logger
    incident_logger = IncidentLogger()
    print(f"[Main] Incident Logger initialized. Log directory: {config.LOGS_DIR}")

    # 3. Configure Camera and Vision Worker
    if args.mock:
        config.ENABLE_MOCK_FALLBACK = True
    config.CAMERA_INDEX = args.camera

    vision_worker = VisionWorker(incident_logger=incident_logger)
    if args.mock:
        vision_worker.using_mock = True

    # 4. Initialize Main Window (Kiosk UI)
    if args.windowed:
        config.KIOSK_FULLSCREEN = False
        config.KIOSK_STAYS_ON_TOP = False

    window = MainWindow(vision_worker=vision_worker, incident_logger=incident_logger)

    # 5. Initialize Low-level Keyboard Hook with thread-safe Qt Signal Bridge
    keyboard_locker = None
    if not args.no_hook:
        bridge = KeyboardHookBridge(window)
        bridge.blocked_key_signal.connect(window.on_keyboard_blocked_key)
        bridge.emergency_unlock_signal.connect(window._admin_unlock_prompt)

        def handle_blocked_key(key_name: str):
            bridge.blocked_key_signal.emit(key_name)

        def handle_emergency_unlock():
            bridge.emergency_unlock_signal.emit()

        keyboard_locker = KeyboardLocker(
            on_blocked_hotkey=handle_blocked_key,
            on_emergency_unlock=handle_emergency_unlock
        )
        keyboard_locker.start()
        window.keyboard_locker = keyboard_locker
    else:
        print("[Main] Keyboard locker disabled via --no-hook flag.")

    # 6. Show Window and Start Workers
    if config.KIOSK_FULLSCREEN:
        window.showFullScreen()
    else:
        window.resize(1280, 820)
        window.show()

    # Start vision inference thread
    vision_worker.start()

    # Start OS focus monitor
    window.security_watcher.start()

    print("[Main] System fully initialized and running.")
    print("  * Для выхода нажмите 'Выход', клавишу Esc или горячие клавиши Ctrl+Alt+Shift+F12 (выход без пароля)")

    # 7. Run Main Event Loop
    exit_code = app.exec()

    # 8. Clean Shutdown
    print("[Main] Shutting down proctoring system...")
    if keyboard_locker:
        keyboard_locker.stop()
    vision_worker.stop()
    print("[Main] Shutdown complete. Goodbye.")

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
