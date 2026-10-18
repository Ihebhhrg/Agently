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

OUT_RATE = 48000       # full CD-quality rate so music/speech both sound right
OUT_CHANNELS = 2       # stereo
CHUNK_MS = 100
GAIN = 1.8             # loopback levels are often quiet; a little lift helps


def _co_init():
    """soundcard talks to Windows audio through COM, which must be initialised
    per thread or the device enumerator fails with CLASS_E_NOAGGREGATION."""
    try:
        import pythoncom
        pythoncom.CoInitialize()
        return True
    except Exception:
        return False


def _to_s16(data, in_rate, gain=GAIN):
    """(n, ch) float -> 48 kHz stereo int16 little-endian bytes."""
    arr = np.asarray(data, dtype=np.float32)
    if arr.ndim == 1:
        arr = arr.reshape(-1, 1)

    # stereo: take the first two channels, or duplicate a mono source
    if arr.shape[1] >= 2:
        out = arr[:, :2]
    else:
        out = np.repeat(arr[:, :1], 2, axis=1)

    if in_rate and in_rate != OUT_RATE and out.shape[0]:
        # Cheap linear resample per channel - low latency, low CPU.
        n_out = max(1, int(out.shape[0] * OUT_RATE / float(in_rate)))
        x_old = np.linspace(0.0, 1.0, num=out.shape[0], endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=n_out, endpoint=False)
        out = np.stack([np.interp(x_new, x_old, out[:, c]) for c in range(2)],
                       axis=1).astype(np.float32)

    out = np.clip(out * gain, -1.0, 1.0)
    # float -1..1 must be scaled to the int16 range or it all truncates to zero
    return (out * 32767.0).astype("<i2").tobytes()


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