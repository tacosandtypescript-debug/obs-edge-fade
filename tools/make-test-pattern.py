#!/usr/bin/env python3
"""Generates the RGBA test pattern used by the end-to-end OBS check.

The layout is chosen so a single screenshot answers every question at once.

    y     0 ..  59    solid green band        -> vertical orientation marker
    y    60 .. 719    solid red, alpha 255    -> horizontal fades and the
                                                 premultiplication check
    y   720 .. 899    solid grey, alpha 128   -> same checks over a source that
                                                 is already semi transparent: the
                                                 ratio rgb/alpha must not change
    y   900 .. 979    solid blue band         -> vertical orientation marker
    y   980 .. 1079   transparent black       -> the border must reach alpha 0
                                                 with no residue
    corners           flat markers, inset so they never touch a fade edge

The green/blue bands make a vertical flip immediately visible: if blue shows up
at the top of the screenshot, the source texture is stored bottom-up.

Usage:
    python tools/make-test-pattern.py [--width 1920] [--height 1080] [--out path]
"""

from __future__ import annotations

import argparse
from pathlib import Path

BAND = 60
RED_END = 720
SEMI_END = 900
BLUE_END = 980
GREY = 128
MARKER = 30
MARKER_INSET = 40


def build(width: int, height: int) -> bytes:
    data = bytearray(width * height * 4)

    def fill(x0: int, y0: int, x1: int, y1: int, rgba: tuple[int, int, int, int]) -> None:
        for y in range(max(0, y0), min(height, y1)):
            start = (y * width + max(0, x0)) * 4
            end = (y * width + min(width, x1)) * 4
            data[start:end] = bytes(rgba) * ((end - start) // 4)

    fill(0, 0, width, min(BAND, height), (0, 255, 0, 255))
    fill(0, BAND, width, min(RED_END, height), (255, 0, 0, 255))
    fill(0, RED_END, width, min(SEMI_END, height), (GREY, GREY, GREY, 128))
    fill(0, SEMI_END, width, min(BLUE_END, height), (0, 0, 255, 255))
    # The remainder stays fully transparent.

    # Flat markers in the top corners, inset so they sit outside the fades.
    fill(MARKER_INSET, MARKER_INSET, MARKER_INSET + MARKER, MARKER_INSET + MARKER, (255, 255, 0, 255))
    fill(
        width - MARKER_INSET - MARKER,
        MARKER_INSET,
        width - MARKER_INSET,
        MARKER_INSET + MARKER,
        (0, 255, 255, 255),
    )

    return bytes(data)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--width", type=int, default=1920)
    parser.add_argument("--height", type=int, default=1080)
    parser.add_argument("--out", default="tests/fixtures/edge-fade-pattern.png")
    args = parser.parse_args()

    try:
        from PIL import Image
    except ImportError as exc:  # pragma: no cover - tooling helper
        raise SystemExit(f"Pillow is required to write the PNG: {exc}") from exc

    data = build(args.width, args.height)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    image = Image.frombytes("RGBA", (args.width, args.height), data)
    image.save(out)

    print(f"{out}: {args.width}x{args.height} ({image.mode})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
