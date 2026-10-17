import os

from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon, QAction, QPixmap
from PySide6.QtCore import Qt

from utils import paths


class VoiceTray(QSystemTrayIcon):
    def __init__(self, cfg, overlay, on_quit=None):
        super().__init__()
        self.cfg = cfg
        self.overlay = overlay
        self.on_quit = on_quit
        self.setToolTip("Agently — running")

        self.menu = QMenu()
        act_mute = QAction("🎤  Talk / Stop", self)
        act_mute.triggered.connect(self.overlay.toggle_talk)
        act_bubble = QAction("Show / Hide bubble", self)
        act_bubble.triggered.connect(self._toggle_bubble)
        act_trans = QAction("Translate region", self)
        act_trans.triggered.connect(self.overlay._start_region)
        act_settings = QAction("Microphone settings", self)
        act_settings.triggered.connect(self.overlay.open_mic_settings)
        act_quit = QAction("Quit", self)
        act_quit.triggered.connect(self._quit)
        self.menu.addAction(act_mute)
        self.menu.addAction(act_bubble)
        self.menu.addAction(act_trans)
        self.menu.addAction(act_settings)
        self.menu.addSeparator()
        self.menu.addAction(act_quit)

        self.setContextMenu(self.menu)
        self.setIcon(self._icon())
        self.activated.connect(self._on_activated)

    def _icon(self):
        ico = paths.resource_path("app.ico")
        if os.path.exists(ico):
            return QIcon(ico)
        pix = QPixmap(64, 64)
        pix.fill(Qt.transparent)
        return QIcon(pix)

    def _toggle_bubble(self):
        if self.overlay.isVisible():
            self.overlay.hide()
        else:
            self.overlay.show()
            self.overlay.raise_()

    def _on_activated(self, reason):
        if reason == QSystemTrayIcon.Trigger:
            self._toggle_bubble()

    def _quit(self):
        from PySide6.QtWidgets import QApplication
        QApplication.quit()
