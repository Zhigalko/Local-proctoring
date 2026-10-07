"""
Main Fullscreen Kiosk Window for the Local Proctoring System.
Integrates QWebEngineView for online testing, real-time CV PIP webcam preview,
visual alert overlays, incident log inspection, and security lockdown.
"""

import json
import base64
from datetime import datetime
from PyQt6.QtCore import Qt, QTimer, QUrl
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QFrame, QInputDialog, QMessageBox, QGraphicsDropShadowEffect
)
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage

from proctoring_system.config import (
    KIOSK_FULLSCREEN,
    KIOSK_STAYS_ON_TOP,
    ADMIN_UNLOCK_PASSWORD,
    ADMIN_EMERGENCY_HOTKEY
)
from proctoring_system.logger import IncidentLogger, IncidentType
from proctoring_system.security import WindowSecurityWatcher
from proctoring_system.vision import VisionWorker
from proctoring_system.ui.exam_content import EXAM_HTML_CONTENT
from proctoring_system.ui.hud_overlay import (
    CameraPipWidget,
    AlertBannerOverlay,
    FocusLostLockOverlay,
    IncidentLogDialog
)


class ProctorWebEnginePage(QWebEnginePage):
    """Custom web engine page that intercepts proctor:// custom URLs and suppresses native JS popups."""

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self.main_window = main_window

    def acceptNavigationRequest(self, url: QUrl, nav_type, is_main_frame: bool) -> bool:
        url_str = url.toString()
        if url.scheme() == "proctor" or url_str.startswith("proctor://"):
            self.main_window._on_web_url_changed(url)
            return False  # Prevent Chromium from navigating away or opening external handlers
        return super().acceptNavigationRequest(url, nav_type, is_main_frame)

    def javaScriptAlert(self, securityOrigin, msg: str):
        pass  # Suppress browser alert popups

    def javaScriptConfirm(self, securityOrigin, msg: str) -> bool:
        return True  # Suppress browser confirm popups


