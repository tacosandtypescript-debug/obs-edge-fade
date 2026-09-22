#!/usr/bin/env python3
"""End-to-end check of the Edge Fade filter inside a real OBS Studio.

Builds the scene through obs-websocket (scene, image source, Edge Fade filter),
then asks OBS for a screenshot of the *source*, which returns the texture the
filter chain produced, alpha included. The video output path would flatten the
alpha channel, so it is not used here.

Everything the user already had in OBS is backed up first and restored
afterwards.

Usage:
    python tools/obs-e2e.py --dll build_manual/obs-edge-fade.dll --name baseline --no-filter
    python tools/obs-e2e.py --dll build_manual/obs-edge-fade.dll --matrix
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
PROGRAM_DATA_PLUGINS = Path(os.environ.get("ALLUSERSPROFILE", r"C:\ProgramData")) / "obs-studio" / "plugins"
APPDATA_OBS = Path(os.environ["APPDATA"]) / "obs-studio"

FILTER_ID = "obs_source_style_edge_fade"
SOURCE_NAME = "oef_pattern"
SCENE_NAME = "oef_e2e"
WS_PORT = 4455
WS_PASSWORD = "oef-e2e"


# ---------------------------------------------------------------------------
# Plugin installation
# ---------------------------------------------------------------------------


def install_plugin(dll: Path, root: Path) -> None:
    target = PROGRAM_DATA_PLUGINS / "obs-edge-fade"
    bin_dir = target / "bin" / "64bit"
    data_dir = target / "data"
    bin_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(dll, bin_dir / "obs-edge-fade.dll")
    if data_dir.exists():
        shutil.rmtree(data_dir)
    shutil.copytree(root / "data", data_dir)
    print(f"installed plugin: {bin_dir / 'obs-edge-fade.dll'}")


def prepare_websocket_config() -> None:
    ws_cfg = APPDATA_OBS / "plugin_config" / "obs-websocket" / "config.json"
    ws_cfg.parent.mkdir(parents=True, exist_ok=True)
    ws_cfg.write_text(
        json.dumps(
            {
                "alerts_enabled": False,
                "auth_required": True,
                "first_load": False,
                "server_enabled": True,
                "server_password": WS_PASSWORD,
                "server_port": WS_PORT,
            },
            indent=4,
        ),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# obs-websocket
# ---------------------------------------------------------------------------


def connect(timeout: float = 90.0) -> websocket.WebSocket:
    deadline = time.time() + timeout
    last: Exception | None = None
    while time.time() < deadline:
        try:
            ws = websocket.create_connection(f"ws://127.0.0.1:{WS_PORT}", timeout=15)
            break
        except Exception as exc:  # noqa: BLE001 - retry loop
            last = exc
            time.sleep(2)
    else:
        raise SystemExit(f"obs-websocket never came up: {last}")

    while True:
        raw = ws.recv()
        try:
            message = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if message.get("op") == 0:
            hello = message["d"]
            identify: dict = {"rpcVersion": hello.get("rpcVersion", 1), "eventSubscriptions": 0}
            auth = hello.get("authentication")
            if auth:
                secret = base64.b64encode(
                    hashlib.sha256((WS_PASSWORD + auth["salt"]).encode()).digest()
                ).decode()
                identify["authentication"] = base64.b64encode(
                    hashlib.sha256((secret + auth["challenge"]).encode()).digest()
                ).decode()
            ws.send(json.dumps({"op": 1, "d": identify}))
        elif message.get("op") == 2:
            return ws
        elif message.get("op") == 9:
            raise SystemExit(f"obs-websocket rejected identification: {message}")


class Obs:
    def __init__(self, ws: websocket.WebSocket) -> None:
        self.ws = ws
        self.counter = 0

    def request(self, request_type: str, data: dict | None = None, optional: bool = False) -> dict:
        self.counter += 1
        request_id = f"{request_type}-{self.counter}"
        payload: dict = {"op": 6, "d": {"requestType": request_type, "requestId": request_id}}
        if data is not None:
            payload["d"]["requestData"] = data
        self.ws.send(json.dumps(payload))
        while True:
            message = json.loads(self.ws.recv())
            if message.get("op") != 7 or message["d"]["requestId"] != request_id:
                continue
            status = message["d"]["requestStatus"]
            if not status["result"]:
                if optional:
                    return {"__error__": status}
                raise SystemExit(f"{request_type} failed: {status}")
            return message["d"].get("responseData", {})


def build_scene(obs: Obs, pattern: Path, cfg: dict) -> None:
    scene = obs.request("CreateScene", {"sceneName": SCENE_NAME}, optional=True)
    if "__error__" in scene:
        # Already present from an earlier capture in the same OBS session.
        pass

    created = obs.request(
        "CreateInput",
        {
            "sceneName": SCENE_NAME,
            "inputName": SOURCE_NAME,
            "inputKind": "image_source",
            "inputSettings": {"file": str(pattern), "unload": False},
            "sceneItemEnabled": True,
        },
        optional=True,
    )
    if "__error__" in created:
        obs.request("SetInputSettings", {"inputName": SOURCE_NAME, "inputSettings": {"file": str(pattern)}})

    obs.request("SetCurrentProgramScene", {"sceneName": SCENE_NAME}, optional=True)

    settings = {
        "edge_fade.linked": bool(cfg.get("link", False)),
        "edge_fade.left": int(cfg.get("left", 0)),
        "edge_fade.right": int(cfg.get("right", 0)),
        "edge_fade.top": int(cfg.get("top", 0)),
        "edge_fade.bottom": int(cfg.get("bottom", 0)),
        "edge_fade.smoothness": int(cfg.get("smoothness", 50)),
        "edge_fade.curve": int(cfg.get("curve", 1)),
    }

    filters = obs.request("GetSourceFilterList", {"sourceName": SOURCE_NAME}).get("filters", [])
    existing = next((f for f in filters if f.get("filterKind") == FILTER_ID), None)

    if cfg.get("no_filter"):
        if existing:
            obs.request("RemoveSourceFilter", {"sourceName": SOURCE_NAME, "filterName": existing["filterName"]})
        return

    # "bypass" keeps the filter installed with every side at 0: the plugin must
    # skip its own drawing and pass the source through untouched.
    if cfg.get("bypass"):
        settings = {key: 0 for key in settings if key != "edge_fade.linked"}
        settings["edge_fade.linked"] = False

    if not existing:
        obs.request(
            "CreateSourceFilter",
            {
                "sourceName": SOURCE_NAME,
                "filterName": "OBS Edge Fade - Edge Fade",
                "filterKind": FILTER_ID,
                "filterSettings": settings,
            },
        )
    else:
        obs.request(
            "SetSourceFilterSettings",
            {
                "sourceName": SOURCE_NAME,
                "filterName": existing["filterName"],
                "filterSettings": settings,
                "overlay": True,
            },
        )
        obs.request(
            "SetSourceFilterEnabled",
            {"sourceName": SOURCE_NAME, "filterName": existing["filterName"], "filterEnabled": True},
        )


def screenshot(obs: Obs, target: Path, width: int, height: int, source: str) -> None:
    result = obs.request(
        "GetSourceScreenshot",
        {
            "sourceName": source,
            "imageFormat": "png",
            "imageWidth": width,
            "imageHeight": height,
            "imageCompressionQuality": -1,
        },
    )
    data = result.get("imageData", "")
    if not data.startswith("data:image/png;base64,"):
        raise SystemExit("unexpected screenshot payload")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(data.split(",", 1)[1]))


def find_scene_source(obs: Obs) -> str:
    """Name of the scene as a source, so the screenshot shows the composite."""
    scenes = obs.request("GetSceneList").get("scenes", [])
    names = [s.get("sceneName") for s in scenes if s.get("sceneName")]
    for candidate in (SCENE_NAME, *(names or [])):
        if candidate and candidate in names:
            return candidate
    return SCENE_NAME


MATRIX: list[tuple[str, dict]] = [
    ("baseline", {"no_filter": True}),
    ("bypass", {"bypass": True}),
    ("left100", {"left": 100}),
    ("right100", {"right": 100}),
    ("top100", {"top": 100}),
    ("bottom100", {"bottom": 100}),
    ("left_right100", {"left": 100, "right": 100}),
    ("top_bottom100", {"top": 100, "bottom": 100}),
    ("all100", {"left": 100, "right": 100, "top": 100, "bottom": 100}),
    ("all20", {"left": 20, "right": 20, "top": 20, "bottom": 20}),
    ("all300", {"left": 300, "right": 300, "top": 300, "bottom": 300}),
    ("left_top100", {"left": 100, "top": 100}),
    ("all100_linear", {"left": 100, "right": 100, "top": 100, "bottom": 100, "curve": 0}),
    ("all100_soft", {"left": 100, "right": 100, "top": 100, "bottom": 100, "curve": 2}),
    ("all100_sm0", {"left": 100, "right": 100, "top": 100, "bottom": 100, "smoothness": 0}),
    ("all100_sm100", {"left": 100, "right": 100, "top": 100, "bottom": 100, "smoothness": 100}),
]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dll", required=True)
    parser.add_argument("--name")
    parser.add_argument("--left", type=int, default=0)
    parser.add_argument("--right", type=int, default=0)
    parser.add_argument("--top", type=int, default=0)
    parser.add_argument("--bottom", type=int, default=0)
    parser.add_argument("--smoothness", type=int, default=50)
    parser.add_argument("--curve", type=int, default=1)
    parser.add_argument("--link", action="store_true")
    parser.add_argument("--no-filter", action="store_true")
    parser.add_argument("--matrix", action="store_true")
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument(
        "--composited",
        action="store_true",
        help="screenshot the scene (what the audience sees) instead of the raw source texture",
    )
    parser.add_argument("--settle", type=float, default=1.2, help="seconds to wait after a settings change")
    parser.add_argument("--pattern", default="tests/fixtures/edge-fade-pattern.png")
    parser.add_argument("--keep-config", action="store_true")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    dll = Path(args.dll).resolve()
    if not dll.is_file():
        raise SystemExit(f"plugin dll not found: {dll}")

    install_plugin(dll, root)

    backup = APPDATA_OBS.parent / "obs-studio-oef-backup"
    if backup.exists():
        shutil.rmtree(backup)
    shutil.copytree(APPDATA_OBS, backup)
    print(f"backed up OBS config to {backup}")
    prepare_websocket_config()

    # Stale run markers make OBS believe the last session crashed and it then
    # waits on a Safe Mode dialog that would block the capture.
    sentinel = APPDATA_OBS / ".sentinel"
    if sentinel.is_dir():
        for marker in sentinel.glob("run_*"):
            marker.unlink()

    pattern = (root / args.pattern).resolve()
    # OBS caches image_source textures by path, so the pattern is published under
    # a unique name for every run to guarantee the fresh pixels are loaded.
    staged = root / "tools" / "out" / f"pattern-{int(time.time())}{pattern.suffix}"
    staged.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pattern, staged)
    print(f"pattern: {staged}")

    process = subprocess.Popen(
        [str(OBS_EXE), "--disable-updater", "--disable-shutdown-check", "--minimize-to-tray"],
        cwd=str(OBS_EXE.parent),
    )

    try:
        obs = Obs(connect())
        # Let OBS finish loading sources before touching the scene.
        time.sleep(8)

        cases = MATRIX if args.matrix else [
            (
                args.name or "capture",
                {
                    "left": args.left,
                    "right": args.right,
                    "top": args.top,
                    "bottom": args.bottom,
                    "smoothness": args.smoothness,
                    "curve": args.curve,
                    "link": args.link,
                    "no_filter": args.no_filter,
                },
            )
        ]

        for name, cfg in cases:
            build_scene(obs, staged, cfg)
            time.sleep(args.settle)
            target = root / "tools" / "out" / f"{name}.png"
            source = find_scene_source(obs) if args.composited else SOURCE_NAME
            screenshot(obs, target, args.width, args.height, source)
            print(f"[{name}] {target} (source: {source})")

        obs.ws.close()
    finally:
        time.sleep(1)
        process.terminate()
        try:
            process.wait(timeout=25)
        except subprocess.TimeoutExpired:
            process.kill()

        if not args.keep_config:
            shutil.rmtree(APPDATA_OBS)
            shutil.copytree(backup, APPDATA_OBS)
            print("restored OBS config")

    logs = sorted((APPDATA_OBS / "logs").glob("*.txt"), key=lambda p: p.stat().st_mtime)
    if logs:
        for line in logs[-1].read_text(errors="ignore").splitlines():
            if "Edge Fade" in line or "obs-edge-fade" in line:
                print(f"log: {line}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
