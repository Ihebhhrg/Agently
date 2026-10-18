"""Glue between the remote web server and the existing voice pipeline.

The phone sends typed text and/or recorded audio; this decodes audio with
PyAV, transcribes it with the same Whisper STT voice mode uses, asks the same
Agent to pick an action, and executes it through the same PCControl. Risky
actions are never executed here directly - they are parked as a pending
confirmation and only run when the phone taps "Yes".
"""
import base64
import io
import os
import tempfile
import threading
import time
import uuid

from core.control import DESTRUCTIVE

# Actions that touch the live desktop. They are confirm-gated remotely even
# when they are not in DESTRUCTIVE, because the phone is unattended.
_DESKTOP_ACTIONS = {
    "type", "key", "hotkey", "click", "move", "scroll", "window",
    "volume", "media", "lock",
}

_CONFIRM_TTL = 180.0  # a pending "are you sure?" expires after 3 minutes


def is_risky(action, confirm_all=True):
    """True if this action must be confirmed on the phone before it runs."""
    name = str((action or {}).get("action", "")).lower()
    if not name:
        return False
    if name in DESTRUCTIVE or name == "run":
        return True
    if confirm_all and name in _DESKTOP_ACTIONS:
        return True
    return False


def describe(action):
    """Human sentence the phone shows above the Yes/Cancel buttons."""
    a = action or {}
    name = str(a.get("action", "")).lower()
    known = {
        "shutdown": "shut down your PC",
        "restart": "restart your PC",
        "sleep": "put your PC to sleep",
        "logoff": "log you off",
        "lock": "lock your PC",
        "delete": "delete {}".format(a.get("path", "that file")),
        "run": "run the command: {}".format(a.get("command") or a.get("cmd") or "?"),
        "type": "type: {}".format(a.get("text", "")),
        "hotkey": "press {}".format("+".join(a.get("keys") or [])),
        "key": "press {}".format(a.get("key", "")),
        "click": "click at {},{}".format(a.get("x", "?"), a.get("y", "?")),
        "scroll": "scroll {}".format(a.get("amount", "")),
        "move": "move the mouse to {},{}".format(a.get("x", "?"), a.get("y", "?")),
        "window": "do {}".format(a.get("do", "")),
        "volume": "volume {}".format(a.get("level", "")),
        "media": "toggle media playback",
    }
    if name in known:
        return known[name]
    return name.replace("_", " ") or "do that"


class RemoteBridge:
    def __init__(self, cfg, log=None):
        self.cfg = cfg
        self._log = log or (lambda m: None)
        # injected by main.py
        self.agent = None
        self.control = None
        self.stt = None
        self.capture = None
        self.timers = None
        self.audio = None          # optional loopback audio for the live stream
        self.confirm_all = cfg["Main"].getboolean("remote_confirm_all", True)
        self._pending = {}      # confirm_id -> {"action", "desc", "ts"}
        self._lock = threading.Lock()
        self._busy = False
        self._client_ts = 0     # last time a phone talked to us

    # ---------- client presence (drives keep-awake) ----------
    def touch(self):
        self._client_ts = time.time()

    def client_connected(self, since=30.0):
        return (time.time() - self._client_ts) < since

    # ---------- audio -> text ----------
    def transcribe_audio(self, b64_audio, mime=""):
        """b64_audio is a browser MediaRecorder blob (webm/opus or mp4/aac)."""
        if not b64_audio or not self.stt:
            return ""
        try:
            raw = base64.b64decode(b64_audio)
        except Exception:
            return ""
        path = os.path.join(tempfile.gettempdir(), "agently_remote_%s.bin" % uuid.uuid4().hex[:8])
        try:
            with open(path, "wb") as f:
                f.write(raw)
            return self._decode_and_stt(path)
        finally:
            try:
                os.remove(path)
            except Exception:
                pass

    def _decode_and_stt(self, path):
        import av
        import numpy as np
        try:
            with av.open(path) as container:
                stream = container.streams.audio[0]
                resampler = av.audio.resampler.AudioResampler(
                    format="s16", layout="mono", rate=16000
                )
                chunks = []
                for frame in container.decode(stream):
                    for out in resampler.resample(frame):
                        arr = out.to_ndarray()
                        chunks.append(arr.reshape(-1))
                for out in resampler.resample(None):
                    arr = out.to_ndarray()
                    chunks.append(arr.reshape(-1))
            if not chunks:
                return ""
            data = np.concatenate(chunks).astype(np.float32) / 32768.0
            text = self.stt.transcribe(data)
            return (text or "").strip()
        except Exception as e:
            self._log("Remote: audio decode failed (%s)" % e)
            return ""

    # ---------- the main entry: text in, outcome out ----------
    def handle_text(self, text):
        """Run one instruction from the phone. Returns a result dict."""
        text = (text or "").strip()
        if not text:
            return {"type": "reply", "reply": "I didn't catch that."}
        if not self.agent:
            return {"type": "reply", "reply": "The assistant is still starting up."}

        with self._lock:
            if self._busy:
                return {"type": "reply", "reply": "Still working on the last one - one moment."}
            self._busy = True
        try:
            img = None
            info = {"app": "unknown", "title": "unknown"}
            if self.capture:
                try:
                    info = self.capture.get_active_info()
                    if self.cfg["Main"].getboolean("use_active_window", True):
                        img = self.capture.capture_active()
                    else:
                        img = self.capture.capture_full()
                except Exception:
                    pass
            decision = self.agent.decide(text, img, info)
            if not decision or not decision.get("action"):
                return {"type": "reply", "reply": decision.get("reply") or "Okay."}
            action = decision["action"]
            if is_risky(action, self.confirm_all):
                return self._park(action)
            reply, _msg = self.agent.execute_action(action)
            return {"type": "reply", "reply": reply or "Done."}
        except Exception as e:
            self._log("Remote: command failed (%s)" % e)
            return {"type": "reply", "reply": "Sorry, that failed: %s" % e}
        finally:
            with self._lock:
                self._busy = False

    # ---------- confirm gate ----------
    def _park(self, action):
        desc = describe(action)
        cid = uuid.uuid4().hex[:12]
        with self._lock:
            self._pending[cid] = {"action": action, "desc": desc, "ts": time.time()}
            self._prune()
        self._log("Remote: waiting for phone confirm - %s" % desc)
        return {"type": "confirm", "confirm_id": cid, "desc": desc}

    def _prune(self):
        now = time.time()
        for cid in [c for c, p in self._pending.items() if now - p["ts"] > _CONFIRM_TTL]:
            self._pending.pop(cid, None)

    def resolve(self, confirm_id, approved):
        with self._lock:
            self._prune()
            item = self._pending.get(confirm_id)
            if not item:
                return {"type": "reply", "reply": "That request expired."}
            self._pending.pop(confirm_id, None)
        desc = item["desc"]
        if not approved:
            return {"type": "reply", "reply": "Cancelled - I did not %s." % desc}
        try:
            reply, _msg = self.agent.execute_action(item["action"])
            return {"type": "reply", "reply": reply or ("Done - %s." % desc)}
        except Exception as e:
            return {"type": "reply", "reply": "That failed: %s" % e}

    def pending_count(self):
        with self._lock:
            return len(self._pending)