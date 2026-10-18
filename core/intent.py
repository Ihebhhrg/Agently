"""Fast, local intent detection.

Works out whether a message is a general question, a question about what is
currently on screen, or a PC-control command - *before* we pay for a model
call or a screenshot. Everything here is plain string matching so it costs
microseconds and works offline.

The result is only a hint: the model still makes the final decision about the
action. A wrong guess is harmless (we just attached an unneeded screenshot),
so the classifier deliberately errs towards "pc" when it is unsure.
"""

import re

# Asking about what's on the screen - these genuinely need a screenshot.
SCREEN_WORDS = (
    "screen", "my screen", "this page", "this window", "this app",
    "what am i looking at", "what's on", "whats on", "read this",
    "look at", "read the screen", "on screen", "this image", "this picture",
    "this tab", "here on", "in the picture", "from this",
)

# Words that mean "do something to my computer".
PC_WORDS = (
    "open", "close", "launch", "run ", "execute", "type", "click", "scroll",
    "press", "presses", "pressing", "hit the", "shut down", "shutdown",
    "restart", "reboot", "sleep", "log off", "logoff", "sign out", "lock",
    "minimize", "maximize", "fullscreen", "full screen", "switch to",
    "focus", "close the tab", "play", "pause", "volume", "mute", "unmute",
    "louder", "quieter", "brightness", "wifi", "wi-fi", "bluetooth",
    "dark mode", "light mode", "screenshot", "snap a", "copy", "paste",
    "move ", "delete", "rename", "create", "make a", "make a folder",
    "empty", "trash", "download", "search for", "google", "install",
    "uninstall", "timer", "remind", "reminder", "schedule", "file",
    "folder", "document", "spreadsheet", "notepad", "taskbar", "desktop",
    "navigate", "go to", "click on", "select", "window",
)

# Question / general-knowledge shapes.
QUESTION_HINTS = (
    "what is", "what's", "what are", "who is", "who was", "when did",
    "when is", "where is", "why is", "why do", "why does", "how do",
    "how does", "how to", "how can", "which", "explain", "tell me about",
    "describe", "difference between", "summar", "translate", "write a",
    "write me", "poem", "story", "essay", "recipe", "suggest", "opinion",
    "mean", "definition", "pros and cons", "compare", "help me understand",
    "can you explain", "good morning", "good evening", "thanks", "thank you",
    "who are you", "what can you do", "tell me",
)

# Greetings / small talk that must never trigger a screenshot.
SMALLTALK = (
    "hi", "hello", "hey", "yo", "sup", "thanks", "thank you", "ok", "okay",
    "cool", "nice", "lol", "haha", "good morning", "good evening",
    "good night", "how are you", "bye", "see you", "goodbye",
)


def _has(text, words):
    return any(w in text for w in words)


def classify(text):
    """Return one of: "screen", "pc", "chat"."""
    t = " " + (text or "").strip().lower() + " "
    if not (text or "").strip():
        return "chat"

    # Explicitly about what's on screen.
    if _has(t, SCREEN_WORDS):
        return "screen"

    stripped = t.strip(" .?!,")
    if stripped in SMALLTALK:
        return "chat"

    # A question with no PC verb is a general question.
    is_question = bool(re.search(r"\b(what|who|when|where|why|which|how)\b", t)) or \
        _has(t, QUESTION_HINTS)
    if is_question and not _has(t, PC_WORDS):
        return "chat"

    # Ends with a question mark but has no PC verb -> also general.
    if t.strip().endswith("?") and not _has(t, PC_WORDS):
        return "chat"

    # Otherwise assume it wants to control the PC; the model decides for real.
    return "pc"


def is_chat(text):
    return classify(text) == "chat"


def needs_screen(text):
    return classify(text) == "screen"