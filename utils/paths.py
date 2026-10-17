import os
import sys


def _project_dir():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _base_dir():
    # When frozen (PyInstaller), keep writable files next to the executable
    # instead of inside the read-only bundle.
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return _project_dir()


BASE_DIR = _base_dir()
LOGS_DIR = os.path.join(BASE_DIR, "logs")
MODELS_DIR = os.path.join(BASE_DIR, "models")
CONFIG_PATH = os.path.join(BASE_DIR, "config.ini")


def resource_path(*parts):
    # Read-only bundled resources live in _MEIPASS when frozen.
    base = getattr(sys, "_MEIPASS", None) or _project_dir()
    return os.path.join(base, *parts)


def resolve_model(name):
    # Use a locally bundled model directory when present (offline "Full" build).
    local = os.path.join(MODELS_DIR, name)
    if os.path.isdir(local):
        return local
    return name
