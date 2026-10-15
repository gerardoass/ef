"""
ui/theme.py
-----------
Sistema de diseno completo: paleta cyberpunk, estilos ttk, fabrica de
iconos vectoriales en runtime (PIL) y widgets de neon animados.
"""
from __future__ import annotations

import math
import tkinter as tk
from tkinter import ttk

import customtkinter as ctk
from PIL import Image, ImageDraw

# ======================================================================
# PALETA
# ======================================================================
BG_DEEP = "#03050a"
BG_BASE = "#060a12"
BG_PANEL = "#0a1018"
BG_CARD = "#0c1420"
BG_ELEV = "#101a28"

NEON_BLUE = "#00d4ff"
NEON_BLUE_D = "#0a6b82"
NEON_AMBER = "#ffa62b"
NEON_FIRE = "#ff4d1c"
NEON_FIRE_D = "#8a2409"
NEON_RED = "#ff2d55"
NEON_GREEN = "#00ff9d"
NEON_GREEN_D = "#0a6b47"
NEON_PURPLE = "#b14aed"
NEON_CYAN_D = "#0d3b47"

TEXT = "#dceaf7"
TEXT_MID = "#8aa8c2"
TEXT_DIM = "#4d6a85"
MUTED = "#2c3f52"

BORDER = "#16283a"
BORDER_HI = "#1e3d55"

CONSOLE_BG = "#02040a"
CONSOLE_FG = "#5ef2c0"

FONT = "Segoe UI"
FONT_MONO = "Cascadia Mono"
FONT_MONO_FB = "Consolas"

LEVEL_COLOR = {
    "info": "#4fd1c5", "ok": NEON_GREEN, "warn": NEON_AMBER,
    "error": NEON_RED, "cmd": NEON_BLUE, "dim": TEXT_DIM, "fire": NEON_FIRE,
}

CAT_COLOR = {
    "router": NEON_AMBER, "phone": NEON_BLUE, "laptop": "#4fd1c5",
    "desktop": NEON_GREEN, "console": NEON_PURPLE, "tv": "#c792ea",
    "iot": "#7fd1b9", "printer": TEXT_MID, "server": "#58a6ff",
    "unknown": TEXT_DIM,
}

STATE_COLOR = {
    "online": NEON_GREEN, "self": NEON_BLUE, "gateway": NEON_AMBER,
    "isolated": NEON_FIRE, "flooded": NEON_RED,
}


def cat_color(c: str) -> str:
    return CAT_COLOR.get(c, TEXT_DIM)


def state_color(s: str) -> str:
    return STATE_COLOR.get(s, TEXT_DIM)


def dim(hex_color: str, factor: float = 0.32) -> str:
    try:
        h = hex_color.lstrip("#")
        r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
        return "#%02x%02x%02x" % (int(r * factor), int(g * factor), int(b * factor))
    except Exception:
        return hex_color


# ======================================================================
# ICONOS VECTORIALES (PIL -> CTkImage)
# ======================================================================
_ICONS: dict[tuple, ctk.CTkImage] = {}


def _P(v: float, S: int) -> int:
    return int(v * S)


