"""On-demand lifecycle for a local Ollama server.

Rules:
  * Start the server only when the app is actually using the Local provider.
  * Stop it again after it has been idle for ``ollama_idle_sec`` (or when the
    user switches away from Local, or on quit).
  * Never kill a server the app did not start itself (``owned`` gate), so an
    Ollama instance launched for another tool is left alone.
"""

import os
import re
import shutil
import subprocess
import threading
import time
import urllib.request

from utils.debuglog import dlog

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


class OllamaService:
    def __init__(self, cfg):
        self.cfg = cfg
        # Set True only once *we* spawn the server; gates stop().
        self.owned = False
        self._proc = None
        self._lock = threading.Lock()
        self._timer = None

    # ---------- config (read live so UI edits take effect) ----------
    @property
    def _host(self):
        url = self.cfg["Main"].get("ollama_host", "http://localhost:11434/v1/chat/completions")
        # strip the OpenAI-compatible suffix to get the native base URL
        return url.split("/v1/")[0].rstrip("/")

    @property
    def _vbs(self):
        return (self.cfg["Main"].get("ollama_vbs", r"D:\Ollama\start-serve.vbs") or "").strip()

    @property
    def _exe(self):
        return (self.cfg["Main"].get("ollama_exe", r"D:\Ollama\ollama.exe") or "").strip()

    @property
    def _idle_sec(self):
        try:
            return int(self.cfg["Main"].get("ollama_idle_sec", 600))
        except Exception:
            return 600

    def _vbs_env(self):
        """Read the env(iable)s declared in the launcher vbs (single source)."""
        env = {}
        try:
            if not os.path.exists(self._vbs):
                return env
            with open(self._vbs, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            for name, val in re.findall(r'env\("([^"]+)"\)\s*=\s*"([^"]*)"', text):
                env[name] = val
        except Exception as e:
            dlog(f"Ollama: could not read vbs env: {e}")
        return env

    def _find_exe(self):
        """Locate the ollama executable: config, PATH, then standard installs."""
        candidates = [self._exe]
        try:
            found = shutil.which("ollama")
            if found:
                candidates.append(found)
        except Exception:
            pass
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            candidates.append(os.path.join(local, "Programs", "Ollama", "ollama.exe"))
        candidates.append(os.path.join(os.environ.get("PROGRAMFILES", ""), "Ollama", "ollama.exe"))
        for path in candidates:
            if path and os.path.exists(path):
                return path
        return ""

    def _launch(self):
        """Spawn `ollama serve`. Prefer the real exe (with env) over the vbs."""
        env = dict(os.environ)
        env.update(self._vbs_env())
        exe = self._find_exe()
        if exe:
            dlog(f"Ollama: launching {exe} serve")
            self._proc = subprocess.Popen(
                [exe, "serve"], env=env,
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.owned = True
            return True
        if os.path.exists(self._vbs):
            dlog(f"Ollama: exe missing, launching {self._vbs}")
            subprocess.Popen(
                ["wscript.exe", self._vbs],
                creationflags=CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )
            self.owned = True
            return True
        dlog("Ollama: no launcher found (ollama_exe / ollama_vbs missing)")
        return False

    # ---------- probing ----------
    def is_running(self):
        try:
            urllib.request.urlopen(self._host + "/api/tags", timeout=1)
            return True
        except Exception:
            return False

    # ---------- lifecycle ----------
    def _cancel_timer(self):
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def start(self, timeout=90):
        """Start the server if needed. Returns True when it is up."""
        with self._lock:
            if self.is_running():
                return True
            try:
                if not self._launch():
                    return False
            except Exception as e:
                dlog(f"Ollama start failed: {e}")
                return False

        deadline = time.time() + timeout
        while time.time() < deadline:
            if self.is_running():
                dlog("Ollama: server is up")
                self.touch()
                return True
            time.sleep(0.5)
        dlog("Ollama: timed out waiting for server")
        return False

    def ensure_running(self):
        """Called before a local request: start if stopped, else reset idle."""
        if self.is_running():
            self.touch()
            return True
        ok = self.start()
        if ok:
            self.touch()
        return ok

    def touch(self):
        """Reset the idle timer (only meaningful when we own the server)."""
        if not self.owned or self._idle_sec <= 0:
            return
        with self._lock:
            self._cancel_timer()
            self._timer = threading.Timer(self._idle_sec, self._idle_stop)
            self._timer.daemon = True
            self._timer.start()

    def _idle_stop(self):
        dlog(f"Ollama: idle for {self._idle_sec}s -> stopping")
        self.stop()

    def stop(self, wait=8):
        """Stop the server, but only if this app started it."""
        with self._lock:
            self._cancel_timer()
            if not self.owned:
                return False
            self.owned = False
            proc = self._proc
            self._proc = None

        # Prefer the exact process we spawned.
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=wait)
                dlog("Ollama: stopped (owned process)")
                return True
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass

        import psutil
        targets = []
        for p in psutil.process_iter(["name", "cmdline"]):
            try:
                name = (p.info.get("name") or "").lower()
                cmd = " ".join(p.info.get("cmdline") or []).lower()
                if name == "ollama.exe" and "serve" in cmd:
                    targets.append(p)
            except Exception:
                pass

        for p in targets:
            try:
                p.terminate()
            except Exception:
                pass

        deadline = time.time() + wait
        for p in targets:
            try:
                p.wait(timeout=max(0.1, deadline - time.time()))
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

        dlog(f"Ollama: stopped ({len(targets)} process(es))")
        return bool(targets)

    def shutdown(self):
        """Best-effort stop on application quit."""
        try:
            self.stop()
        except Exception:
            pass
