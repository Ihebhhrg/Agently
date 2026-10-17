import ctypes
import os
import shutil
from ctypes import wintypes

# Common folder aliases the model is allowed to use in place of full paths.
def _shell_folder(name):
    try:
        import winreg
        key = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key) as k:
            val, _ = winreg.QueryValueEx(k, name)
            return val
    except Exception:
        return None


_ALIASES = {}


def _build_aliases():
    home = os.path.expanduser("~")
    mapping = {
        "home": home,
        "desktop": os.path.join(home, "Desktop"),
        "downloads": os.path.join(home, "Downloads"),
        "documents": os.path.join(home, "Documents"),
        "pictures": os.path.join(home, "Pictures"),
        "music": os.path.join(home, "Music"),
        "videos": os.path.join(home, "Videos"),
        "temp": os.environ.get("TEMP", os.path.join(home, "AppData", "Local", "Temp")),
        "onedrive": home,
    }
    shell = {
        "desktop": "Desktop",
        "downloads": "{374DE290-123F-4565-9164-39C4925E467B}",
        "documents": "Personal",
        "pictures": "My Pictures",
        "music": "My Music",
        "videos": "My Video",
    }
    for alias, reg_name in shell.items():
        found = _shell_folder(reg_name)
        if found and os.path.isdir(found):
            mapping[alias] = found
    _ALIASES.clear()
    _ALIASES.update(mapping)


_build_aliases()


def resolve(path):
    """Resolve a user/model supplied path: aliases, ~, env vars, and relative-to-home."""
    if path is None:
        return None
    p = str(path).strip().strip('"').strip("'")
    if not p:
        return None
    p = p.replace("/", os.sep)
    # alias on the first path segment
    parts = [seg for seg in p.split(os.sep) if seg not in ("", ".")]
    if parts:
        head = parts[0].lower().rstrip(":")
        if head in _ALIASES:
            rest = parts[1:]
            return os.path.join(_ALIASES[head], *rest) if rest else _ALIASES[head]
    p = os.path.expandvars(os.path.expanduser(p))
    if not os.path.isabs(p):
        p = os.path.join(os.path.expanduser("~"), p)
    return os.path.normpath(p)


def open_path(path):
    target = resolve(path)
    if not target or not os.path.exists(target):
        return False, f"Path not found: {path}"
    try:
        os.startfile(target)  # noqa: S606 - intentional, opens with default app
        return True, f"Opened {target}"
    except Exception as e:
        return False, f"Could not open {target}: {e}"


def make_folder(path):
    target = resolve(path)
    if not target:
        return False, "No path given"
    try:
        os.makedirs(target, exist_ok=True)
        return True, f"Created folder {target}"
    except Exception as e:
        return False, f"Could not create {target}: {e}"


def move(src, dst):
    s = resolve(src)
    d = resolve(dst)
    if not s or not os.path.exists(s):
        return False, f"Source not found: {src}"
    try:
        if d and os.path.isdir(d):
            d = os.path.join(d, os.path.basename(s))
        if d and os.path.exists(d):
            return False, f"Destination already exists: {d}"
        shutil.move(s, d)
        return True, f"Moved {s} to {d}"
    except Exception as e:
        return False, f"Could not move: {e}"


def copy(src, dst):
    s = resolve(src)
    d = resolve(dst)
    if not s or not os.path.exists(s):
        return False, f"Source not found: {src}"
    try:
        if d and os.path.isdir(d):
            shutil.copy2(s, d)
            d = os.path.join(d, os.path.basename(s))
        elif os.path.isdir(s):
            shutil.copytree(s, d)
        else:
            shutil.copy2(s, d)
        return True, f"Copied {s} to {d}"
    except Exception as e:
        return False, f"Could not copy: {e}"


# ---- Recycle Bin delete via SHFileOperation ----
class _SHFILEOPSTRUCTW(ctypes.Structure):
    _fields_ = [
        ("hwnd", wintypes.HWND),
        ("wFunc", wintypes.UINT),
        ("pFrom", wintypes.LPCWSTR),
        ("pTo", wintypes.LPCWSTR),
        ("fFlags", ctypes.c_ushort),
        ("fAnyOperationsAborted", wintypes.BOOL),
        ("hNameMappings", ctypes.c_void_p),
        ("lpszProgressTitle", wintypes.LPCWSTR),
    ]


_FO_DELETE = 3
_FOF_ALLOWUNDO = 0x40
_FOF_NOCONFIRMATION = 0x10
_FOF_SILENT = 0x4
_FOF_NOERRORUI = 0x400


def delete(path):
    target = resolve(path)
    if not target or not os.path.exists(target):
        return False, f"Not found: {path}"
    if os.path.normcase(os.path.abspath(target)) in (
        os.path.normcase(os.path.abspath(os.path.expanduser("~"))),
        os.path.normcase(os.path.abspath(os.environ.get("SystemRoot", "C:\\Windows"))),
    ):
        return False, "Refusing to delete a protected system folder."
    op = _SHFILEOPSTRUCTW()
    op.hwnd = None
    op.wFunc = _FO_DELETE
    op.pFrom = target + "\0\0"
    op.pTo = None
    op.fFlags = _FOF_ALLOWUNDO | _FOF_NOCONFIRMATION | _FOF_SILENT | _FOF_NOERRORUI
    try:
        res = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    except Exception as e:
        return False, f"Delete failed: {e}"
    if res != 0:
        return False, f"Delete failed (code {res})"
    return True, f"Moved to Recycle Bin: {target}"
