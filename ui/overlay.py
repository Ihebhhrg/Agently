import re
import subprocess

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QPushButton,
    QScrollArea, QFrame, QSizePolicy, QProgressBar, QMessageBox, QGraphicsOpacityEffect
)
from PySide6.QtCore import (
    Qt, QThread, Signal, QTimer, QSize, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
)
from PySide6.QtGui import QFont, QIcon

from ui.theme import BUBBLE_STYLESHEET
from utils import paths
from utils.debuglog import dlog


class Worker(QThread):
    done = Signal(object)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            self.done.emit(self.fn(*self.args, **self.kwargs))
        except Exception as e:
            self.done.emit(f"Error: {e}")


class Bubble(QLabel):
    def __init__(self, text, who):
        super().__init__(text)
        self.setWordWrap(True)
        self.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.setObjectName("UserBubble" if who == "user" else "BotBubble")
        self.setMaximumWidth(280)
        self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)


class MiniButton(QLabel):
    """Small floating button shown when the bubble is collapsed. Click to expand,
    drag to move it around the screen."""

    clicked = Signal()

    def __init__(self, text="🎙", parent=None):
        super().__init__(text, parent)
        self.setAlignment(Qt.AlignCenter)
        self.setObjectName("MiniBtn")
        self.setCursor(Qt.PointingHandCursor)
        self._press = None
        self._moved = False
        self._win = None

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._press = e.globalPosition().toPoint()
            self._win = self.window().pos()
            self._moved = False

    def mouseMoveEvent(self, e):
        if self._press is None or not (e.buttons() & Qt.LeftButton):
            return
        pos = e.globalPosition().toPoint()
        delta = pos - self._press
        if delta.manhattanLength() > 4:
            self._moved = True
        if self._moved and self._win is not None:
            self.window().move(self._win + delta)

    def mouseReleaseEvent(self, e):
        if not self._moved:
            self.clicked.emit()
        self._press = None
        self._moved = False


