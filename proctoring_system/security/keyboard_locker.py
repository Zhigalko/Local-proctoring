"""
Low-Level Windows Keyboard Hook (WH_KEYBOARD_LL) for kiosk lockdown and hotkey suppression.
Intercepts and suppresses forbidden OS navigation and clipboard hotkeys.
"""

import ctypes
from ctypes import wintypes
import threading
import time
from typing import Callable

# Win32 Constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# Virtual Key Codes
VK_TAB = 0x09
VK_ESCAPE = 0x1B
VK_SNAPSHOT = 0x2C      # PrintScreen
VK_LWIN = 0x5B          # Left Windows Key
VK_RWIN = 0x5C          # Right Windows Key
VK_F4 = 0x73            # F4
VK_F12 = 0x7B           # F12
VK_CONTROL = 0x11
VK_MENU = 0x12          # Alt
VK_SHIFT = 0x10

# Character Keys
VK_C = 0x43
VK_V = 0x56
VK_X = 0x58
VK_A = 0x41
VK_Q = 0x51

# KBDLLHOOKSTRUCT flags
LLKHF_EXTENDED = 0x01
LLKHF_ALTDOWN = 0x20

LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long

class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", wintypes.DWORD),
        ("scanCode", wintypes.DWORD),
        ("flags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", ctypes.c_size_t)
    ]

PKBDLLHOOKSTRUCT = ctypes.POINTER(KBDLLHOOKSTRUCT)
HOOKPROC = ctypes.WINFUNCTYPE(LRESULT, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)

import sys
IS_WINDOWS = sys.platform == "win32"

