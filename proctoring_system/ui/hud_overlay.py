"""
HUD Overlays and Widgets for the Proctoring Interface.
Includes Camera PiP preview, animated alert banners, focus-lost curtain, and incident inspector.
"""

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QPushButton,
    QFrame, QTableWidget, QTableWidgetItem, QHeaderView, QDialog,
    QScrollArea
)
from PyQt6.QtGui import QImage, QPixmap, QColor, QFont

from proctoring_system.logger import IncidentRecord, Severity


class CameraPipWidget(QFrame):
    """
    Floating Picture-in-Picture webcam monitor displaying real-time video feed with CV telemetry.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(300, 225)
        self.setStyleSheet("""
            CameraPipWidget {
                background-color: #0b1120;
                border: 2px solid #22c55e;
                border-radius: 12px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(2)

        # Video frame display label
        self.video_label = QLabel(self)
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet("border-radius: 8px; background-color: #020617;")
        layout.addWidget(self.video_label, stretch=1)

        # Bottom telemetry bar
        bottom_bar = QHBoxLayout()
        bottom_bar.setContentsMargins(6, 2, 6, 2)

        self.status_chip = QLabel("● SECURE", self)
        self.status_chip.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 11px;")
        bottom_bar.addWidget(self.status_chip)

        bottom_bar.addStretch()

        self.telemetry_label = QLabel("FPS: -- | Gaze: --", self)
        self.telemetry_label.setStyleSheet("color: #94a3b8; font-size: 10px; font-family: monospace;")
        bottom_bar.addWidget(self.telemetry_label)

        layout.addLayout(bottom_bar)

    def update_frame(self, q_img: QImage):
        """Update video preview with scaled pixmap."""
        try:
            if q_img.isNull():
                return
            size = self.video_label.size()
            if size.width() > 0 and size.height() > 0:
                scaled_pix = QPixmap.fromImage(q_img).scaled(
                    size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation
                )
                self.video_label.setPixmap(scaled_pix)
        except Exception as e:
            print(f"[CameraPipWidget] Error updating frame: {e}")

    def update_status(self, status: str, fps: float, gaze: str, phone: bool):
        """Update border color and status indicators with state caching to avoid redraw thrashing."""
        try:
            target_state = "VIOLATION" if (status == "VIOLATION" or phone) else status
            if getattr(self, "_last_state", None) != target_state:
                self._last_state = target_state
                if target_state == "VIOLATION":
                    self.setStyleSheet("""
                        CameraPipWidget {
                            background-color: #0b1120;
                            border: 2px solid #ef4444;
                            border-radius: 12px;
                        }
                    """)
                    self.status_chip.setText("● VIOLATION")
                    self.status_chip.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 11px;")
                elif target_state == "WARNING":
                    self.setStyleSheet("""
                        CameraPipWidget {
                            background-color: #0b1120;
                            border: 2px solid #f59e0b;
                            border-radius: 12px;
                        }
                    """)
                    self.status_chip.setText("● WARNING")
                    self.status_chip.setStyleSheet("color: #f59e0b; font-weight: bold; font-size: 11px;")
                else:
                    self.setStyleSheet("""
                        CameraPipWidget {
                            background-color: #0b1120;
                            border: 2px solid #22c55e;
                            border-radius: 12px;
                        }
                    """)
                    self.status_chip.setText("● SECURE")
                    self.status_chip.setStyleSheet("color: #22c55e; font-weight: bold; font-size: 11px;")

            self.telemetry_label.setText(f"FPS: {fps:.0f} | Gaze: {gaze}")
        except Exception as e:
            print(f"[CameraPipWidget] Error updating status: {e}")


class AlertBannerOverlay(QFrame):
    """
    Sleek glowing top banner that pops up when a security violation occurs.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(64)
        self.hide()

        self.setStyleSheet("""
            AlertBannerOverlay {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #991b1b, stop:1 #dc2626);
                border-bottom: 2px solid #f87171;
                border-radius: 0px 0px 14px 14px;
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(32, 8, 32, 8)

        self.icon_label = QLabel("⚠️", self)
        self.icon_label.setStyleSheet("font-size: 24px;")
        layout.addWidget(self.icon_label)

        self.text_layout = QVBoxLayout()
        self.title_label = QLabel("ВНИМАНИЕ! ЗАФИКСИРОВАНО НАРУШЕНИЕ", self)
        self.title_label.setStyleSheet("color: #ffffff; font-weight: 800; font-size: 14px; letter-spacing: 0.05em;")

        self.desc_label = QLabel("Описание инцидента", self)
        self.desc_label.setStyleSheet("color: #fecaca; font-size: 12px;")

        self.text_layout.addWidget(self.title_label)
        self.text_layout.addWidget(self.desc_label)
        layout.addLayout(self.text_layout)

        layout.addStretch()

        self.badge_label = QLabel("ИНЦИДЕНТ СОХРАНЕН В ЛОГ", self)
        self.badge_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 0.4);
            color: #ffffff;
            font-size: 11px;
            font-weight: 700;
            padding: 4px 12px;
            border-radius: 6px;
        """)
        layout.addWidget(self.badge_label)

        # Auto-dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self.hide)

    def show_alert(self, title: str, description: str, severity: str = "HIGH", duration_ms: int = 2000):
        """Display non-blocking alert banner for 2 seconds."""
        try:
            self.title_label.setText(title.upper())
            self.desc_label.setText(description)

            is_crit = (severity in ("CRITICAL", "HIGH"))
            if getattr(self, "_last_is_crit", None) != is_crit:
                self._last_is_crit = is_crit
                if is_crit:
                    self.setStyleSheet("""
                        AlertBannerOverlay {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7f1d1d, stop:1 #dc2626);
                            border-bottom: 2px solid #ef4444;
                            border-radius: 0px 0px 14px 14px;
                        }
                    """)
                else:
                    self.setStyleSheet("""
                        AlertBannerOverlay {
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #78350f, stop:1 #d97706);
                            border-bottom: 2px solid #f59e0b;
                            border-radius: 0px 0px 14px 14px;
                        }
                    """)

            self.show()
            self.raise_()
            self.dismiss_timer.start(duration_ms)
        except Exception as e:
            print(f"[AlertBannerOverlay] Error showing alert: {e}")


class FocusLostLockOverlay(QWidget):
    """
    Security curtain displayed when user attempts to leave the application window.
    """

    resumed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide()
        self.setStyleSheet("background-color: rgba(10, 15, 26, 0.96);")

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)

        card = QFrame(self)
        card.setFixedSize(540, 360)
        card.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 2px solid #ef4444;
                border-radius: 18px;
            }
        """)

        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(36, 36, 36, 36)
        card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.setSpacing(16)

        icon = QLabel("🔒", card)
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon.setStyleSheet("font-size: 52px; background: transparent; border: none;")
        card_layout.addWidget(icon)

        title = QLabel("НАРУШЕНИЕ РЕЖИМА БЕЗОПАСНОСТИ", card)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("color: #ef4444; font-size: 18px; font-weight: 800; background: transparent; border: none;")
        card_layout.addWidget(title)

        msg = QLabel(
            "Окно экзамена потеряло фокус (попытка переключения на стороннее приложение).\n"
            "Инцидент зафиксирован в журнале прокторинга со скриншотом рабочего стола.",
            card
        )
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setWordWrap(True)
        msg.setStyleSheet("color: #cbd5e1; font-size: 13px; line-height: 1.5; background: transparent; border: none;")
        card_layout.addWidget(msg)

        card_layout.addSpacing(10)

        resume_btn = QPushButton("Вернуться к экзамену", card)
        resume_btn.setFixedHeight(44)
        resume_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        resume_btn.setStyleSheet("""
            QPushButton {
                background: linear-gradient(135deg, #38bdf8, #6366f1);
                background-color: #3b82f6;
                color: #ffffff;
                font-weight: 700;
                font-size: 14px;
                border-radius: 8px;
                border: none;
            }
            QPushButton:hover {
                background-color: #2563eb;
            }
        """)
        resume_btn.clicked.connect(self._on_resume_clicked)
        card_layout.addWidget(resume_btn)

        layout.addWidget(card)

    def _on_resume_clicked(self):
        self.hide()
        self.resumed.emit()


