import threading

import mss
import mss.tools
import win32gui
import win32process
import psutil
from utils.temp import get_path
from PIL import Image

class ScreenCapture:
    def __init__(self, cfg):
        self.cfg = cfg
        self._sct = None
        # mss handles are not thread-safe, so serialise every grab and let
        # long-lived streams pass their own dedicated handle.
        self._grab_lock = threading.Lock()

    # ---------- fast path for live streaming ----------
    def _stream_handle(self):
        if self._sct is None:
            try:
                self._sct = mss.mss()
            except Exception:
                self._sct = False
        return self._sct or None

    @staticmethod
    def new_handle():
        """A dedicated mss handle owned by the calling thread."""
        try:
            return mss.mss()
        except Exception:
            return None

    def grab_image(self, max_width=0, handle=None):
        """Grab the primary monitor straight into a PIL image (no PNG round-trip)."""
        sct = handle if handle is not None else self._stream_handle()
        if sct is None:
            return None
        try:
            with self._grab_lock:
                mon = sct.monitors[1] if len(sct.monitors) > 1 else sct.monitors[0]
                shot = sct.grab(mon)
            # BGRX -> RGB without mss' slower .rgb conversion
            img = Image.frombytes("RGB", shot.size, shot.bgra, "raw", "BGRX")
            if max_width and img.width > max_width:
                # reduce() is a cheap box-average downscale, then a small
                # bilinear pass to land exactly on the target width.
                k = max(1, int(img.width // max_width))
                if k > 1:
                    img = img.reduce(k)
                if img.width != max_width:
                    img = img.resize(
                        (max_width, max(1, int(img.height * max_width / img.width))),
                        Image.BILINEAR,
                    )
            return img
        except Exception:
            return None

    def close_stream(self):
        try:
            if self._sct:
                self._sct.close()
        except Exception:
            pass
        self._sct = None

    def capture_rect(self, rect) -> str:
        x, y, w, h = rect
        with mss.mss() as sct:
            monitor = {"left": x, "top": y, "width": w, "height": h}
            img = sct.grab(monitor)
            path = get_path("png")
            mss.tools.to_png(img.rgb, img.size, output=path)
            return path
    
    def capture_full(self) -> str:
        with mss.mss() as sct:
            img = sct.grab(sct.monitors[0])
            path = get_path("png")
            mss.tools.to_png(img.rgb, img.size, output=path)
            return path
    
    def capture_active(self) -> str:
        try:
            hwnd = win32gui.GetForegroundWindow()
            rect = win32gui.GetWindowRect(hwnd)
            return self.capture_rect((rect[0], rect[1], rect[2]-rect[0], rect[3]-rect[1]))
        except Exception:
            return self.capture_full()
    
    def get_active_info(self) -> dict:
        try:
            hwnd = win32gui.GetForegroundWindow()
            title = win32gui.GetWindowText(hwnd)
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            app = proc.name()
            return {"app": app, "title": title, "hwnd": hwnd}
        except Exception:
            return {"app": "unknown", "title": "unknown"}
