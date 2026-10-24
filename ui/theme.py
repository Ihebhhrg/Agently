ORANGE = "#FF6B00"
ORANGE_DARK = "#E05E00"
ORANGE_LIGHT = "#FF8533"
BG = "#09090b"
PANEL = "#18181b"
CARD = "#1e1e22"
BORDER = "#27272a"
TEXT = "#fafafa"
MUTED = "#a1a1aa"
MUTED_DARK = "#71717a"
SUCCESS = "#22c55e"
WARNING = "#f59e0b"
DANGER = "#ef4444"

STYLESHEET = f"""
* {{
    font-family: "SF Pro Display", "SF Pro Text", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
}}

QMainWindow, QWidget {{
    background: {BG};
}}

/* ---------- header ---------- */
QLabel#Header {{
    font-size: 24px;
    font-weight: 700;
    color: {TEXT};
    padding: 4px 0 2px 0;
    letter-spacing: -0.5px;
}}
QLabel#Sub {{
    color: {MUTED};
    font-size: 13px;
    font-weight: 400;
}}

/* ---------- cards (replaces QGroupBox) ---------- */
QGroupBox {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 12px;
    margin-top: 0px;
    padding: 16px 18px 18px 18px;
    font-weight: 600;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 16px;
    top: -1px;
    padding: 2px 10px;
    color: {MUTED};
    background: {PANEL};
    border-radius: 6px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1.2px;
}}

/* ---------- buttons ---------- */
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 10px;
    color: {TEXT};
    font-weight: 500;
    font-size: 12px;
    min-height: 26px;
}}
QPushButton:hover {{
    background: #27272a;
    border: 1px solid #3f3f46;
}}
QPushButton:pressed {{
    background: #18181b;
    border: 1px solid #27272a;
}}
QPushButton#Primary {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #09090b;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#Primary:hover {{
    background: {ORANGE_LIGHT};
    border: 1px solid {ORANGE_LIGHT};
}}
QPushButton#Primary:pressed {{
    background: {ORANGE_DARK};
    border: 1px solid {ORANGE_DARK};
    color: #ffffff;
}}
QPushButton#Danger {{
    background: {DANGER};
    border: 1px solid {DANGER};
    color: #ffffff;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#Danger:hover {{
    background: #dc2626;
    border: 1px solid #dc2626;
}}

/* ---------- inputs ---------- */
QComboBox {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    min-width: 120px;
    font-size: 12px;
}}
QComboBox:hover {{ border: 1px solid #3f3f46; }}
QComboBox:focus {{ border: 1px solid {ORANGE}; }}
QComboBox::drop-down {{ border: none; width: 20px; }}
QComboBox QAbstractItemView {{
    background: {PANEL};
    border: 1px solid {BORDER};
    border-radius: 6px;
    selection-background-color: {ORANGE};
    selection-color: #09090b;
    outline: none;
    padding: 4px;
}}

QLineEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 6px;
    padding: 4px 8px;
    font-size: 12px;
    min-height: 24px;
}}
QLineEdit:hover {{ border: 1px solid #3f3f46; }}
QLineEdit:focus {{ border: 1px solid {ORANGE}; }}

/* ---------- checkboxes ---------- */
QCheckBox {{
    spacing: 10px;
    color: {TEXT};
    font-size: 13px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 5px;
    border: 1px solid {BORDER};
    background: {CARD};
}}
QCheckBox::indicator:hover {{
    border: 1px solid #3f3f46;
}}
QCheckBox::indicator:checked {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
}}

/* ---------- text edit / log ---------- */
QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 10px;
    selection-background-color: {ORANGE};
    selection-color: #09090b;
    font-family: "SF Mono", "Consolas", monospace;
    font-size: 12px;
    line-height: 1.5;
}}

/* ---------- status bar ---------- */
QStatusBar {{
    background: {PANEL};
    color: {MUTED};
    border-top: 1px solid {BORDER};
    font-size: 12px;
    padding: 4px 12px;
}}

/* ---------- scroll bars ---------- */
QScrollBar:vertical {{
    background: transparent;
    width: 8px;
    margin: 4px 2px;
}}
QScrollBar::handle:vertical {{
    background: #3f3f46;
    border-radius: 4px;
    min-height: 32px;
}}
QScrollBar::handle:vertical:hover {{
    background: {ORANGE};
}}
QScrollBar::add-line, QScrollBar::sub-line {{
    height: 0;
}}
QScrollBar::add-page, QScrollBar::sub-page {{
    background: transparent;
}}

/* ---------- sidebar ---------- */
QWidget#Sidebar {{
    background: {PANEL};
    border-right: 1px solid {BORDER};
}}
QLabel#SidebarTitle {{
    font-size: 20px;
    font-weight: 700;
    color: {TEXT};
    padding: 4px 0 0 0;
    letter-spacing: -0.5px;
}}
QLabel#SidebarSub {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 400;
    padding: 0 0 4px 0;
}}
QLabel#SidebarFooter {{
    color: {MUTED_DARK};
    font-size: 10px;
    font-weight: 400;
    padding: 8px 0 0 0;
}}
QPushButton#NavBtn {{
    background: transparent;
    border: none;
    border-radius: 8px;
    padding: 8px 12px;
    color: {MUTED};
    font-weight: 500;
    font-size: 13px;
    text-align: left;
    min-height: 0;
    padding-left: 12px;
}}
QPushButton#NavBtn:hover {{
    background: {CARD};
    color: {TEXT};
}}
QPushButton#NavBtn:checked {{
    background: {CARD};
    color: {TEXT};
    font-weight: 600;
    border-left: 2px solid {ORANGE};
}}

/* ---------- top bar ---------- */
QWidget#TopBar {{
    background: {PANEL};
    border-bottom: 1px solid {BORDER};
}}
QLabel#SectionTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {TEXT};
    letter-spacing: -0.3px;
}}
QLabel#StatusPill {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9999px;
    padding: 4px 12px;
    color: {MUTED};
    font-size: 11px;
    font-weight: 500;
}}

/* ---------- labels ---------- */
QLabel {{
    background: transparent;
}}
"""

