import json
import re

from core.control import ACTION_PERMISSION, DESTRUCTIVE


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

    # ---- decision (no side effects) ----
    def decide(self, text, img=None, active_info=None):
        """Ask the model what to do. Returns {'action': dict|None, 'reply': str}."""
        info = active_info or {"app": "unknown", "title": "unknown"}
        if img is None and self.capture:
            img = self.capture.capture_active()

        prompt = (
            f'The user said: "{text}"\n'
            f"Active app: {info.get('app')} | Window title: {info.get('title')}\n"
            f"A screenshot of the screen is attached.\n\n"
            f"Reply with ONE JSON object following the EXAMPLES.\n\n"
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
            return {"action": None, "reply": self._clean(raw) or "Okay."}

        action = str(data.get("action", "chat")).lower()
        if action == "chat":
            return {"action": None, "reply": data.get("reply") or "Okay."}
        return {"action": data, "reply": data.get("reply") or ""}

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
