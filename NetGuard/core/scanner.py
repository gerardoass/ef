"""
core/scanner.py
---------------
Motor de descubrimiento de hosts. Dos estrategias:

  1) PREFERENTE - ARP scan con scapy/srp(): rapido, fiable y funciona
     incluso con ICMP bloqueado en los clientes.
  2) FALLBACK   - ping sweep multihilo + lectura de la tabla ARP del
     sistema (arp -a). No requiere Npcap.

Sobre cada host encontrado se aplica un pipeline de fingerprinting:
  OUI -> hostname (DNS/NetBIOS) -> puertos -> heuristica combinada.
"""
from __future__ import annotations

import concurrent.futures as futures
import ipaddress
import re
import socket
import threading
from dataclasses import dataclass, field

from . import netinfo, oui, proc

PROBE_PORTS = (22, 53, 80, 443, 445, 515, 631, 1883, 3389, 5000,
               5555, 8008, 8009, 9100, 62078)


# ----------------------------------------------------------------------
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
    is_gateway: bool = False
    is_self: bool = False
    randomized_mac: bool = False

    @property
    def label(self) -> str:
        return oui.CATEGORY_LABEL.get(self.category, "Desconocido")

    @property
    def icon(self) -> str:
        return oui.CATEGORY_ICON.get(self.category, "❔")

    @property
    def sort_key(self) -> tuple:
        try:
            return tuple(int(x) for x in self.ip.split("."))
        except Exception:
            return (999, 999, 999, 999)

    def as_row(self) -> tuple:
        return (
            self.icon,
            self.ip,
            self.mac or "-",
            self.hostname or "-",
            f"{self.label}",
            self.vendor,
            f"{self.rtt:.0f} ms" if self.rtt is not None else "-",
        )


# ----------------------------------------------------------------------
def arp_table() -> dict[str, str]:
    """Lee la tabla ARP del sistema. {ip: mac}"""
    out = proc.run_hidden(["arp", "-a"], timeout=10)
    table: dict[str, str] = {}
    for line in out.splitlines():
        m = re.match(
            r"\s*([0-9]{1,3}(?:\.[0-9]{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})",
            line,
        )
        if not m:
            continue
        ip, mac = m.group(1), oui.normalize_mac(m.group(2))
        if ip.startswith(("224.", "239.", "255.")) or ip.endswith(".255"):
            continue
        if mac.startswith(("FF:FF:FF", "01:00:5E", "00:00:00")):
            continue
        table[ip] = mac
    return table


def ping_sweep(cidr: str, timeout: float = 0.7, workers: int = 96) -> None:
    """Barrido ICMP concurrente para poblar la tabla ARP."""
    try:
        net = ipaddress.IPv4Network(cidr, strict=False)
    except Exception:
        return

    def one(ip: str) -> None:
        netinfo.ping_once(ip, timeout=timeout)

    hosts = [str(h) for h in net.hosts()]
    with futures.ThreadPoolExecutor(max_workers=workers) as ex:
        list(ex.map(one, hosts))


def scapy_arp_scan(cidr: str, iface: str | None = None,
                   timeout: float = 2.5) -> list[tuple[str, str]]:
    """
    ARP scan en capa 2 con scapy. Devuelve [(ip, mac)].
    Lanza ImportError/OSError si scapy o Npcap no estan disponibles.
    """
    from scapy.all import ARP, Ether, srp  # type: ignore

    pkt = Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=cidr)
    kw = {"timeout": timeout, "verbose": 0, "retry": 1}
    if iface:
        kw["iface"] = iface
    ans, _ = srp(pkt, **kw)
    return [(rcv[ARP].psrc, oui.normalize_mac(rcv[Ether].src)) for _, rcv in ans]


# ----------------------------------------------------------------------
def resolve_hostname(ip: str, timeout: float = 1.2) -> str:
    """
    Intenta DNS inverso y, si falla, NetBIOS via nbtstat.
    Todo con timeout porque gethostbyaddr puede colgarse segundos.
    """
    result: list[str] = []

    def _dns() -> None:
        try:
            name = socket.gethostbyaddr(ip)[0]
            if name and not name.startswith(ip):
                result.append(name.split(".")[0])
        except Exception:
            pass

    t = threading.Thread(target=_dns, daemon=True)
    t.start()
    t.join(timeout)
    if result:
        return result[0]

    out = proc.run_hidden(["nbtstat", "-A", ip], timeout=3)
    m = re.search(r"^\s*([^\s<]+)\s*<00>\s+UNIQUE", out, re.M)
    if m and m.group(1).strip():
        return m.group(1).strip()
    m = re.search(r"(?:Nombre|Name)\s*:\s*(\S+)", out, re.I)
    return m.group(1) if m else ""


def probe_ports(ip: str, ports=PROBE_PORTS, timeout: float = 0.35) -> list[int]:
    """Escaneo TCP connect muy ligero sobre puertos firma."""
    open_ports: list[int] = []

    def one(port: int) -> None:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        try:
            if s.connect_ex((ip, port)) == 0:
                open_ports.append(port)
        finally:
            s.close()

    with futures.ThreadPoolExecutor(max_workers=len(ports)) as ex:
        list(ex.map(one, ports))
    return sorted(open_ports)


def guess_os(ports: list[int], ttl: int | None, hostname: str,
             category: str) -> str:
    """Estimacion de SO por TTL + puertos + categoria."""
    if 3389 in ports:
        return "Windows (RDP)"
    if 445 in ports and 139 in ports:
        return "Windows"
    if 548 in ports or category in ("phone", "laptop") and "mac" in hostname.lower():
        return "macOS / iOS"
    if 22 in ports and 445 not in ports:
        return "Linux / Unix"
    if 62078 in ports:
        return "iOS"
    if 5555 in ports:
        return "Android"
    if category == "router":
        return "Firmware embebido (Linux)"
    if category == "printer":
        return "Firmware de impresora"
    if ttl is not None:
        if ttl >= 250:
            return "Red / Embebido"
        if ttl >= 120:
            return "Windows"
        if ttl >= 60:
            return "Linux / macOS"
        return "Desconocido"
    return "Desconocido"


