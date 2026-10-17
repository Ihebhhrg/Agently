import os
import subprocess
import webbrowser
import time

import pyautogui

from core import appwin
from core import files
from core import shell
from core import syssettings

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.15

SHUTDOWN_EXE = os.path.join(os.environ.get("SystemRoot", r"C:\Windows"), "System32", "shutdown.exe")

KEY_ALIASES = {
    "escape": "esc",
    "return": "enter",
    "windows": "win",
    "control": "ctrl",
}

APP_ALIASES = {
    "chrome": "chrome",
    "browser": "chrome",
    "edge": "msedge",
    "firefox": "firefox",
    "notepad": "notepad",
    "calculator": "calc",
    "calc": "calc",
    "explorer": "explorer",
    "files": "explorer",
    "file explorer": "explorer",
    "settings": "ms-settings:",
    "cmd": "cmd",
    "terminal": "wt",
    "powershell": "powershell",
    "task manager": "taskmgr",
    "paint": "mspaint",
    "vscode": "code",
    "vs code": "code",
    "code": "code",
    "spotify": "spotify",
    "word": "winword",
    "excel": "excel",
}

# Which permission flag (config key) each action needs. Missing = always allowed.
ACTION_PERMISSION = {
    "close_app": "perm_apps",
    "focus_app": "perm_apps",
    "show_desktop": "perm_apps",
    "list_windows": "perm_apps",
    "open_path": "perm_files",
    "mkdir": "perm_files",
    "move_file": "perm_files",
    "copy": "perm_files",
    "delete": "perm_files",
    "clip_get": "perm_clip_screens",
    "clip_set": "perm_clip_screens",
    "screenshot": "perm_clip_screens",
    "timer": "perm_timers",
    "reminder": "perm_timers",
    "cancel_timers": "perm_timers",
    "list_timers": "perm_timers",
    "shutdown": "perm_power",
    "restart": "perm_power",
    "sleep": "perm_power",
    "logoff": "perm_power",
    "run": "perm_shell",
    "brightness": "perm_system",
    "wifi": "perm_system",
    "bluetooth": "perm_system",
    "dark_mode": "perm_system",
}

# Actions that require the voice two-step confirmation (when pc_control_confirm is on).
DESTRUCTIVE = {"shutdown", "restart", "sleep", "logoff", "delete"}