if IS_WINDOWS:
    # WinAPI bindings
    user32 = ctypes.windll.user32
    kernel32 = ctypes.windll.kernel32

    user32.SetWindowsHookExW.argtypes = [ctypes.c_int, HOOKPROC, wintypes.HINSTANCE, wintypes.DWORD]
    user32.SetWindowsHookExW.restype = wintypes.HHOOK

    user32.CallNextHookEx.argtypes = [wintypes.HHOOK, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM]
    user32.CallNextHookEx.restype = LRESULT

    user32.UnhookWindowsHookEx.argtypes = [wintypes.HHOOK]
    user32.UnhookWindowsHookEx.restype = wintypes.BOOL

    user32.GetMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    user32.GetMessageW.restype = wintypes.BOOL

    user32.PostThreadMessageW.argtypes = [wintypes.DWORD, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    user32.PostThreadMessageW.restype = wintypes.BOOL

    user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
    user32.GetAsyncKeyState.restype = wintypes.SHORT
else:
    user32 = None
    kernel32 = None


class KeyboardLocker:
    """
    Suppresses OS-level hotkeys (Alt+Tab, Win, Ctrl+C, Ctrl+V, PrtScn, Alt+F4, Ctrl+Shift+Esc).
    Runs a low-level keyboard hook in a dedicated Windows message pump thread.
    """

    def __init__(
        self,
        on_blocked_hotkey: Callable[[str], None] | None = None,
        on_emergency_unlock: Callable[[], None] | None = None
    ):
        self.on_blocked_hotkey = on_blocked_hotkey
        self.on_emergency_unlock = on_emergency_unlock
        self.hook_id = None
        self.thread = None
        self.thread_id = None
        self.is_active = False
        self._hook_proc_ref = None  # Prevent GC of ctypes callback

    def _is_key_pressed(self, vk: int) -> bool:
        """Check if modifier key is currently pressed."""
        return (user32.GetAsyncKeyState(vk) & 0x8000) != 0

    def _hook_callback(self, n_code: int, w_param: wintypes.WPARAM, l_param: wintypes.LPARAM) -> LRESULT:
        if n_code < 0:
            return user32.CallNextHookEx(self.hook_id, n_code, w_param, l_param)

        is_key_down = (w_param == WM_KEYDOWN or w_param == WM_SYSKEYDOWN)
        kbd = ctypes.cast(l_param, PKBDLLHOOKSTRUCT).contents
        vk = kbd.vkCode
        alt_down = bool(kbd.flags & LLKHF_ALTDOWN)
        ctrl_down = self._is_key_pressed(VK_CONTROL)
        shift_down = self._is_key_pressed(VK_SHIFT)

        # Emergency escape hotkey: Ctrl + Alt + Shift + F12
        if is_key_down and ctrl_down and alt_down and shift_down and vk == VK_F12:
            print("[KeyboardLocker] EMERGENCY UNLOCK TRIGGERED (Ctrl+Alt+Shift+F12)")
            if self.on_emergency_unlock:
                self.on_emergency_unlock()
            return 1  # Suppress key from other apps

        blocked_key_name: str | None = None

        if is_key_down:
            # 1. Alt + Tab
            if alt_down and vk == VK_TAB:
                blocked_key_name = "Alt+Tab (Application Switch)"

            # 2. Windows Start Key (Left or Right)
            elif vk in (VK_LWIN, VK_RWIN):
                blocked_key_name = "Win Key (Start Menu)"

            # 3. Ctrl + Esc (Alternative Start Menu)
            elif ctrl_down and vk == VK_ESCAPE:
                blocked_key_name = "Ctrl+Esc (Start Menu)"

            # 4. Alt + Esc (Switch between windows)
            elif alt_down and vk == VK_ESCAPE:
                blocked_key_name = "Alt+Esc (Window Switch)"

            # 5. Alt + F4 (Close application)
            elif alt_down and vk == VK_F4:
                blocked_key_name = "Alt+F4 (Close Window)"

            # 6. PrintScreen (Capture screen)
            elif vk == VK_SNAPSHOT:
                blocked_key_name = "PrintScreen (Screenshot)"

            # 7. Ctrl + Shift + Esc (Task Manager)
            elif ctrl_down and shift_down and vk == VK_ESCAPE:
                blocked_key_name = "Ctrl+Shift+Esc (Task Manager)"

            # 8. Clipboard operations (Ctrl+C, Ctrl+V, Ctrl+X, Ctrl+A)
            elif ctrl_down and vk == VK_C:
                blocked_key_name = "Ctrl+C (Copy Blocked)"
            elif ctrl_down and vk == VK_V:
                blocked_key_name = "Ctrl+V (Paste Blocked)"
            elif ctrl_down and vk == VK_X:
                blocked_key_name = "Ctrl+X (Cut Blocked)"

        if blocked_key_name:
            if self.on_blocked_hotkey:
                try:
                    self.on_blocked_hotkey(blocked_key_name)
                except Exception as e:
                    print(f"[KeyboardLocker] Callback error: {e}")
            # Return 1 to suppress the key event
            return 1

        return user32.CallNextHookEx(self.hook_id, n_code, w_param, l_param)

    def _message_loop(self):
        self.thread_id = kernel32.GetCurrentThreadId()
        self._hook_proc_ref = HOOKPROC(self._hook_callback)

        self.hook_id = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            self._hook_proc_ref,
            None,
            0
        )

        if not self.hook_id:
            error_code = kernel32.GetLastError()
            print(f"[KeyboardLocker] Failed to install hook. Error code: {error_code}")
            self.is_active = False
            return

        self.is_active = True
        print("[KeyboardLocker] Low-level Windows keyboard hook installed successfully.")

        msg = wintypes.MSG()
        while self.is_active:
            res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
            if res <= 0:
                break
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))

        if self.hook_id:
            user32.UnhookWindowsHookEx(self.hook_id)
            self.hook_id = None
            print("[KeyboardLocker] Keyboard hook uninstalled.")

    def start(self):
        """Start low-level keyboard locker thread."""
        if not IS_WINDOWS:
            print("[KeyboardLocker] Skipping keyboard hook on non-Windows platform.")
            return
        if self.is_active:
            return
        self.thread = threading.Thread(target=self._message_loop, daemon=True, name="KeyboardLockerThread")
        self.thread.start()
        # Wait a moment for thread initialization
        time.sleep(0.05)

    def stop(self):
        """Stop keyboard locker and unhook immediately."""
        self.is_active = False
        if self.thread_id and user32:
            # Post WM_QUIT (0x0012) to exit message loop
            user32.PostThreadMessageW(self.thread_id, 0x0012, 0, 0)
        if self.hook_id and user32:
            try:
                user32.UnhookWindowsHookEx(self.hook_id)
            except Exception:
                pass
            self.hook_id = None
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=1.0)
        self.thread = None
        self.thread_id = None
        print("[KeyboardLocker] Keyboard hook uninstalled and thread stopped.")