def ttl_of(ip: str) -> int | None:
    out = proc.run_hidden(["ping", "-n", "1", "-w", "800", ip], timeout=3)
    m = re.search(r"(?:TTL|ttl)[=\s]+(\d+)", out)
    return int(m.group(1)) if m else None


# ----------------------------------------------------------------------
def fingerprint(ip: str, mac: str, gateway: str | None, local_ip: str,
                deep: bool = True, stop: threading.Event | None = None) -> Device:
    """Construye el Device con toda la informacion disponible."""
    dev = Device(ip=ip, mac=mac)
    dev.is_gateway = (ip == gateway)
    dev.is_self = (ip == local_ip)
    dev.randomized_mac = oui.is_randomized(mac)

    if stop and stop.is_set():
        return dev

    dev.rtt = netinfo.ping_once(ip, timeout=0.8)
    dev.hostname = resolve_hostname(ip) if deep else ""

    if stop and stop.is_set():
        return dev

    vendor, cat = oui.lookup_vendor(mac)
    dev.vendor = vendor
    dev.category = cat

    if deep and not dev.is_self:
        dev.ports = probe_ports(ip)

    # --- Cascada de clasificacion (mayor -> menor prioridad) ---
    if dev.is_gateway:
        dev.category = "router"
    elif dev.is_self:
        dev.category = "desktop" if "laptop" not in (dev.hostname or "").lower() else "laptop"

    if dev.category == "unknown":
        h = oui.guess_category_from_hostname(dev.hostname)
        if h:
            dev.category = h

    if dev.category == "unknown":
        p = oui.guess_category_from_ports(dev.ports)
        if p:
            dev.category = p

    # MAC aleatoria + puerto movil => movil
    if dev.category == "unknown" and dev.randomized_mac:
        if dev.ports and (62078 in dev.ports or 5555 in dev.ports):
            dev.category = "phone"
        else:
            dev.category = "phone"

    ttl = ttl_of(ip) if deep else None
    dev.os_guess = guess_os(dev.ports, ttl, dev.hostname, dev.category)

    if dev.randomized_mac and dev.vendor == "Desconocido":
        dev.vendor = "MAC aleatoria (privada)"

    return dev


# ----------------------------------------------------------------------
def scan_lan(on_device=None, on_progress=None, on_log=None,
             iface: str | None = None, deep: bool = True,
             stop: threading.Event | None = None) -> list[Device]:
    """
    Escaneo completo de la LAN.

    on_device(Device)      -> callback por host descubierto
    on_progress(int, str)  -> progreso 0..100 + mensaje
    on_log(str)            -> mensajes a la consola
    """
    def log(msg: str) -> None:
        if on_log:
            on_log(msg)

    def prog(v: int, msg: str = "") -> None:
        if on_progress:
            on_progress(v, msg)

    cidr = netinfo.get_cidr()
    gateway = netinfo.get_gateway()
    local_ip = netinfo.get_local_ip()

    log(f"Objetivo de barrido: {cidr}")
    prog(5, "Preparando")

    hosts: dict[str, str] = {}

    # --- Fase 1: descubrimiento ---
    prog(10, "Descubriendo hosts")
    used_scapy = False
    try:
        log("Intentando ARP scan (scapy / Npcap)...")
        for ip, mac in scapy_arp_scan(cidr, iface=iface):
            hosts[ip] = mac
        used_scapy = True
        log(f"ARP scan completado: {len(hosts)} respuestas.")
    except Exception as exc:
        log(f"ARP scan no disponible ({type(exc).__name__}). Usando fallback nativo.")

    if not used_scapy or not hosts:
        prog(15, "Ping sweep")
        log("Ejecutando ping sweep multihilo...")
        ping_sweep(cidr)
        log("Leyendo tabla ARP del sistema...")
        hosts.update(arp_table())

    if stop and stop.is_set():
        return []

    # Asegurar gateway y host local
    if gateway and gateway not in hosts:
        hosts[gateway] = ""
    if local_ip not in hosts:
        hosts[local_ip] = netinfo.get_local_mac()

    prog(40, f"{len(hosts)} hosts")

    # --- Fase 2: fingerprinting ---
    devices: list[Device] = []
    total = max(1, len(hosts))
    for idx, (ip, mac) in enumerate(sorted(
            hosts.items(), key=lambda kv: tuple(int(x) for x in kv[0].split(".")))):
        if stop and stop.is_set():
            break
        pct = 40 + int(55 * (idx + 1) / total)
        prog(pct, f"Analizando {ip}")
        try:
            dev = fingerprint(ip, mac, gateway, local_ip, deep=deep, stop=stop)
        except Exception as exc:
            log(f"Error analizando {ip}: {exc}")
            continue
        devices.append(dev)
        if on_device:
            on_device(dev)

    prog(100, "Completado")
    log(f"Escaneo finalizado. {len(devices)} dispositivo(s) detectado(s).")
    return devices


def export_csv(devices: list[Device], path: str) -> None:
    import csv
    with open(path, "w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh, delimiter=";")
        w.writerow(["IP", "MAC", "Hostname", "Tipo", "Fabricante", "SO", "Puertos"])
        for d in devices:
            w.writerow([d.ip, d.mac, d.hostname, d.label, d.vendor,
                        d.os_guess, ",".join(map(str, d.ports))])