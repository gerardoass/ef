from __future__ import annotations

import os
import queue
import sys
import time
import tkinter as tk
from pathlib import Path

# ----------------------------------------------------------------------
# Rutas: raiz del proyecto y carpeta ui al frente de sys.path.
# ----------------------------------------------------------------------
_HERE = os.path.abspath(os.path.dirname(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ----------------------------------------------------------------------
# Tema: import absoluto directo
# ----------------------------------------------------------------------
import ui.theme as theme