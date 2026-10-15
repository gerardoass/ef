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
# Rutas: raiz del proyecto y carpeta ui al frente de sys.path.
# ----------------------------------------------------------------------
_HERE = os.path.abspath(os.path.dirname(__file__))        # <raiz>\ui
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))   # <raiz>
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ----------------------------------------------------------------------
# Imports absolutos explicitos. Cero try/except, cero from . import
# ----------------------------------------------------------------------
import ui.theme as theme
import ui.console as console

from ui.theme import (BG_BASE, BG_CARD, BG_DEEP, BG_ELEV, BG_PANEL, LedDot,
                      NeonButton, NeonFrame, ScanBar, StatCard, bind_tree,
                      device_icon, glyph_icon)

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

# Renombrado obligatorio en el cuerpo del archivo:
#   Console(...)  ->  console.Console(...)