"""
core/proc.py
------------
Subprocesos invisibles + perfilado de hardware para dimensionar
automaticamente el paralelismo del motor de red.
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess

IS_WIN = platform.system() == "Windows"
CREATE_NO_WINDOW = 0x08000000
CREATE_NEW_PROCESS_GROUP = 0x00000200
DEVNULL = subprocess.DEVNULL


def _kw() -> dict:
    return {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP} if IS_WIN else {}


def run_hidden(cmd, timeout: float = 10.0) -> str:
    try:
        p = subprocess.run(list(cmd), capture_output=True, text=True,
                           errors="ignore", timeout=timeout, **_kw())
        return p.stdout or ""
    except Exception:
        return ""


def run_hidden_rc(cmd, timeout: float = 10.0) -> tuple[int, str]:
    try:
        p = subprocess.run(list(cmd), capture_output=True, text=True,
                           errors="ignore", timeout=timeout, **_kw())
        return p.returncode, (p.stdout or "")
    except Exception:
        return -1, ""


def popen_hidden(cmd) -> subprocess.Popen:
    kw = {"creationflags": CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP} if IS_WIN else {"start_new_session": True}
    return subprocess.Popen(list(cmd), stdout=DEVNULL, stderr=DEVNULL, **kw)


def powershell(script: str, timeout: float = 10.0) -> str:
    return run_hidden(["powershell", "-NoProfile", "-NonInteractive", "-Command", script], timeout)


def which(name: str) -> str | None:
    return shutil.which(name)


# ----------------------------------------------------------------------
def cpu_cores() -> int:
    return os.cpu_count() or 4


def cpu_threads() -> int:
    """Hilos logicos disponibles (HT incluido)."""
    try:
        import psutil
        return psutil.cpu_count(logical=True) or cpu_cores()
    except Exception:
        return cpu_cores()


def ram_mb() -> int:
    try:
        import psutil
        return int(psutil.virtual_memory().total / (1024 * 1024))
    except Exception:
        return 4096


def optimal_workers(multiplier: int = 4, cap: int = 64) -> int:
    """Pool de hilos recomendado para escaneo/inyeccion."""
    return max(8, min(cap, cpu_threads() * multiplier))


def hardware_profile() -> dict:
    return {
        "cores": cpu_cores(),
        "threads": cpu_threads(),
        "ram_mb": ram_mb(),
        "workers": optimal_workers(),
        "tier": "ALTO" if cpu_threads() >= 12 and ram_mb() >= 16384
                else ("MEDIO" if cpu_threads() >= 6 else "BASICO"),
    }