def _glyph(cat: str, S: int, col: str) -> Image.Image:
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, S // 14)
    c = col

    def rr(x0, y0, x1, y1, r, fill=None, outline=None, width=1):
        d.rounded_rectangle([_P(x0, S), _P(y0, S), _P(x1, S), _P(y1, S)],
                            radius=_P(r, S), fill=fill, outline=outline, width=width)

    if cat == "phone":
        rr(.30, .07, .70, .93, .09, outline=c, width=w)
        d.line([_P(.42, .14, S), _P(.58, .14, S)], fill=c, width=w)
        d.line([_P(.43, .87, S), _P(.57, .87, S)], fill=c, width=w)
    elif cat == "laptop":
        rr(.17, .18, .83, .66, .04, outline=c, width=w)
        d.polygon([(_P(.08, .66, S), _P(.92, .66, S)),
                   (_P(.86, .80, S), _P(.14, .80, S))], outline=c, width=w)
        d.line([_P(.40, .73, S), _P(.60, .73, S)], fill=c, width=w)
    elif cat == "desktop":
        rr(.13, .12, .87, .62, .04, outline=c, width=w)
        d.line([_P(.50, .62, S), _P(.50, .78, S)], fill=c, width=w)
        d.line([_P(.30, .80, S), _P(.70, .80, S)], fill=c, width=w)
        d.rectangle([_P(.20, .20, S), _P(.80, .54, S)], outline=dim(c, .5), width=max(1, w - 2))
    elif cat == "router":
        rr(.10, .54, .90, .84, .06, outline=c, width=w)
        d.line([_P(.26, .54, S), _P(.18, .22, S)], fill=c, width=w)
        d.line([_P(.74, .54, S), _P(.82, .22, S)], fill=c, width=w)
        for i, rad in enumerate((.10, .18, .26)):
            d.arc([_P(.50 - rad, .34 - rad, S), _P(.50 + rad, .34 + rad, S)],
                  start=200, end=340, fill=dim(c, .9 - i * .22), width=max(1, w - 1))
        d.ellipse([_P(.20, .62, S), _P(.28, .70, S)], fill=dim(c, .7))
        d.ellipse([_P(.32, .62, S), _P(.40, .70, S)], fill=dim(c, .5))
    elif cat == "printer":
        rr(.20, .38, .80, .78, .05, outline=c, width=w)
        rr(.32, .12, .68, .40, .02, outline=c, width=w)
        rr(.30, .62, .70, .90, .02, outline=c, width=w)
        d.ellipse([_P(.68, .45, S), _P(.75, .52, S)], fill=c)
    elif cat == "tv":
        rr(.08, .18, .92, .68, .05, outline=c, width=w)
        d.line([_P(.50, .68, S), _P(.50, .82, S)], fill=c, width=w)
        d.line([_P(.32, .84, S), _P(.68, .84, S)], fill=c, width=w)
    elif cat == "console":
        rr(.08, .34, .92, .74, .16, outline=c, width=w)
        d.line([_P(.26, .54, S), _P(.36, .54, S)], fill=c, width=w)
        d.line([_P(.31, .47, S), _P(.31, .61, S)], fill=c, width=w)
        d.ellipse([_P(.62, .46, S), _P(.70, .54, S)], fill=c)
        d.ellipse([_P(.74, .56, S), _P(.82, .64, S)], fill=dim(c, .6))
    elif cat == "iot":
        d.ellipse([_P(.28, .28, S), _P(.72, .72, S)], outline=c, width=w)
        for a in (0, 120, 240):
            r = math.radians(a)
            d.ellipse([_P(.50 + .34 * math.cos(r) - .05, .50 + .34 * math.sin(r) - .05, S),
                       _P(.50 + .34 * math.cos(r) + .05, .50 + .34 * math.sin(r) + .05, S)],
                      outline=c, width=max(1, w - 1))
    elif cat == "server":
        for i, y in enumerate((.10, .38, .66)):
            rr(.14, y, .86, y + .22, .03, outline=c, width=w)
            d.ellipse([_P(.19, y + .07, S), _P(.26, y + .14, S)], fill=dim(c, .9 - i * .2))
    else:
        d.ellipse([_P(.14, .14, S), _P(.86, .86, S)], outline=c, width=w)
        d.ellipse([_P(.44, .44, S), _P(.56, .56, S)], fill=c)

    return img


def device_icon(cat: str, size: int = 36, color: str | None = None) -> ctk.CTkImage:
    key = (cat, size, color)
    if key in _ICONS:
        return _ICONS[key]
    col = color or cat_color(cat)
    img = _glyph(cat, size * 4, col).resize((size, size), Image.LANCZOS)
    ck = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _ICONS[key] = ck
    return ck