class PCControl:
    def __init__(self, cfg):
        self.cfg = cfg
        self.confirm = cfg["Main"].getboolean("pc_control_confirm", True)
        self.capture = None   # injected by main
        self.timers = None    # injected by main

    # ---- public API ----
    def execute(self, action: dict) -> dict:
        """Execute a structured action dict. Returns {'ok': bool, 'message': str}."""
        try:
            name = (action or {}).get("action", "").strip().lower()
            if not name or name in ("chat", "none", "reply"):
                return {"ok": True, "message": ""}

            perm = ACTION_PERMISSION.get(name)
            if perm and not self.cfg["Main"].getboolean(perm, True):
                label = perm.replace("perm_", "").replace("_", " ")
                return {"ok": False,
                        "message": f"the '{label}' permission is turned off. You can enable it in Permissions."}

            handler = getattr(self, f"_do_{name}", None)
            if not handler:
                return {"ok": False, "message": f"Unknown action: {name}"}
            return handler(action)
        except Exception as e:
            return {"ok": False, "message": f"Control error: {e}"}

    # ---- general ----
    def _do_open(self, a):
        target = str(a.get("target", "")).strip()
        if not target:
            return {"ok": False, "message": "No target to open"}
        low = target.lower()
        if low.startswith(("http://", "https://", "www.")):
            url = target if target.startswith("http") else "https://" + target
            webbrowser.open(url)
            return {"ok": True, "message": f"Opened {target}"}
        if low.endswith(".com") or ("." in low and " " not in low):
            webbrowser.open("https://" + low)
            return {"ok": True, "message": f"Opened {target}"}
        app = APP_ALIASES.get(low, target)
        subprocess.Popen(f'start "" "{app}"', shell=True)
        return {"ok": True, "message": f"Opened {target}"}

    def _do_search(self, a):
        q = str(a.get("query", "")).strip()
        if not q:
            return {"ok": False, "message": "No search query"}
        webbrowser.open("https://www.google.com/search?q=" + q.replace(" ", "+"))
        return {"ok": True, "message": f"Searched for {q}"}

    def _do_type(self, a):
        text = str(a.get("text", ""))
        pyautogui.write(text, interval=0.01)
        return {"ok": True, "message": "Typed text"}

    def _do_hotkey(self, a):
        keys = a.get("keys") or []
        keys = [KEY_ALIASES.get(str(k).lower(), str(k).lower()) for k in keys]
        if not keys:
            return {"ok": False, "message": "No keys"}
        pyautogui.hotkey(*keys)
        return {"ok": True, "message": "Pressed " + "+".join(keys)}

    def _do_key(self, a):
        k = str(a.get("key", "")).lower()
        k = KEY_ALIASES.get(k, k)
        if not k:
            return {"ok": False, "message": "No key"}
        pyautogui.press(k)
        return {"ok": True, "message": f"Pressed {k}"}

    def _do_click(self, a):
        x, y = a.get("x"), a.get("y")
        button = str(a.get("button", "left")).lower()
        clicks = 2 if button == "double" else 1
        btn = "right" if button == "right" else "left"
        if x is not None and y is not None:
            pyautogui.click(int(x), int(y), clicks=clicks, button=btn)
        else:
            pyautogui.click(clicks=clicks, button=btn)
        return {"ok": True, "message": f"Clicked at {x},{y}" if x is not None else "Clicked"}

    def _do_move(self, a):
        pyautogui.moveTo(int(a.get("x", 0)), int(a.get("y", 0)), duration=0.2)
        return {"ok": True, "message": "Moved cursor"}

    def _do_scroll(self, a):
        amount = int(a.get("amount", -3))
        pyautogui.scroll(amount)
        return {"ok": True, "message": "Scrolled"}

    def _do_volume(self, a):
        level = str(a.get("level", "")).lower()
        key = {"up": "volumeup", "down": "volumedown", "mute": "volumemute"}.get(level)
        if not key:
            return {"ok": False, "message": "Unknown volume level"}
        for _ in range(3 if level in ("up", "down") else 1):
            pyautogui.press(key)
        return {"ok": True, "message": f"Volume {level}"}

    def _do_media(self, a):
        pyautogui.press("playpause")
        return {"ok": True, "message": "Toggled media"}

    def _do_window(self, a):
        do = str(a.get("do", "")).lower()
        if do == "minimize":
            pyautogui.hotkey("win", "down")
        elif do == "maximize":
            pyautogui.hotkey("win", "up")
        elif do == "close":
            pyautogui.hotkey("alt", "f4")
        elif do == "switch":
            pyautogui.hotkey("alt", "tab")
        else:
            return {"ok": False, "message": f"Unknown window op: {do}"}
        return {"ok": True, "message": f"Window {do}"}

    def _do_lock(self, a):
        pyautogui.hotkey("win", "l")
        return {"ok": True, "message": "Locked PC"}

    def _do_sleep_display(self, a):
        subprocess.Popen("rundll32.exe user32.dll,LockWorkStation", shell=True)
        return {"ok": True, "message": "Locked display"}

    def _do_wait(self, a):
        time.sleep(min(float(a.get("seconds", 1)), 5))
        return {"ok": True, "message": "Waited"}

    # ---- apps & windows ----
    def _do_close_app(self, a):
        name = a.get("name") or a.get("target") or a.get("app")
        if not name:
            return {"ok": False, "message": "No app name given"}
        hwnd = appwin.find_window(name)
        if not hwnd:
            return {"ok": False, "message": f"No open window matching '{name}'"}
        if appwin.close_window(hwnd):
            return {"ok": True, "message": f"Closed {name}"}
        return {"ok": False, "message": f"Could not close {name}"}

    def _do_focus_app(self, a):
        name = a.get("name") or a.get("target") or a.get("app")
        if not name:
            return {"ok": False, "message": "No app name given"}
        hwnd = appwin.find_window(name)
        if not hwnd:
            return {"ok": False, "message": f"No open window matching '{name}'"}
        if appwin.focus_window(hwnd):
            return {"ok": True, "message": f"Switched to {name}"}
        return {"ok": False, "message": f"Could not focus {name}"}

    def _do_show_desktop(self, a):
        pyautogui.hotkey("win", "d")
        return {"ok": True, "message": "Showed the desktop"}

    def _do_list_windows(self, a):
        wins = appwin.list_windows()
        titles = [t for _, t, _ in wins]
        if not titles:
            return {"ok": True, "message": "No windows are open."}
        listed = "; ".join(titles[:25])
        return {"ok": True, "message": f"{len(titles)} windows: {listed}"}

    # ---- files & folders ----
    def _do_open_path(self, a):
        path = a.get("path") or a.get("target")
        ok, msg = files.open_path(path)
        return {"ok": ok, "message": msg}

    def _do_mkdir(self, a):
        path = a.get("path") or a.get("target")
        ok, msg = files.make_folder(path)
        return {"ok": ok, "message": msg}

    def _do_move_file(self, a):
        ok, msg = files.move(a.get("src"), a.get("dst"))
        return {"ok": ok, "message": msg}

    def _do_copy(self, a):
        ok, msg = files.copy(a.get("src"), a.get("dst"))
        return {"ok": ok, "message": msg}

    def _do_delete(self, a):
        path = a.get("path") or a.get("target")
        ok, msg = files.delete(path)
        return {"ok": ok, "message": msg}

    # ---- clipboard & screenshots ----
    def _do_clip_get(self, a):
        import win32clipboard
        try:
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_UNICODETEXT):
                    data = win32clipboard.GetClipboardData(win32clipboard.CF_UNICODETEXT)
                    return {"ok": True, "message": f"Clipboard: {data}"}
                return {"ok": True, "message": "The clipboard has no text."}
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            return {"ok": False, "message": f"Could not read the clipboard: {e}"}

    def _do_clip_set(self, a):
        import win32clipboard
        text = str(a.get("text", ""))
        try:
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardData(win32clipboard.CF_UNICODETEXT, text)
            finally:
                win32clipboard.CloseClipboard()
            return {"ok": True, "message": "Copied to the clipboard."}
        except Exception as e:
            return {"ok": False, "message": f"Could not write the clipboard: {e}"}

    def _do_screenshot(self, a):
        if not self.capture:
            return {"ok": False, "message": "Screenshot is not available."}
        try:
            tmp = self.capture.capture_full()
        except Exception as e:
            return {"ok": False, "message": f"Screenshot failed: {e}"}
        try:
            folder = files.resolve("pictures")
            out_dir = os.path.join(folder, "Agently")
            os.makedirs(out_dir, exist_ok=True)
            stamp = time.strftime("%Y-%m-%d_%H-%M-%S")
            dest = os.path.join(out_dir, f"screenshot_{stamp}.png")
            import shutil
            shutil.copy2(tmp, dest)
            return {"ok": True, "message": f"Saved screenshot to {dest}"}
        except Exception as e:
            return {"ok": False, "message": f"Screenshot saved to temp only: {e}"}

    # ---- timers & reminders ----
    def _do_timer(self, a):
        if not self.timers:
            return {"ok": False, "message": "Timers are not available."}
        seconds = a.get("seconds", a.get("minutes", 0))
        label = a.get("label") or "timer"
        if "minutes" in a and "seconds" not in a:
            seconds = float(a.get("minutes", 0)) * 60
        item, err = self.timers.add_timer(seconds, label)
        if err:
            return {"ok": False, "message": err}
        return {"ok": True, "message": f"Timer set for {int(float(seconds))} seconds."}

    def _do_reminder(self, a):
        if not self.timers:
            return {"ok": False, "message": "Reminders are not available."}
        minutes = a.get("minutes", 0)
        text = a.get("text") or a.get("label") or "reminder"
        item, err = self.timers.add_reminder(minutes, text)
        if err:
            return {"ok": False, "message": err}
        return {"ok": True, "message": f"Reminder set for {minutes} minutes: {text}"}

    def _do_cancel_timers(self, a):
        if not self.timers:
            return {"ok": False, "message": "Timers are not available."}
        n = self.timers.cancel_all()
        return {"ok": True, "message": f"Cancelled {n} timer(s)."}

    def _do_list_timers(self, a):
        if not self.timers:
            return {"ok": False, "message": "Timers are not available."}
        items = self.timers.list_items()
        if not items:
            return {"ok": True, "message": "No timers are running."}
        parts = [f"{txt} in {sec}s" for _, txt, sec in items]
        return {"ok": True, "message": "Timers: " + "; ".join(parts)}

    # ---- system settings ----
    def _do_brightness(self, a):
        ok, msg = syssettings.set_brightness(a.get("level", 50))
        return {"ok": ok, "message": msg}

    def _do_dark_mode(self, a):
        ok, msg = syssettings.set_dark_mode(a.get("on", True))
        return {"ok": ok, "message": msg}

    def _do_wifi(self, a):
        ok, msg = syssettings.set_wifi(a.get("on", True))
        return {"ok": ok, "message": msg}

    def _do_bluetooth(self, a):
        ok, msg = syssettings.set_bluetooth(a.get("on", True))
        return {"ok": ok, "message": msg}

    # ---- run commands ----
    def _do_run(self, a):
        command = a.get("command") or a.get("cmd") or a.get("text")
        kind = a.get("kind", "cmd")
        ok, out = shell.run(command, kind=kind)
        return {"ok": ok, "message": out}

    # ---- power ----
    def _do_shutdown(self, a):
        subprocess.Popen([SHUTDOWN_EXE, "/s", "/t", "0"])
        return {"ok": True, "message": "Shutting down the PC."}

    def _do_restart(self, a):
        subprocess.Popen([SHUTDOWN_EXE, "/r", "/t", "0"])
        return {"ok": True, "message": "Restarting the PC."}

    def _do_sleep(self, a):
        subprocess.Popen(["rundll32.exe", "powrprof.dll,SetSuspendState", "0,1,0"])
        return {"ok": True, "message": "Putting the PC to sleep."}

    def _do_logoff(self, a):
        subprocess.Popen([SHUTDOWN_EXE, "/l"])
        return {"ok": True, "message": "Logging off."}

    # Backwards-compatible helper (kept so old callers don't break)
    def maybe_execute(self, response: str) -> str:
        return ""
