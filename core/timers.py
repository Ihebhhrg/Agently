import threading
import time


class Timers:
    """In-memory timers and reminders. Fires with a notification callback."""

    def __init__(self, speak=None, notify=None):
        self.speak = speak
        self.notify = notify
        self._items = []
        self._lock = threading.Lock()
        self._counter = 0

    def _fire(self, item):
        with self._lock:
            if item not in self._items:
                return
            self._items.remove(item)
        text = item["text"] or item["label"]
        if self.notify:
            try:
                self.notify(text)
            except Exception:
                pass
        if self.speak:
            try:
                self.speak(text)
            except Exception:
                pass

    def add_timer(self, seconds, label="timer"):
        try:
            seconds = float(seconds)
        except (TypeError, ValueError):
            return None, "I need a number of seconds for the timer."
        if seconds <= 0:
            return None, "The timer length must be positive."
        return self._add(seconds, label, f"Time's up: {label}")

    def add_reminder(self, minutes, text):
        try:
            minutes = float(minutes)
        except (TypeError, ValueError):
            return None, "I need a number of minutes for the reminder."
        if minutes <= 0:
            return None, "The reminder time must be positive."
        text = (text or "reminder").strip()
        return self._add(minutes * 60.0, "reminder", f"Reminder: {text}")

    def _add(self, seconds, label, text):
        self._counter += 1
        item = {
            "id": self._counter,
            "label": label,
            "text": text,
            "due": time.time() + seconds,
            "timer": None,
        }
        t = threading.Timer(seconds, self._fire, args=(item,))
        t.daemon = True
        item["timer"] = t
        with self._lock:
            self._items.append(item)
        t.start()
        return item, None

    def cancel_all(self):
        with self._lock:
            items = list(self._items)
            self._items.clear()
        for it in items:
            try:
                it["timer"].cancel()
            except Exception:
                pass
        return len(items)

    def list_items(self):
        now = time.time()
        with self._lock:
            items = sorted(self._items, key=lambda i: i["due"])
        out = []
        for it in items:
            remaining = int(round(it["due"] - now))
            out.append((it["label"], it["text"], remaining))
        return out