OVERLAY_STYLESHEET = f"""
QWidget#OverlayBg {{
    background: rgba(14, 14, 14, 0.96);
    border: 1px solid {BORDER};
    border-radius: 16px;
}}
QLabel#Status {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
    border: none;
    letter-spacing: 0.3px;
}}
QTextEdit {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px;
    color: {TEXT};
    selection-background-color: {ORANGE};
    selection-color: #09090b;
    font-size: 12px;
}}
QPushButton {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 6px 10px;
    color: {TEXT};
    font-weight: 600;
    font-size: 12px;
}}
QPushButton:hover {{
    border: 1px solid #3f3f46;
    background: #27272a;
}}
QPushButton#Primary {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #09090b;
    font-weight: 700;
}}
QPushButton#Primary:hover {{
    background: {ORANGE_LIGHT};
    border: 1px solid {ORANGE_LIGHT};
}}
"""

BUBBLE_STYLESHEET = f"""
* {{
    font-family: "SF Pro Display", "SF Pro Text", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 12px;
    color: {TEXT};
}}

QWidget#BubbleCard {{
    background: rgba(14, 14, 14, 0.97);
    border: 1px solid #27272a;
    border-radius: 16px;
}}

QLabel#BubbleTitle {{
    color: {TEXT};
    font-size: 13px;
    font-weight: 600;
    background: transparent;
    letter-spacing: -0.2px;
}}
QLabel#Dot {{ color: {MUTED}; font-size: 10px; background: transparent; }}

QWidget#ChatHost, QWidget#BubbleRow {{ background: transparent; }}

QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}

QLabel#UserBubble {{
    background: {ORANGE};
    color: #09090b;
    border-radius: 14px;
    padding: 7px 12px;
    font-weight: 600;
    font-size: 12px;
}}
QLabel#BotBubble {{
    background: {CARD};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 14px;
    padding: 7px 12px;
    font-size: 12px;
}}

QPushButton#IconBtn {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #09090b;
    font-size: 12px;
    font-weight: 800;
    border-radius: 5px;
    padding: 0px;
}}
QPushButton#IconBtn:hover {{ background: {ORANGE_LIGHT}; color: #09090b; }}

QLabel#MiniBtn {{
    background: {ORANGE};
    color: #09090b;
    border: 1px solid {ORANGE};
    border-radius: 8px;
}}

QPushButton#MicBtn {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    font-size: 14px;
}}
QPushButton#MicBtn:hover {{ border: 1px solid #3f3f46; background: #27272a; }}

QPushButton#Primary {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #09090b;
    border-radius: 10px;
    font-weight: 700;
    font-size: 13px;
}}
QPushButton#Primary:hover {{ background: {ORANGE_LIGHT}; }}

QLineEdit#ChatInput {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 10px;
    padding: 8px 12px;
    color: {TEXT};
    selection-background-color: {ORANGE};
    selection-color: #09090b;
    font-size: 12px;
}}
QLineEdit#ChatInput:focus {{ border: 1px solid {ORANGE}; }}

QPushButton#SendBtn {{
    background: {CARD};
    border: 1px solid {BORDER};
    color: {ORANGE};
    border-radius: 10px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#SendBtn:hover {{ border: 1px solid {ORANGE}; background: #1e1e22; }}

QLabel#MicStatus {{
    color: {MUTED};
    font-size: 11px;
    font-weight: 500;
    background: transparent;
}}
QProgressBar#LevelBar {{
    background: #0a0a0a;
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
    font-size: 12px;
}}
QPushButton#MuteBtn:hover {{ border: 1px solid #3f3f46; background: #27272a; }}
QPushButton#GhostBtn {{
    background: transparent;
    border: 1px solid {BORDER};
    color: {MUTED};
    border-radius: 9px;
    padding: 8px 10px;
    font-weight: 600;
    font-size: 12px;
}}
QPushButton#GhostBtn:hover {{ border: 1px solid #3f3f46; color: {TEXT}; background: #1e1e22; }}

QPushButton#TalkBtn {{
    background: {ORANGE};
    border: 1px solid {ORANGE};
    color: #09090b;
    border-radius: 12px;
    padding: 11px 14px;
    font-size: 13px;
    font-weight: 700;
}}
QPushButton#TalkBtn:hover {{ background: {ORANGE_LIGHT}; }}
QPushButton#TalkBtn[listening="true"] {{
    background: #ef4444;
    border: 1px solid #ef4444;
    color: #ffffff;
}}
QPushButton#TalkBtn:disabled {{ background: #3f3f46; border-color: #3f3f46; color: #71717a; }}

QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: #3f3f46; border-radius: 4px; min-height: 20px; }}
QScrollBar::handle:vertical:hover {{ background: {ORANGE}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}
"""