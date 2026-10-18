import os
# Limit math-library thread arenas BEFORE numpy/OpenBLAS load.
# Without this, OpenBLAS reserves hundreds of MB of committed memory.
for _v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
           "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
    os.environ.setdefault(_v, "2")

import configparser
import sys

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QComboBox, QCheckBox, QGroupBox, QFormLayout, QStatusBar,
    QLineEdit, QMessageBox, QGridLayout, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QFont, QTextCursor, QIcon
from ui.theme import STYLESHEET

from ui.overlay import VoiceOverlay
from ui.tray import VoiceTray
from ui.region import RegionSelector
from core.hotkey import HotkeyManager
from core.mic import MicListener, list_input_devices
from core.stt import STT
from core.capture import ScreenCapture
from core.ocr import OCR
from core.ollama import OllamaClient
from core.ollama_service import OllamaService
from core import providers
from core.control import PCControl
from core.agent import Agent
from core.tts import TTS
from core.timers import Timers
from utils import paths, secretstore


def load_config():
    cfg = configparser.ConfigParser()
    if not os.path.exists(paths.CONFIG_PATH):
        try:
            with open(paths.resource_path("config.default.ini"), "r", encoding="utf-8") as f:
                default = f.read()
        except Exception:
            default = "[Main]\n"
        try:
            with open(paths.CONFIG_PATH, "w", encoding="utf-8") as f:
                f.write(default)
        except Exception:
            pass
    cfg.read(paths.CONFIG_PATH, encoding="utf-8")
    _merge_missing_defaults(cfg)
    # Keys on disk are DPAPI-encrypted; decrypt in memory, and migrate any
    # legacy plaintext keys once so they get encrypted immediately.
    migrate = secretstore.has_plaintext_keys(cfg)
    secretstore.decrypt_config(cfg)
    if migrate:
        try:
            secretstore.save_config(cfg, paths.CONFIG_PATH)
        except Exception:
            pass
    return cfg


def _merge_missing_defaults(cfg):
    """config.ini may predate newer keys (e.g. perm_*). Copy missing keys from the
    shipped defaults so getboolean() never falls back to a wrong implicit value."""
    defaults = configparser.ConfigParser()
    try:
        defaults.read(paths.resource_path("config.default.ini"), encoding="utf-8")
    except Exception:
        return
    changed = False
    for section in defaults.sections():
        if not cfg.has_section(section):
            cfg.add_section(section)
            changed = True
        for key, value in defaults.items(section):
            if not cfg.has_option(section, key):
                cfg.set(section, key, value)
                changed = True
    if changed:
        try:
            with open(paths.CONFIG_PATH, "w", encoding="utf-8") as f:
                cfg.write(f)
        except Exception:
            pass


