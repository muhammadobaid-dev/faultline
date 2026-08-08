"""WiFi Device Room Detection — Camera Screen server."""

from __future__ import annotations

import threading
import time
from datetime import datetime

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO

import scanner
import storage

app = Flask(__name__)
app.config["SECRET_KEY"] = "wifi-room-camera-dev"
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

SCAN_INTERVAL_SEC = 20
_bg_started = False
_bg_lock = threading.Lock()


def _emit_devices() -> list:
    scanned, scanned_at = scanner.get_last_scan()
    devices = storage.merge_devices_with_mappings(scanned)
    payload = {
        "devices": devices,
        "scanned_at": scanned_at,
        "scanning": scanner.is_scanning(),
        "local_ip": scanner.get_local_ip(),
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }
    socketio.emit("devices_update", payload)
    return devices


def _background_scanner() -> None:
    # First scan with ping sweep
    try:
        scanner.scan_network(do_ping_sweep=True)
        _emit_devices()
    except Exception as exc:  # noqa: BLE001
        print(f"[scan] initial error: {exc}")

    while True:
        time.sleep(SCAN_INTERVAL_SEC)
        try:
            # Periodic lighter refresh: ARP only (faster); full sweep every other cycle
            scanner.scan_network(do_ping_sweep=True)
            _emit_devices()
        except Exception as exc:  # noqa: BLE001
            print(f"[scan] background error: {exc}")


def start_background_scanner() -> None:
    global _bg_started
    with _bg_lock:
        if _bg_started:
            return
        _bg_started = True
        t = threading.Thread(target=_background_scanner, daemon=True, name="lan-scanner")
        t.start()


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/rooms")
def api_rooms():
    data = storage.load_rooms()
    return jsonify(data)


@app.route("/api/devices")
def api_devices():
    scanned, scanned_at = scanner.get_last_scan()
    devices = storage.merge_devices_with_mappings(scanned)
    return jsonify(
        {
            "devices": devices,
            "scanned_at": scanned_at,
            "scanning": scanner.is_scanning(),
            "local_ip": scanner.get_local_ip(),
            "server_time": datetime.now().isoformat(timespec="seconds"),
        }
    )


@app.route("/api/scan", methods=["POST"])
def api_scan():
    body = request.get_json(silent=True) or {}
    do_sweep = body.get("ping_sweep", True)
    devices_raw = scanner.scan_network(do_ping_sweep=bool(do_sweep))
    devices = storage.merge_devices_with_mappings(devices_raw)
    _, scanned_at = scanner.get_last_scan()
    payload = {
        "devices": devices,
        "scanned_at": scanned_at,
        "scanning": False,
        "local_ip": scanner.get_local_ip(),
        "server_time": datetime.now().isoformat(timespec="seconds"),
    }
    socketio.emit("devices_update", payload)
    return jsonify(payload)


@app.route("/api/devices/<path:mac>", methods=["POST"])
def api_assign_device(mac: str):
    body = request.get_json(silent=True) or {}
    mapping = storage.update_mapping(mac, body)
    scanned, scanned_at = scanner.get_last_scan()
    devices = storage.merge_devices_with_mappings(scanned)
    payload = {
        "devices": devices,
        "scanned_at": scanned_at,
        "scanning": scanner.is_scanning(),
        "local_ip": scanner.get_local_ip(),
        "server_time": datetime.now().isoformat(timespec="seconds"),
        "updated": {"mac": storage.normalize_mac(mac), **mapping},
    }
    socketio.emit("devices_update", payload)
    return jsonify(payload)


@socketio.on("connect")
def on_connect():
    scanned, scanned_at = scanner.get_last_scan()
    devices = storage.merge_devices_with_mappings(scanned)
    socketio.emit(
        "devices_update",
        {
            "devices": devices,
            "scanned_at": scanned_at,
            "scanning": scanner.is_scanning(),
            "local_ip": scanner.get_local_ip(),
            "server_time": datetime.now().isoformat(timespec="seconds"),
        },
    )


@socketio.on("request_scan")
def on_request_scan():
    scanner.scan_network(do_ping_sweep=True)
    _emit_devices()


if __name__ == "__main__":
    start_background_scanner()
    print("WiFi Room Camera -> http://127.0.0.1:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False, allow_unsafe_werkzeug=True)
