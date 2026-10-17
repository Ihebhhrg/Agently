import gc
import os
import threading
import time

import numpy as np
from faster_whisper import WhisperModel

from utils.debuglog import dlog
from utils import paths

_LOG_DIR = paths.LOGS_DIR
_CLIP = os.path.join(_LOG_DIR, "last_clip.wav")


class STT:
    """Speech-to-text using faster-whisper.

    The model is loaded lazily on first use and unloaded again after an idle
    period so it doesn't hold ~350 MB of RAM while you're not speaking.
    """

    def __init__(self, cfg):
        self.cfg = cfg
        self.model_name = cfg["Main"].get("whisper_model", "small")
        self.device = cfg["Main"].get("whisper_device", "auto")
        self.idle_sec = int(cfg["Main"].get("whisper_idle_sec", "120"))
        self.cpu_threads = int(cfg["Main"].get("whisper_threads", "2"))
        self.model = None
        self._lock = threading.Lock()
        self._load_lock = threading.Lock()
        self._active = 0
        self._last_used = 0.0
        self._stop = False
        threading.Thread(target=self._reaper, daemon=True).start()

    # ---------- model lifecycle ----------
    def is_ready(self):
        return self.model is not None

    def _ensure_model(self):
        if self.model is not None:
            return True
        with self._load_lock:
            if self.model is not None:
                return True
            compute = self.device
            if compute == "auto":
                compute = "cuda" if _has_cuda() else "cpu"
            dlog(f"STT: loading {self.model_name} on {compute} (int8, threads={self.cpu_threads})")
            try:
                self.model = WhisperModel(
                    paths.resolve_model(self.model_name),
                    device=compute,
                    compute_type="int8",
                    cpu_threads=self.cpu_threads,
                )
                dlog("STT: model loaded")
                return True
            except Exception as e:
                dlog(f"STT load failed ({e}); falling back to base/cpu")
                try:
                    self.model = WhisperModel(
                        "base", device="cpu", compute_type="int8",
                        cpu_threads=self.cpu_threads,
                    )
                    return True
                except Exception as e2:
                    dlog(f"STT fallback failed: {e2}")
                    self.model = None
                    return False

    def unload(self):
        with self._load_lock:
            if self.model is not None and self._active == 0:
                self.model = None
                gc.collect()
                dlog("STT: model unloaded (idle)")

    def _reaper(self):
        while not self._stop:
            time.sleep(5)
            try:
                if (self.model is not None and self.idle_sec > 0
                        and self._active == 0
                        and (time.time() - self._last_used) > self.idle_sec):
                    self.unload()
            except Exception:
                pass

    # ---------- transcription ----------
    def transcribe(self, audio) -> str:
        """audio: path to wav OR numpy float32 mono @16k."""
        if not self._ensure_model():
            dlog("STT skipped: model unavailable")
            return ""
        self._last_used = time.time()
        self._active += 1
        try:
            if isinstance(audio, np.ndarray):
                data = audio.astype(np.float32)
                if data.ndim > 1:
                    data = data[:, 0]
                peak = float(np.abs(data).max()) if data.size else 0.0
                dlog(f"STT input: {data.size} samples peak={peak:.4f}")
                try:
                    from scipy.io import wavfile
                    os.makedirs(_LOG_DIR, exist_ok=True)
                    wavfile.write(_CLIP, 16000, (np.clip(data, -1, 1) * 32767).astype(np.int16))
                except Exception:
                    pass
                if peak < 0.004:
                    dlog("STT: audio too quiet, ignoring (likely silence)")
                    return ""
                if peak > 0:
                    data = data / max(peak, 0.001) * 0.95
            else:
                data = audio
            with self._lock:
                segments, _info = self.model.transcribe(
                    data,
                    language=None,
                    beam_size=1,
                    vad_filter=True,
                    vad_parameters=dict(min_silence_duration_ms=300),
                )
                texts = [s.text.strip() for s in segments]
            result = " ".join(t for t in texts if t).strip()
            dlog(f"STT transcript: {result!r}")
            return result
        except Exception as e:
            dlog(f"STT error: {e}")
            return ""
        finally:
            self._active = max(0, self._active - 1)
            self._last_used = time.time()


def _has_cuda():
    try:
        import torch
        return torch.cuda.is_available()
    except Exception:
        return False
