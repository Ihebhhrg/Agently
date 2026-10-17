import os
import tempfile
import uuid

TEMP_ROOT = os.path.join(tempfile.gettempdir(), "agently")

def ensure_dir():
    os.makedirs(TEMP_ROOT, exist_ok=True)

def get_path(ext: str) -> str:
    ensure_dir()
    return os.path.join(TEMP_ROOT, f"{uuid.uuid4()}.{ext}")
