"""Capture what the PC is playing (system audio loopback) for the phone stream.

Uses `soundcard` (WASAPI loopback on Windows) so any sound the PC outputs -
music, videos, call audio - can be streamed to the phone. The browser plays
these small PCM chunks with the Web Audio API.

If `soundcard` is unavailable, streaming degrades to video-only instead of
breaking anything.
"""
import queue
import threading
import time

import numpy as np

try:
    import soundcard as sc
    HAVE_SOUNDCARD = True
except Exception:      # pragma: no cover
    sc = None
    HAVE_SOUNDCARD = False

OUT_RATE = 16000       # what the phone plays; plenty for speech and music
CHUNK_MS = 100


def _co_init():
    """soundcard talks to Windows audio through COM, which must be initialised
    per thread or the device enumerator fails with CLASS_E_NOAGGREGATION."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        return True
    except Exception:
        return False


def _to_s16(data, in_rate, gain=1.0):
    """(n, ch) float in -1..1 -> 16 kHz mono int16 little-endian bytes."""
    arr = np.asarray(data, dtype=np.float32)
    if arr.ndim > 1:
        arr = arr.mean(axis=1)
    if in_rate and in_rate != OUT_RATE and arr.size:
        # Cheap linear resample - keeps latency low and CPU cheap.
        n_out = max(1, int(arr.size * OUT_RATE / float(in_rate)))
        x_old = np.linspace(0.0, 1.0, num=arr.size, endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        arr = np.interp(x_new, x_old, arr).astype(np.float32)
    arr = np.clip(arr * gain, -1.0, 1.0)
    # float -1..1 must be scaled to the int16 range or it all truncates to zero
    return (arr * 32767.0).astype("<i2").tobytes()


class LoopbackAudio:
    """Background loopback recorder that hands out PCM chunks."""

    def __init__(self, cfg, log=None):
        self.cfg = cfg
        self._log = log or (lambda m: None)
        self.rate = 48000
        self._rec = None
        self.running = False
        self._queue = queue.Queue(maxsize=8)
        self._thread = None
        self._ready = threading.Event()
        self._speaker_name = ""
        self.muted = False

    @property
    def available(self):
        return HAVE_SOUNDCARD

    def start(self):
        if self.running:
            return True
        if not HAVE_SOUNDCARD:
            return False
        self.running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        # The recorder is created and used on the worker thread (MediaFoundation
        # capture objects are thread-affine), so wait until it is live.
        self._ready.wait(timeout=4.0)
        return self._ready.is_set()

    def _loop(self):
        global _speaker_name
        _co_init()
        rec = None
        try:
            spk = sc.default_speaker()
            mic = sc.get_microphone(id=str(spk.id), include_loopback=True)
            try:
                self.rate = int(spk.samplerate) or 48000
            except Exception:
                self.rate = 48000
            rec = mic.recorder(samplerate=self.rate)
            rec.__enter__()
            self._rec = rec
            self._speaker_name = spk.name
            self._log("Audio loopback started (%s)" % spk.name)
        except Exception as e:
            self._log("Audio loopback unavailable: %s" % e)
            self._ready.set()
            return
        self._ready.set()

        frames = max(1, int(self.rate * CHUNK_MS / 1000))
        while self.running:
            try:
                data = rec.record(numframes=frames)
                if self.muted:
                    continue
                pcm = _to_s16(data, self.rate)
                if self._queue.full():
                    try:
                        self._queue.get_nowait()
                    except queue.Empty:
                        pass
                self._queue.put(pcm)
            except Exception as e:
                if self.running:
                    self._log("Audio capture error: %s" % e)
                time.sleep(0.2)
        try:
            rec.__exit__(None, None, None)
        except Exception:
            pass
        self._log("Audio loopback stopped")

    def next_chunk(self, timeout=1.0):
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def stop(self):
        self.running = False
        # The recorder is closed by the worker thread that opened it.
        th = self._thread
        if th is not None:
            th.join(timeout=2.0)
        self._thread = None
        self._rec = None
        self._ready.clear()