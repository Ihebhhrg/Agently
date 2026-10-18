"""Tiny HTTP server so a phone on the same Tailscale tailnet can control the PC.

Design notes:
- Binds to the machine's Tailscale IP by default (never 0.0.0.0), so the
  server is not reachable from the public internet. "auto" falls back to
  127.0.0.1 if Tailscale is not running.
- Every request except the login page must carry the access token. The token
  is DPAPI-encrypted at rest in config.ini via utils.secretstore.
- Keeps the PC awake only while a phone is actually connected.
"""
import json
import os
import re
import socket
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ui.remote_web import PAGE_HTML

MAX_BODY = 24 * 1024 * 1024  # generous enough for a short voice clip

_active_clients = 0
_clients_lock = threading.Lock()
_last_client_ts = 0.0


def _client_seen():
    global _active_clients, _last_client_ts
    with _clients_lock:
        _active_clients += 1
        _last_client_ts = time.time()


def _client_gone():
    global _active_clients
    with _clients_lock:
        _active_clients = max(0, _active_clients - 1)


def _someone_connected(since=15.0):
    return (time.time() - _last_client_ts) < since


# ---------- Tailscale ----------
def tailscale_ip():
    """Return this machine's Tailscale IPv4, or None if not available."""
    try:
        exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                           "Tailscale", "tailscale.exe")
        if not os.path.exists(exe):
            return None
        out = subprocess.run([exe, "ip", "-4"], capture_output=True, text=True, timeout=5)
        m = re.search(r"(\d+\.\d+\.\d+\.\d+)", out.stdout or "")
        if m:
            return m.group(1)
    except Exception:
        pass
    # Fallback: any non-loopback private IPv4 (covers Tailscale's 100.x range).
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 53))
        ip = s.getsockname()[0]
        s.close()
        if ip and not ip.startswith("127."):
            return ip
    except Exception:
        pass
    return None


def _server_ip(cfg):
    mode = (cfg["Main"].get("remote_bind", "auto") or "auto").strip().lower()
    if mode in ("localhost", "127.0.0.1", "loopback"):
        return "127.0.0.1"
    ts = tailscale_ip()
    if mode == "auto":
        return ts or "127.0.0.1"
    return mode  # explicit IP


# ---------- keep-awake, only while a phone is connected ----------
_awake_handle = {"on": False}


def _set_awake(on):
    if on == _awake_handle["on"]:
        return
    try:
        import ctypes
        ES_CONTINUOUS, ES_SYSTEM_REQUIRED = 0x80000000, 0x00000001
        ctypes.windll.kernel32.SetThreadExecutionState(
            ES_CONTINUOUS | ES_SYSTEM_REQUIRED if on else ES_CONTINUOUS)
    except Exception:
        pass
    _awake_handle["on"] = on


