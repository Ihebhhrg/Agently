"""Global hotkey handling using the native Windows RegisterHotKey API.

This replaces the third-party ``keyboard`` package, which installs a low-level
keyboard hook (``SetWindowsHookEx``) and is routinely flagged by antivirus as a
keylogger. ``RegisterHotKey`` is the same mechanism Windows itself uses for
application shortcuts and installs no hook.
"""

import ctypes
from ctypes import wintypes

from PySide6.QtCore import QObject, QAbstractNativeEventFilter, Signal
from PySide6.QtWidgets import QApplication

user32 = ctypes.windll.user32

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, wintypes.UINT, wintypes.UINT]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL

_MODS = {
    "alt": MOD_ALT,
    "ctrl": MOD_CONTROL,
    "control": MOD_CONTROL,
    "shift": MOD_SHIFT,
    "win": MOD_WIN,
    "windows": MOD_WIN,
    "super": MOD_WIN,
    "cmd": MOD_WIN,
}

_VK = {
    "space": 0x20,
    "enter": 0x0D,
    "return": 0x0D,
    "tab": 0x09,
    "esc": 0x1B,
    "escape": 0x1B,
    "backspace": 0x08,
    "delete": 0x2E,
    "del": 0x2E,
    "insert": 0x2D,
    "ins": 0x2D,
    "home": 0x24,
    "end": 0x23,
    "pageup": 0x21,
    "pagedown": 0x22,
    "up": 0x26,
    "down": 0x28,
    "left": 0x25,
    "right": 0x27,
}
for _c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
    _VK[_c.lower()] = ord(_c)
for _d in "0123456789":
    _VK[_d] = ord(_d)
for _i in range(1, 25):
    _VK[f"f{_i}"] = 0x6F + _i  # VK_F1 = 0x70 ... VK_F24 = 0x87


def _parse(hotkey):
    """Return (modifiers, virtual_key) for a string like 'Alt+Shift+V'."""
    parts = [p.strip().lower() for p in hotkey.split("+") if p.strip()]
    mods = 0
    key = None
    for p in parts:
        if p in _MODS:
            mods |= _MODS[p]
        else:
            key = p
    if key is None:
        return None
    vk = _VK.get(key)
    if vk is None:
        return None
    return mods, vk


class _HotkeyFilter(QAbstractNativeEventFilter):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager

    def nativeEventFilter(self, eventType, message):
        try:
            if eventType in (b"windows_generic_MSG", "windows_generic_MSG"):
                msg = ctypes.cast(int(message), ctypes.POINTER(wintypes.MSG)).contents
                if msg.message == WM_HOTKEY and msg.wParam == self.manager._id:
                    self.manager._trigger()
        except Exception:
            pass
        return False, 0


class HotkeyManager(QObject):
    triggered = Signal()

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.hotkey = cfg["Main"].get("hotkey", "Alt+Shift+V")
        self._cb = None
        self._id = 19000
        self._registered = False
        app = QApplication.instance()
        self._filter = _HotkeyFilter(self)
        if app is not None:
            app.installNativeEventFilter(self._filter)
        self._register(self.hotkey)

    def _register(self, hk):
        combo = _parse(hk)
        if combo is None:
            print(f"Failed to register hotkey {hk}: unrecognized")
            return
        mods, vk = combo
        if user32.RegisterHotKey(None, self._id, mods | MOD_NOREPEAT, vk):
            self._registered = True
        else:
            err = ctypes.get_last_error() or ctypes.windll.kernel32.GetLastError()
            print(f"Failed to register hotkey {hk}: error {err}")

    def _unregister(self):
        if self._registered:
            try:
                user32.UnregisterHotKey(None, self._id)
            except Exception:
                pass
            self._registered = False

    def rebind(self, hk):
        self._unregister()
        self.hotkey = hk
        self._register(hk)

    def _trigger(self):
        if self._cb:
            self._cb()

    def set_callback(self, cb):
        self._cb = cb
