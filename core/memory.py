"""Short-term conversation memory.

Keeps the last few user/assistant exchanges so follow-up questions work
("tell me more", "in Spanish", "what about the other one?"). Nothing is
written to disk - it lives for the session only, and can be cleared.
"""

import threading
import time


class Memory:
    def __init__(self, turns=6, max_chars=6000):
        self.turns = max(0, int(turns))
        self.max_chars = max_chars
        self._items = []          # list of (role, text, ts)
        self._lock = threading.Lock()
        self._seq = 0

    def clear(self):
        with self._lock:
            self._items = []

    def add(self, role, text, kind="chat"):
        text = (text or "").strip()
        if not text:
            return
        with self._lock:
            self._items.append({
                "role": role, "text": text, "kind": kind,
                "ts": time.time(), "seq": self._seq,
            })
            self._seq += 1
            self._trim()

    def _trim(self):
        # Keep only the most recent N entries.
        if self.turns <= 0:
            self._items = []
            return
        if len(self._items) > self.turns * 2:
            self._items = self._items[-self.turns * 2:]
        # Keep the total size bounded too.
        total = 0
        while self._items and total > self.max_chars:
            total -= len(self._items[0]["text"])
            self._items.pop(0)

    def recent(self, limit=None):
        """Return [{'role','text'}] for the previous turns, oldest first."""
        n = self.turns * 2 if limit is None else limit
        with self._lock:
            return [{"role": i["role"], "text": i["text"]} for i in self._items[-n:]]

    def recent_as_messages(self, limit=None):
        """Previous turns formatted as OpenAI-style messages."""
        return [{"role": m["role"], "content": m["text"]}
                for m in self.recent(limit)]

    def last_user_text(self):
        with self._lock:
            for i in reversed(self._items):
                if i["role"] == "user":
                    return i["text"]
            return ""

    def size(self):
        with self._lock:
            return len(self._items)

    def summary(self):
        n = self.size()
        return f"{n} remembered message(s)" if n else "empty"