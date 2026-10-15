"""
core/scanner.py
---------------
Descubrimiento ARP en capa 2 + pipeline de fingerprinting paralelo
masivo. Toda la fase de analisis corre en ThreadPoolExecutor.
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import ipaddress
import re
import socket
import threading
from dataclasses import dataclass, field

from . import netinfo, oui, proc

PROBE_PORTS = (22, 53, 80, 443, 445, 515, 631, 1883, 3389, 5000, 5555, 8008, 8009, 9100, 62078)


class State:
    ONLINE = "online"
    SELF = "self"
    GATEWAY = "gateway"
    ISOLATED = "isolated"
    FLOODED = "flooded"


@dataclass
class Device:
    ip: str
    mac: str = ""
    hostname: str = ""
    vendor: str = "Desconocido"
    category: str = "unknown"
    os_guess: str = "Desconocido"
    ports: list[int] = field(default_factory=list)
    rtt: float | None = None
    ttl: int | None = None
    state: str = State.ONLINE
    randomized: bool = False

    @property
    def label(self) -> str:
        return oui.CATEGORY_LABEL.get(self.category, "DESCONOCIDO")

    @property
    def sort_key(self) -> tuple:
        try:
            return tuple(int(x) for x in self.ip.split("."))
        except Exception:
            return (999, 999, 999, 999)

    @property
    def risky(self) -> bool:
        """Heuristica de dispositivo 'intruso' a vigilar."""
        return (self.randomized and self.category in ("unknown", "phone")
                and not self.hostname)


def arp_table() -> dict[str, str]:
    out = proc.run_hidden(["arp", "-a"], timeout=10)
    t: dict[str, str] = {}
    for line in out.splitlines():
        m = re.match(r"\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+"
                     r"([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})", line)
        if not m:
            continue
        ip, mac = m.group(1), oui.normalize_mac(m.group(2))
        if ip.startswith(("224.", "239.", "255.")) or ip.endswith(".255"):
            continue
        if mac.startswith(("FF:FF:FF", "01:00:5E", "00:00:00")):
            continue
        t[ip] = mac
    return t


def ping_sweep(cidr: str, timeout: float = 0.6, workers: int = 0) -> None:
    try:
        net = ipaddress.IPv4Network(cidr, strict=False)
    except Exception:
        return
    workers = workers or proc.optimal_workers(8, 128)
    hosts = [str(h) for h in net.hosts()]
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(lambda ip: netinfo.ping_once(ip, timeout), hosts))


def arp_scan(cidr: str, iface: str | None = None, timeout: float = 2.0,
             retry: int = 2) -> list[tuple[str, str]]:
    from scapy.all import ARP, Ether, srp
    kw = {"timeout": timeout, "verbose": 0, "retry": retry}
    if iface:
        kw["iface"] = iface
    ans, _ = srp(Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr), **kw)
    return [(r[ARP].psrc, oui.normalize_mac(r[Ether].src)) for _, r in ans]


def resolve_hostname(ip: str, timeout: float = 1.0) -> str:
    box: list[str] = []

    def job():
        try:
            n = socket.gethostbyaddr(ip)[0]
            if n and not n.startswith(ip):
                box.append(n.split(".")[0])
        except Exception:
            pass

    t = threading.Thread(target=job, daemon=True)
    t.start()
    t.join(timeout)
    if box:
        return box[0]
    m = re.search(r"^\s*([^\s<]+)\s*<00>\s+UNIQUE",
                  proc.run_hidden(["nbtstat", "-A", ip], timeout=3), re.M)
    return m.group(1).strip() if m else ""


def probe_ports(ip: str, ports=PROBE_PORTS, timeout: float = 0.28) -> list[int]:
    found: list[int] = []

    def one(p: int) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            if s.connect_ex((ip, p)) == 0:
                found.append(p)
        finally:
            s.close()

    with cf.ThreadPoolExecutor(max_workers=len(ports)) as ex:
        list(ex.map(one, ports))
    return sorted(found)


def ttl_of(ip: str) -> int | None:
    m = re.search(r"(?:TTL|ttl)[=\s]+(\d+)",
                  proc.run_hidden(["ping", "-n", "1", "-w", "700", ip], timeout=3))
    return int(m.group(1)) if m else None


def guess_os(ports: list[int], ttl: int | None, hostname: str, cat: str) -> str:
    if 3389 in ports:
        return "Windows (RDP)"
    if 445 in ports and 139 in ports:
        return "Windows"
    if 62078 in ports:
        return "iOS"
    if 5555 in ports:
        return "Android"
    if 22 in ports and 445 not in ports:
        return "Linux / Unix"
    if cat == "router":
        return "Firmware embebido"
    if cat == "printer":
        return "Firmware impresora"
    if cat in ("tv", "console"):
        return "SO propietario"
    if "mac" in hostname.lower():
        return "macOS"
    if ttl is not None:
        if ttl >= 250:
            return "Embebido"
        if ttl >= 120:
            return "Windows"
        if ttl >= 60:
            return "Linux / macOS"
    return "Desconocido"


def fingerprint(ip: str, mac: str, gw: str | None, me: str,
                deep: bool, stop: threading.Event | None) -> Device:
    d = Device(ip=ip, mac=mac)
    if ip == gw:
        d.state = State.GATEWAY
        d.category = "router"
    if ip == me:
        d.state = State.SELF
    d.randomized = oui.is_randomized(mac)

    if stop and stop.is_set():
        return d

    d.rtt = netinfo.ping_once(ip, timeout=0.7)
    d.hostname = resolve_hostname(ip) if deep else ""

    if stop and stop.is_set():
        return d

    d.vendor, cat = oui.lookup_vendor(mac)
    d.category = cat

    if deep and d.state != State.SELF:
        d.ports = probe_ports(ip)

    if d.state == State.GATEWAY:
        d.category = "router"
    elif d.state == State.SELF:
        d.category = "laptop" if "laptop" in (d.hostname or "").lower() else "desktop"

    if d.category == "unknown":
        d.category = oui.from_hostname(d.hostname) or "unknown"
    if d.category == "unknown":
        d.category = oui.from_ports(d.ports) or "unknown"
    if d.category == "unknown" and d.randomized:
        d.category = "phone"

    d.ttl = ttl_of(ip) if deep else None
    d.os_guess = guess_os(d.ports, d.ttl, d.hostname, d.category)
    return d


def scan_lan(on_device=None, on_progress=None, on_log=None, iface=None,
             deep: bool = True, stop: threading.Event | None = None) -> list[Device]:
    log = on_log or (lambda m: None)
    prog = on_progress or (lambda p, m="": None)

    cidr = netinfo.get_cidr()
    gw = netinfo.get_gateway()
    me = netinfo.get_local_ip()
    log(f"Barrido objetivo: {cidr}")

    hosts: dict[str, str] = {}
    prog(6, "Descubriendo")

    try:
        log("ARP scan L2 (scapy/Npcap)...")
        for ip, mac in arp_scan(cidr, iface):
            hosts[ip] = mac
        log(f"ARP scan: {len(hosts)} respuesta(s)")
    except Exception as exc:
        log(f"ARP scan no disponible ({type(exc).__name__}) -> fallback")

    if not hosts:
        prog(16, "Ping sweep")
        ping_sweep(cidr)
        hosts.update(arp_table())

    if stop and stop.is_set():
        return []

    if gw:
        hosts.setdefault(gw, "")
    hosts.setdefault(me, netinfo.get_local_mac())

    prog(38, f"{len(hosts)} hosts")
    ordered = sorted(hosts.items(), key=lambda kv: tuple(int(x) for x in kv[0].split(".")))
    devices: list[Device] = []
    total = max(1, len(ordered))
    workers = proc.optimal_workers(6, 48)

    def work(item):
        ip, mac = item
        try:
            return fingerprint(ip, mac, gw, me, deep, stop)
        except Exception as exc:
            log(f"Error en {ip}: {exc}")
            return None

    done = 0
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for dev in ex.map(work, ordered):
            if stop and stop.is_set():
                break
            done += 1
            prog(38 + int(58 * done / total), f"Analizando {ordered[done-1][0]}")
            if dev:
                devices.append(dev)
                if on_device:
                    on_device(dev)

    prog(100, "Completado")
    log(f"Escaneo finalizado: {len(devices)} dispositivo(s)")
    return devices


def export_csv(devices: list[Device], path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["IP", "MAC", "Hostname", "Tipo", "Fabricante", "SO", "Puertos", "Estado"])
        for d in devices:
            w.writerow([d.ip, d.mac, d.hostname, d.label, d.vendor, d.os_guess,
                        ",".join(map(str, d.ports)), d.state])