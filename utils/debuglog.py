import os
import time
import threading

from utils import paths

_LOCK = threading.Lock()
_LOG_DIR = paths.LOGS_DIR
_LOG_FILE = os.path.join(_LOG_DIR, "debug.log")


def dlog(msg):
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        line = f"{time.strftime('%H:%M:%S')}  {msg}\n"
        with _LOCK:
            with open(_LOG_FILE, "a", encoding="utf-8") as f:
                f.write(line)
    except Exception:
        pass


def clear():
    try:
        os.makedirs(_LOG_DIR, exist_ok=True)
        open(_LOG_FILE, "w", encoding="utf-8").close()
    except Exception:
        pass
