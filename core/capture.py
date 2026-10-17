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
