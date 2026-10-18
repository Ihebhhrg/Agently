import json
import re
import threading

from core.control import ACTION_PERMISSION, DESTRUCTIVE
from core import intent
from core.memory import Memory

CHAT_SYSTEM = (
    "You are Agently, a helpful assistant on the user's Windows PC. "
    "Answer general questions accurately and clearly on any topic - science, "
    "history, coding, cooking, health, writing, current events. "
    "Be concise but complete: prefer a few well-organised paragraphs or a "
    "short list over a wall of text. "
    "Use markdown formatting (bold, bullet points, short code blocks) since "
    "your reply is shown in a chat bubble on screen. "
    "If you are unsure, say so plainly instead of inventing facts. "
    "If the user clearly wants you to control the computer (open an app, run "
    "a command, change a setting), briefly say what you would do and suggest "
    "they phrase it as a command - the command engine handles those. "
    "Never answer with raw JSON."
)


SYSTEM = (
    "You are a Windows desktop voice assistant that both chats and controls the PC. "
    "You CAN control this computer: open and close apps, manage windows, work with files and "
    "folders, use the clipboard, take screenshots, set timers and reminders, change system "
    "settings, run commands, and control power (shut down, restart, sleep, log off). "
    "Never tell the user you lack permission - just do what they asked. If something is truly "
    "impossible, briefly say what you can do instead. "
    "You ALWAYS reply with a single JSON object. Never write anything before or after the JSON."
)

_CHEATSHEET = """EXAMPLES (follow this exactly, do not copy the words, follow the pattern):
User: hello                                     -> {"action":"chat","reply":"Hi! How can I help you?"}
User: what's on my screen                       -> {"action":"chat","reply":"<describe the screen in one sentence>"}
User: open notepad                              -> {"action":"open","target":"notepad"}
User: open youtube                              -> {"action":"open","target":"youtube.com"}
User: search for italian recipes                -> {"action":"search","query":"italian recipes"}
User: type hello world                          -> {"action":"type","text":"hello world"}
User: press ctrl s                              -> {"action":"hotkey","keys":["ctrl","s"]}
User: turn the volume up                        -> {"action":"volume","level":"up"}
User: scroll down                               -> {"action":"scroll","amount":-5}
User: minimize this                             -> {"action":"window","do":"minimize"}
User: lock my pc                                -> {"action":"lock"}
User: close chrome                              -> {"action":"close_app","name":"chrome"}
User: switch to notepad                         -> {"action":"focus_app","name":"notepad"}
User: show the desktop                          -> {"action":"show_desktop"}
User: what windows are open                     -> {"action":"list_windows"}
User: open my downloads folder                  -> {"action":"open_path","path":"downloads"}
User: make a folder called notes on my desktop  -> {"action":"mkdir","path":"desktop/notes"}
User: move report.pdf to documents              -> {"action":"move_file","src":"downloads/report.pdf","dst":"documents"}
User: copy report.pdf to the desktop            -> {"action":"copy","src":"downloads/report.pdf","dst":"desktop"}
User: delete the file test.txt                  -> {"action":"delete","path":"downloads/test.txt"}
User: copy hello to the clipboard               -> {"action":"clip_set","text":"hello"}
User: what's in my clipboard                    -> {"action":"clip_get"}
User: take a screenshot                         -> {"action":"screenshot"}
User: set a timer for 5 minutes                 -> {"action":"timer","seconds":300,"label":"timer"}
User: remind me in 10 minutes to stretch        -> {"action":"reminder","minutes":10,"text":"stretch"}
User: cancel my timers                          -> {"action":"cancel_timers"}
User: what timers do I have                     -> {"action":"list_timers"}
User: shut down my pc                           -> {"action":"shutdown"}
User: restart my computer                       -> {"action":"restart"}
User: put my pc to sleep                        -> {"action":"sleep"}
User: log me off                                -> {"action":"logoff"}
User: run ipconfig                              -> {"action":"run","command":"ipconfig","kind":"cmd"}
User: set brightness to 50                      -> {"action":"brightness","level":50}
User: turn off wifi                             -> {"action":"wifi","on":false}
User: turn on bluetooth                         -> {"action":"bluetooth","on":true}
User: enable dark mode                          -> {"action":"dark_mode","on":true}

FIELD RULES:
- "action" must be one of: chat, open, search, type, key, hotkey, click, move, scroll, volume, media, window, lock, close_app, focus_app, show_desktop, list_windows, open_path, mkdir, move_file, copy, delete, clip_get, clip_set, screenshot, timer, reminder, cancel_timers, list_timers, shutdown, restart, sleep, logoff, run, brightness, wifi, bluetooth, dark_mode.
- Use "chat" whenever the user is only talking or asking something (not asking you to control the PC).
- "volume" level is one of: up, down, mute.
- "window" do is one of: minimize, maximize, close, switch.
- "click" needs integer x and y pixel coordinates taken from the current screen image.
- File paths may use the aliases: desktop, downloads, documents, pictures, music, videos.
- "timer" uses seconds; "reminder" uses minutes.
- Output valid JSON with double quotes. No comments, no code fences.
"""