class VoiceOverlay(QWidget):
    utterance_signal = Signal(object, int)
    level_signal = Signal(float, float, bool)
    error_signal = Signal(str)

    def __init__(self, cfg):
        super().__init__()
        self.cfg = cfg
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setWindowTitle("Agently")
        self.setWindowIcon(QIcon(paths.resource_path("app.ico")))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.resize(420, 320)
        self.move(60, 60)

        self._drag_pos = None
        self.worker = None
        self._workers = []
        self._busy = False
        self.log_cb = None
        self._warned = False
        # pending destructive action awaiting voice confirmation ("say yes")
        self._pending = None
        self._pending_desc = ""
        # collapse/expand animation state
        self._anim_grp = None
        self._opacity_eff = None

        # injected
        self.mic = None
        self.stt = None
        self.agent = None
        self.tts = None
        self.capture = None
        self.ocr = None
        self.region_sel = None

        self._build_ui()

        self.utterance_signal.connect(self._on_utterance)
        self.level_signal.connect(self._on_level)
        self.error_signal.connect(self._on_mic_error)

    # ---------- wiring ----------
    def set_components(self, region_sel, capture, ocr, ollama, control,
                       mic, stt, agent=None, tts=None, log=None):
        self.region_sel = region_sel
        self.capture = capture
        self.ocr = ocr
        self.mic = mic
        self.stt = stt
        self.agent = agent
        self.tts = tts
        self.log_cb = log
        if self.region_sel:
            self.region_sel.selected.connect(self._on_region_selected)

    def set_mode(self, mode):
        if self.mic:
            self.mic.set_mode(mode)
        self.cfg["Main"]["listen_mode"] = mode
        self._set_listening_ui(True)
        self._log(f"Listening mode: {'press-to-talk' if mode == 'ptt' else 'always listening'}")

    def _log(self, msg):
        if self.log_cb:
            try:
                self.log_cb(msg)
            except Exception:
                pass

    def _start_worker(self, fn, on_done):
        """Run fn in a QThread, keeping a reference so Qt never destroys a running thread."""
        w = Worker(fn)
        self._workers.append(w)
        self.worker = w

        def _cleanup():
            try:
                self._workers.remove(w)
            except ValueError:
                pass
            w.deleteLater()

        w.done.connect(on_done)
        w.finished.connect(_cleanup)
        w.start()
        return w

    # ---------- UI ----------
    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        self.card = QWidget(self)
        self.card.setObjectName("BubbleCard")
        card_lay = QVBoxLayout(self.card)
        card_lay.setContentsMargins(12, 8, 12, 10)
        card_lay.setSpacing(6)

        # header
        header = QHBoxLayout()
        self.dot = QLabel("●")
        self.dot.setObjectName("Dot")
        title = QLabel("Agently")
        title.setObjectName("BubbleTitle")
        header.addWidget(self.dot)
        header.addWidget(title)
        header.addStretch(1)
        self.btn_min = QPushButton("–")
        self.btn_min.setObjectName("IconBtn")
        self.btn_min.setFixedSize(20, 20)
        self.btn_min.setToolTip("Minimize to a small button")
        self.btn_min.clicked.connect(self.collapse)
        header.addWidget(self.btn_min)
        card_lay.addLayout(header)

        # chat scroll
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_host = QWidget()
        self.chat_host.setObjectName("ChatHost")
        self.chat_lay = QVBoxLayout(self.chat_host)
        self.chat_lay.setContentsMargins(2, 2, 2, 2)
        self.chat_lay.setSpacing(6)
        self.chat_lay.addStretch(1)
        self.scroll.setWidget(self.chat_host)
        card_lay.addWidget(self.scroll, stretch=1)

        # mic status + level
        self.mic_status = QLabel("🎙  Always listening")
        self.mic_status.setObjectName("MicStatus")
        card_lay.addWidget(self.mic_status)

        self.level = QProgressBar()
        self.level.setObjectName("LevelBar")
        self.level.setRange(0, 100)
        self.level.setValue(0)
        self.level.setTextVisible(False)
        self.level.setFixedHeight(6)
        card_lay.addWidget(self.level)

        # type row
        row = QHBoxLayout()
        row.setSpacing(6)
        self.input = QLineEdit()
        self.input.setObjectName("ChatInput")
        self.input.setPlaceholderText("Type a message…")
        self.input.returnPressed.connect(self._on_submit)
        row.addWidget(self.input, stretch=1)
        self.send_btn = QPushButton("➤")
        self.send_btn.setObjectName("SendBtn")
        self.send_btn.setFixedSize(38, 36)
        self.send_btn.clicked.connect(self._on_submit)
        row.addWidget(self.send_btn)
        card_lay.addLayout(row)

        # controls row
        ctl = QHBoxLayout()
        ctl.setSpacing(6)
        self.mute_btn = QPushButton("🎤  Talk")
        self.mute_btn.setObjectName("MuteBtn")
        self.mute_btn.clicked.connect(self.toggle_talk)
        ctl.addWidget(self.mute_btn)
        self.settings_btn = QPushButton("Mic settings")
        self.settings_btn.setObjectName("GhostBtn")
        self.settings_btn.clicked.connect(self.open_mic_settings)
        ctl.addWidget(self.settings_btn)
        card_lay.addLayout(ctl)

        outer.addWidget(self.card)

        self.mini = MiniButton("", self)
        self.mini.setObjectName("MiniBtn")
        self.mini.setFixedSize(14, 88)
        self.mini.setToolTip("Open Agently")
        self.mini.clicked.connect(self.expand)
        self.mini.hide()
        outer.addWidget(self.mini)

        self.collapsed = False
        self._expanded_size = None
        self._expanded_pos = None
        self.setStyleSheet(BUBBLE_STYLESHEET)

    # ---------- collapse / expand ----------
    ANIM_MS = 220

    def _anim_opacity(self):
        # lazy-created opacity effect used for the collapse/expand fade
        eff = getattr(self, "_opacity_eff", None)
        if eff is None:
            eff = QGraphicsOpacityEffect(self.card)
            self.card.setGraphicsEffect(eff)
            self._opacity_eff = eff
        return eff

    def _animate(self, from_size, to_size, from_op, to_op, on_done):
        # stop any running animation so repeated clicks don't fight
        if getattr(self, "_anim_grp", None) is not None:
            self._anim_grp.stop()
            self._anim_grp = None

        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)

        size_anim = QPropertyAnimation(self, b"size", self)
        size_anim.setDuration(self.ANIM_MS)
        size_anim.setStartValue(from_size)
        size_anim.setEndValue(to_size)
        size_anim.setEasingCurve(QEasingCurve.OutCubic)

        eff = self._anim_opacity()
        op_anim = QPropertyAnimation(eff, b"opacity", self)
        op_anim.setDuration(self.ANIM_MS)
        op_anim.setStartValue(from_op)
        op_anim.setEndValue(to_op)
        op_anim.setEasingCurve(QEasingCurve.OutCubic)

        grp = QParallelAnimationGroup(self)
        grp.addAnimation(size_anim)
        grp.addAnimation(op_anim)
        grp.finished.connect(on_done)
        self._anim_grp = grp
        grp.start()

    def collapse(self):
        if self.collapsed:
            return
        self.collapsed = True
        self._expanded_size = self.size()
        self._expanded_pos = self.pos()
        start_size = self.size()
        # fade the card out while shrinking into the mini button
        self._animate(start_size, QSize(14, 88), 1.0, 0.0, self._finish_collapse)

    def _finish_collapse(self):
        self._anim_grp = None
        self.card.hide()
        self.mini.show()
        self.setFixedSize(14, 88)
        if self._expanded_pos is not None:
            self.move(self._expanded_pos)
        eff = getattr(self, "_opacity_eff", None)
        if eff is not None:
            eff.setOpacity(1.0)

    def expand(self):
        if not self.collapsed:
            return
        self.collapsed = False
        self.mini.hide()
        self.card.show()
        self.card.updateGeometry()
        self.layout().activate()
        size = self._expanded_size or QSize(420, 320)
        if self._expanded_pos is not None:
            self.move(self._expanded_pos)
        self.show()
        self.raise_()
        self.activateWindow()
        # start small and faded, then grow into place
        eff = self._anim_opacity()
        eff.setOpacity(0.0)
        self.resize(QSize(14, 88))
        self._animate(QSize(14, 88), size, 0.0, 1.0, self._finish_expand)

    def _finish_expand(self):
        self._anim_grp = None
        eff = getattr(self, "_opacity_eff", None)
        if eff is not None:
            eff.setOpacity(1.0)
        self.show()
        self.raise_()
        self.activateWindow()

    def toggle_collapse(self):
        self.expand() if self.collapsed else self.collapse()

    # ---------- drag ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._drag_pos = e.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, e):
        if self._drag_pos and e.buttons() & Qt.LeftButton:
            self.move(e.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, e):
        self._drag_pos = None

    # ---------- always-on listening ----------
    def start_listening(self):
        if not self.mic:
            return
        self.mic.on_utterance = self.utterance_signal.emit
        self.mic.on_level = self.level_signal.emit
        self.mic.on_error = self.error_signal.emit
        self.mic.set_muted(False)
        self.mic.start()
        self._set_listening_ui(True)
        mode = getattr(self.mic, "mode", "ptt")
        self._log(f"🎤 Mic ready ({'press to talk' if mode == 'ptt' else 'always listening'})")

    def toggle_talk(self):
        if not self.mic:
            return
        mode = getattr(self.mic, "mode", "ptt")
        if mode == "auto":
            return self.toggle_mute()
        if not self.mic.recording:
            self.mic.start_recording()
            self._set_recording_ui(True)
            self._log("🔴 Recording… press again to stop.")
        else:
            self.mic.stop_recording()
            self._set_recording_ui(False)
            self._log("⏳ Processing…")

    def toggle_mute(self):
        if not self.mic:
            return
        muted = not getattr(self.mic, "muted", False)
        self.mic.set_muted(muted)
        self._set_listening_ui(not muted)
        self._log("🔇 Mic muted" if muted else "🎤 Mic live")

    def _set_listening_ui(self, live):
        mode = getattr(self.mic, "mode", "ptt")
        if live:
            self.mic_status.setText("🎤  Ready — press Talk" if mode == "ptt" else "🎙  Always listening")
            self.mute_btn.setText("🎤  Talk" if mode == "ptt" else "🔇  Mute mic")
        else:
            self.mic_status.setText("🔇  Muted")
            self.mute_btn.setText("🎤  Unmute" if mode == "ptt" else "🎙  Unmute mic")

    def _set_recording_ui(self, rec):
        if rec:
            self.mic_status.setText("🔴  Recording…")
            self.mute_btn.setText("⏹  Stop")
        else:
            self._set_listening_ui(True)

    def _on_level(self, rms, gate, speaking):
        pct = int(min(100, (rms / max(gate * 6.0, 0.02)) * 100))
        self.level.setValue(pct)
        self.dot.setStyleSheet("color:#FF6B00; font-size:14px;" if (speaking or pct > 5)
                               else "color:#a1a1aa; font-size:14px;")

    # ---------- speech -> agent ----------
    def _on_utterance(self, audio, sr):
        if not self.stt:
            return
        # an utterance arrived (auto-sent or manual stop) - clear recording UI
        self._set_recording_ui(False)
        if self._busy:
            dlog("Overlay: busy, ignoring utterance")
            return
        dlog("Overlay: utterance received, transcribing…")
        self._log("Transcribing…")
        self._busy = True

        def task():
            return self.stt.transcribe(audio)

        self._start_worker(task, self._on_transcribed)

    def _on_transcribed(self, text):
        text = (text or "").strip()
        if not text:
            dlog("Overlay: empty transcript, ignoring")
            self._busy = False
            return
        self._add_user(text)
        self._log(f"🗣 You: {text}")
        if self._handle_confirm(text):
            return
        self._handle(text)

    def _on_submit(self):
        text = self.input.text().strip()
        if not text:
            return
        self.input.clear()
        self._add_user(text)
        self._log(f"⌨ You: {text}")
        if self._handle_confirm(text):
            return
        self._handle(text)

    # ---------- confirmation gate ----------
    _YES = {"yes", "y", "yep", "yup", "yeah", "sure", "ok", "okay",
            "confirm", "do it", "go ahead", "please", "affirmative"}
    _NO = {"no", "n", "nope", "nah", "cancel", "stop", "abort", "don't", "dont",
           "negative", "nevermind", "never mind"}

    @staticmethod
    def _verdict(text):
        t = " ".join((text or "").lower().split())
        if not t:
            return None
        # longest first so multi-word phrases beat single short tokens
        for y in sorted(VoiceOverlay._YES, key=len, reverse=True):
            if re.search(r"(?<!\w)" + re.escape(y) + r"(?!\w)", t):
                return True
        for n in sorted(VoiceOverlay._NO, key=len, reverse=True):
            if re.search(r"(?<!\w)" + re.escape(n) + r"(?!\w)", t):
                return False
        return None

    def _handle_confirm(self, text):
        """If a destructive action is waiting for confirmation, act on yes/no."""
        if not self._pending:
            return False
        v = self._verdict(text)
        if v is None:
            # not a clear answer: drop the pending action and treat as a new request
            self._pending = None
            self._pending_desc = ""
            return False
        action = self._pending
        desc = self._pending_desc
        self._pending = None
        self._pending_desc = ""
        if not v:
            self._finish(f"Okay, I didn't {desc}.")
            return True
        self._run_action(action)
        return True

    def _begin_confirm(self, action, desc):
        self._pending = action
        self._pending_desc = desc
        prompt = f"Are you sure you want to {desc}? Say yes to confirm."
        self._finish(prompt)

    def _finish(self, reply):
        if not reply:
            reply = "Done."
        self._add_bot(reply)
        self._log(f"🤖 {reply}")
        if self.tts:
            self.tts.speak(reply)
        self._busy = False

    def _handle(self, text, img=None):
        if not self.agent:
            self._busy = False
            return
        # The agent decides whether a screenshot is actually needed - plain
        # questions skip the capture entirely, which is faster and cheaper.
        info = self.capture.get_active_info() if self.capture else {"app": "unknown", "title": "unknown"}

        self._log("🤔 Thinking…")

        def task():
            return self.agent.decide(text, img, info)

        self._start_worker(task, self._on_decided)

    def _on_decided(self, result):
        if not isinstance(result, dict):
            self._finish(str(result))
            return
        action = result.get("action")
        if not action:
            self._finish(result.get("reply") or "Okay.")
            return
        name = str(action.get("action", "")).lower()
        desc = self._describe(name, action)
        if self.agent.needs_confirm(action):
            self._begin_confirm(action, desc)
            return
        self._run_action(action, desc)

    def _run_action(self, action, desc=None):
        self._log("⚙ Running…")

        def task():
            return self.agent.execute_action(action)

        self._start_worker(task, self._on_reply)

    @staticmethod
    def _describe(name, action):
        who = {
            "shutdown": "turn off your PC",
            "restart": "restart your PC",
            "sleep": "put your PC to sleep",
            "logoff": "log you off",
            "delete": f"delete {action.get('path', 'that file')}",
        }
        return who.get(name, name.replace("_", " "))

    def _on_reply(self, result):
        if isinstance(result, tuple):
            reply, action_msg = (str(result[0]), str(result[1]))
        else:
            reply, action_msg = str(result), ""
        if not reply:
            reply = "Done."
        self._add_bot(reply)
        self._log(f"🤖 {reply}")
        if action_msg:
            self._log(f"⚙ {action_msg}")
        if self.tts:
            self.tts.speak(reply)
        self._busy = False

    # ---------- mic error / permission ----------
    def _on_mic_error(self, msg):
        self._log(f"⚠ {msg}")
        if self._warned:
            return
        self._warned = True
        self.show()
        self.raise_()
        box = QMessageBox(self)
        box.setWindowTitle("Microphone problem")
        box.setIcon(QMessageBox.Warning)
        box.setText(msg)
        box.setInformativeText(
            "If you're not heard:\n"
            "1) Open Windows microphone settings and allow mic access.\n"
            "2) Make sure the right input device is selected.\n\n"
            "Open microphone settings now?"
        )
        open_btn = box.addButton("Open mic settings", QMessageBox.AcceptRole)
        box.addButton("Dismiss", QMessageBox.RejectRole)
        box.exec()
        if box.clickedButton() is open_btn:
            self.open_mic_settings()

    def open_mic_settings(self):
        try:
            subprocess.Popen("start ms-settings:privacy-microphone", shell=True)
        except Exception:
            pass

    # ---------- chat bubbles ----------
    def notify(self, text):
        """External notification (timers/reminders): show bubble + speak it."""
        if not text:
            return
        self.show()
        self.raise_()
        self._add_bot(text)
        self._log(f"⏰ {text}")
    def _add_bubble(self, text, who):
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        b = Bubble(text, who)
        if who == "user":
            row.addStretch(1)
            row.addWidget(b)
        else:
            row.addWidget(b)
            row.addStretch(1)
        holder = QWidget()
        holder.setObjectName("BubbleRow")
        holder.setLayout(row)
        self.chat_lay.insertWidget(self.chat_lay.count() - 1, holder)
        QTimer.singleShot(30, self._scroll_down)

    def _add_user(self, text):
        self._add_bubble(text, "user")

    def _add_bot(self, text):
        if text:
            self._add_bubble(text, "bot")

    def _scroll_down(self):
        sb = self.scroll.verticalScrollBar()
        sb.setValue(sb.maximum())

    def _clear(self):
        while self.chat_lay.count() > 1:
            item = self.chat_lay.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    # ---------- translation ----------
    def _start_region(self):
        if self.region_sel:
            self.region_sel.show()
            self.region_sel.raise_()

    def _on_region_selected(self, x, y, w, h):
        img = self.capture.capture_rect((x, y, w, h)) if self.capture else None
        text = self.ocr.extract_text(img) if self.ocr and img else ""
        self.show()
        self.raise_()
        self._log(f"🔎 Region {w}x{h}, OCR {len(text)} chars")
        self._add_user(f"[translate region {w}×{h}]")
        prompt = (
            "Translate the text visible in this image and the OCR text below into clear natural English. "
            "Return ONLY the translation.\n\nOCR:\n" + text
        )

        def task():
            r = self.agent.ollama.query(prompt, img, "You are a translator. Return only the translation.")
            return (r, "")

        self._start_worker(task, self._on_reply)

    def _ask_screen(self):
        text = self.input.text().strip() or "What do you see on my screen?"
        self.input.clear()
        self._add_user(text)
        self._handle(text)
