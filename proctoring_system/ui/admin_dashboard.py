"""
Admin / Proctor Dashboard Window for instructors to review exam sessions,
incident timelines, violation proofs, and export official reports.
"""

import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QListWidget, QListWidgetItem,
    QFrame, QScrollArea, QDialog, QFileDialog, QMessageBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QGridLayout
)
from PyQt6.QtGui import QPixmap, QColor, QFont, QIcon, QCursor

from proctoring_system.config import REPORTS_DIR
from proctoring_system.reports_manager import SessionReportManager


class ImagePreviewModal(QDialog):
    """Full-resolution modal viewer for incident screenshots."""

    def __init__(self, image_path: str, title: str, details_text: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Фотофиксация нарушения — {title}")
        self.setMinimumSize(780, 580)
        self.setStyleSheet("""
            QDialog {
                background-color: #0b1120;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header with title and details
        hdr_layout = QHBoxLayout()
        title_label = QLabel(f"📷 {title}", self)
        title_label.setStyleSheet("color: #38bdf8; font-size: 17px; font-weight: 800;")
        hdr_layout.addWidget(title_label)
        hdr_layout.addStretch()

        close_btn = QPushButton("✕ Закрыть", self)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 6px 14px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        close_btn.clicked.connect(self.close)
        hdr_layout.addWidget(close_btn)
        layout.addLayout(hdr_layout)

        if details_text:
            desc_label = QLabel(details_text, self)
            desc_label.setStyleSheet("color: #94a3b8; font-size: 13px; line-height: 1.4;")
            desc_label.setWordWrap(True)
            layout.addWidget(desc_label)

        # Image display container
        self.img_label = QLabel(self)
        self.img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.img_label.setStyleSheet("""
            QLabel {
                background-color: #020617;
                border: 1px solid #1e293b;
                border-radius: 10px;
                padding: 4px;
            }
        """)

        if image_path and Path(image_path).exists():
            pix = QPixmap(image_path)
            if not pix.isNull():
                self.img_label.setPixmap(pix.scaled(
                    740, 480,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                ))
            else:
                self.img_label.setText("Ошибка загрузки изображения")
                self.img_label.setStyleSheet("color: #ef4444; font-size: 14px;")
        else:
            self.img_label.setText("Скриншот отсутствует на диске")
            self.img_label.setStyleSheet("color: #94a3b8; font-size: 14px;")

        layout.addWidget(self.img_label, stretch=1)


class AdminDashboardWindow(QMainWindow):
    """
    Instructor and Proctor Admin Dashboard for reviewing examination sessions,
    incident timelines, evidence gallery, and official report exports.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Панель преподавателя (Admin Dashboard) — Local Proctoring")
        self.resize(1240, 800)
        self.setMinimumSize(960, 640)

        # Ensure sample data exists if fresh install
        SessionReportManager.ensure_demo_sessions()

        self.all_sessions: List[Dict[str, Any]] = []
        self.filtered_sessions: List[Dict[str, Any]] = []
        self.current_session: Optional[Dict[str, Any]] = None

        self._init_ui()
        self._load_sessions()

    def _init_ui(self):
        # Central widget and layout
        self.central_widget = QWidget(self)
        self.setCentralWidget(self.central_widget)
        self.central_widget.setStyleSheet("background-color: #0b1120; color: #f8fafc;")

        main_layout = QVBoxLayout(self.central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Control Bar (Search, Filters, Export, Refresh)
        top_bar = self._create_top_bar()
        main_layout.addWidget(top_bar)

        # 2. Main Two-Column Content
        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        # Left Column: Sessions List (width: ~380px)
        left_column = self._create_left_column()
        content_layout.addWidget(left_column, stretch=3)

        # Right Column: Protocol & Evidence Detail (width: stretch)
        self.right_column = self._create_right_column()
        content_layout.addWidget(self.right_column, stretch=7)

        main_layout.addLayout(content_layout, stretch=1)

    def _create_top_bar(self) -> QWidget:
        bar = QFrame(self)
        bar.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Brand / Title
        brand_layout = QVBoxLayout()
        brand_layout.setSpacing(2)
        title = QLabel("🎓 Панель преподавателя", bar)
        title.setStyleSheet("color: #38bdf8; font-size: 17px; font-weight: 800; border: none;")
        subtitle = QLabel("Протоколы тестирования и анализ нарушений", bar)
        subtitle.setStyleSheet("color: #94a3b8; font-size: 11.5px; border: none;")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        layout.addLayout(brand_layout)

        layout.addSpacing(10)

        # Search field
        self.search_input = QLineEdit(bar)
        self.search_input.setPlaceholderText("🔍 Поиск по ФИО студента...")
        self.search_input.setStyleSheet("""
            QLineEdit {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 7px 12px;
                color: #ffffff;
                font-size: 13px;
                min-width: 220px;
            }
            QLineEdit:focus {
                border-color: #38bdf8;
            }
        """)
        self.search_input.textChanged.connect(self._apply_filters)
        layout.addWidget(self.search_input)

        # Filter: Status
        self.status_filter = QComboBox(bar)
        self.status_filter.addItems([
            "Все статусы",
            "🟢 Чисто (0)",
            "🟡 Внимание (1–2)",
            "🔴 Подозрение (3+)"
        ])
        self.status_filter.setStyleSheet(self._combo_style())
        self.status_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.status_filter)

        # Filter: Violation Type
        self.type_filter = QComboBox(bar)
        self.type_filter.addItems([
            "Все типы нарушений",
            "📱 Смартфон",
            "➡️ Отвод головы / взгляда",
            "👥 Посторонние лица",
            "🔒 Фокус и хоткеи"
        ])
        self.type_filter.setStyleSheet(self._combo_style())
        self.type_filter.currentIndexChanged.connect(self._apply_filters)
        layout.addWidget(self.type_filter)

        layout.addStretch()

        # Button: Export Report
        self.export_btn = QPushButton("📥 Экспорт отчёта", bar)
        self.export_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.export_btn.setStyleSheet("""
            QPushButton {
                background-color: #0369a1;
                color: #ffffff;
                border: 1px solid #38bdf8;
                border-radius: 8px;
                padding: 8px 16px;
                font-size: 12.5px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #0284c7;
            }
        """)
        self.export_btn.clicked.connect(self._export_current_report)
        layout.addWidget(self.export_btn)

        # Button: Refresh
        refresh_btn = QPushButton("🔄", bar)
        refresh_btn.setToolTip("Обновить список сессий")
        refresh_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        refresh_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #e2e8f0;
                border: 1px solid #475569;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                font-weight: 700;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """)
        refresh_btn.clicked.connect(self._load_sessions)
        layout.addWidget(refresh_btn)

        return bar

    def _combo_style(self) -> str:
        return """
            QComboBox {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px 12px;
                color: #ffffff;
                font-size: 12.5px;
                font-weight: 600;
                min-width: 150px;
            }
            QComboBox QAbstractItemView {
                background-color: #1e293b;
                color: #ffffff;
                selection-background-color: #0284c7;
                border: 1px solid #334155;
            }
        """

    def _create_left_column(self) -> QWidget:
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(10)

        # Stats header
        self.stats_lbl = QLabel("Сессии студентов (0)", container)
        self.stats_lbl.setStyleSheet("color: #e2e8f0; font-size: 14px; font-weight: 800; border: none;")
        layout.addWidget(self.stats_lbl)

        # List of sessions
        self.sessions_list = QListWidget(container)
        self.sessions_list.setStyleSheet("""
            QListWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                outline: none;
                padding: 4px;
            }
            QListWidget::item {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 8px;
                margin: 4px 2px;
                padding: 8px;
            }
            QListWidget::item:hover {
                border-color: #38bdf8;
                background-color: #273549;
            }
            QListWidget::item:selected {
                border: 1.5px solid #38bdf8;
                background-color: #1e3a5f;
            }
        """)
        self.sessions_list.currentRowChanged.connect(self._on_session_selected)
        layout.addWidget(self.sessions_list, stretch=1)

        return container

    def _create_right_column(self) -> QWidget:
        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 12px;
            }
        """)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        # 1. Student Hero Banner (Dynamic)
        self.hero_card = QFrame(container)
        self.hero_card.setStyleSheet("""
            QFrame {
                background: linear-gradient(180deg, #0f172a, #111c33);
                border: 1px solid #334155;
                border-radius: 10px;
                padding: 16px;
            }
        """)
        hero_layout = QHBoxLayout(self.hero_card)
        hero_layout.setContentsMargins(16, 14, 16, 14)

        hero_left = QVBoxLayout()
        self.hero_student_name = QLabel("Выберите сессию для просмотра", self.hero_card)
        self.hero_student_name.setStyleSheet("color: #f8fafc; font-size: 20px; font-weight: 800; border: none;")
        hero_left.addWidget(self.hero_student_name)

        self.hero_meta = QLabel("—", self.hero_card)
        self.hero_meta.setStyleSheet("color: #94a3b8; font-size: 13px; border: none;")
        hero_left.addWidget(self.hero_meta)
        hero_layout.addLayout(hero_left, stretch=1)

        # Status badge pill
        self.hero_status_pill = QLabel("—", self.hero_card)
        self.hero_status_pill.setStyleSheet("""
            background-color: #334155;
            color: #cbd5e1;
            padding: 6px 14px;
            border-radius: 8px;
            font-weight: 800;
            font-size: 13px;
            border: none;
        """)
        hero_layout.addWidget(self.hero_status_pill)

        # Score pill
        self.hero_score_pill = QLabel("—", self.hero_card)
        self.hero_score_pill.setStyleSheet("""
            background-color: #0f172a;
            border: 1px solid #38bdf8;
            color: #38bdf8;
            padding: 6px 14px;
            border-radius: 8px;
            font-weight: 800;
            font-size: 14px;
        """)
        hero_layout.addWidget(self.hero_score_pill)

        layout.addWidget(self.hero_card)

        # 2. Tabs / Section Switcher
        switch_layout = QHBoxLayout()
        self.tab_timeline_btn = QPushButton("📋 Таймлайн нарушений", container)
        self.tab_timeline_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_timeline_btn.setStyleSheet("""
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 7px 18px;
            }
        """)
        self.tab_timeline_btn.clicked.connect(lambda: self._set_right_view("timeline"))
        switch_layout.addWidget(self.tab_timeline_btn)

        self.tab_gallery_btn = QPushButton("📸 Галерея доказательств", container)
        self.tab_gallery_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tab_gallery_btn.setStyleSheet("""
            QPushButton {
                background-color: #334155;
                color: #cbd5e1;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 18px;
            }
        """)
        self.tab_gallery_btn.clicked.connect(lambda: self._set_right_view("gallery"))
        switch_layout.addWidget(self.tab_gallery_btn)

        switch_layout.addStretch()
        layout.addLayout(switch_layout)

        # 3. Stacked Views (Timeline Table & Photo Gallery)
        self.view_container = QWidget(container)
        self.view_layout = QVBoxLayout(self.view_container)
        self.view_layout.setContentsMargins(0, 0, 0, 0)

        # View A: Timeline Table
        self.timeline_table = QTableWidget(self.view_container)
        self.timeline_table.setColumnCount(5)
        self.timeline_table.setHorizontalHeaderLabels([
            "Таймкод", "Тип нарушения", "Уровень", "Длительность", "Описание инцидента"
        ])
        self.timeline_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        self.timeline_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.timeline_table.setAlternatingRowColors(True)
        self.timeline_table.verticalHeader().setVisible(False)
        self.timeline_table.setStyleSheet("""
            QTableWidget {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
                color: #f8fafc;
                gridline-color: #1e293b;
            }
            QHeaderView::section {
                background-color: #1e293b;
                color: #94a3b8;
                font-weight: 700;
                padding: 8px;
                border: 1px solid #334155;
            }
            QTableWidget::item {
                padding: 8px;
            }
        """)
        self.view_layout.addWidget(self.timeline_table)

        # View B: Evidence Gallery (ScrollArea)
        self.gallery_scroll = QScrollArea(self.view_container)
        self.gallery_scroll.setWidgetResizable(True)
        self.gallery_scroll.setStyleSheet("""
            QScrollArea {
                background-color: #0f172a;
                border: 1px solid #334155;
                border-radius: 8px;
            }
        """)
        self.gallery_content = QWidget()
        self.gallery_layout = QGridLayout(self.gallery_content)
        self.gallery_layout.setContentsMargins(14, 14, 14, 14)
        self.gallery_layout.setSpacing(14)
        self.gallery_scroll.setWidget(self.gallery_content)
        self.gallery_scroll.hide()
        self.view_layout.addWidget(self.gallery_scroll)

        # Empty state label
        self.empty_incidents_lbl = QLabel("В ходе тестирования нарушений не зафиксировано.", self.view_container)
        self.empty_incidents_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_incidents_lbl.setStyleSheet("""
            background-color: rgba(34, 197, 94, 0.1);
            border: 1px dashed rgba(34, 197, 94, 0.4);
            color: #86efac;
            font-size: 15px;
            font-weight: 700;
            padding: 40px;
            border-radius: 10px;
        """)
        self.empty_incidents_lbl.hide()
        self.view_layout.addWidget(self.empty_incidents_lbl)

        layout.addWidget(self.view_container, stretch=1)
        return container

    def _set_right_view(self, view_name: str):
        active_style = """
            QPushButton {
                background-color: #0284c7;
                color: #ffffff;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #38bdf8;
                border-radius: 6px;
                padding: 7px 18px;
            }
        """
        inactive_style = """
            QPushButton {
                background-color: #334155;
                color: #cbd5e1;
                font-weight: 700;
                font-size: 13px;
                border: 1px solid #475569;
                border-radius: 6px;
                padding: 7px 18px;
            }
            QPushButton:hover {
                background-color: #475569;
            }
        """
        if view_name == "timeline":
            self.tab_timeline_btn.setStyleSheet(active_style)
            self.tab_gallery_btn.setStyleSheet(inactive_style)
            self.timeline_table.show()
            self.gallery_scroll.hide()
        else:
            self.tab_timeline_btn.setStyleSheet(inactive_style)
            self.tab_gallery_btn.setStyleSheet(active_style)
            self.timeline_table.hide()
            self.gallery_scroll.show()

    def _load_sessions(self):
        """Reloads all saved sessions from disk."""
        self.all_sessions = SessionReportManager.list_sessions()
        self._apply_filters()

    def _apply_filters(self):
        query = self.search_input.text().lower().strip()
        status_filter = self.status_filter.currentText()
        type_filter = self.type_filter.currentText()

        self.filtered_sessions = []
        clean_count = 0
        attention_count = 0
        cheating_count = 0

        for s in self.all_sessions:
            name = s.get("student_name", "").lower()
            status = s.get("status", "")
            incidents = s.get("incidents", [])

            if status == "CLEAN":
                clean_count += 1
            elif status == "ATTENTION":
                attention_count += 1
            else:
                cheating_count += 1

            # Match search text
            if query and (query not in name):
                continue

            # Match status
            if "Чисто" in status_filter and status != "CLEAN":
                continue
            if "Внимание" in status_filter and status != "ATTENTION":
                continue
            if "Подозрение" in status_filter and status != "CHEATING":
                continue

            # Match violation type
            if type_filter != "Все типы нарушений":
                has_type = False
                for inc in incidents:
                    itype = inc.get("type", "")
                    if "Смартфон" in type_filter and itype == "PHONE_DETECTED":
                        has_type = True
                    elif "Отвод" in type_filter and ("LOOKING" in itype or "GAZE" in itype):
                        has_type = True
                    elif "Посторонние" in type_filter and ("FACES" in itype or "NO_FACE" in itype):
                        has_type = True
                    elif "Фокус" in type_filter and ("FOCUS" in itype or "HOTKEY" in itype):
                        has_type = True
                if not has_type:
                    continue

            self.filtered_sessions.append(s)

        self.stats_lbl.setText(
            f"Всего: {len(self.all_sessions)} | 🟢 {clean_count} | 🟡 {attention_count} | 🔴 {cheating_count}"
        )
        self._render_sessions_list()

    def _render_sessions_list(self):
        self.sessions_list.clear()

        for s in self.filtered_sessions:
            item = QListWidgetItem()
            item.setSizeHint(QSize(320, 72))

            widget = QWidget()
            w_layout = QVBoxLayout(widget)
            w_layout.setContentsMargins(6, 6, 6, 6)
            w_layout.setSpacing(3)

            # Top row: Student name & Status badge
            top_row = QHBoxLayout()
            name_lbl = QLabel(s.get("student_name", "Студент"))
            name_lbl.setStyleSheet("color: #ffffff; font-size: 13.5px; font-weight: 700;")
            top_row.addWidget(name_lbl)
            top_row.addStretch()

            status_lbl = QLabel(s.get("status_ru", ""))
            status_color = s.get("status_color", "#94a3b8")
            status_lbl.setStyleSheet(f"""
                color: {status_color};
                background: {status_color}22;
                border: 1px solid {status_color}55;
                border-radius: 4px;
                padding: 2px 6px;
                font-size: 11px;
                font-weight: 700;
            """)
            top_row.addWidget(status_lbl)
            w_layout.addLayout(top_row)

            # Bottom row: Date & Score
            bot_row = QHBoxLayout()
            dt_str = s.get("start_time", "")
            try:
                dt_fmt = datetime.fromisoformat(dt_str).strftime("%d.%m.%Y %H:%M")
            except Exception:
                dt_fmt = dt_str
            date_lbl = QLabel(f"📅 {dt_fmt} | ⏱️ {s.get('time_spent', '00:00')}")
            date_lbl.setStyleSheet("color: #94a3b8; font-size: 11px;")
            bot_row.addWidget(date_lbl)
            bot_row.addStretch()

            score_lbl = QLabel(f"Балл: {s.get('score', '')}")
            score_lbl.setStyleSheet("color: #38bdf8; font-weight: 700; font-size: 11.5px;")
            bot_row.addWidget(score_lbl)
            w_layout.addLayout(bot_row)

            self.sessions_list.addItem(item)
            self.sessions_list.setItemWidget(item, widget)

        if self.filtered_sessions:
            self.sessions_list.setCurrentRow(0)
        else:
            self._render_empty_detail()

    def _on_session_selected(self, row: int):
        if row < 0 or row >= len(self.filtered_sessions):
            return
        self.current_session = self.filtered_sessions[row]
        self._render_session_detail(self.current_session)

    def _render_session_detail(self, s: Dict[str, Any]):
        # Update Hero Card
        name = s.get("student_name", "Студент")
        self.hero_student_name.setText(name)

        start_str = s.get("start_time", "")
        try:
            dt_fmt = datetime.fromisoformat(start_str).strftime("%d.%m.%Y в %H:%M")
        except Exception:
            dt_fmt = start_str
        self.hero_meta.setText(
            f"Сессия от {dt_fmt} • Время прохождения: {s.get('time_spent', '')} • Нарушений: {s.get('total_violations', 0)}"
        )

        # Status Pill
        status_ru = s.get("status_ru", "")
        status_color = s.get("status_color", "#22c55e")
        self.hero_status_pill.setText(status_ru)
        self.hero_status_pill.setStyleSheet(f"""
            background-color: {status_color}25;
            color: {status_color};
            border: 1px solid {status_color}66;
            padding: 6px 14px;
            border-radius: 8px;
            font-weight: 800;
            font-size: 13px;
        """)

        # Score Pill
        score = s.get("score", "0 / 10")
        pct = s.get("score_pct", 0)
        self.hero_score_pill.setText(f"Результат: {score} ({pct}%)")

        incidents = s.get("incidents", [])
        if not incidents:
            self.timeline_table.hide()
            self.gallery_scroll.hide()
            self.empty_incidents_lbl.show()
            return

        self.empty_incidents_lbl.hide()
        if self.tab_timeline_btn.styleSheet().count("#0284c7") > 0:
            self.timeline_table.show()
            self.gallery_scroll.hide()
        else:
            self.timeline_table.hide()
            self.gallery_scroll.show()

        # Fill Timeline Table
        self.timeline_table.setRowCount(len(incidents))
        for row, inc in enumerate(incidents):
            # Timecode
            tc_item = QTableWidgetItem(f"⏱️ {inc.get('time_code', '00:00')}")
            tc_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.timeline_table.setItem(row, 0, tc_item)

            # Type
            type_item = QTableWidgetItem(inc.get("type_ru", ""))
            type_item.setForeground(QColor("#38bdf8"))
            self.timeline_table.setItem(row, 1, type_item)

            # Severity
            sev = inc.get("severity", "MEDIUM")
            sev_item = QTableWidgetItem(sev)
            sev_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if sev in ["CRITICAL", "HIGH"]:
                sev_item.setForeground(QColor("#ef4444"))
            else:
                sev_item.setForeground(QColor("#f59e0b"))
            self.timeline_table.setItem(row, 2, sev_item)

            # Duration
            dur_item = QTableWidgetItem(f"{inc.get('duration_sec', 1.5):.1f} сек")
            dur_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.timeline_table.setItem(row, 3, dur_item)

            # Description
            desc_item = QTableWidgetItem(inc.get("description", ""))
            self.timeline_table.setItem(row, 4, desc_item)

        # Fill Gallery Grid
        # Clear existing items
        while self.gallery_layout.count():
            child = self.gallery_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()

        session_folder = Path(s.get("folder_path", ""))
        cols = 3
        for idx, inc in enumerate(incidents):
            shot_rel = inc.get("screenshot", "")
            shot_full = session_folder / shot_rel if shot_rel else None

            card = QFrame(self.gallery_content)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.setStyleSheet("""
                QFrame {
                    background-color: #1e293b;
                    border: 1px solid #334155;
                    border-radius: 8px;
                    padding: 8px;
                }
                QFrame:hover {
                    border-color: #38bdf8;
                    background-color: #273549;
                }
            """)
            card_layout = QVBoxLayout(card)
            card_layout.setContentsMargins(6, 6, 6, 6)
            card_layout.setSpacing(6)

            thumb_label = QLabel(card)
            thumb_label.setFixedSize(200, 130)
            thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            thumb_label.setStyleSheet("background-color: #020617; border-radius: 6px;")

            if shot_full and shot_full.exists():
                pix = QPixmap(str(shot_full))
                if not pix.isNull():
                    thumb_label.setPixmap(pix.scaled(
                        200, 130,
                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                        Qt.TransformationMode.SmoothTransformation
                    ))
                else:
                    thumb_label.setText("Нет изображения")
            else:
                thumb_label.setText("Нет скриншота")
                thumb_label.setStyleSheet("color: #64748b; font-size: 11px;")

            card_layout.addWidget(thumb_label)

            info_label = QLabel(f"#{idx+1} {inc.get('type_ru', '')}\n⏱️ {inc.get('time_code', '')} ({inc.get('duration_sec', 1.5):.1f}с)", card)
            info_label.setStyleSheet("color: #e2e8f0; font-size: 11px; font-weight: 700;")
            card_layout.addWidget(info_label)

            # Click handler to open full modal
            def make_click_handler(path=str(shot_full) if shot_full else "", title=inc.get("type_ru", ""), desc=inc.get("description", "")):
                return lambda event: self._show_image_modal(path, title, desc)

            card.mousePressEvent = make_click_handler()

            row_i = idx // cols
            col_i = idx % cols
            self.gallery_layout.addWidget(card, row_i, col_i)

    def _show_image_modal(self, shot_path: str, title: str, details: str):
        dlg = ImagePreviewModal(shot_path, title, details, self)
        dlg.exec()

    def _render_empty_detail(self):
        self.hero_student_name.setText("Сессии не найдены")
        self.hero_meta.setText("Попробуйте изменить параметры поиска или фильтров")
        self.hero_status_pill.setText("—")
        self.hero_score_pill.setText("—")
        self.timeline_table.hide()
        self.gallery_scroll.hide()
        self.empty_incidents_lbl.hide()

    def _export_current_report(self):
        if not self.current_session:
            QMessageBox.information(self, "Экспорт", "Выберите сессию студента для экспорта отчёта.")
            return

        session_folder = Path(self.current_session.get("folder_path", ""))
        student_name = self.current_session.get("student_name", "Студент")
        default_name = f"Протокол_{student_name.replace(' ', '_')}.html"

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Сохранить отчет о тестировании",
            default_name,
            "HTML Document (*.html);;CSV Table (*.csv)"
        )

        if not file_path:
            return

        out_path = Path(file_path)
        if out_path.suffix.lower() == ".csv":
            ok = SessionReportManager.export_session_csv(session_folder, out_path)
        else:
            ok = SessionReportManager.export_session_html(session_folder, out_path)

        if ok:
            QMessageBox.information(
                self,
                "Экспорт завершен",
                f"Отчет успешно сохранен в файл:\n{out_path.name}"
            )
        else:
            QMessageBox.critical(self, "Ошибка", "Не удалось экспортировать отчет.")
