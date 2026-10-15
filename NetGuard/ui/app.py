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
# Rutas del proyecto al frente de sys.path (dev y _MEIPASS).
# ----------------------------------------------------------------------
_HERE = os.path.abspath(os.path.dirname(__file__))
_ROOT = os.path.abspath(os.path.join(_HERE, os.pardir))
for _p in (_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

# ----------------------------------------------------------------------
# Subpaquetes hermanos: import relativo explicito.
# El namespace `ui` ya esta vivo cuando se ejecuta este modulo.
# ----------------------------------------------------------------------
from . import theme
from . import console

# ----------------------------------------------------------------------
# Nucleo de red
# ----------------------------------------------------------------------
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

# ----------------------------------------------------------------------
# Renombrados obligatorios en el cuerpo del archivo:
#   CONSOLE_BG / CONSOLE_FG   ->  theme.CONSOLE_BG / theme.CONSOLE_FG
#   BG_BASE / BG_CARD / ...   ->  theme.BG_BASE / theme.BG_CARD / ...
#   LedDot / NeonFrame / ...  ->  theme.LedDot / theme.NeonFrame / ...
#   dim() / cat_color() / ... ->  theme.dim() / theme.cat_color() / ...
#   Console(...)              ->  console.Console(...)
# ----------------------------------------------------------------------  

# ======================================================================
# VENTANA PRINCIPAL
# ======================================================================
class App:
    """Interfaz principal de NetGuard."""

    PUMP_MS = 80

    def __init__(self, master):
        self.master = master
        self.master.title(f"{APP}  v{VER}")
        self.master.geometry("1360x820")
        self.master.minsize(1120, 680)
        self.master.configure(bg=theme.BG_DEEP)

        theme.apply_ttk(self.master)

        self._lock = threading.Lock()
        self._events = []
        self._devices = {}
        self._rows = {}
        self._worker = None
        self._stop = threading.Event()

        self._local = "-"
        self._gateway = "-"
        self._cidr = None
        self._latency = "-"

        self._build_header()
        self._build_stats()
        self._build_toolbar()
        self._build_workspace()
        self._build_console()

        self.master.protocol("WM_DELETE_WINDOW", self._on_close)
        self.master.after(self.PUMP_MS, self._pump)

        self._load_netinfo()
        self.log("info", f"{APP} v{VER} inicializado.")
        self.log("cmd", "Listo. Pulsa ESCANEAR para descubrir la red.")

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------
    @staticmethod
    def _call(module, name, default, *args):
        fn = getattr(module, name, None)
        if fn is None:
            return default
        try:
            return fn(*args)
        except Exception:
            return default

    @staticmethod
    def _state_name(dev) -> str:
        state = getattr(dev, "state", None)
        if isinstance(state, State):
            return state.name.lower()
        return str(state or "online").lower()

    def log(self, level: str, msg: str) -> None:
        sink = getattr(self.console, "write", None) or getattr(self.console, "log", None)
        if sink is not None:
            sink(level, msg)

    def _post(self, kind: str, *payload) -> None:
        with self._lock:
            self._events.append((kind,) + payload)

    def _pump(self) -> None:
        with self._lock:
            events, self._events = self._events, []
        for ev in events:
            self._dispatch(ev)
        self.master.after(self.PUMP_MS, self._pump)

    def _dispatch(self, ev) -> None:
        kind = ev[0]
        if kind == "device":
            self._add_device(ev[1])
        elif kind == "progress":
            done, total = ev[1], ev[2]
            self.scanbar.set(done / total if total else 0.0)
        elif kind == "log":
            self.log(ev[1], ev[2])
        elif kind == "latency":
            self._latency = f"{ev[2]} ms"
            self.cards["latencia"].set(self._latency, theme.NEON_PURPLE)
            self._render_detail()
        elif kind == "error":
            self.log("error", ev[1])
        elif kind == "done":
            self._finish_scan()

    def _selected(self):
        sel = self.tree.selection()
        if not sel:
            return None
        for mac, iid in self._rows.items():
            if iid == sel[0]:
                return self._devices.get(mac)
        return None

    # ------------------------------------------------------------------
    # CONSTRUCCION DE LA INTERFAZ
    # ------------------------------------------------------------------
    def _build_header(self) -> None:
        bar = theme.NeonFrame(self.master, glow=theme.NEON_BLUE, pulse=True)
        bar.pack(fill="x", padx=14, pady=(14, 8))

        left = ctk.CTkFrame(bar, fg_color="transparent")
        left.pack(side="left", padx=16, pady=12)
        ctk.CTkLabel(left, text="", image=theme.glyph_icon("shield", 30, theme.NEON_BLUE)).pack(side="left")
        ctk.CTkLabel(left, text=APP, font=(theme.FONT, 22, "bold"),
                     text_color=theme.NEON_BLUE).pack(side="left", padx=(10, 8))
        ctk.CTkLabel(left, text=f"v{VER}", font=(theme.FONT, 11),
                     text_color=theme.TEXT_DIM).pack(side="left", pady=(8, 0))

        right = ctk.CTkFrame(bar, fg_color="transparent")
        right.pack(side="right", padx=16, pady=12)
        self.led = theme.LedDot(right, color=theme.NEON_AMBER, size=14)
        self.led.pack(side="right", padx=(10, 0))
        self.status = ctk.CTkLabel(right, text="EN ESPERA", font=(theme.FONT_MONO, 11, "bold"),
                                   text_color=theme.NEON_AMBER)
        self.status.pack(side="right")

    def _build_stats(self) -> None:
        row = ctk.CTkFrame(self.master, fg_color="transparent")
        row.pack(fill="x", padx=14, pady=(0, 8))

        specs = (
            ("dispositivos", "Dispositivos", "0", theme.NEON_BLUE, "radar"),
            ("activos", "Activos", "0", theme.NEON_GREEN, "pulse"),
            ("gateway", "Puerta de enlace", "-", theme.NEON_AMBER, "target"),
            ("latencia", "Latencia", "-", theme.NEON_PURPLE, "bolt"),
        )
        self.cards = {}
        for i, (key, title, val, accent, icon) in enumerate(specs):
            card = theme.StatCard(row, title=title, value=val, accent=accent, icon=icon)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 8, 0))
            row.grid_columnconfigure(i, weight=1)
            self.cards[key] = card

    def _build_toolbar(self) -> None:
        bar = ctk.CTkFrame(self.master, fg_color="transparent")
        bar.pack(fill="x", padx=14, pady=(0, 8))

        self.btn_scan = theme.NeonButton(bar, text="ESCANEAR", glow=theme.NEON_GREEN,
                                         width=130, command=self.on_scan)
        self.btn_scan.pack(side="left")
        self.btn_stop = theme.NeonButton(bar, text="DETENER", glow=theme.NEON_FIRE,
                                         width=110, command=self.on_stop)
        self.btn_stop.pack(side="left", padx=8)
        self.btn_arp = theme.NeonButton(bar, text="ARP SPOOF", glow=theme.NEON_BLUE,
                                        width=120, command=self.on_arp)
        self.btn_arp.pack(side="left", padx=(0, 8))
        self.btn_flood = theme.NeonButton(bar, text="FLOOD", glow=theme.NEON_PURPLE,
                                          width=110, command=self.on_flood)
        self.btn_flood.pack(side="left")

        theme.NeonButton(bar, text="EXPORTAR", glow=theme.NEON_AMBER,
                         width=110, command=self.on_export).pack(side="right")
        theme.NeonButton(bar, text="LIMPIAR", glow=theme.TEXT_MID,
                         width=100, command=self.on_clear).pack(side="right", padx=8)

        self.scanbar = theme.ScanBar(self.master, height=4, color=theme.NEON_BLUE)
        self.scanbar.pack(fill="x", padx=14, pady=(0, 8))

    def _build_workspace(self) -> None:
        wrap = ctk.CTkFrame(self.master, fg_color="transparent")
        wrap.pack(fill="both", expand=True, padx=14)

        pane = tk.PanedWindow(wrap, orient="horizontal", bg=theme.BG_DEEP,
                              sashwidth=6, bd=0, highlightthickness=0)
        pane.pack(fill="both", expand=True)

        left = theme.NeonFrame(pane, glow=theme.NEON_BLUE)
        right = theme.NeonFrame(pane, glow=theme.NEON_PURPLE, width=380)
        pane.add(left, stretch="always")
        pane.add(right)

        cols = ("ip", "mac", "vendor", "host", "state")
        widths = (130, 150, 220, 190, 110)
        heads = ("IP", "MAC", "FABRICANTE", "HOST", "ESTADO")
        anchors = ("w", "w", "w", "w", "center")

        self.tree = ttk.Treeview(left, columns=cols, show="headings", style="NG.Treeview")
        for cid, txt, w, anc in zip(cols, heads, widths, anchors):
            self.tree.heading(cid, text=txt)
            self.tree.column(cid, width=w, anchor=anc, stretch=True)

        vsb = ttk.Scrollbar(left, orient="vertical", style="NG.Vertical.TScrollbar",
                            command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y", padx=(0, 6), pady=6)
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)

        theme.bind_tree(self.tree, "<ButtonRelease-1>", lambda e: self._render_detail())

        head = ctk.CTkFrame(right, fg_color="transparent")
        head.pack(fill="x", padx=14, pady=(14, 4))
        self.detail_icon = ctk.CTkLabel(head, text="", image=theme.glyph_icon("cpu", 34, theme.NEON_PURPLE))
        self.detail_icon.pack(side="left")
        self.detail_title = ctk.CTkLabel(head, text="SIN SELECCION", font=(theme.FONT, 12, "bold"),
                                         text_color=theme.TEXT_MID)
        self.detail_title.pack(side="left", padx=10)

        self.detail = {}
        for key, label in (("ip", "IP"), ("mac", "MAC"), ("vendor", "FABRICANTE"),
                           ("host", "HOST"), ("state", "ESTADO")):
            line = ctk.CTkFrame(right, fg_color=theme.BG_CARD, corner_radius=8)
            line.pack(fill="x", padx=14, pady=3)
            ctk.CTkLabel(line, text=label, font=(theme.FONT, 9, "bold"),
                         text_color=theme.TEXT_DIM, width=90, anchor="w").pack(side="left", padx=10, pady=6)
            value = ctk.CTkLabel(line, text="-", font=(theme.FONT_MONO, 11),
                                 text_color=theme.TEXT, anchor="w")
            value.pack(side="left", padx=(0, 10))
            self.detail[key] = value

        acts = ctk.CTkFrame(right, fg_color="transparent")
        acts.pack(fill="x", padx=14, pady=14)
        theme.NeonButton(acts, text="PING", glow=theme.NEON_PURPLE, width=100,
                         command=self.on_ping).pack(side="left")
        theme.NeonButton(acts, text="AISLAR", glow=theme.NEON_FIRE, width=100,
                         command=self.on_arp).pack(side="left", padx=8)
        theme.NeonButton(acts, text="FLOOD", glow=theme.NEON_RED, width=100,
                         command=self.on_flood).pack(side="left")

    def _build_console(self) -> None:
        self.console = console.Console(self.master)
        self.console.pack(fill="x", padx=14, pady=(8, 14))

    # ------------------------------------------------------------------
    # ESTADO / DETALLE
    # ------------------------------------------------------------------
    def _load_netinfo(self) -> None:
        self._local = self._call(netinfo, "local_ip", "-")
        self._gateway = self._call(netinfo, "gateway", "-")
        self._cidr = self._call(netinfo, "cidr", None) or self._call(netinfo, "subnet", None)

        self.cards["gateway"].set(self._gateway, theme.NEON_AMBER)
        self.log("info", f"Interfaz local: {self._local}")
        self.log("info", f"Puerta de enlace: {self._gateway}")
        self.log("info", f"Subred: {self._cidr or 'desconocida'}")

    def _render_detail(self) -> None:
        dev = self._selected()
        if dev is None:
            self.detail_title.configure(text="SIN SELECCION", text_color=theme.TEXT_MID)
            for value in self.detail.values():
                value.configure(text="-")
            return

        mac = (getattr(dev, "mac", "") or "-").upper()
        state = self._state_name(dev)
        cat = getattr(dev, "category", "unknown")

        self.detail_icon.configure(image=theme.device_icon(cat, 34))
        self.detail_title.configure(text=cat.upper(), text_color=theme.cat_color(cat))
        self.detail["ip"].configure(text=getattr(dev, "ip", "-"))
        self.detail["mac"].configure(text=mac)
        self.detail["vendor"].configure(text=getattr(dev, "vendor", "") or "-")
        self.detail["host"].configure(text=getattr(dev, "hostname", "") or "-")
        self.detail["state"].configure(text=state.upper(), text_color=theme.state_color(state))

    def _add_device(self, dev) -> None:
        if not isinstance(dev, Device):
            return
        mac = (getattr(dev, "mac", "") or "").upper()
        if not mac or mac in self._rows:
            return

        ip = getattr(dev, "ip", "-")
        vendor = getattr(dev, "vendor", "") or self._call(oui, "vendor", "Desconocido", mac)
        host = getattr(dev, "hostname", "") or "-"
        state = self._state_name(dev)

        iid = self.tree.insert("", "end", values=(ip, mac, vendor, host, state.upper()))
        self.tree.tag_configure(state, foreground=theme.state_color(state))
        self.tree.item(iid, tags=(state,))

        self._rows[mac] = iid
        self._devices[mac] = dev

        self.cards["dispositivos"].set(str(len(self._devices)), theme.NEON_BLUE)
        if state in ("online", "self", "gateway"):
            self.cards["activos"].set(str(self._count_active()), theme.NEON_GREEN)
        self.log("ok", f"{ip}  {mac}  {vendor}")

    def _count_active(self) -> int:
        return sum(1 for d in self._devices.values() if self._state_name(d) in ("online", "self", "gateway"))

    # ------------------------------------------------------------------
    # ACCIONES
    # ------------------------------------------------------------------
    def on_scan(self) -> None:
        if self._worker is not None and self._worker.is_alive():
            self.log("warn", "Ya hay un escaneo en curso.")
            return
        if not self._cidr:
            messagebox.showwarning(APP, "No se pudo determinar la subred local.")
            return

        self._stop.clear()
        self.btn_scan.configure(state="disabled")
        self.btn_stop.configure(state="normal")
        self.status.configure(text="ESCANEANDO", text_color=theme.NEON_GREEN)
        self.led.set_color(theme.NEON_GREEN, blink=True)
        self.scanbar.set_color(theme.NEON_GREEN)
        self.scanbar.start()
        self.log("cmd", f"scan {self._cidr}")

        self._worker = threading.Thread(target=self._worker_scan, args=(self._cidr,), daemon=True)
        self._worker.start()

    def _worker_scan(self, cidr: str) -> None:
        try:
            scanner.scan(cidr,
                         on_device=self._on_device_cb,
                         on_progress=self._on_progress_cb)
        except Exception as exc:
            self._post("error", f"scan: {exc}")
        finally:
            self._post("done")

    def _on_device_cb(self, dev) -> None:
        if not self._stop.is_set():
            self._post("device", dev)

    def _on_progress_cb(self, done, total) -> None:
        self._post("progress", done, total)

    def _finish_scan(self) -> None:
        self.scanbar.stop()
        self.scanbar.set(0.0)
        self.btn_scan.configure(state="normal")
        self.btn_stop.configure(state="disabled")
        self.status.configure(text="EN ESPERA", text_color=theme.NEON_AMBER)
        self.led.set_color(theme.NEON_AMBER, blink=False)
        self.cards["dispositivos"].set(str(len(self._devices)), theme.NEON_BLUE)
        self.cards["activos"].set(str(self._count_active()), theme.NEON_GREEN)
        self.log("ok", f"Escaneo finalizado: {len(self._devices)} dispositivo(s).")
        self._worker = None

    def on_stop(self) -> None:
        self._stop.set()
        stopper = getattr(scanner, "stop", None)
        if stopper is not None:
            stopper()
        self.log("warn", "Detencion solicitada.")

    def on_ping(self) -> None:
        dev = self._selected()
        ip = getattr(dev, "ip", None) if dev is not None else None
        if not ip:
            self.log("warn", "Selecciona un dispositivo para medir latencia.")
            return
        self.log("cmd", f"ping {ip}")
        threading.Thread(target=self._worker_ping, args=(ip,), daemon=True).start()

    def _worker_ping(self, ip: str) -> None:
        try:
            ms = latency.ping(ip)
            self._post("latency", ip, ms)
            self._post("log", "ok", f"ping {ip}: {ms} ms")
        except Exception as exc:
            self._post("log", "error", f"ping {ip}: {exc}")

    def on_arp(self) -> None:
        dev = self._selected()
        target = getattr(dev, "ip", None) if dev is not None else None
        if not (target and self._gateway and self._gateway != "-"):
            self.log("warn", "Selecciona un dispositivo (y define puerta de enlace).")
            return
        self.log("cmd", f"arp spoof {target} <-> {self._gateway}")
        threading.Thread(target=self._worker_arp,
                         args=(self._gateway, target, getattr(dev, "mac", None)),
                         daemon=True).start()

    def _worker_arp(self, gateway: str, target: str, mac) -> None:
        try:
            arp.spoof(gateway, target, mac)
            self._post("log", "ok", f"ARP activo sobre {target}")
        except Exception as exc:
            self._post("log", "error", f"arp: {exc}")

    def on_flood(self) -> None:
        dev = self._selected()
        target = getattr(dev, "ip", None) if dev is not None else None
        if not target:
            self.log("warn", "Selecciona un dispositivo para saturar.")
            return
        self.log("cmd", f"flood {target}")
        threading.Thread(target=self._worker_flood,
                         args=(target, getattr(dev, "mac", None)), daemon=True).start()

    def _worker_flood(self, target: str, mac) -> None:
        try:
            flood.start(target, mac)
            self._post("log", "fire", f"Flood sobre {target}")
        except Exception as exc:
            self._post("log", "error", f"flood: {exc}")

    def on_export(self) -> None:
        if not self._devices:
            messagebox.showinfo(APP, "No hay dispositivos que exportar.")
            return
        stamp = time.strftime("%Y%m%d-%H%M%S")
        path = filedialog.asksaveasfilename(
            title="Exportar inventario",
            defaultextension=".csv",
            initialfile=f"netguard-{stamp}.csv",
            filetypes=[("CSV", "*.csv"), ("Todos", "*.*")],
        )
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write("ip,mac,fabricante,host,estado\n")
                for dev in self._devices.values():
                    row = (getattr(dev, "ip", ""), getattr(dev, "mac", ""),
                           getattr(dev, "vendor", ""), getattr(dev, "hostname", ""),
                           self._state_name(dev))
                    fh.write(",".join(str(c).replace(",", ";") for c in row) + "\n")
            self.log("ok", f"Exportado: {Path(path).name}")
        except Exception as exc:
            self.log("error", f"export: {exc}")

    def on_clear(self) -> None:
        for iid in self.tree.get_children():
            self.tree.delete(iid)
        self._devices.clear()
        self._rows.clear()
        self.cards["dispositivos"].set("0")
        self.cards["activos"].set("0")
        self.cards["latencia"].set("-", theme.NEON_PURPLE)
        self._latency = "-"
        self._render_detail()
        self.log("dim", "Inventario limpiado.")

    def _on_close(self) -> None:
        self._stop.set()
        stopper = getattr(scanner, "stop", None)
        if stopper is not None:
            stopper()
        self.master.destroy()

# ----------------------------------------------------------------------
# PUNTOS DE INTEGRACION CON core (ajusta solo si tu firma difiere):
#   netinfo.local_ip() / netinfo.gateway() / netinfo.cidr()|netinfo.subnet()
#   scanner.scan(cidr, on_device=cb, on_progress=cb)
#   scanner.stop()
#   latency.ping(ip) -> ms
#   arp.spoof(gateway_ip, target_ip, target_mac)
#   flood.start(target_ip, target_mac)
#   oui.vendor(mac) -> str
#   scanner.Device  con atributos .ip / .mac / .vendor / .hostname
#                   / .category / .state (State)
#   console.Console(master) con write(level, msg) o log(level, msg)
# ----------------------------------------------------------------------