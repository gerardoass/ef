# -*- mode: python ; coding: utf-8 -*-
"""
Spec de PyInstaller para NetGuard.
Empaqueta en un unico .exe sin consola y con manifest UAC admin.

Uso:
    pyinstaller netguard.spec --clean --noconfirm
"""
import sys
from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# scapy necesita sus ficheros de datos (bases de OUI, modulos de capa 2)
scapy_datas, scapy_bins, scapy_hidden = collect_all("scapy")
ctk_datas, ctk_bins, ctk_hidden = collect_all("customtkinter")

hidden = (
    scapy_hidden
    + ctk_hidden
    + collect_submodules("scapy.layers")
    + [
        "scapy.arch.windows",
        "scapy.layers.l2",
        "scapy.layers.inet",
        "scapy.sendrecv",
        "PIL._tkinter_finder",
    ]
)

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=scapy_bins + ctk_bins,
    datas=scapy_datas + ctk_datas,
    hiddenimports=hidden,
    hookspath=[],
    runtime_hooks=[],
    excludes=["matplotlib", "numpy.testing", "pytest", "IPython"],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="NetGuard",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,           # <- oculta la consola de fondo
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    uac_admin=True,          # <- solicita elevacion UAC automaticamente
    icon=None,               # ej: "assets/netguard.ico"
)