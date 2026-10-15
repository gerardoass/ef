#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetGuard LAN Console
====================
Panel de control de administracion, monitoreo y diagnostico de red local.

Arranque:
    python main.py

Empaquetado:
    pyinstaller netguard.spec
"""
from __future__ import annotations

import ctypes
import sys


def _set_dpi_awareness() -> None:
    """Evita que Windows escale la GUI y la vuelva borrosa."""
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    _set_dpi_awareness()

    from core import admin

    # Verifica privilegios; si puede, relanza elevado y termina.
    is_admin = admin.ensure_admin(auto_elevate=True)

    from ui.app import run

    try:
        run()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        # En modo --windowed no hay stdout: mostramos el error en un dialogo
        ctypes.windll.user32.MessageBoxW(
            None, f"Error fatal:\n\n{exc}", "NetGuard", 0x10)
        raise


if __name__ == "__main__":
    main()