#!/usr/bin/env python3
"""Installs OBS Edge Fade into the real OBS Studio and verifies that OBS loads it.

Unlike tools/obs-e2e.py this does not touch the scene collection: it copies the
plugin into the OBS plugin folder, launches OBS, asks obs-websocket which filter
kinds are registered, and reports whether the Edge Fade filter is available.

Usage:
    python tools/install-to-obs.py [--dll build_manual/obs-edge-fade.dll]
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import websocket  # type: ignore

OBS_EXE = Path(r"C:\Program Files\obs-studio\bin\64bit\obs64.exe")
PLUGINS_ROOT = Path(os.environ.get("ALLUSERSPROFILE", r"C:\ProgramData")) / "obs-studio" / "plugins"
APPDATA_OBS = Path(os.environ["APPDATA"]) / "obs-studio"
FILTER_ID = "obs_source_style_edge_fade"
FILTER_NAME = "OBS Edge Fade - Edge Fade"
WS_PORT = 4455


def install(dll: Path, root: Path) -> Path:
    target = PLUGINS_ROOT / "obs-edge-fade"
    bin_dir = target / "bin" / "64bit"
    data_dir = target / "data"

    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, bin_dir / "obs-edge-fade.dll")

    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(root / "data", data_dir)

    print(f"plugin : {bin_dir / 'obs-edge-fade.dll'} ({dll.stat().st_size} bytes)")
    print(f"data   : {data_dir}")
    return target


def websocket_config() -> tuple[bool, str, bool]:
    """Returns (auth_required, password, changed)."""
    path = APPDATA_OBS / "plugin_config" / "obs-websocket" / "config.json"
    if not path.is_file():
        return False, "", False

    cfg = json.loads(path.read_text(encoding="utf-8"))
    if not cfg.get("server_enabled", True):
        cfg["server_enabled"] = True
        path.write_text(json.dumps(cfg, indent=4), encoding="utf-8")
        print("note   : obs-websocket was disabled, enabled it for this check")
    return bool(cfg.get("auth_required")), cfg.get("server_password", ""), False


def connect(password: str, auth_required: bool, timeout: float = 90.0) -> websocket.WebSocket:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            ws = websocket.create_connection(f"ws://127.0.0.1:{WS_PORT}", timeout=10)
            break
        except Exception as exc:  # noqa: BLE001 - retry loop
            last = exc
            time.sleep(2)
    else:
        raise SystemExit(f"obs-websocket never came up: {last}")

    while True:
        message = json.loads(ws.recv())
        op = message.get("op")
        if op == 0:
            hello = message["d"]
            identify: dict = {"rpcVersion": hello.get("rpcVersion", 1), "eventSubscriptions": 0}
            auth = hello.get("authentication")
            if auth and auth_required and password:
                secret = base64.b64encode(
                    hashlib.sha256((password + auth["salt"]).encode()).digest()
                ).decode()
                identify["authentication"] = base64.b64encode(
                    hashlib.sha256((secret + auth["challenge"]).encode()).digest()
                ).decode()
            ws.send(json.dumps({"op": 1, "d": identify}))
        elif op == 2:
            return ws
        elif op == 9:
            raise SystemExit(f"obs-websocket rejected identification: {message}")


def request(ws: websocket.WebSocket, request_type: str, data: dict | None = None) -> dict:
    request_id = f"{request_type}-{time.time()}"
    payload: dict = {"op": 6, "d": {"requestType": request_type, "requestId": request_id}}
    if data is not None:
        payload["d"]["requestData"] = data
    ws.send(json.dumps(payload))
    while True:
        message = json.loads(ws.recv())
        if message.get("op") != 7 or message["d"]["requestId"] != request_id:
            continue
        status = message["d"]["requestStatus"]
        if not status["result"]:
            raise SystemExit(f"{request_type} failed: {status}")
        return message["d"].get("responseData", {})


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", default="build_manual/obs-edge-fade.dll")
    parser.add_argument("--keep-open", action="store_true", help="leave OBS running when done")
    parser.add_argument("--seconds", type=float, default=12.0)
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    dll = Path(args.dll)
    if not dll.is_absolute():
        dll = root / dll
    if not dll.is_file():
        raise SystemExit(f"plugin dll not found: {dll}")

    if (Path(os.environ.get("ProgramFiles", "")) / "obs-studio" / "bin" / "64bit" / "obs64.exe").is_file():
        pass
    elif not OBS_EXE.is_file():
        raise SystemExit(f"OBS Studio not found at {OBS_EXE}")

    if subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq obs64.exe", "/NH"], capture_output=True, text=True
    ).stdout.lower().count("obs64.exe"):
        raise SystemExit("OBS Studio is running. Close it and run this again.")

    install(dll, root)

    auth_required, password, _ = websocket_config()
    ws_cfg_path = APPDATA_OBS / "plugin_config" / "obs-websocket" / "config.json"
    original_cfg = ws_cfg_path.read_text(encoding="utf-8") if ws_cfg_path.is_file() else None

    sentinel = APPDATA_OBS / ".sentinel"
    if sentinel.is_dir():
        for marker in sentinel.glob("run_*"):
            marker.unlink()

    logs_before = set((APPDATA_OBS / "logs").glob("*.txt")) if (APPDATA_OBS / "logs").is_dir() else set()
    process = subprocess.Popen(
        [str(OBS_EXE), "--disable-updater", "--disable-shutdown-check", "--minimize-to-tray"],
        cwd=str(OBS_EXE.parent),
    )

    loaded = False
    try:
        ws = connect(password, auth_required)
        time.sleep(args.seconds)
        kinds = request(ws, "GetSourceFilterKindList").get("sourceFilterKinds", [])
        loaded = FILTER_ID in kinds

        print(f"filter kinds registered: {len(kinds)}")
        print(f"'{FILTER_ID}' registered: {'YES' if loaded else 'NO'}")

        if loaded:
            # Round-trip the filter through a throwaway scene to prove it can be
            # created with the settings the UI would send.
            request(ws, "CreateScene", {"sceneName": "oef_install_check"})
            request(
                ws,
                "CreateInput",
                {
                    "sceneName": "oef_install_check",
                    "inputName": "oef_check_source",
                    "inputKind": "color_source_v3",
                    "inputSettings": {"color": 4294901760, "width": 1920, "height": 1080},
                    "sceneItemEnabled": True,
                },
            )
            request(
                ws,
                "CreateSourceFilter",
                {
                    "sourceName": "oef_check_source",
                    "filterName": FILTER_NAME,
                    "filterKind": FILTER_ID,
                    "filterSettings": {
                        "edge_fade.linked": False,
                        "edge_fade.left": 120,
                        "edge_fade.right": 120,
                        "edge_fade.top": 120,
                        "edge_fade.bottom": 120,
                        "edge_fade.smoothness": 50,
                        "edge_fade.curve": 1,
                    },
                },
            )
            filters = request(ws, "GetSourceFilterList", {"sourceName": "oef_check_source"}).get("filters", [])
            entry = next((f for f in filters if f.get("filterKind") == FILTER_ID), None)
            print(f"filter instance name: {entry['filterName'] if entry else 'MISSING'}")
            print(f"filter settings     : {json.dumps(entry.get('filterSettings', {})) if entry else '-'}")

            request(ws, "RemoveSourceFilter", {"sourceName": "oef_check_source", "filterName": FILTER_NAME})
            request(ws, "RemoveInput", {"inputName": "oef_check_source"})
            request(ws, "RemoveScene", {"sceneName": "oef_install_check"})

        ws.close()
    finally:
        time.sleep(0.5)
        if not args.keep_open:
            process.terminate()
            try:
                process.wait(timeout=25)
            except subprocess.TimeoutExpired:
                process.kill()
        if original_cfg is not None and ws_cfg_path.read_text(encoding="utf-8") != original_cfg:
            ws_cfg_path.write_text(original_cfg, encoding="utf-8")

    logs_after = set((APPDATA_OBS / "logs").glob("*.txt"))
    new_logs = sorted(logs_after - logs_before, key=lambda p: p.stat().st_mtime)
    if new_logs:
        print(f"obs log: {new_logs[-1]}")
        for line in new_logs[-1].read_text(errors="ignore").splitlines():
            if "Edge Fade" in line or "obs-edge-fade" in line:
                print(f"  {line}")

    print()
    if loaded:
        print("RESULT: installed and loaded by OBS.")
        print(f"Add it in OBS via Filters > + > '{FILTER_NAME}'.")
        return 0

    print("RESULT: plugin files installed, but OBS did not register the filter.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
