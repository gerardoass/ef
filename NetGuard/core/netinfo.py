"""
core/netinfo.py
---------------
Topologia local, WiFi, contadores de interfaz y medicion de enlace.
Parseo tolerante a locale ES/EN.
"""
from __future__ import annotations

import ipaddress
import platform
import re
import socket
import time
import uuid

from . import proc

IS_WIN = platform.system() == "Windows"
INTERNET = "8.8.8.8"

_GW = [
    r"(?:Puerta de enlace predeterminada|Default Gateway)[\s.]*:[\s]*([0-9]{1,3}(?:\.[0-9]{1,3}){3})",
    r"(?:Puerta de enlace|Gateway)[\s.]*:[\s]*([0-9]{1,3}(?:\.[0-9]{1,3}){3})",
]
_MASK = r"(?:M.scara de subred|Subnet Mask)[\s.]*:[\s]*([0-9]{1,3}(?:\.[0-9]{1,3}){3})"


def get_local_ip() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("1.1.1.1", 80))
        return s.getsockname()[0]
    except Exception:
        return "127.0.0.1"
    finally:
        s.close()


def get_gateway() -> str | None:
    if IS_WIN:
        out = proc.run_hidden(["ipconfig"], timeout=8)
        for pat in _GW:
            m = re.search(pat, out, re.I)
            if m and m.group(1) != "0.0.0.0":
                return m.group(1)
        out = proc.run_hidden(["route", "print", "0.0.0.0"], timeout=8)
        m = re.search(r"0\.0\.0\.0\s+0\.0\.0\.0\s+([0-9.]+)", out)
        return m.group(1) if m else None
    out = proc.run_hidden(["ip", "route", "get", "1.1.1.1"], timeout=6)
    m = re.search(r"default via\s*([0-9.]+)", out)
    return m.group(1) if m else None


def get_subnet_mask() -> str:
    if IS_WIN:
        m = re.search(_MASK, proc.run_hidden(["ipconfig"], timeout=8), re.I)
        if m:
            return m.group(1)
    return "255.255.255.0"


def get_cidr() -> str:
    try:
        return str(ipaddress.IPv4Network(f"{get_local_ip()}/{get_subnet_mask()}", strict=False))
    except Exception:
        return ".".join(get_local_ip().split(".")[:3]) + ".0/24"


def get_local_mac() -> str:
    try:
        from scapy.all import conf, get_if_hwaddr
        mac = get_if_hwaddr(conf.iface)
        if mac and mac != "00:00:00:00:00:00":
            return mac.upper()
    except Exception:
        pass
    if IS_WIN:
        out = proc.run_hidden(["getmac", "/v", "/fo", "csv"], timeout=8)
        ip = get_local_ip()
        for line in out.splitlines():
            if ip in line:
                m = re.search(r"([0-9A-F]{2}(?:-[0-9A-F]{2}){5})", line, re.I)
                if m:
                    return m.group(1).replace("-", ":").upper()
    n = uuid.getnode()
    return ":".join(f"{(n >> b) & 0xFF:02X}" for b in range(40, -1, -8))


def get_interface_name() -> str | None:
    try:
        from scapy.all import conf, get_working_if
        try:
            return get_working_if()
        except Exception:
            return str(conf.iface)
    except Exception:
        return None


def list_interfaces() -> list[str]:
    try:
        from scapy.all import get_if_list
        return sorted(get_if_list())
    except Exception:
        return []


def get_wifi_info() -> dict:
    info: dict = {}
    if not IS_WIN:
        return info
    out = proc.run_hidden(["netsh", "wlan", "show", "interfaces"], timeout=8)
    if not out:
        return info

    def g(p):
        m = re.search(p, out, re.I | re.M)
        return m.group(1).strip() if m else None

    info["ssid"] = g(r"^\s*SSID\s*:\s*(.+)$")
    ch = g(r"(?:Canal|Channel)\s*:\s*(\d+)")
    if ch:
        info["canal"] = ch
        c = int(ch)
        info["banda"] = "2.4 GHz" if c <= 14 else ("6 GHz" if c > 200 else "5 GHz")
    sig = g(r"(?:Se.al|Signal)\s*:\s*(\d+)%")
    if sig:
        info["señal"] = sig + "%"
    return info


def net_bytes() -> int:
    if IS_WIN:
        out = proc.powershell(
            "$a=(Get-NetAdapterStatistics|Measure-Object ReceivedBytes -Sum).Sum;"
            "$b=(Get-NetAdapterStatistics|Measure-Object SentBytes -Sum).Sum;$a+$b", timeout=8)
        try:
            return int(out.strip())
        except Exception:
            pass
        m = re.search(r"(?im)^\s*Bytes\s+([0-9]+)\s+([0-9]+)",
                      proc.run_hidden(["netstat", "-e"], timeout=6))
        return (int(m.group(1)) + int(m.group(2))) if m else 0
    total = 0
    try:
        import os
        for ifc in os.listdir("/sys/class/net"):
            if ifc == "lo":
                continue
            for f in ("tx_bytes", "rx_bytes"):
                try:
                    with open(f"/sys/class/net/{ifc}/statistics/{f}") as fh:
                        total += int(fh.read())
                except Exception:
                    pass
    except Exception:
        pass
    return total


def ping_once(host: str, timeout: float = 1.0) -> float | None:
    cmd = (["ping", "-n", "1", "-w", str(int(timeout * 1000)), host] if IS_WIN
           else ["ping", "-c", "1", "-W", str(int(timeout)), host])
    m = re.search(r"(?:time|tiempo)\s*[=<]\s*([0-9]+(?:[.,][0-9]+)?)",
                  proc.run_hidden(cmd, timeout=timeout + 1.5), re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def measure_link_speed(streams: int = 8, payload: int = 1400) -> float:
    from .flood import udp_process_cmd
    procs = []
    for i in range(streams):
        try:
            procs.append(proc.popen_hidden(udp_process_cmd(INTERNET, 41000 + i, payload)))
        except Exception:
            pass
    time.sleep(1.2)
    b0, t0 = net_bytes(), time.time()
    time.sleep(1.4)
    b1 = net_bytes()
    dt = max(0.5, time.time() - t0)
    for p in procs:
        try:
            p.kill()
        except Exception:
            pass
    return max(0.0, (b1 - b0) * 8 / dt / 1e6)


def snapshot() -> dict:
    return {
        "local_ip": get_local_ip(),
        "local_mac": get_local_mac(),
        "gateway": get_gateway(),
        "cidr": get_cidr(),
        "wifi": get_wifi_info(),
        "hostname": socket.gethostname(),
        "iface": get_interface_name(),
    }