"""Load and save device mappings and room config."""

from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DEVICES_PATH = DATA_DIR / "devices.json"
ROOMS_PATH = DATA_DIR / "rooms.json"

_lock = threading.Lock()


def _ensure_data_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    if not DEVICES_PATH.exists():
        DEVICES_PATH.write_text(json.dumps({"mappings": {}}, indent=2), encoding="utf-8")
    if not ROOMS_PATH.exists():
        default_rooms = {
            "rooms": [
                {
                    "id": "living_room",
                    "name": "Living Room",
                    "label": "LIVING ROOM",
                    "x": 15,
                    "y": 15,
                    "w": 40,
                    "h": 40,
                },
                {
                    "id": "bedroom",
                    "name": "Bedroom",
                    "label": "BEDROOM",
                    "x": 55,
                    "y": 15,
                    "w": 40,
                    "h": 40,
                },
                {
                    "id": "kitchen",
                    "name": "Kitchen",
                    "label": "KITCHEN",
                    "x": 15,
                    "y": 55,
                    "w": 40,
                    "h": 40,
                },
                {
                    "id": "office",
                    "name": "Office",
                    "label": "OFFICE",
                    "x": 55,
                    "y": 55,
                    "w": 40,
                    "h": 40,
                },
            ],
            "unassigned_id": "unassigned",
        }
        ROOMS_PATH.write_text(json.dumps(default_rooms, indent=2), encoding="utf-8")


def load_rooms() -> dict[str, Any]:
    _ensure_data_files()
    with _lock:
        with ROOMS_PATH.open(encoding="utf-8") as f:
            return json.load(f)


def load_mappings() -> dict[str, Any]:
    _ensure_data_files()
    with _lock:
        with DEVICES_PATH.open(encoding="utf-8") as f:
            data = json.load(f)
    return data.get("mappings", {})


def save_mappings(mappings: dict[str, Any]) -> None:
    _ensure_data_files()
    with _lock:
        with DEVICES_PATH.open("w", encoding="utf-8") as f:
            json.dump({"mappings": mappings}, f, indent=2)


def normalize_mac(mac: str) -> str:
    cleaned = mac.strip().lower().replace("-", ":")
    parts = cleaned.split(":")
    if len(parts) == 6:
        return ":".join(p.zfill(2)[-2:] for p in parts)
    return cleaned


def get_mapping(mac: str) -> dict[str, Any]:
    mac = normalize_mac(mac)
    mappings = load_mappings()
    return mappings.get(
        mac,
        {
            "name": "",
            "person": "",
            "room": "unassigned",
            "icon": "device",
        },
    )


def update_mapping(mac: str, payload: dict[str, Any]) -> dict[str, Any]:
    mac = normalize_mac(mac)
    mappings = load_mappings()
    current = mappings.get(
        mac,
        {
            "name": "",
            "person": "",
            "room": "unassigned",
            "icon": "device",
        },
    )
    for key in ("name", "person", "room", "icon"):
        if key in payload and payload[key] is not None:
            current[key] = str(payload[key]).strip()
    if not current.get("room"):
        current["room"] = "unassigned"
    mappings[mac] = current
    save_mappings(mappings)
    return current


def merge_devices_with_mappings(scanned: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mappings = load_mappings()
    rooms_data = load_rooms()
    room_by_id = {r["id"]: r for r in rooms_data.get("rooms", [])}
    room_by_id["unassigned"] = {
        "id": "unassigned",
        "name": "Unassigned",
        "label": "UNASSIGNED",
    }

    merged: list[dict[str, Any]] = []
    for device in scanned:
        mac = normalize_mac(device.get("mac", ""))
        mapping = mappings.get(
            mac,
            {
                "name": "",
                "person": "",
                "room": "unassigned",
                "icon": "device",
            },
        )
        room_id = mapping.get("room") or "unassigned"
        room_info = room_by_id.get(room_id, room_by_id["unassigned"])
        display_name = mapping.get("name") or device.get("hostname") or mac
        merged.append(
            {
                **device,
                "mac": mac,
                "display_name": display_name,
                "person": mapping.get("person", ""),
                "room": room_id,
                "room_name": room_info.get("name", "Unassigned"),
                "room_label": room_info.get("label", "UNASSIGNED"),
                "icon": mapping.get("icon") or "device",
                "assigned": mac in mappings and bool(mappings[mac].get("room") != "unassigned" or mappings[mac].get("name") or mappings[mac].get("person")),
            }
        )
    return merged