class MainWindow(QMainWindow):
    ollama_event = Signal()
    local_models = Signal(object)

    def __init__(self):
        super().__init__()
        self.cfg = load_config()
        self.remote = None
        self.remote_bridge = None
        self.setWindowTitle("Agently — Voice Agent")
        self.resize(760, 900)
        self.setMinimumWidth(520)

        # core components
        self.overlay = VoiceOverlay(self.cfg)
        self.tray = VoiceTray(self.cfg, self.overlay, on_quit=self.close)
        self.region = RegionSelector(self.cfg)
        self.hotkey = HotkeyManager(self.cfg)
        self.mic = MicListener(self.cfg)
        self.stt = STT(self.cfg)
        self.capture = ScreenCapture(self.cfg)
        self.ocr = OCR(self.cfg)
        self.ollama_service = OllamaService(self.cfg)
        self.ollama = OllamaClient(self.cfg, service=self.ollama_service)
        self.control = PCControl(self.cfg)
        self.control.capture = self.capture
        self.tts = TTS(self.cfg)
        self.timers = Timers(speak=self.tts.speak,
                             notify=lambda t: self.overlay.notify(t))
        self.control.timers = self.timers
        self.agent = Agent(self.cfg, self.ollama, self.control, self.capture)

        self.overlay.set_components(
            self.region, self.capture, self.ocr, self.ollama,
            self.control, self.mic, self.stt, agent=self.agent, tts=self.tts, log=self.log
        )
        self.hotkey.set_callback(self.overlay.toggle_talk)

        self._build_ui()
        self.tray.show()

        # status polling
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(2000)
        self._refresh_status()

        # start the local server only if we boot straight into Local Ollama
        self.ollama_event.connect(self._refresh_status)
        self.ollama_event.connect(self._on_ollama_event)
        self.local_models.connect(self._on_local_models)
        if (self.cfg["Main"].get("provider", "gemini") or "").strip().lower() == "local":
            self._start_ollama_async()

        self.log("App started. Press Alt+Shift+V to talk, or use the buttons below.")
        QTimer.singleShot(300, self._maybe_ask_consent)

        # remote access (starts only if it was left enabled)
        QTimer.singleShot(400, self._start_remote)

    # ---------- UI ----------
    def _build_ui(self):
        # Everything lives in a scroll area so the window never squashes the
        # controls when the content is taller than the window (small screens,
        # high DPI scaling, or long provider/model names).
        outer = QWidget()
        outer_root = QVBoxLayout(outer)
        outer_root.setContentsMargins(0, 0, 0, 0)
        outer_root.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignTop)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet("QScrollArea { background: transparent; } "
                             "QScrollArea > QWidget > QWidget { background: transparent; }")

        central = QWidget()
        scroll.setWidget(central)
        outer_root.addWidget(scroll)

        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # header
        head = QLabel("🎙  Agently")
        head.setObjectName("Header")
        root.addWidget(head)
        sub = QLabel("Voice agent · smart cloud model · private on-device speech")
        sub.setObjectName("Sub")
        root.addWidget(sub)

        # status box
        sb = QGroupBox("Status")
        sform = QFormLayout(sb)
        self.lbl_model = QLabel("?")
        self.lbl_ollama = QLabel("checking...")
        self.lbl_hotkey = QLabel(self.cfg["Main"].get("hotkey", "?"))
        self.lbl_mic = QLabel("idle")
        self.lbl_whisper = QLabel("loading...")
        sform.addRow("Model:", self.lbl_model)
        sform.addRow("Provider:", self.lbl_ollama)
        sform.addRow("Voice hotkey (talk):", self.lbl_hotkey)
        sform.addRow("Microphone:", self.lbl_mic)
        sform.addRow("Speech-to-text:", self.lbl_whisper)
        root.addWidget(sb)

        # action buttons
        ab = QGroupBox("Actions")
        arow = QHBoxLayout(ab)
        b_mute = QPushButton("🎤  Talk / Stop")
        b_mute.setObjectName("Primary")
        b_mute.clicked.connect(self.overlay.toggle_talk)
        b_bubble = QPushButton("Show bubble")
        b_bubble.clicked.connect(self._show_bubble)
        b_trans = QPushButton("Translate Region")
        b_trans.clicked.connect(self.overlay._start_region)
        b_screen = QPushButton("Ask about screen")
        b_screen.clicked.connect(self.overlay._ask_screen)
        b_clear = QPushButton("Clear log")
        b_clear.clicked.connect(self._clear_log)
        for b in (b_mute, b_bubble, b_trans, b_screen, b_clear):
            arow.addWidget(b)
        root.addWidget(ab)

        # log
        lb = QGroupBox("Activity log")
        llay = QVBoxLayout(lb)
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        self.log_box.setFont(QFont("Consolas", 9))
        self.log_box.setMinimumHeight(120)
        self.log_box.setMaximumHeight(200)
        llay.addWidget(self.log_box)
        root.addWidget(lb, stretch=0)

        # settings
        setb = QGroupBox("Settings")
        srow = QHBoxLayout(setb)
        srow.addWidget(QLabel("Hotkey:"))
        self.cmb_hotkey = QComboBox()
        self.cmb_hotkey.addItems([
            "Alt+Shift+V", "Ctrl+Shift+V", "Alt+Space",
            "Ctrl+Alt+V", "F9", "F10"
        ])
        self.cmb_hotkey.setCurrentText(self.cfg["Main"].get("hotkey", "Alt+Shift+V"))
        self.cmb_hotkey.currentTextChanged.connect(self._change_hotkey)
        srow.addWidget(self.cmb_hotkey)

        self.chk_active = QCheckBox("Use active window (else full screen)")
        self.chk_active.setChecked(self.cfg["Main"].getboolean("use_active_window", True))
        self.chk_active.stateChanged.connect(self._save_active)
        srow.addWidget(self.chk_active)

        self.chk_tts = QCheckBox("Voice replies (TTS)")
        self.chk_tts.setChecked(self.cfg["Main"].getboolean("tts", True))
        self.chk_tts.stateChanged.connect(self._save_tts)
        srow.addWidget(self.chk_tts)
        srow.addStretch(1)
        root.addWidget(setb)

        # microphone settings
        mb = QGroupBox("Microphone")
        mform = QFormLayout(mb)
        self.cmb_mic = QComboBox()
        self._populate_mics()
        self.cmb_mic.currentIndexChanged.connect(self._change_mic)
        mform.addRow("Input device:", self.cmb_mic)
        self.cmb_mode = QComboBox()
        self.cmb_mode.addItem("Press to talk (recommended)", "ptt")
        self.cmb_mode.addItem("Always listening (auto)", "auto")
        cur = self.cfg["Main"].get("listen_mode", "ptt")
        self.cmb_mode.setCurrentIndex(0 if cur == "ptt" else 1)
        self.cmb_mode.currentIndexChanged.connect(self._change_mode)
        mform.addRow("Listening mode:", self.cmb_mode)

        self.cmb_end = QComboBox()
        for s in ("2", "3", "4", "5", "6", "8"):
            self.cmb_end.addItem(f"{s} seconds", s)
        cur_end = str(self.cfg["Main"].get("end_silence_sec", "4"))
        pos = self.cmb_end.findData(cur_end)
        self.cmb_end.setCurrentIndex(pos if pos >= 0 else 2)
        self.cmb_end.currentIndexChanged.connect(self._change_end_silence)
        mform.addRow("Answer after silence:", self.cmb_end)
        mrow = QHBoxLayout()
        b_micset = QPushButton("Open Windows mic settings")
        b_micset.clicked.connect(self.overlay.open_mic_settings)
        b_restart = QPushButton("Restart listening")
        b_restart.clicked.connect(self._restart_listening)
        mrow.addWidget(b_micset)
        mrow.addWidget(b_restart)
        mform.addRow(mrow)
        root.addWidget(mb)

        # brain (AI model) settings
        bb = QGroupBox("Brain — AI model")
        bform = QFormLayout(bb)
        self.cmb_provider = QComboBox()
        for pid in providers.PROVIDER_ORDER:
            self.cmb_provider.addItem(providers.get(pid)["label"], pid)
        cur_prov = (self.cfg["Main"].get("provider", "gemini") or "gemini").strip().lower()
        pos = self.cmb_provider.findData(cur_prov)
        self.cmb_provider.setCurrentIndex(pos if pos >= 0 else 0)
        self.cmb_provider.currentIndexChanged.connect(self._change_provider)
        bform.addRow("Provider:", self.cmb_provider)

        self.txt_key = QLineEdit()
        self.txt_key.setEchoMode(QLineEdit.Password)
        bform.addRow("API key:", self.txt_key)

        self.cmb_cloud_model = QComboBox()
        self.cmb_cloud_model.setEditable(True)
        bform.addRow("Model:", self.cmb_cloud_model)

        brow = QHBoxLayout()
        b_save = QPushButton("Save brain settings")
        b_save.setObjectName("Primary")
        b_save.clicked.connect(self._save_brain)
        self.b_getkey = QPushButton("Get API key")
        self.b_getkey.clicked.connect(self._open_key_page)
        brow.addWidget(b_save)
        brow.addWidget(self.b_getkey)
        bform.addRow(brow)
        root.addWidget(bb)

        self._load_provider_fields(cur_prov, initial=True)

        # permissions
        permb = QGroupBox("Permissions — what Agently may do")
        pgrid = QGridLayout(permb)
        pgrid.setSpacing(4)
        self._perm_boxes = {}
        perm_defs = [
            ("perm_apps", "Apps & windows", "Close, focus, list open windows"),
            ("perm_files", "Files & folders", "Open, create, move, copy, delete"),
            ("perm_clip_screens", "Clipboard & screenshots", "Read/write clipboard, capture"),
            ("perm_timers", "Timers & reminders", "Set and cancel timers"),
            ("perm_system", "System settings", "Brightness, Wi-Fi, dark mode"),
            ("perm_power", "Power actions", "Shut down, restart, sleep, log off"),
            ("perm_shell", "Run commands", "Execute shell commands and scripts"),
        ]
        for i, (key, label, hint) in enumerate(perm_defs):
            box = QCheckBox(label)
            box.setToolTip(hint)
            box.setChecked(self.cfg["Main"].getboolean(key, True))
            box.stateChanged.connect(self._save_perm(key))
            self._perm_boxes[key] = box
            pgrid.addWidget(box, i // 2, i % 2)
        confirm_row = QHBoxLayout()
        self.chk_confirm = QCheckBox("Confirm power actions and deletion (voice: say yes)")
        self.chk_confirm.setChecked(self.cfg["Main"].getboolean("pc_control_confirm", True))
        self.chk_confirm.stateChanged.connect(self._save_confirm)
        confirm_row.addWidget(self.chk_confirm)
        confirm_row.addStretch(1)
        pgrid.addLayout(confirm_row, len(perm_defs) // 2 + 1, 0, 1, 2)
        root.addWidget(permb)

        # remote (control from your phone over Tailscale)
        rb = QGroupBox("Remote — control from your phone (Tailscale)")
        rform = QFormLayout(rb)
        self.chk_remote = QCheckBox("Enable remote access")
        self.chk_remote.setChecked(self.cfg["Main"].getboolean("remote_enabled", False))
        self.chk_remote.stateChanged.connect(self._toggle_remote)
        rform.addRow(self.chk_remote)

        self.lbl_remote_url = QLabel("—")
        self.lbl_remote_url.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_remote_url.setWordWrap(True)
        rform.addRow("Open on your phone:", self.lbl_remote_url)

        self.lbl_remote_token = QLabel("—")
        self.lbl_remote_token.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.lbl_remote_token.setWordWrap(True)
        rform.addRow("Access token:", self.lbl_remote_token)

        rrow = QHBoxLayout()
        b_newtok = QPushButton("New token")
        b_newtok.clicked.connect(self._new_remote_token)
        b_copy = QPushButton("Copy link + token")
        b_copy.clicked.connect(self._copy_remote_info)
        rrow.addWidget(b_newtok)
        rrow.addWidget(b_copy)
        rrow.addStretch(1)
        rform.addRow(rrow)

        rnote = QLabel(
            "Works only over your private Tailscale network (no open ports). "
            "Risky actions always ask Yes/Cancel on your phone."
        )
        rnote.setWordWrap(True)
        rform.addRow(rnote)
        root.addWidget(rb)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Ready")

        self.setCentralWidget(outer)

    def resizeEvent(self, e):
        # Keep the settings readable on wide monitors instead of stretching
        # one giant column across 2000px.
        super().resizeEvent(e)
        try:
            w = max(520, min(e.size().width() - 24, 980))
            self.findChild(QScrollArea).setMaximumWidth(w + 24)
        except Exception:
            pass

    # ---------- helpers ----------
    def log(self, msg):
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.log_box.insertPlainText(msg.rstrip() + "\n")
        self.log_box.moveCursor(QTextCursor.MoveOperation.End)
        self.statusBar().showMessage(msg[:80])

    def _clear_log(self):
        self.log_box.clear()

    def _refresh_status(self):
        # provider / model
        prov = (self.cfg["Main"].get("provider", "gemini") or "gemini").strip().lower()
        preset = providers.get(prov)
        model = (self.cfg["Main"].get("ollama_model", "?") if not preset["use_cloud"]
                 else self.cfg["Main"].get("cloud_model", "?"))
        self.lbl_model.setText(model or "?")

        if preset["use_cloud"]:
            key = (self.cfg["Main"].get(providers.key_name(prov), "") or "").strip()
            state = "configured ✔" if key else "no API key ✘"
            self.lbl_ollama.setText(f"{preset['label']} — {state}")
        else:
            if self.ollama_service.is_running():
                state = "running ✔"
            elif self.ollama_service.owned:
                state = "starting…"
            else:
                state = "stopped (starts on use)"
            self.lbl_ollama.setText(f"{preset['label']} — {state}")
        # whisper
        wm = self.cfg['Main'].get('whisper_model')
        if self.stt.model is not None:
            self.lbl_whisper.setText(f"ready ({wm}) ✔")
        else:
            self.lbl_whisper.setText(f"{wm} — loads on demand")
        # mic
        if getattr(self.mic, "muted", False):
            self.lbl_mic.setText("muted 🔇")
        elif getattr(self.mic, "running", False):
            self.lbl_mic.setText("listening 🎙")
        else:
            self.lbl_mic.setText("stopped ✘")

    def _populate_mics(self):
        self.cmb_mic.blockSignals(True)
        self.cmb_mic.clear()
        self.cmb_mic.addItem("System default", "default")
        for idx, name, ch in list_input_devices():
            self.cmb_mic.addItem(f"[{idx}] {name}", str(idx))
        current = self.cfg["Main"].get("mic_device", "default")
        pos = self.cmb_mic.findData(str(current))
        self.cmb_mic.setCurrentIndex(pos if pos >= 0 else 0)
        self.cmb_mic.blockSignals(False)

    def _change_mic(self):
        dev = self.cmb_mic.currentData()
        self.cfg["Main"]["mic_device"] = str(dev)
        secretstore.save_config(self.cfg, paths.CONFIG_PATH)
        self.log(f"Microphone device set to {self.cmb_mic.currentText()}")
        self._restart_listening()

    def _restart_listening(self):
        try:
            self.mic.stop()
        except Exception:
            pass
        self.overlay.start_listening()
        self.log("Restarted microphone listening.")

    def _change_mode(self):
        mode = self.cmb_mode.currentData()
        self.overlay.set_mode(mode)
        self._save_config()
        self.log(f"Listening mode: {self.cmb_mode.currentText()}")

    def _change_end_silence(self):
        sec = self.cmb_end.currentData()
        self.cfg["Main"]["end_silence_sec"] = str(sec)
        self.mic.set_end_silence(float(sec))
        self._save_config()
        self.log(f"Will answer after {sec}s of silence.")

    def _change_hotkey(self, hk):
        try:
            self.hotkey.rebind(hk)
            self.cfg["Main"]["hotkey"] = hk
            secretstore.save_config(self.cfg, paths.CONFIG_PATH)
            self.lbl_hotkey.setText(hk)
            self.log(f"Hotkey changed to {hk}")
        except Exception as e:
            self.log(f"Hotkey change failed: {e}")

    def _save_active(self, state):
        self.cfg["Main"]["use_active_window"] = "true" if state else "false"
        secretstore.save_config(self.cfg, paths.CONFIG_PATH)
        self.log(f"Active-window mode: {'on' if state else 'off'}")

    def _save_tts(self, state):
        self.cfg["Main"]["tts"] = "true" if state else "false"
        self.tts.set_enabled(bool(state))
        secretstore.save_config(self.cfg, paths.CONFIG_PATH)
        self.log(f"Voice replies: {'on' if state else 'off'}")

    def _save_perm(self, key):
        def handler(state):
            self.cfg["Main"][key] = "true" if state else "false"
            self._save_config()
            self.log(f"Permission '{key}': {'on' if state else 'off'}")
        return handler

    def _save_confirm(self, state):
        self.cfg["Main"]["pc_control_confirm"] = "true" if state else "false"
        self.control.confirm = bool(state)
        if hasattr(self, "agent"):
            self.agent.confirm = bool(state)
        self._save_config()
        self.log(f"Confirm dangerous actions: {'on' if state else 'off'}")

    # ---------- remote (phone over Tailscale) ----------
    def _remote_url(self):
        ip = (self.remote.ip if (self.remote and self.remote.ip) else "127.0.0.1")
        port = self.cfg["Main"].get("remote_port", "8765")
        return f"http://{ip}:{port}"

    def _refresh_remote_labels(self):
        if not hasattr(self, "chk_remote"):
            return
        if self.cfg["Main"].getboolean("remote_enabled", False):
            self.lbl_remote_url.setText(self._remote_url())
        else:
            self.lbl_remote_url.setText("disabled")
        tok = self.cfg["Main"].get("remote_token", "") or ""
        self.lbl_remote_token.setText(tok if tok else "(none yet - click New token)")

    def _toggle_remote(self, state):
        on = bool(state)
        self.cfg["Main"]["remote_enabled"] = "true" if on else "false"
        if on and not self.cfg["Main"].get("remote_token", ""):
            self.cfg["Main"]["remote_token"] = secretstore.new_token()
        self._save_config()
        if on:
            self._start_remote()
        else:
            self._stop_remote()
        self._refresh_remote_labels()
        self.log("Remote access: " + ("enabled" if on else "disabled"))

    def _new_remote_token(self):
        self.cfg["Main"]["remote_token"] = secretstore.new_token()
        self._save_config()
        if self.remote:
            self.remote.httpd = None
            self._start_remote(force=True)
        self._refresh_remote_labels()
        self.log("New remote access token generated.")

    def _copy_remote_info(self):
        info = f"{self._remote_url()}\nToken: {self.cfg['Main'].get('remote_token', '')}"
        try:
            import subprocess as sp
            sp.Popen(["clip"], stdin=sp.PIPE, text=True).communicate(info)
            self.log("Link + token copied to clipboard.")
        except Exception:
            self.log("Copy failed - select and copy the text manually.")

    def _start_remote(self, force=False):
        if not self.cfg["Main"].getboolean("remote_enabled", False) and not force:
            return
        if self.remote and self.remote.httpd and not force:
            return
        self._stop_remote()
        tok = self.cfg["Main"].get("remote_token", "")
        if not tok:
            self.cfg["Main"]["remote_token"] = secretstore.new_token()
            self._save_config()
            tok = self.cfg["Main"].get("remote_token", "")
        from core.remote_bridge import RemoteBridge
        from core.remote_server import RemoteServer
        bridge = RemoteBridge(self.cfg, log=self.log)
        bridge.agent = self.agent
        bridge.control = self.control
        bridge.stt = self.stt
        bridge.capture = self.capture
        bridge.timers = self.timers
        self.remote_bridge = bridge
        self.remote = RemoteServer(self.cfg, bridge, log=self.log)
        self.remote.start()
        self._refresh_remote_labels()

    def _stop_remote(self):
        if getattr(self, "remote", None):
            self.remote.stop()
            self.remote = None

    def _maybe_ask_consent(self):
        """One-time first-run permission dialog. Saves the choice and never asks again."""
        if self.cfg["Main"].getboolean("consent_done", False):
            return
        box = QMessageBox(self)
        box.setIcon(QMessageBox.Question)
        box.setWindowTitle("Give Agently permission")
        box.setText("Give Agently full control of this PC?")
        box.setInformativeText(
            "Agently can already chat, open apps, read your screen and type for you.\n\n"
            "Allowing full control also lets it:\n"
            "· manage windows and files\n"
            "· read/write the clipboard and take screenshots\n"
            "· set timers and reminders\n"
            "· change system settings (brightness, Wi-Fi, dark mode)\n"
            "· run commands\n"
            "· shut down / restart / sleep the PC\n\n"
            "Power actions and deletions always ask you first "
            "unless you turn that off. You can change any of this later in Permissions."
        )
        full = box.addButton("Allow full control", QMessageBox.AcceptRole)
        safe = box.addButton("Keep me safe (recommended)", QMessageBox.RejectRole)
        box.setDefaultButton(safe)
        box.exec()
        allow_full = box.clickedButton() is full
        for key, boxw in self._perm_boxes.items():
            enabled = allow_full or key in ("perm_apps", "perm_files",
                                            "perm_clip_screens", "perm_timers")
            boxw.setChecked(enabled)
        self.cfg["Main"]["consent_done"] = "true"
        self._save_config()
        self.log(f"Permission granted: {'full control' if allow_full else 'safe subset only'}")

    def _save_config(self):
        secretstore.save_config(self.cfg, paths.CONFIG_PATH)

    def _change_provider(self):
        old = (self.cfg["Main"].get("provider", "gemini") or "gemini").strip().lower()
        new = self.cmb_provider.currentData()

        # remember the model/key we were just using, under the old provider's slots
        self._store_active(old)

        self._load_provider_fields(new)
        self._apply_preset(new)
        self._save_config()
        self._rebuild_brain()

        if new == "local":
            exe = self.ollama_service.exe_path()
            self.log("Local AI: Ollama found at " + exe if exe
                     else "Local AI: Ollama not found — install from https://ollama.com/download")
            self._refresh_local_models()
            self._start_ollama_async()
        else:
            self.ollama_service.stop()
        self.log(f"Provider set to {providers.get(new)['label']}")

    def _apply_preset(self, prov):
        """Write the provider's host/model/key-mode into config."""
        preset = providers.get(prov)
        self.cfg["Main"]["provider"] = prov
        self.cfg["Main"]["use_cloud"] = "true" if preset["use_cloud"] else "false"
        if preset["use_cloud"]:
            self.cfg["Main"]["api_host"] = preset["host"]
            self.cfg["Main"]["reasoning_effort"] = preset.get("reasoning_effort", "")
            model = self.cmb_cloud_model.currentText().strip() or preset["models"][0]
            self.cfg["Main"]["cloud_model"] = model
            self.cfg["Main"][providers.model_name(prov)] = model

    def _store_active(self, prov):
        """Persist the model currently shown in the combo into *prov*'s slot."""
        if not prov:
            return
        model = self.cmb_cloud_model.currentText().strip()
        if model:
            self.cfg["Main"][providers.model_name(prov)] = model
        preset = providers.get(prov)
        if preset["needs_key"]:
            self.cfg["Main"][providers.key_name(prov)] = self.txt_key.text().strip()

    def _load_provider_fields(self, prov, initial=False):
        """Apply the preset for *prov* to the API-key + model widgets."""
        preset = providers.get(prov)

        # model list: saved model first (if custom), then the presets
        saved = (self.cfg["Main"].get(providers.model_name(prov), "") or "").strip()
        models = list(preset["models"])
        if saved and saved not in models:
            models.insert(0, saved)
        self.cmb_cloud_model.blockSignals(True)
        self.cmb_cloud_model.clear()
        self.cmb_cloud_model.addItems(models)
        self.cmb_cloud_model.setCurrentText(saved or (models[0] if models else ""))
        self.cmb_cloud_model.blockSignals(False)

        # api key
        self.txt_key.blockSignals(True)
        self.b_getkey.setText("Get API key")
        if preset["needs_key"]:
            self.txt_key.setText(self.cfg["Main"].get(providers.key_name(prov), ""))
            self.txt_key.setEnabled(True)
            self.txt_key.setPlaceholderText(f"Paste your {preset['key_label']} here")
            self.b_getkey.setEnabled(True)
        else:
            self.txt_key.setText("")
            self.txt_key.setEnabled(False)
            self.txt_key.setPlaceholderText("not needed for local models")
            if prov == "local":
                self.b_getkey.setText("Install Ollama")
                self.b_getkey.setEnabled(bool(preset.get("key_hint")))
            else:
                self.b_getkey.setEnabled(False)
        self.txt_key.blockSignals(False)

    def _open_key_page(self):
        preset = providers.get(self.cmb_provider.currentData())
        url = preset.get("key_hint", "")
        if url:
            __import__("subprocess").Popen(f'start "" "{url}"', shell=True)

    def _save_brain(self):
        prov = self.cmb_provider.currentData()
        self._store_active(prov)
        self._apply_preset(prov)
        self._save_config()
        self._rebuild_brain()
        if prov == "local":
            self._refresh_local_models()
        self.log("Brain settings saved.")

    def _rebuild_brain(self):
        try:
            self.ollama = OllamaClient(self.cfg, service=self.ollama_service)
            self.agent = Agent(self.cfg, self.ollama, self.control, self.capture)
            if self.overlay:
                self.overlay.agent = self.agent
                self.overlay.ollama = self.ollama
            self._refresh_status()
        except Exception as e:
            self.log(f"Brain rebuild failed: {e}")

    # ---------- local ollama lifecycle ----------
    def _start_ollama_async(self):
        if self.ollama_service.is_running():
            self._refresh_status()
            self._refresh_local_models()
            return
        import threading
        threading.Thread(target=self._start_ollama_worker, daemon=True).start()

    def _start_ollama_worker(self):
        self.log("Starting Ollama on demand…")
        ok = self.ollama_service.start()
        if ok:
            self.log("Ollama is running.")
        else:
            self.log("Ollama failed to start: " +
                     (self.ollama_service.last_error or "unknown reason"))
        self.ollama_event.emit()

    def _on_ollama_event(self):
        """After a start attempt, fill the model list once the server is up."""
        if (self.cmb_provider.currentData() == "local"
                and self.ollama_service.is_running()):
            self._refresh_local_models()

    def _refresh_local_models(self):
        """Ask Ollama (in the background) which models are installed."""
        import threading
        threading.Thread(
            target=lambda: self.local_models.emit(self.ollama_service.list_models()),
            daemon=True,
        ).start()

    def _on_local_models(self, names):
        """Merge installed models into the Model dropdown (saved value first)."""
        if self.cmb_provider.currentData() != "local":
            return
        preset = providers.get("local")
        saved = self.cmb_cloud_model.currentText().strip()
        models = []
        for n in (names or []):
            if n and n not in models:
                models.append(n)
        for n in preset["models"]:
            if n not in models:
                models.append(n)
        if saved and saved not in models:
            models.insert(0, saved)
        self.cmb_cloud_model.blockSignals(True)
        self.cmb_cloud_model.clear()
        self.cmb_cloud_model.addItems(models)
        self.cmb_cloud_model.setCurrentText(saved or (models[0] if models else ""))
        self.cmb_cloud_model.blockSignals(False)

    def _show_bubble(self):
        if getattr(self.overlay, "collapsed", False):
            self.overlay.expand()
        self.overlay.show()
        self.overlay.raise_()
        self.overlay.activateWindow()

    def closeEvent(self, e):
        # hide to tray instead of quitting
        e.ignore()
        self.hide()
        self.log("Window hidden to tray (app still running).")


def main():
    from utils import debuglog
    aumid_ok = False
    try:
        import ctypes
        aumid_ok = ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("Ihebhhrg.Agently") == 0
    except Exception:
        aumid_ok = False
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setStyleSheet(STYLESHEET)
    icon_path = paths.resource_path("app.ico")
    _ico = QIcon(icon_path)
    app.setWindowIcon(_ico)
    debuglog.clear()
    debuglog.dlog("=== Agently starting ===")
    debuglog.dlog(f"AUMID set: {aumid_ok}; icon loaded: {not _ico.isNull()}; icon={icon_path}")
    try:
        import faulthandler, os
        crash = open(os.path.join(debuglog._LOG_DIR, "crash.log"), "w")
        faulthandler.enable(crash)
    except Exception:
        pass
    win = MainWindow()
    win.setWindowIcon(_ico)
    app.aboutToQuit.connect(win.ollama_service.shutdown)
    win.show()
    win._show_bubble()
    win.overlay.start_listening()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
