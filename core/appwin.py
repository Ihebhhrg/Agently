import win32gui
import win32con
import win32process
import psutil


def list_windows():
    """Return visible top-level windows as (hwnd, title, process_name)."""
    items = []

    def _cb(hwnd, _):
        if not win32gui.IsWindowVisible(hwnd):
            return
        title = win32gui.GetWindowText(hwnd)
        if not title:
            return
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid).name()
        except Exception:
            proc = ""
        items.append((hwnd, title, proc))

    win32gui.EnumWindows(_cb, None)
    return items


def find_window(name):
    """Find a window whose title or process name contains *name* (case-insensitive)."""
    if not name:
        return None
    needle = str(name).strip().lower()
    if not needle:
        return None
    for hwnd, title, proc in list_windows():
        if needle in f"{title} {proc}".lower():
            return hwnd
    return None


def focus_window(hwnd):
    try:
        if win32gui.IsIconic(hwnd):
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
        return True
    except Exception:
        return False


def close_window(hwnd):
    try:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
        return True
    except Exception:
        return False