class MainWindow(QMainWindow):
    """
    Kiosk exam window with integrated computer vision proctoring and desktop security.
    """

    def __init__(self, vision_worker: VisionWorker, incident_logger: IncidentLogger):
        super().__init__()
        self.vision_worker = vision_worker
        self.logger = incident_logger

        self.setWindowTitle("Local proctoring")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)

        # Apply Kiosk window flags
        flags = Qt.WindowType.Window
        if KIOSK_FULLSCREEN:
            flags |= Qt.WindowType.FramelessWindowHint
        if KIOSK_STAYS_ON_TOP:
            flags |= Qt.WindowType.WindowStaysOnTopHint
        self.setWindowFlags(flags)

        # Metrics cache & Session tracking
        self.total_violations = 0
        self.exam_finished = False
        self.keyboard_locker = None
        self.session_student_name = "Студент"
        self.session_start_time = datetime.now()
        self.session_incidents = []
        self.current_session_dir = None
        self.admin_window = None

        # Build UI layout
        self._init_ui()

        # Wire vision worker signals
        self.vision_worker.frame_ready.connect(self.pip_widget.update_frame)
        self.vision_worker.status_updated.connect(self._on_status_updated)
        self.vision_worker.incident_triggered.connect(self._on_incident_triggered)

        # Security watcher
        self.security_watcher = WindowSecurityWatcher(self)
        self.security_watcher.focus_lost.connect(self._on_focus_lost)
        self.security_watcher.focus_regained.connect(self._on_focus_regained)

        # Keyboard exit shortcuts (both Esc and Ctrl+Alt+Shift+F12)
        self.escape_shortcut = QShortcut(QKeySequence("Ctrl+Alt+Shift+F12"), self)
        self.escape_shortcut.activated.connect(self._exit_prompt)
        self.esc_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.esc_shortcut.activated.connect(self._exit_prompt)

        # Admin / Proctor Dashboard shortcut (Ctrl + Shift + A)
        self.admin_shortcut = QShortcut(QKeySequence("Ctrl+Shift+A"), self)
        self.admin_shortcut.activated.connect(self._open_admin_dashboard)

        # Baseline recalibration shortcut (key 'C')
        self.calib_shortcut = QShortcut(QKeySequence("C"), self)
        self.calib_shortcut.activated.connect(self._trigger_recalibration)

    def _init_ui(self):
        """Create central widget and all overlay layers with clean, modern layout."""
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        # 1. Main Exam Browser View (occupies full screen)
        self.web_view = QWebEngineView(self)
        self.web_page = ProctorWebEnginePage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.setHtml(EXAM_HTML_CONTENT)
        self.web_page.windowCloseRequested.connect(self.close)
        self.web_view.urlChanged.connect(self._on_web_url_changed)
        self.central_layout.addWidget(self.web_view, stretch=1)

        # 2. Floating Camera PiP Widget (anchored bottom-right with compact status indicator)
        self.pip_widget = CameraPipWidget(self)
        self.pip_widget.show()

        # 3. Alert Banner Overlay (anchored top-center)
        self.alert_banner = AlertBannerOverlay(self)

        # 4. Focus Lost Security Curtain (covers entire window)
        self.focus_lock = FocusLostLockOverlay(self)
        self.focus_lock.resumed.connect(self._on_focus_lock_resumed)

    def resizeEvent(self, event):
        """Keep PiP, banner, and curtain sized and positioned correctly."""
        super().resizeEvent(event)
        if not (hasattr(self, "pip_widget") and hasattr(self, "alert_banner") and hasattr(self, "focus_lock")):
            return

        w = self.width()
        h = self.height()

        # Position PiP widget at bottom-right corner
        pip_w, pip_h = self.pip_widget.width(), self.pip_widget.height()
        self.pip_widget.move(w - pip_w - 20, h - pip_h - 20)

        # Position Alert Banner at top-center
        banner_w = min(720, w - 80)
        self.alert_banner.setGeometry((w - banner_w) // 2, 20, banner_w, 64)

        # Position Focus Lost lock to cover the full window
        self.focus_lock.setGeometry(0, 0, w, h)

    def _on_status_updated(self, metrics: dict):
        """Update PiP camera status badge."""
        if getattr(self, "exam_finished", False):
            try:
                self.pip_widget.update_status("FINISHED", 0.0, "CENTER", False)
            except Exception:
                pass
            return
        try:
            status = metrics.get("status", "NORMAL")
            fps = metrics.get("fps", 0.0)
            gaze = metrics.get("gaze", "NONE")
            phone = metrics.get("phone_detected", False)

            # Update PiP widget
            self.pip_widget.update_status(status, fps, gaze, phone)

            if hasattr(self, "status_chip") and self.status_chip:
                target_chip_state = "VIOLATION" if (status == "VIOLATION" or phone) else status
                if getattr(self, "_last_chip_state", None) != target_chip_state:
                    self._last_chip_state = target_chip_state
                    if target_chip_state == "VIOLATION":
                        self.status_chip.setText("СТАТУС: НАРУШЕНИЕ!")
                    elif target_chip_state == "WARNING":
                        self.status_chip.setText("СТАТУС: ПРЕДУПРЕЖДЕНИЕ")
                    else:
                        self.status_chip.setText("СТАТУС: В НОРМЕ")

        except Exception as e:
            print(f"[MainWindow] Error in _on_status_updated: {e}")

    def _trigger_recalibration(self):
        """Trigger baseline neutral gaze auto-recalibration."""
        if getattr(self, "exam_finished", False):
            return
        self.vision_worker.recalibrate()
        self.alert_banner.show_alert(
            title="АВТОКАЛИБРОВКА ПОЛОЖЕНИЯ",
            description="Пожалуйста, смотрите прямо в центр монитора...",
            severity="LOW",
            duration_ms=1500
        )

    def _on_incident_triggered(self, incident_type: str, description: str, severity: str, screenshot_path: str):
        """Trigger visual banner and increment incident counter with non-blocking 2s HUD overlay."""
        if getattr(self, "exam_finished", False):
            return
        try:
            self.total_violations += 1
            if hasattr(self, "violations_chip") and self.violations_chip:
                self.violations_chip.setText(f"Инцидентов: {self.total_violations}")

            # Record in active session history
            self.session_incidents.append({
                "incident_type": incident_type,
                "description": description,
                "severity": severity,
                "screenshot_path": screenshot_path,
                "timestamp": datetime.now().isoformat()
            })

            # Non-blocking HUD alert overlay for 2 seconds
            self.alert_banner.show_alert(
                title=f"НАРУШЕНИЕ: {incident_type}",
                description=description,
                severity=severity,
                duration_ms=2000
            )
        except Exception as e:
            print(f"[MainWindow] Error in _on_incident_triggered: {e}")

    def on_keyboard_blocked_key(self, key_name: str):
        """Handle blocked hotkey event safely in the GUI thread."""
        if getattr(self, "exam_finished", False):
            return
        try:
            rec = self.logger.log_incident(
                incident_type=IncidentType.HOTKEY_BLOCKED,
                details={"key": key_name},
                custom_desc=f"Попытка нажатия запрещенной клавиши: {key_name}"
            )
            self._on_incident_triggered(
                incident_type=rec.incident_type,
                description=rec.description,
                severity=rec.severity,
                screenshot_path=rec.screenshot_path
            )
        except Exception as e:
            print(f"[MainWindow] Error handling blocked hotkey: {e}")

    def _on_focus_lost(self):
        """Focus lost event triggered by OS watcher."""
        if getattr(self, "exam_finished", False):
            return
        try:
            self.focus_lock.show()
            self.focus_lock.raise_()
            self.logger.log_incident(
                incident_type=IncidentType.FOCUS_LOST,
                details={"window_state": "deactivated"}
            )
            self.total_violations += 1
            if hasattr(self, "violations_chip") and self.violations_chip:
                self.violations_chip.setText(f"Инцидентов: {self.total_violations}")

            self.session_incidents.append({
                "incident_type": IncidentType.FOCUS_LOST.value,
                "description": "Потеря фокуса окна: попытка переключения на другое приложение",
                "severity": "CRITICAL",
                "screenshot_path": "",
                "timestamp": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[MainWindow] Error handling focus lost: {e}")

    def _on_focus_regained(self):
        """Focus regained from OS."""
        pass

    def _on_focus_lock_resumed(self):
        """Student clicked return from focus lock."""
        self.security_watcher.force_restore_focus()

    def _set_simulation_mode(self, mode: str | None):
        """Activate demo simulation on the vision worker."""
        if getattr(self, "exam_finished", False):
            return
        self.vision_worker.trigger_simulation_mode(mode)
        mode_text = mode if mode else "ОБЫЧНЫЙ РЕЖИМ (КАМЕРА)"
        self.alert_banner.show_alert(
            title="ДЕМО-РЕЖИМ АКТИВИРОВАН",
            description=f"Симуляция поведения: {mode_text}",
            severity="MEDIUM",
            duration_ms=2000
        )

    def _show_incident_dialog(self):
        """Display non-blocking dialog with recorded incidents and screenshots."""
        self.security_watcher.stop()  # Temporarily pause focus alerts while admin dialog is open
        dlg = IncidentLogDialog(self.logger.incidents, self)
        dlg.finished.connect(lambda _: self.security_watcher.start())
        dlg.show()

    def _open_admin_dashboard(self):
        """Opens Admin / Proctor Dashboard window for the instructor."""
        from proctoring_system.ui.admin_dashboard import AdminDashboardWindow
        if not hasattr(self, "admin_window") or self.admin_window is None:
            self.admin_window = AdminDashboardWindow(parent=self)
        self.admin_window.show()
        self.admin_window.raise_()
        self.admin_window.activateWindow()

    def _on_exam_started(self, student_name: str):
        """Called when student clicks 'Start Exam' on the login screen."""
        self.session_student_name = student_name or "Студент"
        self.session_start_time = datetime.now()
        self.session_incidents = []
        self.total_violations = 0
        print(f"[MainWindow] Exam session started for student: {self.session_student_name}")

    def _on_web_url_changed(self, url: QUrl):
        """Handle internal navigation and signals from Exam web view."""
        url_str = url.toString()
        if url.scheme() == "proctor" or url_str.startswith("proctor://"):
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url_str)
            params = parse_qs(parsed.query)
            host = url.host()

            if host == "exit" or "exit" in url_str:
                print("[MainWindow] Exit requested from Exam interface. Exiting kiosk.")
                self.close()
            elif host == "open_admin" or "open_admin" in url_str:
                self._open_admin_dashboard()
            elif host == "start" or "start" in url_str:
                name = params.get("name", ["Студент"])[0]
                self._on_exam_started(name)
            elif host == "finished" or "finished" in url_str:
                try:
                    correct = int(params.get("correct", [0])[0])
                    total = int(params.get("total", [10])[0])
                    score_pct = int(params.get("scorePct", [0])[0])
                    spent = params.get("spent", ["00:00"])[0]
                except Exception:
                    correct, total, score_pct, spent = 0, 10, 0, "00:00"
                self._on_exam_finished(correct, total, score_pct, spent)
            elif host == "appeal" or "appeal" in url_str:
                inc_id = params.get("id", [""])[0]
                reason = params.get("reason", ["Другая причина"])[0]
                comment = params.get("comment", [""])[0]
                self._on_student_appeal_submitted(inc_id, reason, comment)
            elif host == "restarted" or "restarted" in url_str:
                self._on_exam_restarted()

    def _on_student_appeal_submitted(self, incident_id: str, reason: str, comment: str):
        """Processes and saves student appeal for a violation incident."""
        print(f"[MainWindow] Student appeal received for incident {incident_id}: {reason}")
        if hasattr(self, "current_session_dir") and self.current_session_dir:
            from proctoring_system.reports_manager import SessionReportManager
            appeal_data = SessionReportManager.submit_appeal(
                self.current_session_dir,
                incident_id,
                reason,
                comment
            )
            if appeal_data:
                try:
                    payload = json.dumps(appeal_data)
                    self.web_page.runJavaScript(f"updateIncidentAppealStatus('{incident_id}', {payload});")
                except Exception as e:
                    print(f"[MainWindow] Error syncing appeal status to web view: {e}")

    def _on_exam_finished(self, correct: int = 0, total: int = 10, score_pct: int = 0, spent: str = "00:00"):
        """Silences all proctoring alerts, lock screens, archives session report, and updates UI."""
        print("[MainWindow] Exam finished signal received. Silencing alerts and archiving session.")
        self.exam_finished = True

        # Send proctoring violations count to the Web results page
        try:
            self.web_page.runJavaScript(f"setProctoringViolationsCount({self.total_violations});")
        except Exception as e:
            print(f"[MainWindow] Error updating JS proctoring verdict: {e}")

        # Archive session report to reports/<YYYY-MM-DD_HH-MM>_<student_name>/
        try:
            from proctoring_system.reports_manager import SessionReportManager
            session_dir = SessionReportManager.save_session(
                student_name=self.session_student_name,
                start_time=self.session_start_time,
                end_time=datetime.now(),
                correct_count=correct,
                total_count=total,
                score_pct=score_pct,
                time_spent=spent,
                incidents=self.session_incidents
            )
            self.current_session_dir = session_dir

            # Load summary data with base64 encoded screenshots to display on student results screen
            summary_data = SessionReportManager.get_session(session_dir.name)
            if summary_data:
                incidents_list = summary_data.get("incidents", [])
                for inc in incidents_list:
                    shot_rel = inc.get("screenshot", "")
                    if shot_rel:
                        shot_path = session_dir / shot_rel
                        if shot_path.exists():
                            try:
                                with open(shot_path, "rb") as f:
                                    b64 = base64.b64encode(f.read()).decode("utf-8")
                                    inc["screenshot_b64"] = f"data:image/jpeg;base64,{b64}"
                            except Exception as e:
                                print(f"[MainWindow] Error encoding screenshot b64: {e}")

                payload = json.dumps(incidents_list)
                self.web_page.runJavaScript(f"loadExamIncidents({payload});")
        except Exception as e:
            print(f"[MainWindow] Error archiving session report or loading incidents: {e}")

        # Stop security watcher so focus lost doesn't trigger
        if hasattr(self, "security_watcher") and self.security_watcher:
            self.security_watcher.stop()

        # Stop keyboard locker if connected
        if hasattr(self, "keyboard_locker") and self.keyboard_locker:
            try:
                self.keyboard_locker.stop()
            except Exception as e:
                print(f"[MainWindow] Error stopping keyboard locker: {e}")

        # Silence vision worker incidents
        if hasattr(self, "vision_worker") and self.vision_worker:
            self.vision_worker.silence_incidents = True

        # Hide any active overlays
        if hasattr(self, "alert_banner") and self.alert_banner:
            self.alert_banner.hide()
        if hasattr(self, "focus_lock") and self.focus_lock:
            self.focus_lock.hide()

        # Update PiP widget to finished status
        if hasattr(self, "pip_widget") and self.pip_widget:
            self.pip_widget.update_status("FINISHED", 0.0, "CENTER", False)

    def _on_exam_restarted(self):
        """Restores proctoring monitoring if the student restarts the exam."""
        print("[MainWindow] Exam restarted signal received. Reactivating proctoring.")
        self.exam_finished = False

        if hasattr(self, "vision_worker") and self.vision_worker:
            self.vision_worker.silence_incidents = False

        if hasattr(self, "security_watcher") and self.security_watcher:
            self.security_watcher.start()

        if hasattr(self, "keyboard_locker") and self.keyboard_locker:
            try:
                self.keyboard_locker.start()
            except Exception as e:
                print(f"[MainWindow] Error starting keyboard locker: {e}")

        if hasattr(self, "pip_widget") and self.pip_widget:
            self.pip_widget.update_status("NORMAL", 0.0, "CENTER", False)

    def _exit_prompt(self):
        """Prompt to confirm exit from kiosk without requiring any password."""
        if getattr(self, "exam_finished", False):
            self.close()
            return

        self.security_watcher.stop()
        reply = QMessageBox.question(
            self,
            "Выход из тестирования",
            "Вы действительно хотите завершить тестирование и выйти из системы?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            print("[MainWindow] User confirmed exit without password. Closing kiosk.")
            self.close()
        else:
            self.security_watcher.start()

    # Alias for backwards compatibility with any callers or tests
    _admin_unlock_prompt = _exit_prompt

    def closeEvent(self, event):
        """Gracefully cleanup threads and security hooks on exit."""
        print("[MainWindow] Closing window and terminating all child workers...")
        if hasattr(self, "security_watcher") and self.security_watcher:
            try:
                self.security_watcher.stop()
            except Exception as e:
                print(f"[MainWindow] Error stopping security watcher: {e}")
        if hasattr(self, "keyboard_locker") and self.keyboard_locker:
            try:
                self.keyboard_locker.stop()
            except Exception as e:
                print(f"[MainWindow] Error stopping keyboard locker: {e}")
        if hasattr(self, "vision_worker") and self.vision_worker:
            try:
                self.vision_worker.stop()
            except Exception as e:
                print(f"[MainWindow] Error stopping vision worker: {e}")
        event.accept()
