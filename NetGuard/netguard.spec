# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec - NetGuard v2.0 (Optimizado)
--------------------------------
Un unico .exe con manifest UAC admin y soporte para Python 3.14+
"""
import os
import sys

from PyInstaller.utils.hooks import collect_all, collect_submodules

# 1. Raiz del proyecto en sys.path (SPECPATH = carpeta del .spec)
_HERE = os.path.abspath(SPECPATH)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

# 2. Dependencias de terceros
scapy_d, scapy_b, scapy_h = collect_all("scapy")
ctk_d, ctk_b, ctk_h = collect_all("customtkinter")
pil_d, pil_b, pil_h = collect_all("PIL")

# 3. Paquetes propios: lista literal + rastreo automatico
_NETGUARD = [
    "ui",
    "ui.app",
    "ui.console",
    "ui.theme",
    "core",
    "core.admin",
    "core.arp",
    "core.flood",
    "core.latency",
    "core.netinfo",
    "core.oui",
    "core.proc",
    "core.scanner",
]

ui_h = collect_submodules("ui")
core_h = collect_submodules("core")

print("[netguard.spec] ui   ->", ui_h)
print("[netguard.spec] core ->", core_h)

hidden = sorted(set(
    scapy_h
    + ctk_h
    + pil_h
    + ui_h
    + core_h
    + _NETGUARD
    + collect_submodules("scapy.layers")
    + [
        "scapy.arch.windows",
        "scapy.layers.l2",
        "scapy.layers.inet",
        "scapy.sendrecv",
        "PIL._tkinter_finder",
    ]
))

# 4. Analisis de dependencias y empaquetado
a = Analysis(
    ["main.py"],
    pathex=[_HERE],
    binaries=scapy_b + ctk_b + pil_b,
    datas=scapy_d + ctk_d + pil_d,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "numpy.testing",
        "pytest",
        "IPython",
        "PyQt5",
        "PyQt6",
        "PySide2",
        "PySide6",
    ],
    noarchive=False,
    optimize=0,
    module_collection_mode={
        "ui": "py",
        "core": "py",
    },
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="NetGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,
    icon="icono.ico",
)
