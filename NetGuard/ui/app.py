"""
ui/app.py
---------
Ventana principal. Layout:

  +----------------------------------------------------------+
  | SIDEBAR (240px)   |  AREA DE PAGINAS (stack de frames)     |
  |  - Panel          |                                        |
  |  - Escaneo        |                                        |
  |  - Diagnostico    |                                        |
  |  - ARP / Bloqueo  |                                        |
  |  - Ajustes        |                                        |
  +----------------------------------------------------------+
  | CONSOLA INTEGRADA (dock inferior, siempre visible)        |
  +----------------------------------------------------------+
  | BARRA DE ESTADO                                           |
  +----------------------------------------------------------+
"""
from __future__ import annotations

import os
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk

from core import admin, arp, flood, latency, netinfo, oui, scanner
from core.scanner import Device
from ui import theme
from ui.console import Console

APP_NAME = "NetGuard LAN Console"
APP_VER = "1.0"


class NetGuardApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        ctk.set_appearance_mode("dark")
        theme.apply_ttk_theme(self)

        self.title(f"{APP_NAME}  v{APP_VER}")
        self.geometry("1360x860")
        self.minsize(1120, 720)
        self.configure(fg_color=theme.BG)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # --- Estado ---
        self.env = {
            "local_ip": "-", "gateway": "-", "mac": "-",
            "cidr": "-", "ssid": None, "banda": None, "canal": None,
            "iface": None,
        }
        self.devices: list[Device] = []
        self.device_by_ip: dict[str, Device] = {}
        self.selected_ip: str | None = None
        self.scanning = False
        self.scan_stop = threading.Event()
        self.link_mbps = 0.0

        self.flood = flood.FloodEngine(log=self.log)
        self.spoofer = arp.ArpSpoofer(log=self.log)
        self.monitor: latency.LatencyMonitor | None = None

        self._pages: dict[str, ctk.CTkFrame] = {}
        self._nav_buttons: dict[str, ctk.CTkButton] = {}
        self._current = ""

        self._build_layout()
        self._build_sidebar()
        self._build_pages()
        self._build_console()
        self._build_statusbar()

        self.log(f"{APP_NAME} v{APP_VER} iniciado", "ok")
        self.log(f"Administrador: {'SI' if admin.is_admin() else 'NO'}", 
                 "ok" if admin.is_admin() else "error")
        self._check_stack()

        threading.Thread(target=self._load_environment, daemon=True).start()
        self.after(600, self._tick)

    # ================================================== LAYOUT
    def _build_layout(self) -> None:
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0,
                                    fg_color=theme.BG_ALT)
        self.sidebar.grid(row=0, column=0, sticky="nsw")
        self.sidebar.grid_propagate(False)

        self.body = ctk.CTkFrame(self, corner_radius=0, fg_color=theme.BG)
        self.body.grid(row=0, column=1, sticky="nsew")

        self.console_host = ctk.CTkFrame(self, corner_radius=0,
                                         fg_color=theme.BG)
        self.console_host.grid(row=1, column=0, columnspan=2, sticky="ew")

        self.statusbar = ctk.CTkFrame(self, height=26, corner_radius=0,
                                      fg_color=theme.BG_ALT)
        self.statusbar.grid(row=2, column=0, columnspan=2, sticky="ew")

    # -------------------------------------------------- sidebar
    def _build_sidebar(self) -> None:
        brand = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        brand.pack(fill="x", padx=18, pady=(22, 6))

        ctk.CTkLabel(brand, text="NETGUARD",
                     font=(theme.FONT, 19, "bold"),
                     text_color=theme.ACCENT).pack(anchor="w")
        ctk.CTkLabel(brand, text="Administracion de LAN",
                     font=(theme.FONT_SMALL),
                     text_color=theme.TEXT_DIM).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=theme.BORDER).pack(
            fill="x", padx=18, pady=14)

        items = [
            ("dashboard", "Panel de control"),
            ("scan",      "Escaneo de red"),
            ("diag",      "Diagnostico"),
            ("arp",       "ARP / Bloqueo"),
            ("settings",  "Ajustes"),
        ]
        for key, label in items:
            btn = ctk.CTkButton(
                self.sidebar, text=label, anchor="w", height=38,
                corner_radius=8, border_spacing=10,
                fg_color="transparent", hover_color=theme.PANEL_HI,
                text_color=theme.TEXT, font=(theme.FONT, 12),
                command=lambda k=key: self.show_page(k),
            )
            btn.pack(fill="x", padx=12, pady=2)
            self._nav_buttons[key] = btn

        # --- Bloque de acciones rapidas ---
        ctk.CTkFrame(self.sidebar, height=1, fg_color=theme.BORDER).pack(
            fill="x", padx=18, pady=14)

        ctk.CTkLabel(self.sidebar, text="ACCIONES RAPIDAS",
                     font=(theme.FONT, 9, "bold"),
                     text_color=theme.MUTED).pack(anchor="w", padx=20)

        ctk.CTkButton(self.sidebar, text="Escanear LAN", height=34,
                      corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color="#04120f",
                      font=(theme.FONT, 11, "bold"),
                      command=self.start_scan).pack(fill="x", padx=12, pady=(8, 3))

        ctk.CTkButton(self.sidebar, text="PARAR TODO", height=34,
                      corner_radius=8, fg_color=theme.DANGER,
                      hover_color="#cc3b3b", text_color="#ffffff",
                      font=(theme.FONT, 11, "bold"),
                      command=self.stop_everything).pack(fill="x", padx=12, pady=3)

        ctk.CTkButton(self.sidebar, text="Restaurar red", height=34,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, text_color=theme.TEXT,
                      font=(theme.FONT, 11),
                      command=self.restore_network).pack(fill="x", padx=12, pady=3)

        # --- Info de entorno al pie ---
        self.env_box = ctk.CTkFrame(self.sidebar, fg_color=theme.PANEL,
                                    corner_radius=10)
        self.env_box.pack(side="bottom", fill="x", padx=12, pady=12)
        self.env_labels: dict[str, ctk.CTkLabel] = {}
        for key, caption in (("local_ip", "IP local"), ("gateway", "Gateway"),
                             ("cidr", "Subred"), ("ssid", "WiFi")):
            row = ctk.CTkFrame(self.env_box, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=1)
            ctk.CTkLabel(row, text=caption, font=(theme.FONT_SMALL),
                         text_color=theme.MUTED, width=58,
                         anchor="w").pack(side="left")
            lbl = ctk.CTkLabel(row, text="-", font=(theme.FONT_MONO, 9),
                               text_color=theme.TEXT, anchor="w")
            lbl.pack(side="left")
            self.env_labels[key] = lbl

    # -------------------------------------------------- pages
    def _build_pages(self) -> None:
        for key, builder in (
            ("dashboard", self._page_dashboard),
            ("scan",      self._page_scan),
            ("diag",      self._page_diag),
            ("arp",       self._page_arp),
            ("settings",  self._page_settings),
        ):
            frame = ctk.CTkFrame(self.body, corner_radius=0, fg_color=theme.BG)
            frame.grid(row=0, column=0, sticky="nsew")
            self.body.grid_rowconfigure(0, weight=1)
            self.body.grid_columnconfigure(0, weight=1)
            builder(frame)
            self._pages[key] = frame

        self.show_page("dashboard")

    def show_page(self, key: str) -> None:
        if key == self._current:
            return
        self._pages[key].tkraise()
        self._current = key
        for k, btn in self._nav_buttons.items():
            if k == key:
                btn.configure(fg_color=theme.PANEL_HI,
                              text_color=theme.ACCENT)
            else:
                btn.configure(fg_color="transparent",
                              text_color=theme.TEXT)

    # ================================================== DASHBOARD
    def _page_dashboard(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Panel de control",
                     font=theme.FONT_H1, text_color=theme.TEXT).pack(
            anchor="w", padx=26, pady=(22, 2))
        ctk.CTkLabel(parent,
                     text="Estado de la red local, enlace y sesiones activas.",
                     font=theme.FONT_BODY, text_color=theme.TEXT_DIM).pack(
            anchor="w", padx=26, pady=(0, 18))

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=26)
        for c in range(4):
            grid.grid_columnconfigure(c, weight=1)

        self.cards: dict[str, ctk.CTkLabel] = {}
        specs = [
            ("iface",  "Interfaz Npcap"),
            ("mac",    "MAC local"),
            ("link",   "Ancho de banda"),
            ("procs",  "Procesos activos"),
        ]
        for i, (key, title) in enumerate(specs):
            card = ctk.CTkFrame(grid, fg_color=theme.PANEL, corner_radius=12,
                                border_width=1, border_color=theme.BORDER)
            card.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 6),
                      pady=0, ipady=6)
            ctk.CTkLabel(card, text=title.upper(), font=(theme.FONT, 9, "bold"),
                         text_color=theme.MUTED).pack(anchor="w", padx=14,
                                                      pady=(12, 0))
            val = ctk.CTkLabel(card, text="-", font=(theme.FONT_MONO, 12),
                               text_color=theme.ACCENT, anchor="w",
                               wraplength=200)
            val.pack(anchor="w", padx=14, pady=(2, 12))
            self.cards[key] = val

        # --- Tarjetas de estado de motores ---
        engines = ctk.CTkFrame(parent, fg_color="transparent")
        engines.pack(fill="x", padx=26, pady=20)
        for c in range(3):
            engines.grid_columnconfigure(c, weight=1)

        self.engine_labels: dict[str, ctk.CTkLabel] = {}
        for i, (key, title) in enumerate((
            ("flood", "Motor de inyeccion"),
            ("arp",   "Motor ARP spoof"),
            ("mon",   "Monitor de latencia"),
        )):
            box = ctk.CTkFrame(engines, fg_color=theme.PANEL, corner_radius=12,
                               border_width=1, border_color=theme.BORDER)
            box.grid(row=0, column=i, sticky="nsew",
                     padx=(0 if i == 0 else 6, 6), ipady=8)
            ctk.CTkLabel(box, text=title, font=(theme.FONT, 11, "bold"),
                         text_color=theme.TEXT).pack(anchor="w", padx=14,
                                                     pady=(12, 0))
            st = ctk.CTkLabel(box, text="INACTIVO", font=(theme.FONT_MONO, 11),
                              text_color=theme.MUTED)
            st.pack(anchor="w", padx=14, pady=(2, 12))
            self.engine_labels[key] = st

        # --- Botonera principal ---
        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=26, pady=(4, 22))

        ctk.CTkButton(bar, text="Escanear red local", height=46, width=210,
                      corner_radius=10, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color="#04120f",
                      font=(theme.FONT, 13, "bold"),
                      command=self.start_scan).pack(side="left", padx=(0, 10))

        ctk.CTkButton(bar, text="Inyectar trafico", height=46, width=190,
                      corner_radius=10, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, text_color=theme.TEXT,
                      font=(theme.FONT, 13),
                      command=lambda: (self.show_page("diag"),
                                       self._flood_from_entry())
                      ).pack(side="left", padx=10)

        ctk.CTkButton(bar, text="Detener inyeccion", height=46, width=190,
                      corner_radius=10, fg_color=theme.WARN,
                      hover_color="#e09a10", text_color="#1a1200",
                      font=(theme.FONT, 13, "bold"),
                      command=self.stop_flood).pack(side="left", padx=10)

        # --- Log de resumen ---
        info = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                            border_width=1, border_color=theme.BORDER)
        info.pack(fill="both", expand=True, padx=26, pady=(0, 22))
        ctk.CTkLabel(info, text="COMO USARLO",
                     font=(theme.FONT, 10, "bold"),
                     text_color=theme.ACCENT).pack(anchor="w", padx=16,
                                                   pady=(14, 6))
        txt = (
            "1. Pulsa 'Escanear red local'. La tabla se rellena en vivo.\n"
            "2. Selecciona un dispositivo en la pestana Escaneo.\n"
            "3. 'Inyectar trafico' satura su enlace (nping o UDP).\n"
            "4. 'ARP / Bloqueo' corta la salida a internet de ese equipo.\n"
            "5. 'PARAR TODO' termina procesos y restaura las tablas ARP.\n"
        )
        ctk.CTkLabel(info, text=txt, justify="left", font=(theme.FONT_MONO, 10),
                     text_color=theme.TEXT_DIM).pack(anchor="w", padx=16,
                                                     pady=(0, 16))

    # ================================================== SCAN
    def _page_scan(self, parent: ctk.CTkFrame) -> None:
        top = ctk.CTkFrame(parent, fg_color="transparent")
        top.pack(fill="x", padx=26, pady=(22, 10))

        ctk.CTkLabel(top, text="Escaneo y reconocimiento",
                     font=theme.FONT_H1, text_color=theme.TEXT).pack(anchor="w")
        ctk.CTkLabel(top, text="Descubrimiento ARP + fingerprinting de SO y tipo.",
                     font=theme.FONT_BODY, text_color=theme.TEXT_DIM).pack(anchor="w")

        bar = ctk.CTkFrame(parent, fg_color="transparent")
        bar.pack(fill="x", padx=26, pady=8)

        self.btn_scan = ctk.CTkButton(
            bar, text="Escanear LAN", width=150, height=36, corner_radius=8,
            fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
            text_color="#04120f", font=(theme.FONT, 11, "bold"),
            command=self.start_scan)
        self.btn_scan.pack(side="left")

        ctk.CTkButton(bar, text="Detener", width=110, height=36, corner_radius=8,
                      fg_color=theme.DANGER, hover_color="#cc3b3b",
                      font=(theme.FONT, 11), command=self.stop_scan
                      ).pack(side="left", padx=8)

        ctk.CTkButton(bar, text="Exportar CSV", width=130, height=36,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 11),
                      command=self.export_devices).pack(side="left", padx=8)

        self.sw_deep = ctk.CTkSwitch(bar, text="Analisis profundo",
                                     font=(theme.FONT, 11),
                                     text_color=theme.TEXT_DIM,
                                     progress_color=theme.ACCENT)
        self.sw_deep.select()
        self.sw_deep.pack(side="left", padx=16)

        self.progress = ctk.CTkProgressBar(parent, height=6,
                                           progress_color=theme.ACCENT,
                                           fg_color=theme.PANEL)
        self.progress.set(0)
        self.progress.pack(fill="x", padx=26, pady=(6, 4))

        self.scan_status = ctk.CTkLabel(parent, text="Listo.",
                                        font=(theme.FONT_SMALL),
                                        text_color=theme.TEXT_DIM)
        self.scan_status.pack(anchor="w", padx=26)

        # --- Tabla ---
        table_host = ctk.CTkFrame(parent, fg_color=theme.PANEL,
                                  corner_radius=12, border_width=1,
                                  border_color=theme.BORDER)
        table_host.pack(fill="both", expand=True, padx=26, pady=(10, 8))

        cols = ("tipo", "ip", "mac", "hostname", "cat", "vendor", "rtt")
        heads = ("", "IP Address", "MAC Address", "Hostname",
                 "Device Type / OS", "Fabricante", "RTT")
        widths = (44, 130, 150, 190, 190, 190, 70)

        self.tree = ttk.Treeview(table_host, columns=cols, show="headings",
                                 style="NG.Treeview", selectmode="browse")
        for c, h, w in zip(cols, heads, widths):
            self.tree.heading(c, text=h)
            self.tree.column(c, width=w, anchor="w", stretch=(c in ("hostname", "cat", "vendor")))
        self.tree.pack(side="left", fill="both", expand=True, padx=(6, 0), pady=6)

        sb = ttk.Scrollbar(table_host, orient="vertical",
                           command=self.tree.yview,
                           style="NG.Vertical.TScrollbar")
        sb.pack(side="right", fill="y", pady=6, padx=(0, 6))
        self.tree.configure(yscrollcommand=sb.set)

        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", lambda e: self.ping_selected())

        # --- Acciones sobre la seleccion ---
        act = ctk.CTkFrame(parent, fg_color="transparent")
        act.pack(fill="x", padx=26, pady=(0, 20))

        self.sel_label = ctk.CTkLabel(act, text="Sin seleccion",
                                      font=(theme.FONT_MONO, 10),
                                      text_color=theme.MUTED)
        self.sel_label.pack(side="left", padx=(0, 16))

        ctk.CTkButton(act, text="Diagnostico", width=120, height=34,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 11),
                      command=self.ping_selected).pack(side="left", padx=4)

        ctk.CTkButton(act, text="Inyectar trafico", width=140, height=34,
                      corner_radius=8, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color="#04120f",
                      font=(theme.FONT, 11, "bold"),
                      command=self.flood_selected).pack(side="left", padx=4)

        ctk.CTkButton(act, text="Bloquear / Desconectar", width=190, height=34,
                      corner_radius=8, fg_color=theme.DANGER,
                      hover_color="#cc3b3b", font=(theme.FONT, 11, "bold"),
                      command=self.block_selected).pack(side="left", padx=4)

    # ================================================== DIAGNOSTICO
    def _page_diag(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Diagnostico y simulacion de trafico",
                     font=theme.FONT_H1, text_color=theme.TEXT).pack(
            anchor="w", padx=26, pady=(22, 2))
        ctk.CTkLabel(parent,
                     text="Ping continuo, traceroute e inyeccion de paquetes.",
                     font=theme.FONT_BODY, text_color=theme.TEXT_DIM).pack(
            anchor="w", padx=26, pady=(0, 16))

        # --- Objetivo ---
        row = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                           border_width=1, border_color=theme.BORDER)
        row.pack(fill="x", padx=26, pady=6)

        ctk.CTkLabel(row, text="OBJETIVO", font=(theme.FONT, 9, "bold"),
                     text_color=theme.MUTED).pack(anchor="w", padx=16, pady=(12, 0))

        line = ctk.CTkFrame(row, fg_color="transparent")
        line.pack(fill="x", padx=16, pady=(4, 14))

        self.entry_target = ctk.CTkEntry(
            line, placeholder_text="192.168.1.1", height=38, corner_radius=8,
            fg_color=theme.BG, border_color=theme.BORDER,
            font=(theme.FONT_MONO, 12))
        self.entry_target.pack(side="left", fill="x", expand=True)
        self.entry_target.insert(0, self.env.get("gateway") or "")

        ctk.CTkButton(line, text="Usar gateway", width=130, height=38,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 11),
                      command=lambda: self._set_entry(self.env.get("gateway"))
                      ).pack(side="left", padx=6)
        ctk.CTkButton(line, text="Usar seleccion", width=130, height=38,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 11),
                      command=lambda: self._set_entry(self.selected_ip)
                      ).pack(side="left", padx=6)

        # --- Acciones ---
        acts = ctk.CTkFrame(parent, fg_color="transparent")
        acts.pack(fill="x", padx=26, pady=12)

        self.btn_ping = ctk.CTkButton(
            acts, text="Iniciar ping continuo", width=190, height=42,
            corner_radius=10, fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER, text_color="#04120f",
            font=(theme.FONT, 12, "bold"), command=self.start_ping)
        self.btn_ping.pack(side="left")

        ctk.CTkButton(acts, text="Traceroute", width=130, height=42,
                      corner_radius=10, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 12),
                      command=self.traceroute).pack(side="left", padx=8)

        ctk.CTkButton(acts, text="INYECTAR", width=150, height=42,
                      corner_radius=10, fg_color="#c792ea",
                      hover_color="#a97bcc", text_color="#160b22",
                      font=(theme.FONT, 12, "bold"),
                      command=self._flood_from_entry).pack(side="left", padx=8)

        ctk.CTkButton(acts, text="PARAR", width=120, height=42,
                      corner_radius=10, fg_color=theme.DANGER,
                      hover_color="#cc3b3b", font=(theme.FONT, 12, "bold"),
                      command=self.stop_diag).pack(side="left", padx=8)

        # --- Medidor en vivo ---
        meter = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                             border_width=1, border_color=theme.BORDER)
        meter.pack(fill="both", expand=True, padx=26, pady=(0, 10))

        head = ctk.CTkFrame(meter, fg_color="transparent")
        head.pack(fill="x", padx=16, pady=(12, 0))
        ctk.CTkLabel(head, text="LATENCIA EN VIVO", font=(theme.FONT, 9, "bold"),
                     text_color=theme.MUTED).pack(side="left")

        self.lat_big = ctk.CTkLabel(head, text="-- ms",
                                    font=(theme.FONT_MONO, 22, "bold"),
                                    text_color=theme.ACCENT)
        self.lat_big.pack(side="right")

        self.stats_label = ctk.CTkLabel(
            meter, text="min --  max --  media --  jitter --  perdida --",
            font=(theme.FONT_MONO, 10), text_color=theme.TEXT_DIM)
        self.stats_label.pack(anchor="w", padx=16, pady=(0, 6))

        self.canvas = tk.Canvas(meter, height=170, bg=theme.CONSOLE_BG,
                                highlightthickness=0)
        self.canvas.pack(fill="both", expand=True, padx=16, pady=(0, 16))
        self.canvas.bind("<Configure>", lambda e: self._draw_graph())

    # ================================================== ARP
    def _page_arp(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Control ARP / Bloqueo de dispositivos",
                     font=theme.FONT_H1, text_color=theme.TEXT).pack(
            anchor="w", padx=26, pady=(22, 2))
        ctk.CTkLabel(parent,
                     text="Envenenamiento ARP selectivo para cortar o interceptar "
                          "el trafico de un equipo de la LAN.",
                     font=theme.FONT_BODY, text_color=theme.TEXT_DIM).pack(
            anchor="w", padx=26, pady=(0, 16))

        cfg = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                           border_width=1, border_color=theme.BORDER)
        cfg.pack(fill="x", padx=26, pady=6)

        ctk.CTkLabel(cfg, text="VICTIMA", font=(theme.FONT, 9, "bold"),
                     text_color=theme.MUTED).pack(anchor="w", padx=16, pady=(12, 0))

        l1 = ctk.CTkFrame(cfg, fg_color="transparent")
        l1.pack(fill="x", padx=16, pady=(4, 8))

        self.entry_victim = ctk.CTkEntry(
            l1, placeholder_text="192.168.1.50", height=38, corner_radius=8,
            fg_color=theme.BG, border_color=theme.BORDER,
            font=(theme.FONT_MONO, 12))
        self.entry_victim.pack(side="left", fill="x", expand=True)

        self.opt_devices = ctk.CTkOptionMenu(
            l1, values=["(vacio)"], width=230, height=38, corner_radius=8,
            fg_color=theme.BG, button_color=theme.PANEL_HI,
            button_hover_color=theme.BORDER, font=(theme.FONT, 10),
            command=self._pick_victim)
        self.opt_devices.pack(side="left", padx=8)

        l2 = ctk.CTkFrame(cfg, fg_color="transparent")
        l2.pack(fill="x", padx=16, pady=(0, 14))

        ctk.CTkLabel(l2, text="Gateway:", font=(theme.FONT, 11),
                     text_color=theme.TEXT_DIM).pack(side="left", padx=(0, 6))
        self.entry_gw = ctk.CTkEntry(l2, height=34, width=170, corner_radius=8,
                                     fg_color=theme.BG, border_color=theme.BORDER,
                                     font=(theme.FONT_MONO, 11))
        self.entry_gw.pack(side="left")

        ctk.CTkLabel(l2, text="Modo:", font=(theme.FONT, 11),
                     text_color=theme.TEXT_DIM).pack(side="left", padx=(18, 6))
        self.seg_mode = ctk.CTkSegmentedButton(
            l2, values=["Cortar (1 via)", "MITM (2 vias)"],
            font=(theme.FONT, 11), selected_color=theme.ACCENT,
            selected_hover_color=theme.ACCENT_HOVER,
            unselected_color=theme.PANEL_HI,
            unselected_hover_color=theme.BORDER, height=34)
        self.seg_mode.set("Cortar (1 via)")
        self.seg_mode.pack(side="left")

        acts = ctk.CTkFrame(parent, fg_color="transparent")
        acts.pack(fill="x", padx=26, pady=12)

        ctk.CTkButton(acts, text="Desconectar / Bloquear", width=210, height=44,
                      corner_radius=10, fg_color=theme.DANGER,
                      hover_color="#cc3b3b", font=(theme.FONT, 12, "bold"),
                      command=self.block_victim).pack(side="left")

        ctk.CTkButton(acts, text="Restaurar ARP", width=160, height=44,
                      corner_radius=10, fg_color=theme.ACCENT,
                      hover_color=theme.ACCENT_HOVER, text_color="#04120f",
                      font=(theme.FONT, 12, "bold"),
                      command=self.restore_arp).pack(side="left", padx=8)

        self.sw_forward = ctk.CTkSwitch(
            acts, text="IP forwarding", font=(theme.FONT, 11),
            text_color=theme.TEXT_DIM, progress_color=theme.ACCENT,
            command=self._toggle_forwarding)
        self.sw_forward.pack(side="left", padx=18)

        # --- Sesiones activas ---
        sess_box = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                                border_width=1, border_color=theme.BORDER)
        sess_box.pack(fill="both", expand=True, padx=26, pady=(0, 20))

        ctk.CTkLabel(sess_box, text="SESIONES ARP ACTIVAS",
                     font=(theme.FONT, 9, "bold"),
                     text_color=theme.ACCENT).pack(anchor="w", padx=16,
                                                   pady=(12, 4))

        scols = ("ip", "mac", "gw", "modo", "paquetes", "tiempo")
        self.stree = ttk.Treeview(sess_box, columns=scols, show="headings",
                                  style="NG.Treeview", height=8)
        for c, h, w in zip(scols, ("Victima", "MAC victima", "Gateway",
                                   "Modo", "Paquetes", "Activo"),
                           (150, 170, 150, 110, 110, 90)):
            self.stree.heading(c, text=h)
            self.stree.column(c, width=w, anchor="w")
        self.stree.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        foot = ctk.CTkFrame(sess_box, fg_color="transparent")
        foot.pack(fill="x", padx=16, pady=(0, 12))
        ctk.CTkButton(foot, text="Quitar seleccionada", width=170, height=32,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 10),
                      command=self.remove_session).pack(side="left")
        ctk.CTkButton(foot, text="Cortar todas", width=140, height=32,
                      corner_radius=8, fg_color=theme.DANGER,
                      hover_color="#cc3b3b", font=(theme.FONT, 10),
                      command=self.restore_arp).pack(side="left", padx=8)

        self.arp_note = ctk.CTkLabel(
            parent,
            text="Nota: el ARP spoof requiere Npcap instalado y permisos de "
                 "Administrador. El modo MITM necesita IP forwarding activo.",
            font=(theme.FONT_SMALL), text_color=theme.MUTED)
        self.arp_note.pack(anchor="w", padx=26, pady=(0, 14))

    # ================================================== AJUSTES
    def _page_settings(self, parent: ctk.CTkFrame) -> None:
        ctk.CTkLabel(parent, text="Ajustes", font=theme.FONT_H1,
                     text_color=theme.TEXT).pack(anchor="w", padx=26,
                                                 pady=(22, 2))
        ctk.CTkLabel(parent, text="Parametros del motor de inyeccion y del "
                                  "adaptador de captura.",
                     font=theme.FONT_BODY, text_color=theme.TEXT_DIM).pack(
            anchor="w", padx=26, pady=(0, 16))

        box = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                           border_width=1, border_color=theme.BORDER)
        box.pack(fill="x", padx=26, pady=6)

        # Potencia
        r1 = ctk.CTkFrame(box, fg_color="transparent")
        r1.pack(fill="x", padx=16, pady=(16, 4))
        ctk.CTkLabel(r1, text="Procesos de inyeccion", width=200, anchor="w",
                     font=(theme.FONT, 11), text_color=theme.TEXT).pack(side="left")
        self.lbl_power = ctk.CTkLabel(r1, text=str(flood.DEFAULT_POWER),
                                      font=(theme.FONT_MONO, 11),
                                      text_color=theme.ACCENT, width=40)
        self.lbl_power.pack(side="right")
        self.sl_power = ctk.CTkSlider(r1, from_=1, to=32, number_of_steps=31,
                                      progress_color=theme.ACCENT,
                                      command=lambda v: self.lbl_power.configure(
                                          text=str(int(v))))
        self.sl_power.set(flood.DEFAULT_POWER)
        self.sl_power.pack(side="right", fill="x", expand=True, padx=12)

        # Payload
        r2 = ctk.CTkFrame(box, fg_color="transparent")
        r2.pack(fill="x", padx=16, pady=8)
        ctk.CTkLabel(r2, text="Tamano de payload (bytes)", width=200, anchor="w",
                     font=(theme.FONT, 11), text_color=theme.TEXT).pack(side="left")
        self.lbl_payload = ctk.CTkLabel(r2, text=str(flood.DEFAULT_PAYLOAD),
                                        font=(theme.FONT_MONO, 11),
                                        text_color=theme.ACCENT, width=50)
        self.lbl_payload.pack(side="right")
        self.sl_payload = ctk.CTkSlider(r2, from_=64, to=1472, number_of_steps=22,
                                        progress_color=theme.ACCENT,
                                        command=lambda v: self.lbl_payload.configure(
                                            text=str(int(v))))
        self.sl_payload.set(flood.DEFAULT_PAYLOAD)
        self.sl_payload.pack(side="right", fill="x", expand=True, padx=12)

        # Intervalo ARP
        r3 = ctk.CTkFrame(box, fg_color="transparent")
        r3.pack(fill="x", padx=16, pady=(8, 16))
        ctk.CTkLabel(r3, text="Intervalo ARP (ms)", width=200, anchor="w",
                     font=(theme.FONT, 11), text_color=theme.TEXT).pack(side="left")
        self.lbl_interval = ctk.CTkLabel(r3, text="1000",
                                         font=(theme.FONT_MONO, 11),
                                         text_color=theme.ACCENT, width=50)
        self.lbl_interval.pack(side="right")
        self.sl_interval = ctk.CTkSlider(r3, from_=200, to=3000,
                                         number_of_steps=28,
                                         progress_color=theme.ACCENT,
                                         command=lambda v: self.lbl_interval.configure(
                                             text=str(int(v))))
        self.sl_interval.set(1000)
        self.sl_interval.pack(side="right", fill="x", expand=True, padx=12)

        # Diagnostico de stack
        diag = ctk.CTkFrame(parent, fg_color=theme.PANEL, corner_radius=12,
                            border_width=1, border_color=theme.BORDER)
        diag.pack(fill="x", padx=26, pady=14)

        ctk.CTkLabel(diag, text="DIAGNOSTICO DEL ENTORNO",
                     font=(theme.FONT, 9, "bold"),
                     text_color=theme.ACCENT).pack(anchor="w", padx=16,
                                                   pady=(12, 6))
        self.stack_labels: dict[str, ctk.CTkLabel] = {}
        for key, cap in (("admin", "Privilegios de Administrador"),
                         ("scapy", "scapy (capa 2)"),
                         ("npcap", "Npcap / WinPcap"),
                         ("nping", "nping (Nmap)"),
                         ("iface", "Interfaz de captura"),
                         ("forward", "IP forwarding")):
            r = ctk.CTkFrame(diag, fg_color="transparent")
            r.pack(fill="x", padx=16, pady=1)
            ctk.CTkLabel(r, text=cap, width=230, anchor="w",
                         font=(theme.FONT, 11), text_color=theme.TEXT_DIM
                         ).pack(side="left")
            v = ctk.CTkLabel(r, text="...", anchor="w",
                             font=(theme.FONT_MONO, 10), text_color=theme.MUTED)
            v.pack(side="left")
            self.stack_labels[key] = v

        ctk.CTkButton(diag, text="Re-analizar entorno", height=34, width=180,
                      corner_radius=8, fg_color=theme.PANEL_HI,
                      hover_color=theme.BORDER, font=(theme.FONT, 11),
                      command=self._check_stack).pack(anchor="w", padx=16,
                                                      pady=(10, 16))

        ctk.CTkButton(parent, text="Medir ancho de banda del enlace",
                      height=40, width=280, corner_radius=10,
                      fg_color=theme.ACCENT, hover_color=theme.ACCENT_HOVER,
                      text_color="#04120f", font=(theme.FONT, 12, "bold"),
                      command=self.measure_link).pack(anchor="w", padx=26,
                                                      pady=(4, 20))

    # ================================================== CONSOLA + STATUS
    def _build_console(self) -> None:
        self.console = Console(self.console_host, height=11)
        self.console.pack(fill="both", expand=True)

    def _build_statusbar(self) -> None:
        self.status_dot = ctk.CTkLabel(self.statusbar, text="●",
                                       font=(theme.FONT, 12),
                                       text_color=theme.OK)
        self.status_dot.pack(side="left", padx=(14, 4), pady=3)

        self.status_text = ctk.CTkLabel(self.statusbar, text="Sistema listo",
                                        font=(theme.FONT_SMALL),
                                        text_color=theme.TEXT_DIM)
        self.status_text.pack(side="left", pady=3)

        self.status_right = ctk.CTkLabel(
            self.statusbar, text=f"v{APP_VER}",
            font=(theme.FONT_SMALL), text_color=theme.MUTED)
        self.status_right.pack(side="right", padx=14, pady=3)

    # ================================================== LOG
    def log(self, msg: str, level: str = "info") -> None:
        if hasattr(self, "console"):
            self.console.log(msg, level)
        try:
            self.status_text.configure(text=msg[:90])
        except Exception:
            pass

    # ================================================== ENTORNO
    def _load_environment(self) -> None:
        try:
            self.env["local_ip"] = netinfo.get_local_ip()
            self.env["gateway"] = netinfo.get_gateway() or "-"
            self.env["mac"] = netinfo.get_local_mac()
            self.env["cidr"] = netinfo.get_cidr()
            self.env["iface"] = netinfo.get_interface_name()
            wifi = netinfo.get_wifi_info()
            self.env["ssid"] = wifi.get("ssid")
            self.env["banda"] = wifi.get("banda")
            self.env["canal"] = wifi.get("canal")
        except Exception as exc:
            self.log(f"Error leyendo entorno: {exc}", "error")
        self.after(0, self._apply_environment)

    def _apply_environment(self) -> None:
        for key, lbl in self.env_labels.items():
            if key == "ssid":
                val = self.env.get("ssid") or "cable / n/d"
                if self.env.get("banda"):
                    val += f"  ({self.env['banda']}, ch{self.env.get('canal')})"
            else:
                val = self.env.get(key) or "-"
            lbl.configure(text=str(val))

        self.cards["iface"].configure(text=(self.env.get("iface") or "n/d")[:28])
        self.cards["mac"].configure(text=self.env.get("mac") or "-")

        if not self.entry_target.get():
            self.entry_target.insert(0, self.env.get("gateway") or "")
        if not self.entry_gw.get():
            self.entry_gw.insert(0, self.env.get("gateway") or "")

        self.log(f"IP local {self.env['local_ip']} | gateway "
                 f"{self.env['gateway']} | subred {self.env['cidr']}", "cmd")

    def _check_stack(self) -> None:
        checks = {
            "admin": (admin.is_admin(), "SI", "NO"),
            "scapy": (arp.has_scapy(), "disponible", "ausente"),
            "npcap": (arp.has_npcap(), "instalado", "ausente"),
            "nping": (bool(__import__("shutil").which("nping")),
                      "disponible", "ausente"),
            "iface": (bool(self.env.get("iface")), "detectada", "no detectada"),
            "forward": (arp.get_ip_forwarding() if admin.is_admin() else False,
                        "activo", "inactivo"),
        }
        for key, (ok, yes, no) in checks.items():
            lbl = self.stack_labels.get(key)
            if not lbl:
                continue
            lbl.configure(text=yes if ok else no,
                          text_color=theme.OK if ok else theme.DANGER)

        if self.stack_labels.get("iface") and self.env.get("iface"):
            self.stack_labels["iface"].configure(
                text=(self.env["iface"] or "")[:40], text_color=theme.OK)

    # ================================================== ESCANEO
    def start_scan(self) -> None:
        if self.scanning:
            self.log("Ya hay un escaneo en curso", "warn")
            return
        self.scanning = True
        self.scan_stop.clear()
        self.devices.clear()
        self.device_by_ip.clear()
        self.tree.delete(*self.tree.get_children())
        self.progress.set(0)
        self.btn_scan.configure(state="disabled")
        self.show_page("scan")

        threading.Thread(target=self._scan_worker, daemon=True,
                         name="ScanWorker").start()

    def _scan_worker(self) -> None:
        try:
            scanner.scan_lan(
                on_device=lambda d: self.after(0, self._add_device, d),
                on_progress=lambda p, m: self.after(0, self._on_progress, p, m),
                on_log=lambda m: self.log(m, "info"),
                iface=self.env.get("iface"),
                deep=bool(self.sw_deep.get()),
                stop=self.scan_stop,
            )
        except Exception as exc:
            self.log(f"Error en escaneo: {exc}", "error")
        finally:
            self.after(0, self._scan_done)

    def stop_scan(self) -> None:
        if self.scanning:
            self.scan_stop.set()
            self.log("Deteniendo escaneo...", "warn")

    def _on_progress(self, pct: int, msg: str) -> None:
        self.progress.set(max(0.0, min(1.0, pct / 100)))
        self.scan_status.configure(text=f"{msg}  ({pct}%)")

    def _add_device(self, dev: Device) -> None:
        self.devices.append(dev)
        self.device_by_ip[dev.ip] = dev
        tag = f"c_{dev.category}"
        self.tree.insert("", "end", iid=dev.ip, values=dev.as_row(), tags=(tag,))
        self.tree.tag_configure(tag, foreground=theme.category_color(dev.category))
        if dev.is_gateway or dev.is_self:
            self.tree.tag_configure(tag, foreground=theme.category_color(dev.category))

        # Actualizar selector de victimas
        values = ["(vacio)"] + [
            f"{d.ip}  {d.icon} {d.hostname or d.label}"
            for d in sorted(self.devices, key=lambda x: x.sort_key)
        ]
        self.opt_devices.configure(values=values)

        self.log(f"{dev.icon} {dev.ip}  {dev.mac or '-'}  "
                 f"{dev.hostname or '(sin nombre)'}  -> {dev.label} "
                 f"[{dev.vendor}]", "info")

    def _scan_done(self) -> None:
        self.scanning = False
        self.btn_scan.configure(state="normal")
        self.progress.set(1.0)
        self.scan_status.configure(text=f"Completado: {len(self.devices)} hosts")
        self.cards["link"].configure(text=self.cards["link"].cget("text"))
        self.log(f"Escaneo terminado: {len(self.devices)} dispositivo(s)", "ok")

    def export_devices(self) -> None:
        if not self.devices:
            messagebox.showinfo(APP_NAME, "No hay dispositivos que exportar.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".csv", filetypes=[("CSV", "*.csv")],
            initialfile=f"lan_scan_{time.strftime('%Y%m%d_%H%M%S')}.csv")
        if not path:
            return
        try:
            scanner.export_csv(self.devices, path)
            self.log(f"Exportado: {path}", "ok")
        except Exception as exc:
            self.log(f"Error exportando: {exc}", "error")

    def _on_tree_select(self, _evt=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        ip = sel[0]
        self.selected_ip = ip
        dev = self.device_by_ip.get(ip)
        if dev:
            self.sel_label.configure(
                text=f"{dev.icon} {dev.ip}  {dev.mac or '-'}  {dev.label}",
                text_color=theme.category_color(dev.category))

    # ================================================== DIAGNOSTICO
    def _set_entry(self, value: str | None) -> None:
        if not value:
            return
        self.entry_target.delete(0, "end")
        self.entry_target.insert(0, value)

    def start_ping(self) -> None:
        host = self.entry_target.get().strip()
        if not host:
            self.log("Indica un objetivo", "warn")
            return
        self.stop_ping()
        self.monitor = latency.LatencyMonitor(
            host, on_sample=lambda rtt, st: self.after(0, self._on_sample, rtt, st))
        self.monitor.start()
        self.log(f"Ping continuo iniciado contra {host}", "ok")

    def stop_ping(self) -> None:
        if self.monitor and self.monitor.is_alive():
            self.monitor.stop()
            self.log("Ping continuo detenido", "warn")
        self.monitor = None

    def _on_sample(self, rtt: float | None, st: dict) -> None:
        if rtt is None:
            self.lat_big.configure(text="SIN RESPUESTA", text_color=theme.DANGER)
        else:
            color = theme.OK if rtt < 40 else (theme.WARN if rtt < 120 else theme.DANGER)
            self.lat_big.configure(text=f"{rtt:.1f} ms", text_color=color)
        self.stats_label.configure(
            text=(f"min {st['min']:.0f}  max {st['max']:.0f}  "
                  f"media {st['avg']:.0f}  jitter {st['jitter']:.1f}  "
                  f"perdida {st['loss']:.1f}%  enviados {st['sent']}"))
        self._draw_graph()

    def _draw_graph(self) -> None:
        c = self.canvas
        c.delete("all")
        w = c.winfo_width() or 600
        h = c.winfo_height() or 170
        if not self.monitor or not self.monitor.samples:
            c.create_text(w / 2, h / 2, text="sin datos",
                          fill=theme.MUTED, font=(theme.FONT, 10))
            return

        samples = list(self.monitor.samples)
        n = len(samples)
        if n < 2:
            return
        peak = max([s for s in samples if s is not None] or [1]) * 1.25
        bw = max(1, w / max(n, 1))

        # Rejilla
        for i in range(1, 5):
            y = h * i / 5
            c.create_line(0, y, w, y, fill=theme.BORDER)
            c.create_text(4, y - 7, text=f"{peak * (5 - i) / 5:.0f}",
                          fill=theme.MUTED, anchor="w", font=(theme.FONT_SMALL))

        for i, s in enumerate(samples):
            x0 = i * bw
            x1 = x0 + bw - 1
            if s is None:
                c.create_rectangle(x0, 0, x1, h, fill="#2a0d0d", outline="")
                continue
            bh = max(1, h * (s / peak))
            color = theme.OK if s < 40 else (theme.WARN if s < 120 else theme.DANGER)
            c.create_rectangle(x0, h - bh, x1, h, fill=color, outline="")

    def traceroute(self) -> None:
        host = self.entry_target.get().strip()
        if not host:
            return
        self.log(f"Traceroute a {host}...", "cmd")
        self.show_page("dashboard")

        def worker():
            out = __import__("core.proc", fromlist=["proc"]).run_hidden(
                ["tracert", "-d", "-w", "800", "-h", "12", host], timeout=45)
            for line in out.splitlines():
                if line.strip():
                    self.log(line.rstrip(), "dim")
            self.log("Traceroute completado", "ok")

        threading.Thread(target=worker, daemon=True).start()

    # ================================================== FLOOD
    def _flood_from_entry(self) -> None:
        host = self.entry_target.get().strip()
        if host:
            self._start_flood(host)

    def flood_selected(self) -> None:
        if not self.selected_ip:
            self.log("Selecciona un dispositivo en la tabla", "warn")
            return
        self._start_flood(self.selected_ip)

    def _start_flood(self, target: str) -> None:
        power = int(self.sl_power.get())
        payload = int(self.sl_payload.get())
        self.log(f"Lanzando inyeccion contra {target} "
                 f"({power} procesos, {payload} bytes)", "cmd")
        self.flood.start(target, power=power, payload=payload)
        self.cards["procs"].configure(text=str(self.flood.alive))

    def stop_flood(self) -> None:
        n = self.flood.stop()
        self.cards["procs"].configure(text="0")
        if n == 0:
            self.log("No habia procesos activos", "dim")

    def stop_diag(self) -> None:
        self.stop_ping()
        self.stop_flood()

    # ================================================== ARP
    def _pick_victim(self, value: str) -> None:
        if value and value != "(vacio)":
            ip = value.split()[0]
            self.entry_victim.delete(0, "end")
            self.entry_victim.insert(0, ip)

    def block_victim(self) -> None:
        ip = self.entry_victim.get().strip()
        gw = self.entry_gw.get().strip() or self.env.get("gateway")
        if not ip:
            self.log("Indica la IP de la victima", "warn")
            return
        if ip == gw:
            self.log("La victima no puede ser el gateway", "warn")
            return

        mode = arp.ONE_WAY if self.seg_mode.get().startswith("Cortar") else arp.TWO_WAY
        ok = self.spoofer.add(ip, gateway_ip=gw, mode=mode)
        if ok:
            self.log(f"Bloqueando {ip} [{'MITM' if mode == arp.TWO_WAY else 'corte'}]",
                     "ok")
        self._refresh_sessions()

    def block_selected(self) -> None:
        if not self.selected_ip:
            self.log("Selecciona un dispositivo en la tabla", "warn")
            return
        if self.selected_ip in (self.env.get("gateway"), self.env.get("local_ip")):
            self.log("Gateway/equipo local: selecciona otro host", "warn")
            return
        self.show_page("arp")
        self.entry_victim.delete(0, "end")
        self.entry_victim.insert(0, self.selected_ip)
        self.block_victim()

    def restore_arp(self) -> None:
        self.spoofer.stop(restore=True)
        self._refresh_sessions()
        self.log("Sesiones ARP cerradas y tablas restauradas", "ok")

    def remove_session(self) -> None:
        sel = self.stree.selection()
        if not sel:
            return
        ip = self.stree.item(sel[0], "values")[0]
        self.spoofer.remove(ip, restore=True)
        self._refresh_sessions()

    def _refresh_sessions(self) -> None:
        self.stree.delete(*self.stree.get_children())
        for s in self.spoofer.sessions():
            self.stree.insert("", "end", values=(
                s.target_ip, s.target_mac, s.gateway_ip,
                "MITM" if s.mode == arp.TWO_WAY else "Corte",
                s.packets, f"{time.time() - s.started_at:.0f}s"))

    def _toggle_forwarding(self) -> None:
        state = bool(self.sw_forward.get())
        arp.enable_ip_forwarding(state)
        self.log(f"IP forwarding {'habilitado' if state else 'deshabilitado'}", "ok")

    # ================================================== GLOBAL
    def ping_selected(self) -> None:
        if not self.selected_ip:
            self.log("Selecciona un dispositivo", "warn")
            return
        self.show_page("diag")
        self._set_entry(self.selected_ip)
        self.start_ping()

    def measure_link(self) -> None:
        self.log("Midiendo ancho de banda del enlace...", "cmd")
        self.cards["link"].configure(text="midiendo...")

        def worker():
            mbps = netinfo.measure_link_speed()
            self.link_mbps = mbps
            self.after(0, lambda: self.cards["link"].configure(
                text=f"~{mbps:.0f} Mbps"))
            self.log(f"Ancho de banda estimado: {mbps:.0f} Mbps", "ok")

        threading.Thread(target=worker, daemon=True).start()

    def stop_everything(self) -> None:
        self.log("PARADA TOTAL solicitada", "warn")
        self.scan_stop.set()
        self.stop_ping()
        self.flood.stop()
        self.spoofer.stop(restore=True)
        self.cards["procs"].configure(text="0")
        self._refresh_sessions()
        self.log("Todos los procesos detenidos", "ok")

    def restore_network(self) -> None:
        self.log("Restaurando estado de red...", "cmd")

        def worker():
            __import__("core.proc", fromlist=["proc"]).run_hidden(
                ["arp", "-d", "*"], timeout=10)
            __import__("core.proc", fromlist=["proc"]).run_hidden(
                ["ipconfig", "/flushdns"], timeout=10)
            for host in (self.env.get("gateway"), "8.8.8.8"):
                if host and host != "-":
                    rtt = netinfo.ping_once(host, timeout=1)
                    self.log(f"{host:<16} " + (f"{rtt:.0f} ms" if rtt
                                               else "sin respuesta"),
                             "ok" if rtt else "warn")
            self.log("Tablas ARP y DNS limpiadas. Red libre.", "ok")

        threading.Thread(target=worker, daemon=True).start()

    # ================================================== TICK
    def _tick(self) -> None:
        try:
            alive = self.flood.alive
            self.cards["procs"].configure(
                text=str(alive),
                text_color=theme.OK if alive else theme.TEXT_DIM)

            if self.flood.running:
                self.engine_labels["flood"].configure(
                    text=f"ACTIVO  {alive} proc  {self.flood.uptime:.0f}s",
                    text_color=theme.WARN)
            else:
                self.engine_labels["flood"].configure(text="INACTIVO",
                                                      text_color=theme.MUTED)

            sessions = self.spoofer.sessions()
            if sessions:
                self.engine_labels["arp"].configure(
                    text=f"ENVENENANDO  {len(sessions)} victima(s)",
                    text_color=theme.DANGER)
                self._refresh_sessions()
            else:
                self.engine_labels["arp"].configure(text="INACTIVO",
                                                    text_color=theme.MUTED)

            if self.monitor and self.monitor.is_alive():
                st = self.monitor.stats()
                self.engine_labels["mon"].configure(
                    text=f"ACTIVO  media {st['avg']:.0f} ms  "
                         f"perdida {st['loss']:.0f}%",
                    text_color=theme.ACCENT)
            else:
                self.engine_labels["mon"].configure(text="INACTIVO",
                                                    text_color=theme.MUTED)

            if self.scanning:
                self.status_dot.configure(text_color=theme.WARN)
                self.status_text.configure(text="Escaneando red...")
            elif sessions or self.flood.running:
                self.status_dot.configure(text_color=theme.DANGER)
                self.status_text.configure(text="Modificando la red")
            else:
                self.status_dot.configure(text_color=theme.OK)
        except Exception:
            pass
        self.after(800, self._tick)

    # ================================================== CIERRE
    def _on_close(self) -> None:
        self.log("Cerrando: restaurando red...", "warn")
        try:
            self.scan_stop.set()
            if self.monitor:
                self.monitor.stop()
            self.flood.stop(silent=True)
            self.spoofer.stop(restore=True)
        except Exception:
            pass
        self.destroy()


def run() -> None:
    app = NetGuardApp()
    app.mainloop()