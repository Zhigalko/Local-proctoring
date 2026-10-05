"""
Main Fullscreen Kiosk Window for the Local Proctoring System.
Integrates QWebEngineView for online testing, real-time CV PIP webcam preview,
visual alert overlays, incident log inspection, and security lockdown.
"""

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

        # Metrics cache
        self.total_violations = 0
        self.exam_finished = False
        self.keyboard_locker = None

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

        # Baseline recalibration shortcut (key 'C')
        self.calib_shortcut = QShortcut(QKeySequence("C"), self)
        self.calib_shortcut.activated.connect(self._trigger_recalibration)

    def _init_ui(self):
        """Create central widget and all overlay layers."""
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.central_layout = QVBoxLayout(self.central_widget)
        self.central_layout.setContentsMargins(0, 0, 0, 0)
        self.central_layout.setSpacing(0)

        # 1. Top HUD Status Bar
        self.top_bar = self._create_top_bar()
        self.central_layout.addWidget(self.top_bar)

        # 2. Main Exam Browser View
        self.web_view = QWebEngineView(self)
        self.web_page = ProctorWebEnginePage(self, self.web_view)
        self.web_view.setPage(self.web_page)
        self.web_view.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        self.web_view.setHtml(EXAM_HTML_CONTENT)
        self.web_page.windowCloseRequested.connect(self.close)
        self.web_view.urlChanged.connect(self._on_web_url_changed)
        self.central_layout.addWidget(self.web_view, stretch=1)

        # 3. Hackathon Demo Toolbar (Bottom bar for judges and demonstration)
        self.demo_toolbar = self._create_demo_toolbar()
        self.central_layout.addWidget(self.demo_toolbar)

        # 4. Floating Camera PiP Widget (anchored bottom-right)
        self.pip_widget = CameraPipWidget(self)
        self.pip_widget.show()

        # 5. Alert Banner Overlay (anchored top-center)
        self.alert_banner = AlertBannerOverlay(self)

        # 6. Focus Lost Security Curtain (covers entire window)
        self.focus_lock = FocusLostLockOverlay(self)
        self.focus_lock.resumed.connect(self._on_focus_lock_resumed)

    def _create_top_bar(self) -> QWidget:
        bar = QFrame(self)
        bar.setFixedHeight(54)
        bar.setStyleSheet("""
            QFrame {
                background-color: #0b1120;
                border-bottom: 2px solid #1e293b;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(20, 0, 20, 0)
        layout.setSpacing(16)

        # Application Title / Brand Header
        self.app_title = QLabel("Local proctoring", bar)
        self.app_title.setStyleSheet("color: #38bdf8; font-weight: 800; font-size: 14px; letter-spacing: 0.03em;")
        layout.addWidget(self.app_title)

        # Live Proctor Badge
        self.badge_status = QLabel("● АКТИВЕН", bar)
        self.badge_status.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 12px; letter-spacing: 0.05em;")
        layout.addWidget(self.badge_status)

        # Overall Status Chip
        self.status_chip = QLabel("СТАТУС: В НОРМЕ", bar)
        self.status_chip.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.15);
            color: #22c55e;
            border: 1px solid rgba(34, 197, 94, 0.3);
            border-radius: 6px;
            padding: 4px 10px;
            font-weight: 700;
            font-size: 12px;
        """)
        layout.addWidget(self.status_chip)

        # Violations Count Chip
        self.violations_chip = QLabel("Инцидентов: 0", bar)
        self.violations_chip.setStyleSheet("""
            background-color: #1e293b;
            color: #f8fafc;
            border-radius: 6px;
            padding: 4px 12px;
            font-weight: 700;
            font-size: 12px;
        """)
        layout.addWidget(self.violations_chip)
        layout.addStretch()

        # Button: Auto-Calibrate Baseline
        self.calib_btn = QPushButton("🎯 Автокалибровка (C)", bar)
        self.calib_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.calib_btn.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                color: #f0f9ff;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        self.calib_btn.clicked.connect(self._trigger_recalibration)
        layout.addWidget(self.calib_btn)

        # Button: Open Incident Log
        self.log_btn = QPushButton("📋 Журнал нарушений", bar)
        self.log_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.log_btn.setStyleSheet("""
            QPushButton {
                background-color: #1e293b;
                color: #38bdf8;
                border: 1px solid #334155;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #334155;
            }
        """)
        self.log_btn.clicked.connect(self._show_incident_dialog)
        layout.addWidget(self.log_btn)

        # Button: Exit (No password required)
        self.exit_btn = QPushButton("🚪 Выход", bar)
        self.exit_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.exit_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f1d1d;
                color: #fecaca;
                border: 1px solid #ef4444;
                border-radius: 6px;
                padding: 6px 14px;
                font-size: 12px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #991b1b;
            }
        """)
        self.exit_btn.clicked.connect(self._exit_prompt)
        layout.addWidget(self.exit_btn)

        return bar

    def _create_demo_toolbar(self) -> QWidget:
        """Interactive test bar for judges to test scenarios on demand."""
        bar = QFrame(self)
        bar.setFixedHeight(46)
        bar.setStyleSheet("""
            QFrame {
                background-color: #0f172a;
                border-top: 1px solid #334155;
            }
        """)

        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 4, 16, 4)
        layout.setSpacing(10)

        demo_label = QLabel("⚡ ДЕМО-СИМУЛЯЦИЯ:", bar)
        demo_label.setStyleSheet("color: #e2e8f0; font-weight: 800; font-size: 11px;")
        layout.addWidget(demo_label)

        btn_style = """
            QPushButton {
                background-color: #1e293b;
                color: #cbd5e1;
                border: 1px solid #334155;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #38bdf8;
                color: #0f172a;
            }
        """

        sim_phone_btn = QPushButton("📱 Смартфон", bar)
        sim_phone_btn.setStyleSheet(btn_style)
        sim_phone_btn.clicked.connect(lambda: self._set_simulation_mode("PHONE"))
        layout.addWidget(sim_phone_btn)

        sim_noface_btn = QPushButton("👤 Уход со стула", bar)
        sim_noface_btn.setStyleSheet(btn_style)
        sim_noface_btn.clicked.connect(lambda: self._set_simulation_mode("NO_FACE"))
        layout.addWidget(sim_noface_btn)

        sim_multi_btn = QPushButton("👥 2-й человек", bar)
        sim_multi_btn.setStyleSheet(btn_style)
        sim_multi_btn.clicked.connect(lambda: self._set_simulation_mode("MULTIPLE_FACES"))
        layout.addWidget(sim_multi_btn)

        sim_away_btn = QPushButton("➡️ Поворот головы", bar)
        sim_away_btn.setStyleSheet(btn_style)
        sim_away_btn.clicked.connect(lambda: self._set_simulation_mode("LOOKING_AWAY"))
        layout.addWidget(sim_away_btn)

        sim_down_btn = QPushButton("⬇️ Взгляд вниз", bar)
        sim_down_btn.setStyleSheet(btn_style)
        sim_down_btn.clicked.connect(lambda: self._set_simulation_mode("LOOKING_DOWN"))
        layout.addWidget(sim_down_btn)

        sim_reset_btn = QPushButton("🔄 Сброс симуляции", bar)
        sim_reset_btn.setStyleSheet("""
            QPushButton {
                background-color: #22c55e;
                color: #0f172a;
                border-radius: 4px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #16a34a;
            }
        """)
        sim_reset_btn.clicked.connect(lambda: self._set_simulation_mode(None))
        layout.addWidget(sim_reset_btn)

        layout.addStretch()

        help_label = QLabel("Разблокировка: Ctrl+Alt+Shift+F12 (пароль: proctor2026)", bar)
        help_label.setStyleSheet("color: #64748b; font-size: 11px;")
        layout.addWidget(help_label)

        return bar

    def resizeEvent(self, event):
        """Keep PiP, banner, and curtain sized and positioned correctly."""
        super().resizeEvent(event)
        if not (hasattr(self, "pip_widget") and hasattr(self, "alert_banner") and hasattr(self, "focus_lock")):
            return

        w = self.width()
        h = self.height()

        # Position PiP widget at bottom right (above demo toolbar)
        pip_w, pip_h = self.pip_widget.width(), self.pip_widget.height()
        self.pip_widget.move(w - pip_w - 24, h - pip_h - 60)

        # Position Alert Banner at top center
        banner_w = min(720, w - 80)
        self.alert_banner.setGeometry((w - banner_w) // 2, 54, banner_w, 64)

        # Position Focus Lost lock to cover the full window
        self.focus_lock.setGeometry(0, 0, w, h)

    def _on_status_updated(self, metrics: dict):
        """Update top bar status badge and telemetry readouts with state caching."""
        if getattr(self, "exam_finished", False):
            try:
                fps = metrics.get("fps", 0.0)
                self.pip_widget.update_status("NORMAL", fps, "CENTER", False)
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

            # Update top status chip (only re-style when state changes to avoid QSS overhead)
            target_chip_state = "VIOLATION" if (status == "VIOLATION" or phone) else status
            if getattr(self, "_last_chip_state", None) != target_chip_state:
                self._last_chip_state = target_chip_state
                if target_chip_state == "VIOLATION":
                    self.status_chip.setText("СТАТУС: НАРУШЕНИЕ!")
                    self.status_chip.setStyleSheet("""
                        background-color: rgba(239, 68, 68, 0.2);
                        color: #ef4444;
                        border: 1px solid #ef4444;
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-weight: 800;
                        font-size: 12px;
                    """)
                elif target_chip_state == "WARNING":
                    self.status_chip.setText("СТАТУС: ПРЕДУПРЕЖДЕНИЕ")
                    self.status_chip.setStyleSheet("""
                        background-color: rgba(245, 158, 11, 0.2);
                        color: #f59e0b;
                        border: 1px solid #f59e0b;
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-weight: 700;
                        font-size: 12px;
                    """)
                else:
                    self.status_chip.setText("СТАТУС: В НОРМЕ")
                    self.status_chip.setStyleSheet("""
                        background-color: rgba(34, 197, 94, 0.15);
                        color: #22c55e;
                        border: 1px solid rgba(34, 197, 94, 0.3);
                        border-radius: 6px;
                        padding: 4px 10px;
                        font-weight: 700;
                        font-size: 12px;
                    """)

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
            self.violations_chip.setText(f"Инцидентов: {self.total_violations}")
            if getattr(self, "_violations_chip_styled", False) is False:
                self._violations_chip_styled = True
                self.violations_chip.setStyleSheet("""
                    background-color: #7f1d1d;
                    color: #fecaca;
                    border-radius: 6px;
                    padding: 4px 12px;
                    font-weight: 800;
                    font-size: 12px;
                """)

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
            self.violations_chip.setText(f"Инцидентов: {self.total_violations}")
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

    def _on_web_url_changed(self, url: QUrl):
        """Handle internal navigation and signals from Exam web view."""
        url_str = url.toString()
        if url.scheme() == "proctor" or url_str.startswith("proctor://"):
            host = url.host()
            if host == "exit" or "exit" in url_str:
                print("[MainWindow] Exit requested from Exam interface. Exiting kiosk.")
                self.close()
            elif host == "finished" or "finished" in url_str:
                self._on_exam_finished()
            elif host == "restarted" or "restarted" in url_str:
                self._on_exam_restarted()

    def _on_exam_finished(self):
        """Silences all proctoring alerts, lock screens, and warnings after exam ends."""
        print("[MainWindow] Exam finished signal received. Silencing all alerts and proctoring locks.")
        self.exam_finished = True

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

        # Update HUD chips to show completed state
        if hasattr(self, "badge_status") and self.badge_status:
            self.badge_status.setText("● ЗАВЕРШЕН")
            self.badge_status.setStyleSheet("color: #94a3b8; font-weight: 700; font-size: 12px; letter-spacing: 0.05em;")

        if hasattr(self, "status_chip") and self.status_chip:
            self.status_chip.setText("СТАТУС: ТЕСТ ЗАВЕРШЕН")
            self.status_chip.setStyleSheet("""
                background-color: rgba(56, 189, 248, 0.15);
                color: #38bdf8;
                border: 1px solid rgba(56, 189, 248, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            """)

        if hasattr(self, "pip_widget") and self.pip_widget:
            self.pip_widget.update_status("NORMAL", 0.0, "CENTER", False)

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

        if hasattr(self, "badge_status") and self.badge_status:
            self.badge_status.setText("● АКТИВЕН")
            self.badge_status.setStyleSheet("color: #22c55e; font-weight: 700; font-size: 12px; letter-spacing: 0.05em;")

        if hasattr(self, "status_chip") and self.status_chip:
            self.status_chip.setText("СТАТУС: В НОРМЕ")
            self.status_chip.setStyleSheet("""
                background-color: rgba(34, 197, 94, 0.15);
                color: #22c55e;
                border: 1px solid rgba(34, 197, 94, 0.3);
                border-radius: 6px;
                padding: 4px 10px;
                font-weight: 700;
                font-size: 12px;
            """)

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
        self.security_watcher.stop()
        self.vision_worker.stop()
        event.accept()