def glyph_icon(kind: str, size: int = 20, color: str = TEXT_MID) -> ctk.CTkImage:
    """Iconos de UI: radar, bolt, shield, target, pulse, cpu, gear."""
    key = ("ui", kind, size, color)
    if key in _ICONS:
        return _ICONS[key]
    S = size * 4
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    w = max(2, S // 12)

    if kind == "radar":
        d.ellipse([_P(.08, .08, S), _P(.92, .92, S)], outline=color, width=w)
        d.ellipse([_P(.30, .30, S), _P(.70, .70, S)], outline=dim(color, .6), width=w)
        d.ellipse([_P(.46, .46, S), _P(.54, .54, S)], fill=color)
        d.line([_P(.50, .50, S), _P(.86, .22, S)], fill=color, width=w)
    elif kind == "bolt":
        d.polygon([(_P(.58, .06, S), _P(.24, .54, S)), (_P(.46, .54, S), _P(.40, .94, S)),
                   (_P(.76, .44, S), (_P(.54, .44, S)), (_P(.60, .06, S))],
                  fill=color)
    elif kind == "shield":
        d.polygon([(_P(.50, .06, S), _P(.90, .24, S)), (_P(.90, .56, S)),
                   (_P(.50, .94, S)), (_P(.10, .56, S)), (_P(.10, .24, S))],
                  outline=color, width=w)
    elif kind == "target":
        d.ellipse([_P(.08, .08, S), _P(.92, .92, S)], outline=color, width=w)
        d.ellipse([_P(.36, .36, S), _P(.64, .64, S)], fill=color)
    elif kind == "pulse":
        pts = [(.04, .5), (.24, .5), (.34, .18), (.46, .84), (.58, .34), (.68, .5), (.96, .5)]
        d.line([(_P(x, S), _P(y, S)) for x, y in pts], fill=color, width=w, joint="curve")
    elif kind == "gear":
        d.ellipse([_P(.30, .30, S), _P(.70, .70, S)], outline=color, width=w)
        d.ellipse([_P(.44, .44, S), _P(.56, .56, S)], fill=color)
        for a in range(0, 360, 45):
            r = math.radians(a)
            d.line([_P(.50 + .34 * math.cos(r), .50 + .34 * math.sin(r), S),
                    _P(.50 + .46 * math.cos(r), .50 + .46 * math.sin(r), S)],
                   fill=color, width=w)
    else:
        d.ellipse([_P(.12, .12, S), _P(.88, .88, S)], outline=color, width=w)

    img = img.resize((size, size), Image.LANCZOS)
    ck = ctk.CTkImage(light_image=img, dark_image=img, size=(size, size))
    _ICONS[key] = ck
    return ck


# ======================================================================
# WIDGETS DE NEON
# ======================================================================
class LedDot(tk.Canvas):
    """LED con halo y parpadeo."""

    def __init__(self, master, color: str = NEON_GREEN, size: int = 12, blink: bool = True):
        super().__init__(master, width=size, height=size, bg=master.cget("fg_color")
                         if isinstance(master, ctk.CTkFrame) else BG_BASE,
                         highlightthickness=0, bd=0)
        self._size = size
        self._color = color
        self._blink = blink
        self._on = True
        self._job = None
        self._draw()
        if blink:
            self._cycle()

    def _draw(self) -> None:
        self.delete("all")
        s = self._size
        col = self._color if self._on else dim(self._color, .25)
        halo = dim(self._color, .22) if self._on else dim(self._color, .07)
        self.create_oval(0, 0, s, s, fill=halo, outline="")
        m = s * 0.26
        self.create_oval(m, m, s - m, s - m, fill=col, outline="")

    def _cycle(self) -> None:
        if not self._blink:
            return
        self._on = not self._on
        self._draw()
        self._job = self.after(650, self._cycle)

    def set_color(self, color: str, blink: bool | None = None) -> None:
        self._color = color
        if blink is not None:
            self._blink = blink
        self._on = True
        self._draw()

    def set_blink(self, on: bool) -> None:
        self._blink = on
        self._on = True
        self._draw()
        if on and self._job is None:
            self._cycle()
        elif not on and self._job:
            try:
                self.after_cancel(self._job)
            except Exception:
                pass
            self._job = None


class NeonFrame(ctk.CTkFrame):
    """Frame con borde neon pulsante."""

    def __init__(self, master, glow: str = NEON_BLUE, pulse: bool = False,
                 period: int = 1400, **kw):
        kw.setdefault("fg_color", BG_PANEL)
        kw.setdefault("corner_radius", 14)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", glow)
        super().__init__(master, **kw)
        self._glow = glow
        self._pulse = pulse
        self._period = period
        self._phase = 0.0
        self._job = None
        if pulse:
            self._animate()

    def set_glow(self, color: str, pulse: bool | None = None) -> None:
        self._glow = color
        if pulse is not None:
            self._pulse = pulse
        try:
            self.configure(border_color=color)
        except Exception:
            pass
        if self._pulse and self._job is None:
            self._animate()

    def flash(self, times: int = 4) -> None:
        self._flash(times)

    def _flash(self, n: int) -> None:
        if n <= 0:
            try:
                self.configure(border_color=self._glow)
            except Exception:
                pass
            return
        try:
            self.configure(border_color="#ffffff" if n % 2 else self._glow)
        except Exception:
            pass
        self.after(90, lambda: self._flash(n - 1))

    def _animate(self) -> None:
        if not self._pulse:
            self._job = None
            return
        self._phase += 0.11
        k = 0.5 + 0.5 * math.sin(self._phase)
        try:
            self.configure(border_color=dim(self._glow, 0.35 + 0.65 * k))
        except Exception:
            pass
        self._job = self.after(self._period // 22, self._animate)


class NeonButton(ctk.CTkButton):
    def __init__(self, master, glow: str = NEON_BLUE, **kw):
        kw.setdefault("fg_color", dim(glow, .22))
        kw.setdefault("hover_color", dim(glow, .42))
        kw.setdefault("text_color", glow)
        kw.setdefault("corner_radius", 10)
        kw.setdefault("border_width", 1)
        kw.setdefault("border_color", dim(glow, .55))
        kw.setdefault("font", (FONT, 11, "bold"))
        super().__init__(master, **kw)
        self._glow = glow


class ScanBar(tk.Canvas):
    """Barra de progreso con barrido luminoso animado."""

    def __init__(self, master, height: int = 4, color: str = NEON_BLUE, **kw):
        super().__init__(master, height=height, bg=BG_PANEL, highlightthickness=0, bd=0, **kw)
        self._h = height
        self._color = color
        self._value = 0.0
        self._pos = 0.0
        self._mode = "idle"
        self._job = None
        self.bind("<Configure>", lambda e: self._render())

    def set(self, v: float) -> None:
        self._value = max(0.0, min(1.0, v))
        self._mode = "value"
        self._render()

    def start(self) -> None:
        self._mode = "sweep"
        if self._job is None:
            self._step()

    def stop(self) -> None:
        self._mode = "idle"
        self._render()

    def set_color(self, color: str) -> None:
        self._color = color
        self._render()

    def _step(self) -> None:
        if self._mode != "sweep":
            self._job = None
            return
        self._pos += 0.035
        if self._pos > 1.35:
            self._pos = -0.35
        self._render()
        self._job = self.after(16, self._step)

    def _render(self) -> None:
        self.delete("all")
        w = self.winfo_width() or 300
        h = self._h
        self.create_rectangle(0, 0, w, h, fill=dim(self._color, .12), outline="")
        if self._mode == "sweep":
            bw = max(60, w * 0.28)
            x0 = self._pos * w
            for i in range(8):
                seg = bw / 8
                a = 1 - i / 9
                self.create_rectangle(x0 + i * seg, 0, x0 + (i + 1) * seg, h,
                                      fill=dim(self._color, .25 + .75 * a), outline="")
        else:
            self.create_rectangle(0, 0, w * self._value, h,
                                  fill=self._color, outline="")


class StatCard(ctk.CTkFrame):
    def __init__(self, master, title: str, value: str = "-", accent: str = NEON_BLUE,
                 icon: str | None = None, **kw):
        super().__init__(master, fg_color=BG_CARD, corner_radius=12,
                         border_width=1, border_color=dim(accent, .35), **kw)
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 0))
        if icon:
            ctk.CTkLabel(top, text="", image=glyph_icon(icon, 16, accent)).pack(side="left")
        ctk.CTkLabel(top, text=title.upper(), font=(FONT, 9, "bold"),
                     text_color=TEXT_DIM).pack(side="left", padx=(6 if icon else 0, 0))
        self.value = ctk.CTkLabel(self, text=value, font=(FONT_MONO, 15, "bold"),
                                  text_color=accent, anchor="w")
        self.value.pack(fill="x", padx=14, pady=(4, 12))

    def set(self, text: str, color: str | None = None) -> None:
        self.value.configure(text=text)
        if color:
            self.value.configure(text_color=color)


def apply_ttk(root) -> None:
    st = ttk.Style(root)
    try:
        st.theme_use("clam")
    except Exception:
        pass
    st.configure("NG.Treeview", background=BG_CARD, fieldbackground=BG_CARD,
                 foreground=TEXT, rowheight=28, borderwidth=0, font=(FONT, 10))
    st.configure("NG.Treeview.Heading", background=BG_ELEV, foreground=NEON_BLUE,
                 relief="flat", borderwidth=0, font=(FONT, 10, "bold"), padding=(6, 8))
    st.map("NG.Treeview", background=[("selected", NEON_CYAN_D)],
           foreground=[("selected", "#ffffff")])
    st.configure("NG.Vertical.TScrollbar", background=BG_ELEV, troughcolor=BG_PANEL,
                 bordercolor=BG_PANEL, arrowcolor=TEXT_DIM, relief="flat")


def bind_tree(widget, seq: str, cb) -> None:
    """Enlaza un evento a un widget y a todos sus descendientes."""
    widget.bind(seq, cb)
    for child in widget.winfo_children():
        bind_tree(child, seq, cb)