class RemoteHandler(BaseHTTPRequestHandler):
    server_version = "Agently"
    sys_version = ""
    bridge = None
    token = ""

    def log_message(self, fmt, *args):
        pass

    # ---------- helpers ----------
    def _send(self, code, body=b"", ctype="application/json"):
        if isinstance(body, str):
            body = body.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        try:
            self.wfile.write(body)
        except Exception:
            pass

    def _json(self, obj, code=200):
        self._send(code, json.dumps(obj))

    def _authed(self):
        import hmac
        if not self.token:
            return False
        got = self.headers.get("X-Agently-Token", "") or ""
        if got and hmac.compare_digest(got, self.token):
            return True
        # Also accept the cookie set by the /j/<token> join link.
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            name, _, val = part.strip().partition("=")
            if name == "agently_tok" and hmac.compare_digest(val, self.token):
                return True
        return False

    def _cookie_token(self):
        """Token carried by the join-link cookie, if valid."""
        import hmac
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            name, _, val = part.strip().partition("=")
            if name == "agently_tok" and self.token and hmac.compare_digest(val, self.token):
                return val
        return ""

    def _send_html(self, html, extra_headers=None):
        if isinstance(html, str):
            html = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(html)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        for k, v in (extra_headers or []):
            self.send_header(k, v)
        self.end_headers()
        try:
            self.wfile.write(html)
        except Exception:
            pass

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except Exception:
            return {}
        if n <= 0 or n > MAX_BODY:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode("utf-8"))
        except Exception:
            return {}

    def _touch(self):
        global _last_client_ts
        _last_client_ts = time.time()
        if self.bridge:
            self.bridge.touch()

    # ---------- routes ----------
    def do_GET(self):
        path = self.path.split("?")[0]

        # Join link: /j/<token> -> serve the app already signed in.
        # The token is injected straight into the page AND stored in a cookie,
        # so sign-in works even if the browser refuses to keep cookies.
        if path.startswith("/j/") and len(path) > 3:
            import hmac
            tok = path[3:]
            if self.token and hmac.compare_digest(tok, self.token):
                self._touch()
                html = PAGE_HTML.replace(
                    "<script>",
                    f'<script>window.__AGENTLY_TOKEN__ = "{tok}";</script><script>', 1)
                return self._send_html(html, extra_headers=[
                    ("Set-Cookie",
                     f"agently_tok={tok}; Path=/; Max-Age=31536000; SameSite=Lax"),
                ])
            return self._json({"error": "bad token"}, 401)

        if path in ("/", "/index.html"):
            tok = self._cookie_token()
            html = PAGE_HTML
            if tok:
                # Hand the token straight to the page so it needs no typing.
                html = html.replace(
                    "<script>",
                    f'<script>window.__AGENTLY_TOKEN__ = "{tok}";</script><script>', 1)
            return self._send_html(html)

        if path == "/icon.png":
            return self._icon()
        if not self._authed():
            return self._json({"error": "unauthorized"}, 401)
        if path == "/api/status":
            return self._status()
        if path == "/api/screenshot":
            return self._screenshot()
        return self._json({"error": "not found"}, 404)

    def do_POST(self):
        path = self.path.split("?")[0]
        if not self._authed():
            return self._json({"error": "unauthorized"}, 401)
        body = self._body()
        self._touch()
        if path == "/api/command":
            return self._json(self.bridge.handle_text(body.get("text", "")))
        if path == "/api/voice":
            return self._voice(body)
        if path == "/api/confirm":
            ok = bool(body.get("approve"))
            return self._json(self.bridge.resolve(body.get("confirm_id", ""), ok))
        return self._json({"error": "not found"}, 404)

    # ---------- handlers ----------
    def _icon(self):
        import base64 as _b
        try:
            from utils import paths
            with open(paths.resource_path("app.ico"), "rb") as f:
                data = f.read()
            return self._send(200, data, "image/x-icon")
        except Exception:
            return self._send(404, b"", "text/plain")

    def _status(self):
        info = {"online": True, "timers": 0}
        b = self.bridge
        if b and b.timers:
            try:
                info["timers"] = len(b.timers.list_items())
            except Exception:
                pass
        if b and b.capture:
            try:
                info["window"] = b.capture.get_active_info().get("title", "")
            except Exception:
                pass
        return self._json(info)

    def _screenshot(self):
        b = self.bridge
        if not b or not b.capture:
            return self._json({"type": "reply", "reply": "Screenshots are unavailable."})
        try:
            path = b.capture.capture_full()
            from PIL import Image
            import base64 as _b, io as _io
            im = Image.open(path).convert("RGB")
            im.thumbnail((720, 720))
            buf = _io.BytesIO()
            im.save(buf, format="JPEG", quality=60)
            b64 = _b.b64encode(buf.getvalue()).decode()
            return self._json({"type": "shot", "image": b64, "text": "Here's your screen."})
        except Exception as e:
            return self._json({"type": "reply", "reply": "Screenshot failed: %s" % e})

    def _voice(self, body):
        b = self.bridge
        if not b:
            return self._json({"type": "reply", "reply": "Not ready."})
        text = (b.transcribe_audio(body.get("audio", ""), body.get("mime", "")) or "").strip()
        if not text:
            return self._json({"type": "error", "reply": "I didn't catch that - try again?"})
        result = b.handle_text(text)
        result["transcript"] = text
        return self._json(result)


class RemoteServer:
    def __init__(self, cfg, bridge, log=None):
        self.cfg = cfg
        self.bridge = bridge
        self._log = log or (lambda m: None)
        self.httpd = None
        self.thread = None
        self.ip = None

    def start(self):
        ip = _server_ip(self.cfg)
        port = int(self.cfg["Main"].get("remote_port", "8765") or 8765)
        handler = type("H", (RemoteHandler,),
                       {"bridge": self.bridge, "token": self.cfg["Main"].get("remote_token", "")})
        try:
            self.httpd = ThreadingHTTPServer((ip, port), handler)
        except Exception as e:
            self._log("Remote: could not start (%s on %s:%s)" % (e, ip, port))
            return False
        self.httpd.daemon_threads = True
        self.ip = ip
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self._log("Remote: listening on http://%s:%s" % (ip, port))
        self._start_awake_watch()
        return True

    def _start_awake_watch(self):
        keep = self.cfg["Main"].getboolean("remote_keep_awake", True)

        def watch():
            while True:
                time.sleep(5)
                if not keep:
                    continue
                _set_awake(_someone_connected())

        threading.Thread(target=watch, daemon=True).start()

    def stop(self):
        _set_awake(False)
        if self.httpd:
            try:
                self.httpd.shutdown()
            except Exception:
                pass
        self.httpd = None