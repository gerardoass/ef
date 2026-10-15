"""
ui/console.py
-------------
Terminal visual thread-safe. Usa tk.Text (no CTkTextbox) porque
necesitamos control total de tags de color por nivel de log.
Los mensajes se encolan y se vuelcan en el hilo de la GUI via after().
"""
from __future__ import annotations

import queue
import time
import tkinter as tk

from . import theme


class Console(tk.Frame):
    def __init__(self, master, height: int = 11):
        super().__init__(master, bg=theme.CONSOLE_BG,
                         highlightthickness=1,
                         highlightbackground=theme.BORDER)
        self._queue: queue.Queue[tuple[str, str]] = queue.Queue()
        self._max_lines = 2000

        header = tk.Frame(self, bg=theme.BG_ALT)
        header.pack(fill="x")
        tk.Label(
            header, text="  CONSOLA DE EVENTOS",
            bg=theme.BG_ALT, fg=theme.ACCENT,
            font=(theme.FONT, 9, "bold"), anchor="w",
        ).pack(side="left", pady=4)

        self._status = tk.Label(
            header, text="listo  ", bg=theme.BG_ALT, fg=theme.MUTED,
            font=(theme.FONT_SMALL),
        )
        self._status.pack(side="right", pady=4)

        tk.Button(
            header, text="Limpiar", command=self.clear,
            bg=theme.PANEL, fg=theme.TEXT_DIM, activebackground=theme.PANEL_HI,
            activeforeground=theme.TEXT, relief="flat", bd=0,
            font=(theme.FONT_SMALL), padx=10, cursor="hand2",
        ).pack(side="right", padx=6, pady=3)

        body = tk.Frame(self, bg=theme.CONSOLE_BG)
        body.pack(fill="both", expand=True)

        self.text = tk.Text(
            body, height=height, bg=theme.CONSOLE_BG, fg=theme.CONSOLE_FG,
            insertbackground=theme.ACCENT, relief="flat", bd=0,
            font=(theme.FONT_MONO, 10), wrap="word", padx=10, pady=6,
            selectbackground=theme.ACCENT_DIM, state="disabled",
        )
        scroll = tk.Scrollbar(body, command=self.text.yview,
                              bg=theme.PANEL, troughcolor=theme.BG_ALT,
                              relief="flat", bd=0, width=10)
        self.text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        self.text.pack(side="left", fill="both", expand=True)

        for level, color in theme.LEVEL_COLORS.items():
            self.text.tag_config(level, foreground=color)
        self.text.tag_config("time", foreground=theme.MUTED)
        self.text.tag_config("bold", font=(theme.FONT_MONO, 10, "bold"))

        self.after(80, self._drain)

    # -------------------------------------------------- API
    def log(self, msg: str, level: str = "info") -> None:
        """Seguro desde cualquier hilo."""
        self._queue.put((msg, level))

    def set_status(self, txt: str) -> None:
        try:
            self._status.configure(text=f"{txt}  ")
        except Exception:
            pass

    def clear(self) -> None:
        self.text.configure(state="normal")
        self.text.delete("1.0", "end")
        self.text.configure(state="disabled")

    # -------------------------------------------------- interno
    def _drain(self) -> None:
        drained = 0
        try:
            while drained < 200:
                msg, level = self._queue.get_nowait()
                self._write(msg, level)
                drained += 1
        except queue.Empty:
            pass
        finally:
            self.after(80, self._drain)

    def _write(self, msg: str, level: str) -> None:
        self.text.configure(state="normal")
        stamp = time.strftime("%H:%M:%S")
        prefix = {
            "info": "  ",
            "ok":   "OK",
            "warn": "!!",
            "error": "XX",
            "cmd":  ">>",
            "dim":  "  ",
        }.get(level, "  ")

        self.text.insert("end", f"[{stamp}] ", "time")
        self.text.insert("end", f"{prefix} {msg}\n", level)
        self.text.see("end")

        lines = int(self.text.index("end-1c").split(".")[0])
        if lines > self._max_lines:
            self.text.delete("1.0", f"{lines - self._max_lines}.0")
        self.text.configure(state="disabled")