class IncidentLogDialog(QDialog):
    """
    Admin viewer for incident history and captured screenshots.
    """

    def __init__(self, incidents, parent=None):
        super().__init__(parent)
        incidents_list = list(incidents)
        self.setWindowTitle("Журнал инцидентов прокторинга")
        self.resize(850, 550)
        self.setStyleSheet("""
            QDialog {
                background-color: #0f172a;
                color: #f8fafc;
            }
            QTableWidget {
                background-color: #1e293b;
                color: #f8fafc;
                border: 1px solid #334155;
                gridline-color: #334155;
                selection-background-color: #38bdf8;
                selection-color: #0f172a;
            }
            QHeaderView::section {
                background-color: #0b1120;
                color: #94a3b8;
                padding: 6px;
                font-weight: bold;
                border: 1px solid #334155;
            }
            QPushButton {
                background-color: #334155;
                color: #ffffff;
                padding: 8px 16px;
                border-radius: 6px;
                border: none;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        header = QLabel(f"Всего зафиксировано инцидентов: {len(incidents_list)}", self)
        header.setStyleSheet("font-size: 16px; font-weight: bold; color: #38bdf8;")
        layout.addWidget(header)

        self.table = QTableWidget(self)
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Время", "Тип нарушения", "Уровень", "Описание", "Скриншот"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setRowCount(len(incidents_list))

        for row, inc in enumerate(reversed(incidents_list)):
            time_part = inc.timestamp.split("T")[-1][:8]
            self.table.setItem(row, 0, QTableWidgetItem(time_part))
            self.table.setItem(row, 1, QTableWidgetItem(inc.incident_type))

            sev_item = QTableWidgetItem(inc.severity)
            if inc.severity in ("CRITICAL", "HIGH"):
                sev_item.setForeground(QColor("#ef4444"))
            else:
                sev_item.setForeground(QColor("#f59e0b"))
            self.table.setItem(row, 2, sev_item)

            self.table.setItem(row, 3, QTableWidgetItem(inc.description))

            if inc.screenshot_path:
                btn = QPushButton("Просмотр", self)
                btn.clicked.connect(lambda _, path=inc.screenshot_path: self._view_screenshot(path))
                self.table.setCellWidget(row, 4, btn)
            else:
                self.table.setItem(row, 4, QTableWidgetItem("—"))

        layout.addWidget(self.table)

        btn_box = QHBoxLayout()
        btn_box.addStretch()
        close_btn = QPushButton("Закрыть", self)
        close_btn.clicked.connect(self.accept)
        btn_box.addWidget(close_btn)
        layout.addLayout(btn_box)

    def _view_screenshot(self, path: str):
        """Open screenshot preview popup without modal execution blocking."""
        try:
            dlg = QDialog(self)
            dlg.setWindowTitle("Снимок нарушения")
            dlg.resize(680, 520)
            dlg.setStyleSheet("background-color: #020617;")
            v = QVBoxLayout(dlg)
            lbl = QLabel(dlg)
            pix = QPixmap(path)
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(640, 480, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            else:
                lbl.setText(f"Не удалось открыть: {path}")
                lbl.setStyleSheet("color: white;")
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(lbl)
            self._preview_dlg = dlg
            dlg.show()
        except Exception as e:
            print(f"[IncidentLogDialog] Error showing screenshot: {e}")
