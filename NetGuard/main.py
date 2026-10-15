#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NetGuard v2.0 - Punto de entrada.

Ancla la raiz del proyecto a sys.path ANTES de cualquier import interno.
Todos los imports del proyecto son absolutos explicitos (import pkg.mod).
"""
from __future__ import annotations

import ctypes
import os
import sys

# ----------------------------------------------------------------------
# ANCLA DE RUTA: antes de cualquier import del proyecto.
# ----------------------------------------------------------------------
def _base_dir() -> str:
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(sys.executable)))
    return os.path.dirname(os.path.abspath(__file__))


_BASE = _base_dir()
if _BASE and _BASE not in sys.path:
    sys.path.insert(0, _BASE)

# ----------------------------------------------------------------------
def _dpi() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def _fatal(msg: str) -> None:
    try:
        ctypes.windll.user32.MessageBoxW(None, msg, "NetGuard - Error fatal", 0x10)
    except Exception:
        print(msg)


# ----------------------------------------------------------------------
def main() -> None:
    _dpi()

    # Todo dentro del try: con console=False, cualquier ImportError
    # muestra MessageBox en vez de morir en silencio.
    try:
        import core.admin as admin
        admin.ensure_admin(auto_elevate=True)

        # RUTA DIRECTA al objeto final del submodulo.
        from ui.app import App
        App().mainloop()

    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        import traceback
        _fatal(f"{exc}\n\n{traceback.format_exc()}")
        raise


if __name__ == "__main__":
    main()