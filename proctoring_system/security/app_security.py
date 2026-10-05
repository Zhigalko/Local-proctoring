"""
Application Security & Focus Watcher for Proctoring System.
Monitors OS window focus, suppresses context menus, and enforces active kiosk foreground state.
"""

import ctypes
from ctypes import wintypes
from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QFocusEvent

import sys
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    user32 = ctypes.windll.user32
    user32.GetForegroundWindow.argtypes = []
    user32.GetForegroundWindow.restype = wintypes.HWND

    user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    user32.SetForegroundWindow.restype = wintypes.BOOL

    user32.BringWindowToTop.argtypes = [wintypes.HWND]
    user32.BringWindowToTop.restype = wintypes.BOOL

    user32.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    user32.GetWindowThreadProcessId.restype = wintypes.DWORD
else:
    user32 = None


class WindowSecurityWatcher(QObject):
    """
    Monitors whether the kiosk window is in foreground focus.
    If another application steals focus, triggers FOCUS_LOST security event.
    """

    focus_lost = pyqtSignal()
    focus_regained = pyqtSignal()

    def __init__(self, target_widget: QWidget, check_interval_ms: int = 250):
        super().__init__(target_widget)
        self.target_widget = target_widget
        self.target_hwnd = None
        self.is_currently_focused = True
        self.monitoring_enabled = False

        self.timer = QTimer(self)
        self.timer.setInterval(check_interval_ms)
        self.timer.timeout.connect(self._check_focus)

    def start(self):
        """Start polling foreground window handle."""
        self.target_hwnd = int(self.target_widget.winId())
        self.monitoring_enabled = True
        self.timer.start()

    def stop(self):
        """Pause focus monitoring (e.g. during admin unlock modal)."""
        self.monitoring_enabled = False
        self.timer.stop()

    def _check_focus(self):
        if not self.monitoring_enabled or not self.target_widget:
            return

        # Never trigger focus lost if the exam is finished
        if getattr(self.target_widget, "exam_finished", False):
            return

        foreground_hwnd = user32.GetForegroundWindow() if user32 else self.target_hwnd
        app_active = self.target_widget.isActiveWindow()

        # Check if current foreground window belongs to our kiosk
        is_focused = app_active or (foreground_hwnd == self.target_hwnd)

        # Process ID verification: if foreground window belongs to our own PID, it is NOT an external application
        if not is_focused and foreground_hwnd and user32:
            import os
            proc_id = wintypes.DWORD()
            user32.GetWindowThreadProcessId(foreground_hwnd, ctypes.byref(proc_id))
            if proc_id.value == os.getpid():
                is_focused = True

        if not is_focused and self.is_currently_focused:
            self.is_currently_focused = False
            print("[WindowSecurityWatcher] Focus Lost! Foreground window changed.")
            self.focus_lost.emit()
        elif is_focused and not self.is_currently_focused:
            self.is_currently_focused = True
            print("[WindowSecurityWatcher] Focus Regained.")
            self.focus_regained.emit()

    def force_restore_focus(self):
        """Bring kiosk window back to the front."""
        if self.target_hwnd and user32:
            user32.SetForegroundWindow(self.target_hwnd)
            user32.BringWindowToTop(self.target_hwnd)
        if self.target_widget:
            self.target_widget.activateWindow()
            self.target_widget.raise_()
