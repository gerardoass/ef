"""
core/admin.py
-------------
Verificacion y auto-elevacion via UAC. La app necesita admin porque:
  - sendp() de scapy abre el adaptador Npcap en modo raw.
  - taskkill /F sobre procesos nping requiere permisos.
  - La escritura en el registro para IP forwarding.
"""
from __future__ import annotations

import ctypes
import os
import sys


def is_admin() -> bool:
    """True si el proceso corre elevado."""
    if sys.platform.startswith("win"):
        try:
            return bool(ctypes.windll.shell32.IsUserAnAdmin())
        except Exception:
            return False
    try:
        return os.geteuid() == 0
    except Exception:
        return False


def _msgbox(title: str, text: str, flags: int = 0x40) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, text, title, flags)
    except Exception:
        print(f"[{title}] {text}")


def _target_command() -> tuple[str, str]:
    """Devuelve (ejecutable, argumentos) para relanzar elevado."""
    if getattr(sys, "frozen", False):
        # Ejecutable empaquetado con PyInstaller
        return sys.executable, " ".join(f'"{a}"' for a in sys.argv[1:])
    # Script .py interpretado
    script = os.path.abspath(sys.argv[0])
    return sys.executable, f'"{script}"'


def relaunch_as_admin() -> bool:
    """
    Intenta relanzar el proceso elevado.
    Retorna True si el proceso padre debe terminar (el hijo ya arranco).
    """
    exe, params = _target_command()
    try:
        rc = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", exe, params, None, 1
        )
        return rc > 32
    except Exception:
        return False


def ensure_admin(auto_elevate: bool = True) -> bool:
    """
    Garantiza privilegios. Si no se puede elevar, continua en modo
    degradado (el usuario vera el aviso en la barra de estado).
    """
    if is_admin():
        return True

    if auto_elevate and sys.platform.startswith("win"):
        if relaunch_as_admin():
            sys.exit(0)

    _msgbox(
        "NetGuard - Privilegios insuficientes",
        "Ejecuta la aplicacion como Administrador.\n\n"
        "Sin privilegios elevados no se podra:\n"
        "  - Enviar ARP spoof (driver Npcap)\n"
        "  - Terminar procesos de inyeccion\n"
        "  - Habilitar IP forwarding\n\n"
        "La app continuara en modo degradado.",
        0x30,  # icono advertencia
    )
    return False