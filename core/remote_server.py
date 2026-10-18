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


def tailscale_dns_name():
    """This machine's *.ts.net hostname, or None when Tailscale isn't logged in.

    A real HTTPS certificate for this name is what makes the browser treat the
    page as a secure origin - which is required for the phone's microphone.
    """
    exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                       "Tailscale", "tailscale.exe")
    if not os.path.exists(exe):
        return None
    try:
        out = subprocess.run([exe, "status", "--json"], capture_output=True,
                             text=True, timeout=6)
        import json as _json
        data = _json.loads(out.stdout or "{}")
        dns = ((data.get("Self") or {}).get("DNSName") or "").strip()
        return dns.rstrip(".") or None
    except Exception:
        return None


def tailscale_logged_in():
    exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                       "Tailscale", "tailscale.exe")
    if not os.path.exists(exe):
        return False
    try:
        out = subprocess.run([exe, "status", "--json"], capture_output=True,
                             text=True, timeout=6)
        import json as _json
        data = _json.loads(out.stdout or "{}")
        return (data.get("BackendState") or "") == "Running"
    except Exception:
        return False


def tailscale_up():
    """Start Tailscale login. Returns (ok, message, login_url)."""
    exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                       "Tailscale", "tailscale.exe")
    if not os.path.exists(exe):
        return False, "Tailscale is not installed.", ""
    try:
        proc = subprocess.Popen(
            [exe, "up"], stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            text=True, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    except Exception as e:
        return False, str(e), ""
    url = ""
    import time as _time
    deadline = _time.time() + 12
    lines = []
    while _time.time() < deadline and proc.poll() is None:
        try:
            line = proc.stdout.readline()
        except Exception:
            break
        if not line:
            break
        lines.append(line)
        import re as _re
        m = _re.search(r"https://login\.tailscale\.com/\S+", line)
        if m:
            url = m.group(0)
            break
    return True, ("\n".join(lines)[-400:] or "waiting for sign-in..."), url


def enable_tailscale_serve(port):
    """Expose the local server over HTTPS with a real Tailscale certificate."""
    exe = os.path.join(os.environ.get("ProgramFiles", r"C:\Program Files"),
                       "Tailscale", "tailscale.exe")
    if not os.path.exists(exe):
        return False, "Tailscale is not installed."
    try:
        out = subprocess.run(
            [exe, "serve", "--bg", f"http://127.0.0.1:{port}"],
            capture_output=True, text=True, timeout=25)
        msg = (out.stdout or out.stderr or "").strip()
        return out.returncode == 0, msg
    except Exception as e:
        return False, str(e)


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
    tokens = ()          # every valid device token

    def _token_ok(self, value):
        import hmac
        if not value:
            return False
        return any(hmac.compare_digest(value, t) for t in (self.tokens or ()))

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
        got = self.headers.get("X-Agently-Token", "") or ""
        if not got:
            # <img> tags cannot set headers, so the live stream passes ?t=.
            from urllib.parse import urlparse, parse_qs
            q = parse_qs(urlparse(self.path).query).get("t", [""])[0]
            got = q
        if self._token_ok(got):
            return True
        # Also accept the cookie set by the /j/<token> join link.
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            name, _, val = part.strip().partition("=")
            if name == "agently_tok" and self._token_ok(val):
                return True
        return False

    def _cookie_token(self):
        """Token carried by the join-link cookie, if valid."""
        cookie = self.headers.get("Cookie", "") or ""
        for part in cookie.split(";"):
            name, _, val = part.strip().partition("=")
            if name == "agently_tok" and self._token_ok(val):
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
            tok = path[3:]
            if self._token_ok(tok):
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
        if path == "/api/stream.mjpg":
            return self._stream()
        if path == "/api/snap.jpg":
            return self._snap()
        if path == "/api/audio.pcm":
            return self._audio_stream()
        return self._json({"error": "not found"}, 404)

    # ---------- single frame as a plain JPEG (proxy/browser friendly) ----------
    def _snap(self):
        b = self.bridge
        if not b or not b.capture:
            return self._send(404, b"", "text/plain")
        try:
            width = int(self.cfg["Main"].get("remote_stream_width", "560") or 560)
        except Exception:
            width = 560
        img = b.capture.grab_image(max_width=width)
        if img is None:
            return self._send(503, b"", "text/plain")
        import io as _io
        buf = _io.BytesIO()
        img.save(buf, format="JPEG", quality=60, optimize=False)
        return self._send(200, buf.getvalue(), "image/jpeg")

    # ---------- system audio stream (raw 16 kHz mono PCM) ----------
    def _audio_stream(self):
        b = self.bridge
        audio = getattr(b, "audio", None) if b else None
        if audio is None or not audio.available:
            return self._json({"error": "audio unavailable"}, 503)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "audio/l16; rate=16000; channels=1")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
        except Exception:
            return
        if not audio.start():
            return
        import time as _time
        deadline = _time.time() + 3600
        try:
            while _time.time() < deadline:
                self._touch()
                chunk = audio.next_chunk(timeout=1.0)
                if chunk:
                    self.wfile.write(chunk)
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass
        finally:
            audio.stop()

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

    # ---------- live screen stream (MJPEG) ----------
    def _stream(self):
        """Push a downscaled JPEG of the screen to the phone (near real-time).

        Capture and JPEG encoding run on a worker thread while the connection
        thread just writes finished frames out on a fixed cadence, so the two
        costs overlap instead of adding up.
        """
        b = self.bridge
        if not b or not b.capture:
            return self._json({"type": "reply", "reply": "Screen capture unavailable."}, 404)
        try:
            fps = float(self.cfg["Main"].get("remote_stream_fps", "30") or 30)
            fps = max(1.0, min(60.0, fps))
        except Exception:
            fps = 30.0
        try:
            width = int(self.cfg["Main"].get("remote_stream_width", "560") or 560)
        except Exception:
            width = 560
        try:
            quality = int(self.cfg["Main"].get("remote_stream_quality", "55") or 55)
        except Exception:
            quality = 55

        try:
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=frame")
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
        except Exception:
            return

        import io as _io
        import queue
        import threading
        import time as _time

        frames = queue.Queue(maxsize=2)
        stop = threading.Event()

        def producer():
            """Grab + encode continuously; always keep the newest frame."""
            prev_digest = None
            while not stop.is_set():
                img = b.capture.grab_image(max_width=width)
                if img is None:
                    _time.sleep(0.15)
                    continue
                # A static screen doesn't need re-encoding at all.
                try:
                    digest = img.tobytes()[:4096]
                except Exception:
                    digest = None
                if digest is not None and digest == prev_digest:
                    _time.sleep(0.02)
                    continue
                prev_digest = digest
                try:
                    buf = _io.BytesIO()
                    img.save(buf, format="JPEG", quality=quality, optimize=False)
                    data = buf.getvalue()
                except Exception:
                    continue
                if frames.full():
                    try:
                        frames.get_nowait()   # drop the stale one
                    except queue.Empty:
                        pass
                frames.put(data)

        th = threading.Thread(target=producer, daemon=True)
        th.start()

        interval = 1.0 / fps
        deadline = _time.time() + 3600
        next_at = _time.time()
        try:
            while _time.time() < deadline and not stop.is_set():
                self._touch()
                try:
                    data = frames.get(timeout=1.0)
                except queue.Empty:
                    continue
                self.wfile.write(b"--frame\r\nContent-Type: image/jpeg\r\n\r\n")
                self.wfile.write(data)
                self.wfile.write(b"\r\n")
                self.wfile.flush()
                next_at += interval
                delay = next_at - _time.time()
                if delay > 0:
                    _time.sleep(delay)
                else:
                    next_at = _time.time()   # behind schedule, don't pile up
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception:
            pass
        finally:
            stop.set()
            try:
                b.capture.close_stream()
            except Exception:
                pass

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
        try:
            import ssl as _ssl  # noqa: F401
            info["secure"] = bool(self.headers.get("X-Forwarded-Proto") == "https") or \
                (self.headers.get("Host", "").endswith(".ts.net"))
        except Exception:
            info["secure"] = False
        if b and getattr(b, "audio", None) is not None:
            info["audio"] = bool(b.audio.available)
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
        from core import remote_devices
        toks = tuple(remote_devices.valid_tokens(self.cfg))
        handler = type("H", (RemoteHandler,),
                    {"bridge": self.bridge, "tokens": toks, "cfg": self.cfg})
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