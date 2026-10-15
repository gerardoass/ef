from __future__ import annotations

import os
import sys
import threading
import time
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

# ----------------------------------------------------------------------
# Ancla de sys.path (respaldo: main.py ya lo hace).
# En el bundle __file__ es _MEIPASS/ui/app.py -> parent.parent = raiz.
# ----------------------------------------------------------------------
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

# ----------------------------------------------------------------------
# Imports internos: ABSOLUTOS EXPLICITOS.
# `import paquete.modulo` es la unica forma que el analizador de
# PyInstaller indexa sin ambiguedad. Nada de try/except.
# ----------------------------------------------------------------------
import ui.theme as theme
from ui.theme import (BG_BASE, BG_CARD, BG_DEEP, BG_ELEV, BG_PANEL, LedDot,
                      NeonButton, NeonFrame, ScanBar, StatCard, bind_tree,
                      device_icon, glyph_icon)

from ui.console import Console

import core.admin as admin
import core.arp as arp
import core.flood as flood
import core.latency as latency
import core.netinfo as netinfo
import core.oui as oui
import core.proc as proc
import core.scanner as scanner
from core.scanner import Device, State

APP = "NETGUARD"
VER = "2.0"