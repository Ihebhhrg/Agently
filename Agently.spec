# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

APP_NAME = "Agently"

datas = [
    ("app.ico", "."),
    ("config.default.ini", "."),
]
binaries = []
hiddenimports = [
    "win32com.client", "pythoncom", "pywintypes", "win32api",
    "win32gui", "win32process", "win32con", "win32crypt",
    "pyautogui", "mss", "psutil", "requests", "qrcode",
]

for _pkg in ("rapidocr_onnxruntime", "onnxruntime", "ctranslate2", "av", "sounddevice"):
    try:
        _d, _b, _h = collect_all(_pkg)
        datas += _d
        binaries += _b
        hiddenimports += _h
    except Exception:
        pass

excludes = [
    "tkinter", "scipy", "torch", "matplotlib", "IPython", "pytest",
    "uiautomation", "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets",
    "PySide6.QtWebEngineQuick", "PySide6.QtQml", "PySide6.QtQuick",
    "PySide6.QtQuickWidgets", "PySide6.QtQuick3D", "PySide6.Qt3DCore",
    "PySide6.Qt3DRender", "PySide6.Qt3DInput", "PySide6.Qt3DLogic",
    "PySide6.Qt3DAnimation", "PySide6.Qt3DExtras", "PySide6.QtCharts",
    "PySide6.QtPdf", "PySide6.QtPdfWidgets", "PySide6.QtMultimedia",
    "PySide6.QtMultimediaWidgets", "PySide6.QtDataVisualization",
    "PySide6.QtDesigner", "PySide6.QtBluetooth", "PySide6.QtNfc",
    "PySide6.QtSensors", "PySide6.QtSerialPort", "PySide6.QtTest",
    "PySide6.QtHelp", "PySide6.QtSql", "PySide6.QtRemoteObjects",
    "PySide6.QtScxml", "PySide6.QtWebSockets", "PySide6.QtWebChannel",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon="app.ico",
    version="version_info.txt",
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name=APP_NAME,
)