_VALID = {"chat", "open", "search", "type", "key", "hotkey", "click",
          "move", "scroll", "volume", "media", "window", "lock",
          "close_app", "focus_app", "show_desktop", "list_windows",
          "open_path", "mkdir", "move_file", "copy", "delete",
          "clip_get", "clip_set", "screenshot",
          "timer", "reminder", "cancel_timers", "list_timers",
          "shutdown", "restart", "sleep", "logoff", "run",
          "brightness", "wifi", "bluetooth", "dark_mode"}


def _extract_json(text: str):
    if not text:
        return None
    text = re.sub(r"```(?:json)?", "", text).strip()
    start = text.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(text)):
            if text[i] == "{":
                depth += 1
            elif text[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(text[start:i + 1])
                    except Exception:
                        break
        start = text.find("{", start + 1)
    return None


def _is_error(text):
    """Our client returns 'Error 401: ...' style strings on failure."""
    return bool(re.match(r"^\s*Error\b", text or "", re.I))


def _looks_valid(data: dict) -> bool:
    if not isinstance(data, dict):
        return False
    action = str(data.get("action", "")).lower()
    if action not in _VALID:
        return False
    # guard against placeholder leakage
    for v in data.values():
        if isinstance(v, str) and ("|" in v and "<" not in v and len(v.split("|")) > 1):
            if action not in ("chat",):
                return False
    return True


class Agent:
    def __init__(self, cfg, ollama, control, capture):
        self.cfg = cfg
        self.ollama = ollama
        self.control = control
        self.capture = capture
        self.confirm = cfg["Main"].getboolean("pc_control_confirm", True)

        # chat extras -------------------------------------------------------
        self.memory = Memory(turns=int(cfg["Main"].get("memory_turns", "6") or 6))
        self.chat_max_tokens = int(cfg["Main"].get("chat_max_tokens", "1600") or 1600)
        self.chat_temperature = float(cfg["Main"].get("chat_temperature", "0.7") or 0.7)
        self.skip_screenshot = cfg["Main"].getboolean("chat_skip_screenshot", True)
        self.stats = {"chat": 0, "pc": 0, "routed": 0, "fallbacks": 0}
        self._bad_providers = set()
        self._chat_client = None
        self._chat_provider = None
        self._lock = threading.Lock()

    # ---------- chat routing ----------
    def _has_key(self, provider):
        from core.providers import get as getp, key_name
        preset = getp(provider)
        if not preset["needs_key"]:
            return True
        return bool((self.cfg["Main"].get(key_name(provider), "") or "").strip())

    def pick_chat_provider(self):
        """Which provider answers general questions.

        "auto" only routes when a *better* option exists: a different cloud
        provider that already has a key. It never downgrades questions to the
        small local model just because it is free - local stays on commands.
        A provider that errored is skipped for the rest of the session.
        """
        want = (self.cfg["Main"].get("chat_provider", "auto") or "auto").strip().lower()
        current = (self.cfg["Main"].get("provider", "gemini") or "gemini").strip().lower()
        if want in ("same", "current", ""):
            return current
        if want != "auto":
            return want
        for candidate in ("gemini", "openrouter"):
            if candidate == current or candidate in self._bad_providers:
                continue
            if self._has_key(candidate):
                return candidate
        # No stronger model configured -> stay on the current one.
        return current

    def chat_client(self):
        provider = self.pick_chat_provider()
        current = (self.cfg["Main"].get("provider", "") or "").strip().lower()
        with self._lock:
            if self._chat_client is None or self._chat_provider != provider:
                if provider == current:
                    self._chat_client = self.ollama
                else:
                    from core.ollama import OllamaClient
                    try:
                        self._chat_client = OllamaClient(
                            self.cfg,
                            service=getattr(self.ollama, "service", None),
                            provider_override=provider,
                        )
                    except Exception:
                        self._chat_client = self.ollama
                self._chat_provider = provider
            return self._chat_client

    def clear_memory(self):
        self.memory.clear()

    # ---- decision (no side effects) ----
    def decide(self, text, img=None, active_info=None):
        """Route a message: general question, or a PC command."""
        text = (text or "").strip()
        if not text:
            return {"action": None, "reply": ""}

        kind = intent.classify(text)

        # A plain question: no screenshot, no JSON contract, possibly a
        # different (stronger) model.
        if kind == "chat" and self.skip_screenshot:
            return self._answer(text)

        # Anything else may need to see the screen.
        if img is None and self.capture:
            try:
                img = self.capture.capture_active()
            except Exception:
                img = None
        return self._run_command(text, img, active_info)

    # ---- general question ----
    def _answer(self, text):
        self.memory.add("user", text, kind="chat")
        current = (self.cfg["Main"].get("provider", "") or "").strip().lower()

        client = self.chat_client()
        routed = getattr(client, "provider", current) != current
        history = self.memory.recent_as_messages(limit=8)
        reply = self._ask(client, text, history)

        # If the routed model is broken (bad key, model gone), remember that
        # and answer with the working provider instead.
        if _is_error(reply) and routed:
            self._bad_providers.add(getattr(client, "provider", ""))
            self._chat_client = None
            self._chat_provider = None
            self.stats["fallbacks"] += 1
            client = self.chat_client()
            routed = False
            reply = self._ask(client, text, history)

        reply = (reply or "").strip() or "I didn't get an answer for that."
        self.memory.add("assistant", reply, kind="chat")
        self.stats["chat"] += 1
        if routed:
            self.stats["routed"] += 1
        return {"action": None, "reply": reply, "kind": "chat"}

    def _ask(self, client, text, history):
        try:
            return client.query(
                text,
                None,
                CHAT_SYSTEM,
                history=history,
                max_tokens=self.chat_max_tokens,
                temperature=self.chat_temperature,
            )
        except Exception as e:
            return f"Error: {e}"

    # ---- PC command ----
    def _run_command(self, text, img=None, active_info=None):
        info = active_info or {"app": "unknown", "title": "unknown"}
        prompt = (
            f'The user said: "{text}"\n'
            f"Active app: {info.get('app')} | Window title: {info.get('title')}\n"
            + ("A screenshot of the screen is attached.\n\n" if img else "")
            + "Reply with ONE JSON object following the EXAMPLES.\n\n"
            f"{_CHEATSHEET}"
        )

        raw = self.ollama.query(prompt, img, SYSTEM)
        data = _extract_json(raw)

        if not data or not _looks_valid(data):
            raw = self.ollama.query(
                prompt + "\nRemember: output ONLY a single JSON object now.",
                img, SYSTEM
            )
            data = _extract_json(raw)

        if not data or not _looks_valid(data):
            reply = self._clean(raw) or "Okay."
            self._remember(text, reply)
            return {"action": None, "reply": reply}

        action = str(data.get("action", "chat")).lower()
        if action == "chat":
            reply = data.get("reply") or "Okay."
            self._remember(text, reply)
            return {"action": None, "reply": reply}
        self._remember(text, data.get("reply") or "")
        self.stats["pc"] += 1
        return {"action": data, "reply": data.get("reply") or ""}

    def _remember(self, user_text, reply):
        self.memory.add("user", user_text, kind="pc")
        if reply:
            self.memory.add("assistant", reply, kind="pc")

    # ---- execution ----
    def execute_action(self, data):
        """Run an action dict. Returns (reply_text, action_message)."""
        result = self.control.execute(data)
        msg = result.get("message", "")
        reply = data.get("reply") or (msg if result.get("ok") else f"Sorry, {msg}")
        return (reply, msg)

    def needs_confirm(self, data):
        if not self.confirm:
            return False
        return str((data or {}).get("action", "")).lower() in DESTRUCTIVE

    def permission_flag(self, data):
        return ACTION_PERMISSION.get(str((data or {}).get("action", "")).lower())

    # ---- backwards-compatible one-shot ----
    def handle(self, text, img=None, active_info=None):
        """Decide and execute in one go. Returns (reply_text, action_message)."""
        d = self.decide(text, img, active_info)
        if not d["action"]:
            return (d["reply"], "")
        return self.execute_action(d["action"])

    def _clean(self, raw):
        if not raw:
            return ""
        raw = re.sub(r"```(?:json)?", "", raw).strip()
        return raw
