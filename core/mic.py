import collections
import threading
import time

import numpy as np
import sounddevice as sd

from utils.debuglog import dlog


SR = 16000
MAX_RECORD_SEC = 60


def list_input_devices():
    """Return list of (index, name, channels) for input-capable devices."""
    out = []
    try:
        for i, d in enumerate(sd.query_devices()):
            if d["max_input_channels"] > 0:
                out.append((i, d["name"], d["max_input_channels"]))
    except Exception:
        pass
    return out


def pick_best_device():
    """Probe each input device briefly and return the index with the most signal.

    Skips pseudo-devices (Sound Mapper, Primary Sound Capture) that mirror the
    default and pick the real microphone that actually hears ambient sound.
    """
    skip = ("sound mapper", "primary sound", "wave mapper", "@system32")
    best, best_rms = None, -1.0
    for idx, name, ch in list_input_devices():
        low = name.lower()
        if any(s in low for s in skip):
            continue
        try:
            rec = sd.rec(int(0.25 * SR), samplerate=SR, channels=1, dtype="float32", device=idx)
            sd.wait()
            rms = float(np.sqrt(np.mean(rec ** 2)))
            if rms > best_rms:
                best_rms, best = rms, idx
        except Exception:
            continue
    return best


class MicListener:
    """
    Microphone engine with two modes:

    - mode "ptt"  : press-to-talk. The stream stays open (for the level meter),
                    but audio is only captured between start_recording() and
                    stop_recording(). On stop it emits the whole clip.
    - mode "auto" : always-on energy VAD that auto-segments utterances.

    Callbacks:
      on_utterance(np.float32 mono @16k, sr)
      on_level(rms, gate, active)
      on_error(message)
    """

    def __init__(self, cfg, on_utterance=None, on_level=None, on_error=None):
        self.cfg = cfg
        self.on_utterance = on_utterance
        self.on_level = on_level
        self.on_error = on_error

        self.sr = SR
        self.frames_per_block = 480  # 30 ms
        self.stream = None
        self.running = False
        self.muted = False
        self.mode = (cfg["Main"].get("listen_mode", "ptt") or "ptt").strip().lower()

        # ptt state
        self.recording = False
        self._rec_buf = []
        self._rec_start = 0.0

        # VAD state (auto mode)
        self.speech_buf = []
        self.pre_roll = collections.deque(maxlen=10)
        self.in_speech = False
        self.silence_frames = 0
        self.noise_floor = 0.003
        self.gate = 0.004

        # how long a silence ends the utterance (auto: segments; ptt: auto-stop)
        self.end_silence_sec = float(self.cfg["Main"].get("end_silence_sec", 4) or 4)

        self._blocks_per_sec = self.sr / self.frames_per_block
        self.min_speech_blocks = int(0.25 * self._blocks_per_sec)
        self.max_silence_blocks = int(self.end_silence_sec * self._blocks_per_sec)

        # ptt endpointing
        self._ptt_speech_seen = False
        self._ptt_silence_blocks = 0

        self._silent_levels = 0
        self._warned_silence = False
        self._dbg_level_counter = 0
        self._dbg_max_rms = 0.0

    # ---------- lifecycle ----------
    def set_mode(self, mode):
        self.mode = (mode or "ptt").strip().lower()
        self.in_speech = False
        self.speech_buf = []
        self.recording = False
        self._rec_buf = []
        self._ptt_speech_seen = False
        self._ptt_silence_blocks = 0

    def set_end_silence(self, sec):
        """Seconds of silence after speech that trigger auto-send."""
        try:
            self.end_silence_sec = float(sec)
        except Exception:
            return
        self.max_silence_blocks = max(1, int(self.end_silence_sec * self._blocks_per_sec))

    def _resolve_device(self):
        want = (self.cfg["Main"].get("mic_device", "default") or "default").strip()
        if want and want.lower() != "default":
            try:
                return int(want)
            except Exception:
                pass
        try:
            picked = pick_best_device()
            if picked is not None:
                return picked
        except Exception:
            pass
        return None

    def start(self):
        if self.running:
            return
        self.running = True
        dev = self._resolve_device()
        names = {i: n for i, n, _ in list_input_devices()}
        dlog(f"MIC start: mode={self.mode} device={dev} ({names.get(dev, 'system default')})")
        try:
            self.stream = sd.InputStream(
                samplerate=self.sr,
                channels=1,
                dtype="float32",
                blocksize=self.frames_per_block,
                device=dev,
                callback=self._callback,
            )
            self.stream.start()
            dlog(f"MIC stream started ok on device={dev}")
        except Exception as e:
            self.running = False
            self._err(f"Could not open microphone: {e}")
            dlog(f"MIC stream FAILED: {e}")

    def stop(self):
        self.running = False
        if self.stream:
            try:
                self.stream.stop()
                self.stream.close()
            except Exception:
                pass
            self.stream = None

    def set_muted(self, muted: bool):
        self.muted = bool(muted)
        if self.muted:
            self.in_speech = False
            self.speech_buf = []
            self.silence_frames = 0
            self.recording = False
            self._rec_buf = []

    # ---------- press-to-talk ----------
    def start_recording(self):
        if self.muted:
            self._err("Microphone is muted.")
            return
        self.recording = True
        self._rec_buf = []
        self._rec_start = time.time()
        self._ptt_speech_seen = False
        self._ptt_silence_blocks = 0
        dlog("MIC ptt: recording started")

    def stop_recording(self):
        if not self.recording:
            return
        self.recording = False
        audio = np.concatenate(self._rec_buf).astype(np.float32) if self._rec_buf else np.zeros(0, np.float32)
        self._rec_buf = []
        dlog(f"MIC ptt: recording stopped, {len(audio)} samples ({len(audio)/self.sr:.2f}s) "
             f"peak={float(np.abs(audio).max()) if audio.size else 0.0:.4f}")
        self._emit(audio)

    def cancel_recording(self):
        self.recording = False
        self._rec_buf = []

    # ---------- audio callback ----------
    def _callback(self, indata, frames, time_info, status):
        block = indata[:, 0].copy()
        rms = float(np.sqrt(np.mean(block ** 2)) + 1e-9)

        if self.muted:
            if self.on_level:
                try:
                    self.on_level(0.0, self.gate, False)
                except Exception:
                    pass
            return

        # adaptive noise floor while idle (both modes)
        if (self.mode == "auto" and not self.in_speech) or (self.mode == "ptt" and not self.recording):
            self.noise_floor = 0.95 * self.noise_floor + 0.05 * rms
        self.gate = max(0.004, self.noise_floor * 2.5)

        # periodic debug
        self._dbg_max_rms = max(self._dbg_max_rms, rms)
        self._dbg_level_counter += 1
        if self._dbg_level_counter >= int(3 * self._blocks_per_sec):
            dlog(f"MIC level: max_rms={self._dbg_max_rms:.4f} gate={self.gate:.4f} "
                 f"mode={self.mode} rec={self.recording}")
            self._dbg_max_rms = 0.0
            self._dbg_level_counter = 0

        active = rms > self.gate
        if self.on_level:
            try:
                self.on_level(rms, self.gate, active or self.recording)
            except Exception:
                pass

        # auto-mode silence watchdog
        if self.mode == "auto":
            if rms < 0.002:
                self._silent_levels += 1
            else:
                self._silent_levels = 0
            if self._silent_levels > int(6 * self._blocks_per_sec) and not self._warned_silence:
                self._warned_silence = True
                self._err("Microphone seems silent. Check Windows mic permission or pick another device.")

        if self.mode == "ptt":
            if self.recording:
                self._rec_buf.append(block)
                if rms > self.gate:
                    self._ptt_speech_seen = True
                    self._ptt_silence_blocks = 0
                elif self._ptt_speech_seen:
                    # speech happened, now counting trailing silence
                    self._ptt_silence_blocks += 1
                    if self._ptt_silence_blocks >= self.max_silence_blocks:
                        dlog(f"MIC ptt: {self.end_silence_sec:.1f}s silence -> auto-send")
                        self.stop_recording()
                        return
                if (time.time() - self._rec_start) > MAX_RECORD_SEC:
                    dlog("MIC ptt: max length reached, auto-stop")
                    self.stop_recording()
            return

        # ---- auto mode VAD ----
        if active:
            if not self.in_speech:
                self.in_speech = True
                self.speech_buf = list(self.pre_roll)
                self.silence_frames = 0
                dlog(f"MIC speech started (rms={rms:.4f}, gate={self.gate:.4f})")
            self.speech_buf.append(block)
        else:
            if self.in_speech:
                self.silence_frames += 1
                self.speech_buf.append(block)
                if self.silence_frames >= self.max_silence_blocks:
                    self._emit(np.concatenate(self.speech_buf).astype(np.float32))
                    self.in_speech = False
                    self.speech_buf = []
                    self.silence_frames = 0
            else:
                self.pre_roll.append(block)

    def _emit(self, audio):
        if audio is None or len(audio) < self.min_speech_blocks:
            dlog(f"MIC: clip too short ({0 if audio is None else len(audio)} samples), ignored")
            return
        if self.on_utterance:
            threading.Thread(target=self.on_utterance, args=(audio, self.sr), daemon=True).start()

    def _err(self, msg):
        if self.on_error:
            try:
                self.on_error(msg)
            except Exception:
                pass
