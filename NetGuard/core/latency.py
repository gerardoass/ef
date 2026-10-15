"""
core/latency.py
---------------
Sonda ICMP de alta precision. Usa scapy sr1 si hay Npcap; si no,
cae al ping del sistema. Historial acotado para el osciloscopio.
"""
from __future__ import annotations

import socket
import statistics
import threading
import time
from collections import deque

from . import netinfo


class Pinger(threading.Thread):
    def __init__(self, host: str, interval: float = 0.35, history: int = 180,
                 timeout: float = 0.9, on_sample=None, log=None):
        super().__init__(daemon=True, name=f"Pinger-{host}")
        self.host = host
        self.interval = interval
        self.timeout = timeout
        self.samples: deque[float | None] = deque(maxlen=history)
        self.on_sample = on_sample
        self.log = log or (lambda m, l="info": None)
        self._stop = threading.Event()
        self._use_raw = False
        self._dst: str | None = None
        self.sent = 0
        self.lost = 0
        self.t0 = time.time()

    # ---------------------------------------------------------- API
    def stop(self) -> None:
        self._stop.set()

    @property
    def last(self) -> float | None:
        return self.samples[-1] if self.samples else None

    @property
    def loss(self) -> float:
        return (self.lost / self.sent * 100) if self.sent else 0.0

    def stats(self) -> dict:
        ok = [s for s in self.samples if s is not None]
        return {
            "sent": self.sent, "lost": self.lost, "loss": self.loss,
            "min": min(ok) if ok else 0.0,
            "max": max(ok) if ok else 0.0,
            "avg": statistics.fmean(ok) if ok else 0.0,
            "jitter": statistics.pstdev(ok) if len(ok) > 1 else 0.0,
            "uptime": time.time() - self.t0,
        }

    # ---------------------------------------------------------- interno
    def _prepare(self) -> None:
        try:
            self._dst = socket.gethostbyname(self.host)
        except Exception:
            self._dst = self.host
        try:
            from scapy.all import ICMP, IP, conf, sr1
            self._sr1 = sr1
            self._pkt = IP(dst=self._dst) / ICMP()
            # prueba de humo
            t = time.perf_counter()
            ans = sr1(self._pkt, timeout=0.8, verbose=0)
            if ans is not None:
                self._use_raw = True
                self.samples.append((time.perf_counter() - t) * 1000)
                self.sent += 1
        except Exception:
            self._use_raw = False

    def _probe_raw(self) -> float | None:
        t = time.perf_counter()
        try:
            ans = self._sr1(self._pkt, timeout=self.timeout, verbose=0)
        except Exception:
            return None
        return (time.perf_counter() - t) * 1000 if ans is not None else None

    def run(self) -> None:
        self._prepare()
        if not self._use_raw:
            self.log("Sonda ICMP raw no disponible: usando ping del sistema", "warn")

        while not self._stop.is_set():
            rtt = self._probe_raw() if self._use_raw else netinfo.ping_once(
                self.host, timeout=self.timeout)
            self.sent += 1
            if rtt is None:
                self.lost += 1
            self.samples.append(rtt)
            if self.on_sample:
                try:
                    self.on_sample(rtt, self.stats())
                except Exception:
                    pass
            waited = 0.0
            while waited < self.interval and not self._stop.is_set():
                time.sleep(0.03)
                waited += 0.03