ORANGE = "#FF6B00"
ORANGE_DARK = "#E05E00"
BG = "#0E0E0E"
PANEL = "#161616"
CARD = "#1C1C1C"
BORDER = "#2A2A2A"
TEXT = "#F5F5F5"
MUTED = "#9A9A9A"

STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}

QMainWindow, QWidget {{
    background: {BG};
}}

QLabel#Header {{
    font-size: 22px;
    font-weight: 700;
    color: {TEXT};
    padding: 2px 0 6px 0;
}}
QLabel#Sub {{
    color: {MUTED};
    font-size: 11px;
}}

QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 14px;
    padding: 14px 12px 12px 12px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    padding: 2px 8px;
    color: {ORANGE};
    background: {BG};
    border-radius: 6px;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 1px;
}}

QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 8px 14px;
    color: {TEXT};
    font-weight: 600;
}}
QPushButton:hover {{
    background: #232323;
    border: 1px solid {ORANGE};
}}
QPushButton:pressed {{
    background: {ORANGE_DARK};
    border: 1px solid {ORANGE_DARK};
    color: #ffffff;
}}

QPushButton#Primary {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #0E0E0E;
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: #FF7D1F;
}}
QPushButton#Primary:pressed {{
    background: {ORANGE_DARK};
}}

QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    min-width: 130px;
}}
QComboBox:hover {{ border: 1px solid {ORANGE}; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid {BORDER};
    selection-background-color: {ORANGE};
    selection-color: #0E0E0E;
    outline: none;
}}

QCheckBox {{ spacing: 8px; color: {TEXT}; }}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border-radius: 5px;
    border: 1px solid {BORDER};
    background: {CARD};
}}
QCheckBox::indicator:checked {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
}}

QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px;
    selection-background-color: {ORANGE};
    selection-color: #0E0E0E;
}}

QStatusBar {{
    background: {PANEL};
    color: {MUTED};
    border-top: 1px solid {BORDER};
}}

QScrollBar:vertical {{
    background: transparent; width: 10px; margin: 2px;
}}
QScrollBar::handle:vertical {{
    background: #333; border-radius: 5px; min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{ background: {ORANGE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}

QToolTip {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {ORANGE};
    border-radius: 6px;
    padding: 4px 8px;
}}
"""

OVERLAY_STYLESHEET = f"""
QWidget#OverlayBg {{
    background: rgba(14,14,14,0.96);
    border: 1px solid {ORANGE};
    border-radius: 14px;
}}
QLabel#Status {{
    color: {ORANGE};
    font-size: 12px;
    font-weight: 600;
    background: transparent;
    border: none;
}}
QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 6px;
    color: {TEXT};
    selection-background-color: {ORANGE};
    selection-color: #0E0E0E;
}}
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT};
    font-weight: 600;
}}
QPushButton:hover {{ border: 1px solid {ORANGE}; background: #232323; }}
QPushButton#Primary {{
    background: {ORANGE}; border: 1px solid {ORANGE}; color: #0E0E0E;
}}
QPushButton#Primary:hover {{ background: #FF7D1F; }}
"""

BUBBLE_STYLESHEET = f"""
* {{
    font-family: "Segoe UI", "Segoe UI Variable", sans-serif;
    font-size: 12px;
    color: {TEXT};
}}

QWidget#BubbleCard {{
    background: rgba(14,14,14,0.97);
    border: 1px solid {ORANGE};
    border-radius: 16px;
}}

QLabel#BubbleTitle {{
    color: {TEXT};
    font-size: 12px;
    font-weight: 700;
    background: transparent;
}}
QLabel#Dot {{ color: {MUTED}; font-size: 14px; background: transparent; }}

QWidget#ChatHost, QWidget#BubbleRow {{ background: transparent; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QLabel#UserBubble {{
    background: {ORANGE};
    color: #0E0E0E;
    border-radius: 12px;
    padding: 7px 11px;
    font-weight: 600;
}}
QLabel#BotBubble {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 7px 11px;
}}

QPushButton#IconBtn {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #0E0E0E;
    font-size: 13px;
    font-weight: 800;
    border-radius: 6px;
    padding: 0px;
}}
QPushButton#IconBtn:hover {{ background: #FF7D1F; color: #0E0E0E; }}

QLabel#MiniBtn {{
    background: {ORANGE};
    color: #0E0E0E;
    border: 1px solid {ORANGE};
    border-radius: 7px;
}}

QPushButton#MicBtn {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-size: 15px;
}}
QPushButton#MicBtn:hover {{ border: 1px solid {ORANGE}; }}

QPushButton#Primary {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #0E0E0E;
    border-radius: 10px;
    font-weight: 700;
    font-size: 14px;
}}
QPushButton#Primary:hover {{ background: #FF7D1F; }}

QLineEdit#ChatInput {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 7px 10px;
    color: {TEXT};
    selection-background-color: {ORANGE};
    selection-color: #0E0E0E;
}}
QLineEdit#ChatInput:focus {{ border: 1px solid {ORANGE}; }}

QPushButton#SendBtn {{
    background: {CARD};
    border: 1px solid {BORDER};
    color: {ORANGE};
    border-radius: 10px;
    font-size: 14px;
    font-weight: 700;
}}
QPushButton#SendBtn:hover {{ border: 1px solid {ORANGE}; background: #1E1E1E; }}

QLabel#MicStatus {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 600;
    background: transparent;
}}
QProgressBar#LevelBar {{
    background: #101010;
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QProgressBar#LevelBar::chunk {{
    background: {ORANGE};
    border-radius: 3px;
}}

QPushButton#MuteBtn {{
    background: {CARD};
    border: 1px solid {BORDER};
    color: {TEXT};
    border-radius: 9px;
    padding: 8px 10px;
    font-weight: 600;
}}
QPushButton#MuteBtn:hover {{ border: 1px solid {ORANGE}; }}
QPushButton#GhostBtn {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {MUTED};
    border-radius: 9px;
    padding: 8px 10px;
    font-weight: 600;
}}
QPushButton#GhostBtn:hover {{ border: 1px solid {ORANGE}; color: {TEXT}; }}

QPushButton#TalkBtn {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #0E0E0E;
    border-radius: 12px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#TalkBtn:hover {{ background: #FF7D1F; }}
QPushButton#TalkBtn[listening="true"] {{
    background: #FF3B30;
    border: 1px solid #FF3B30;
    color: #ffffff;
}}
QPushButton#TalkBtn:disabled {{ background: #444; border-color: #444; color: #888; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #333; border-radius: 4px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {ORANGE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""

