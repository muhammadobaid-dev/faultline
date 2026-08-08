"""Windows LAN discovery via ARP table + optional ping sweep + hostname lookup."""

from __future__ import annotations

import concurrent.futures
import ipaddress
import platform
import re
import socket
import subprocess
import threading
import uuid
from datetime import datetime, timezone
from typing import Any

_last_scan: list[dict[str, Any]] = []
_last_scan_at: str | None = None
_scan_lock = threading.Lock()
_scanning = False

ARP_LINE_RE = re.compile(
    r"^\s*(\d{1,3}(?:\.\d{1,3}){3})\s+([0-9a-fA-F]{2}(?:[-:][0-9a-fA-F]{2}){5})\s+(\w+)",
    re.MULTILINE,
)


def _run(cmd: list[str], timeout: float = 30.0) -> str:
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            creationflags=subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0,
        )
        return (result.stdout or "") + (result.stderr or "")
    except (subprocess.TimeoutExpired, OSError, ValueError):
        return ""


def normalize_mac(mac: str) -> str:
    cleaned = mac.strip().lower().replace("-", ":")
    parts = cleaned.split(":")
    if len(parts) == 6:
        return ":".join(p.zfill(2)[-2:] for p in parts)
    return cleaned


def get_local_ip() -> str | None:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
    except OSError:
        return None


def get_subnet_hosts(local_ip: str | None = None) -> list[str]:
    ip = local_ip or get_local_ip()
    if not ip:
        return []
    try:
        # Assume /24 home LAN (common for WiFi routers)
        network = ipaddress.ip_network(f"{ip}/24", strict=False)
        return [str(host) for host in network.hosts()]
    except ValueError:
        return []


def ping_host(ip: str, timeout_ms: int = 400) -> bool:
    system = platform.system()
    if system == "Windows":
        cmd = ["ping", "-n", "1", "-w", str(timeout_ms), ip]
    else:
        cmd = ["ping", "-c", "1", "-W", "1", ip]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=(timeout_ms / 1000.0) + 1.5,
            creationflags=subprocess.CREATE_NO_WINDOW if system == "Windows" else 0,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, OSError):
        return False


def ping_sweep(hosts: list[str], max_workers: int = 64) -> None:
    """Warm ARP table by pinging subnet hosts concurrently."""
    if not hosts:
        return
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as pool:
        list(pool.map(ping_host, hosts))


def parse_arp_table() -> list[dict[str, str]]:
    output = _run(["arp", "-a"])
    devices: list[dict[str, str]] = []
    seen: set[str] = set()

    for match in ARP_LINE_RE.finditer(output):
        ip, mac, iface_type = match.groups()
        mac_n = normalize_mac(mac)
        # Skip multicast / incomplete / broadcast-ish
        if mac_n.startswith("ff:ff:ff") or mac_n == "00:00:00:00:00:00":
            continue
        if mac_n.startswith("01:00:5e") or mac_n.startswith("33:33:"):
            continue
        try:
            first_octet = int(ip.split(".")[0])
            if first_octet >= 224 or ip.endswith(".255"):
                continue
        except ValueError:
            continue
        if mac_n in seen:
            continue
        seen.add(mac_n)
        devices.append(
            {
                "ip": ip,
                "mac": mac_n,
                "arp_type": iface_type.lower(),
            }
        )
    return devices


def resolve_hostname(ip: str, timeout: float = 0.15) -> str:
    try:
        socket.setdefaulttimeout(timeout)
        name, _, _ = socket.gethostbyaddr(ip)
        return name.split(".")[0]
    except (socket.herror, socket.gaierror, OSError, TimeoutError):
        return ""


def get_local_mac(local_ip: str | None = None) -> str | None:
    """Best-effort local adapter MAC."""
    try:
        node = uuid.getnode()
        # uuid.getnode() may be a random 48-bit value if it can't find a MAC
        mac = ":".join(f"{(node >> ele) & 0xFF:02x}" for ele in range(40, -1, -8))
        if mac and mac != "00:00:00:00:00:00":
            return mac
    except Exception:  # noqa: BLE001
        pass

    ip = local_ip or get_local_ip()
    if not ip:
        return None
    for item in parse_arp_table():
        if item["ip"] == ip and not item["mac"].startswith("00:00:00"):
            return item["mac"]
    return None


def estimate_signal_bars(ip: str, local_ip: str | None) -> int:
    """Heuristic signal bars from last octet proximity (display only, not real RSSI)."""
    if not local_ip:
        return 3
    try:
        a = int(ip.split(".")[-1])
        b = int(local_ip.split(".")[-1])
        dist = abs(a - b)
        if dist < 10:
            return 4
        if dist < 40:
            return 3
        if dist < 100:
            return 2
        return 1
    except (ValueError, IndexError):
        return 2


def scan_network(do_ping_sweep: bool = True) -> list[dict[str, Any]]:
    global _last_scan, _last_scan_at, _scanning

    with _scan_lock:
        if _scanning:
            return list(_last_scan)
        _scanning = True

    try:
        local_ip = get_local_ip()
        if do_ping_sweep and local_ip:
            hosts = get_subnet_hosts(local_ip)
            # Cap sweep size for speed on huge networks
            if len(hosts) > 254:
                hosts = hosts[:254]
            ping_sweep(hosts)

        arp_devices = parse_arp_table()
        now = datetime.now(timezone.utc).isoformat()

        results: list[dict[str, Any]] = []
        for item in arp_devices:
            hostname = resolve_hostname(item["ip"])
            results.append(
                {
                    "ip": item["ip"],
                    "mac": item["mac"],
                    "hostname": hostname,
                    "arp_type": item.get("arp_type", ""),
                    "signal_bars": estimate_signal_bars(item["ip"], local_ip),
                    "online": True,
                    "last_seen": now,
                    "is_local": item["ip"] == local_ip,
                }
            )

        # Ensure local machine appears even if ARP omitted it
        if local_ip:
            local_mac = None
            for r in results:
                if r["ip"] == local_ip:
                    local_mac = r["mac"]
                    r["is_local"] = True
                    if local_mac.startswith("00:00:00"):
                        real_mac = get_local_mac(local_ip)
                        if real_mac:
                            r["mac"] = real_mac
                            local_mac = real_mac
                    break
            if local_mac is None:
                real_mac = get_local_mac(local_ip) or "00:00:00:00:00:01"
                results.append(
                    {
                        "ip": local_ip,
                        "mac": real_mac,
                        "hostname": socket.gethostname(),
                        "arp_type": "static",
                        "signal_bars": 4,
                        "online": True,
                        "last_seen": now,
                        "is_local": True,
                    }
                )

        results.sort(key=lambda d: tuple(int(x) for x in d["ip"].split(".")))

        with _scan_lock:
            _last_scan = results
            _last_scan_at = now

        return results
    finally:
        with _scan_lock:
            _scanning = False


def get_last_scan() -> tuple[list[dict[str, Any]], str | None]:
    with _scan_lock:
        return list(_last_scan), _last_scan_at


def is_scanning() -> bool:
    with _scan_lock:
        return _scanning
