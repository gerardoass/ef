"""
ui/theme.py
-----------
Paleta dark profesional y estilos ttk para que el Treeview no
desentone con el resto de la interfaz CustomTkinter.
"""
from __future__ import annotations

from tkinter import ttk

# --- Colores -----------------------------------------------------------
BG          = "#0d1117"
BG_ALT      = "#111823"
PANEL       = "#161b22"
PANEL_HI    = "#1c2430"
BORDER      = "#232c38"

ACCENT      = "#00d4aa"
ACCENT_DIM  = "#0e6b5a"
ACCENT_HOVER= "#00b894"

TEXT        = "#e6edf3"
TEXT_DIM    = "#8b949e"
MUTED       = "#5a6672"

OK          = "#3ddc84"
WARN        = "#ffb020"
DANGER      = "#ff4d4d"
INFO        = "#58a6ff"

CONSOLE_BG  = "#05070a"
CONSOLE_FG  = "#39ff88"

FONT        = "Segoe UI"
FONT_MONO   = "Cascadia Mono"
FONT_MONO_FALLBACK = "Consolas"

FONT_H1     = (FONT, 20, "bold")
FONT_H2     = (FONT, 14, "bold")
FONT_BODY   = (FONT, 11)
FONT_SMALL  = (FONT, 9)
FONT_MONO_S = (FONT_MONO, 9)
FONT_MONO_M = (FONT_MONO, 10)

LEVEL_COLORS = {
    "info":  CONSOLE_FG,
    "ok":    OK,
    "warn":  WARN,
    "error": DANGER,
    "cmd":   INFO,
    "dim":   MUTED,
}


def apply_ttk_theme(root) -> None:
    """Estiliza Treeview / Scrollbar para el modo oscuro."""
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except Exception:
        pass

    style.configure(
        "NG.Treeview",
        background=PANEL,
        fieldbackground=PANEL,
        foreground=TEXT,
        rowheight=28,
        borderwidth=0,
        font=(FONT, 10),
    )
    style.configure(
        "NG.Treeview.Heading",
        background=BG_ALT,
        foreground=ACCENT,
        relief="flat",
        borderwidth=0,
        font=(FONT, 10, "bold"),
        padding=(6, 8),
    )
    style.map(
        "NG.Treeview",
        background=[("selected", ACCENT_DIM)],
        foreground=[("selected", "#ffffff")],
    )
    style.map(
        "NG.Treeview.Heading",
        background=[("active", PANEL_HI)],
    )
    style.configure(
        "NG.Vertical.TScrollbar",
        background=PANEL_HI,
        troughcolor=BG_ALT,
        bordercolor=BG_ALT,
        arrowcolor=TEXT_DIM,
        relief="flat",
    )


def category_color(category: str) -> str:
    return {
        "router":  WARN,
        "phone":   INFO,
        "laptop":  ACCENT,
        "desktop": ACCENT,
        "console": "#c792ea",
        "tv":      "#c792ea",
        "iot":     "#7fd1b9",
        "printer": TEXT_DIM,
        "server":  OK,
        "unknown": MUTED,
    }.get(category, TEXT_DIM)