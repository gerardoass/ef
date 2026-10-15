from __future__ import annotations

import queue
import sys
import time
import tkinter as tk
from pathlib import Path

# ----------------------------------------------------------------------
# Ancla de sys.path (misma logica que en app.py)
# ----------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ----------------------------------------------------------------------
# Tema: import absoluto explicito, sin try/except
# ----------------------------------------------------------------------
import ui.theme as theme