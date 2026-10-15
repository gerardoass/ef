"""
core/admin.py
-------------
Verificacion y auto-elevacion UAC. Imprescindible: los sockets raw
de Npcap y TerminateProcess requieren token elevado.
"""
from __future__ import annotations

import ctypes
import os
import sys


def is_admin() -> bool:
    if sys.platform.startswith("win"):
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    try:
        return os.geteuid() == 0
    except Exception:
        return False


def _msgbox(title: str, text: str, flags: int = 0x30) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        print(f"[{title}] {text}")


def _cmdline() -> tuple[str, str]:
    if getattr(sys, "frozen", False):
        return sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    return sys.executable, f'"{os.path.abspath(sys.argv[0])}"'


def relaunch_as_admin() -> bool:
    exe, params = _cmdline()
    try:
        return ctypes.windll.shell32.ShellExecuteW(None, "runas", exe, params, None, 1) > 32
    except Exception:
        return False


def ensure_admin(auto_elevate: bool = True) -> bool:
    if is_admin():
        return True
    if auto_elevate and sys.platform.startswith("win") and relaunch_as_admin():
        sys.exit(0)
    _msgbox(
        "NetGuard - Privilegios insuficientes",
        "Ejecuta como Administrador para habilitar:\n"
        "  - Sockets raw / Npcap (escaneo L2 y ARP storm)\n"
        "  - Terminacion instantanea de procesos\n"
        "  - IP forwarding para modo MITM",
    )
    return False