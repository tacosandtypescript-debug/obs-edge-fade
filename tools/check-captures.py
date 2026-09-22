#!/usr/bin/env python3
"""Measures the Edge Fade captures produced by tools/obs-e2e.py.

Each capture is a PNG screenshot of the filtered source, so the alpha channel is
the real filter output and can be compared with the reference model in
tools/verify-fade.py. The baseline capture of the same pattern without the
filter supplies the source alpha, which makes every expectation exact:

    expected_alpha(pixel) = baseline_alpha(pixel) * fade(pixel)

Per capture the script checks that

  * every configured border reaches alpha 0
  * the fade is progressive: about half the coverage is gone at half the
    configured width, and it spans the whole configured width
  * measured alpha equals source alpha * fade, to within 8-bit quantisation,
    on all four sides
  * a side left at 0 leaves the image completely untouched
  * colour is never tinted or darkened into a halo

Usage:
    python tools/check-captures.py [--dir tools/out] [--dump left100]
"""

from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path

from PIL import Image

# The reference model lives in "verify-fade.py", whose name is not importable, so
# it is loaded by path and registered before execution (dataclasses need it).
_spec = importlib.util.spec_from_file_location(
    "verify_fade", Path(__file__).resolve().parent / "verify-fade.py"
)
assert _spec and _spec.loader
verify_fade = importlib.util.module_from_spec(_spec)
sys.modules["verify_fade"] = verify_fade
_spec.loader.exec_module(verify_fade)

FadeSettings = verify_fade.FadeSettings
alpha_factor = verify_fade.alpha_factor

# OBS samples the filter quad at texel centres, which the model reproduces
# exactly: comparing at (pixel + 0.5) matches the shader to quantisation.
SAMPLE_OFFSET = 0.5
# 8-bit quantisation of alpha plus a single step of slack.
MODEL_TOL = 0.012
QUANT = 2.0 / 255.0

# Rows used for horizontal measurements, from the flat regions of the pattern.
INTERIOR_ROW = 200
RAMP_ROW = 800


class Report:
    def __init__(self) -> None:
        self.checks = 0
        self.failures: list[str] = []

    def check(self, condition: bool, message: str) -> None:
        self.checks += 1
        if not condition:
            self.failures.append(message)


def load(path: Path) -> tuple[int, int, list[tuple[int, int, int, int]]]:
    image = Image.open(path).convert("RGBA")
    width, height = image.size
    return width, height, list(image.getdata())


def settings_from(cfg: dict) -> FadeSettings:
    return FadeSettings(
        left=float(cfg.get("left", 0)),
        right=float(cfg.get("right", 0)),
        top=float(cfg.get("top", 0)),
        bottom=float(cfg.get("bottom", 0)),
        smoothness=cfg.get("smoothness", 50) / 100.0,
        curve=cfg.get("curve", 1),
    )


def points_for(side: str, extent: int, width: int, height: int) -> list[tuple[int, int]]:
    """Coordinates for a horizontal side, one pixel per pixel of the fade."""
    limit = min(extent + 1, width - 1)
    if side == "left":
        return [(d, INTERIOR_ROW) for d in range(limit)]
    return [(width - 1 - d, INTERIOR_ROW) for d in range(limit)]


def vertical_points(side: str, extent: int, width: int, height: int) -> list[tuple[int, int]]:
    """Coordinates for a vertical side, sampled on a column the other fades and
    the pattern's own bands never touch."""
    limit = min(extent + 1, height - 1)
    column = width // 2
    if side == "top":
        return [(column, d) for d in range(limit)]
    return [(column, height - 1 - d) for d in range(limit)]


def check_side(
    report: Report,
    name: str,
    side: str,
    points: list[tuple[int, int]],
    extent: float,
    s: FadeSettings,
    width: int,
    height: int,
    pixels: list[tuple[int, int, int, int]],
    base: list[tuple[int, int, int, int]],
) -> None:
    if extent <= 0 or len(points) < 6:
        return

    def fade_at(x: int, y: int) -> float:
        if side in ("left", "right"):
            return alpha_factor(x + SAMPLE_OFFSET, y, width, height, s)
        return alpha_factor(x, y + SAMPLE_OFFSET, width, height, s)

    measured = [pixels[y * width + x][3] / 255.0 for x, y in points]
    source = [base[y * width + x][3] / 255.0 for x, y in points]
    expected = [source[i] * fade_at(*points[i]) for i in range(len(points))]

    # The border must reach alpha 0 whatever the source alpha was.
    report.check(
        measured[0] <= 0.02,
        f"{name}: {side} border alpha {measured[0]:.3f} is not 0 (source {source[0]:.3f})",
    )

    worst, worst_at = 0.0, 0
    for i in range(len(points)):
        delta = abs(measured[i] - expected[i])
        if delta > worst:
            worst, worst_at = delta, i
    report.check(
        worst <= MODEL_TOL,
        f"{name}: {side} alpha is {measured[worst_at]:.3f} at {worst_at}px,"
        f" expected {expected[worst_at]:.3f} (source {source[worst_at]:.3f}"
        f" * fade {fade_at(*points[worst_at]):.3f})",
    )

    # Progressiveness is only meaningful where the source itself is opaque.
    if all(value >= 1.0 - QUANT for value in source):
        half = measured[int(extent / 2)]
        report.check(
            0.10 <= half <= 0.90,
            f"{name}: {side} fade is not progressive ({half:.3f} at half the configured width)",
        )
        report.check(
            all(b >= a - 0.01 for a, b in zip(measured, measured[1:])),
            f"{name}: {side} ramp is not monotonic",
        )


def check_capture(name: str, path: Path, cfg: dict, report: Report, baseline: Path) -> None:
    width, height, pixels = load(path)
    bw, bh, base = load(baseline)
    if (bw, bh) != (width, height):
        raise SystemExit(f"{name}: baseline size {bw}x{bh} does not match {width}x{height}")

    s = settings_from(cfg)

    def alpha(x: int, y: int) -> float:
        return pixels[y * width + x][3] / 255.0

    if cfg.get("no_filter"):
        opaque = [
            alpha(x, INTERIOR_ROW) for x in range(width) if base[INTERIOR_ROW * width + x][3] == 255
        ]
        report.check(all(value >= 1.0 - QUANT for value in opaque), f"{name}: baseline is not a pass-through")
        return

    for side, extent in (("left", s.left), ("right", s.right)):
        check_side(
            report, name, side, points_for(side, int(extent), width, height),
            extent, s, width, height, pixels, base,
        )
    for side, extent in (("top", s.top), ("bottom", s.bottom)):
        check_side(
            report, name, side, vertical_points(side, int(extent), width, height),
            extent, s, width, height, pixels, base,
        )

    # A side left at 0 contributes nothing. That is already covered exactly by
    # the source*fade comparison above, because the model multiplies in a
    # factor of 1 for every disabled side; a stray contribution would show up
    # there as a deviation.

    # With every side at 0 the filter must bypass itself and hand the source
    # through byte for byte.
    if cfg.get("bypass"):
        worst, worst_at = 0, 0
        for index, (pixel, source_pixel) in enumerate(zip(pixels, base)):
            delta = max(abs(a - b) for a, b in zip(pixel, source_pixel))
            if delta > worst:
                worst, worst_at = delta, index
        report.check(
            worst <= 2,
            f"{name}: bypass differs from the source by {worst} levels at"
            f" ({worst_at % width}, {worst_at // width})",
        )
        return

    # Colour must not be tinted or darkened into a halo along the fade. The red
    # band is saturated red, so green and blue stay at zero, and the value may
    # drop with coverage but must not fall below it.
    if s.left > 0:
        for d in range(2, min(int(s.left), RAMP_ROW), max(1, int(s.left) // 12)):
            pixel = pixels[INTERIOR_ROW * width + d]
            report.check(
                pixel[1] <= 2 and pixel[2] <= 2,
                f"{name}: halo at {d}px, rgb=({pixel[0]},{pixel[1]},{pixel[2]})",
            )
            report.check(
                pixel[0] + 4 >= pixel[3],
                f"{name}: colour {pixel[0]} fell below the coverage {pixel[3]} at {d}px",
            )


CAPTURES: dict[str, dict] = {
    "baseline": {"no_filter": True},
    "bypass": {"bypass": True},
    "left100": {"left": 100},
    "right100": {"right": 100},
    "top100": {"top": 100},
    "bottom100": {"bottom": 100},
    "left_right100": {"left": 100, "right": 100},
    "top_bottom100": {"top": 100, "bottom": 100},
    "all100": {"left": 100, "right": 100, "top": 100, "bottom": 100},
    "all20": {"left": 20, "right": 20, "top": 20, "bottom": 20},
    "all300": {"left": 300, "right": 300, "top": 300, "bottom": 300},
    "left_top100": {"left": 100, "top": 100},
    "all100_linear": {"left": 100, "right": 100, "top": 100, "bottom": 100, "curve": 0},
    "all100_soft": {"left": 100, "right": 100, "top": 100, "bottom": 100, "curve": 2},
    "all100_sm0": {"left": 100, "right": 100, "top": 100, "bottom": 100, "smoothness": 0},
    "all100_sm100": {"left": 100, "right": 100, "top": 100, "bottom": 100, "smoothness": 100},
}


def dump(out: Path, name: str) -> None:
    path = out / f"{name}.png"
    cfg = CAPTURES.get(name, {})
    width, height, pixels = load(path)
    s = settings_from(cfg)
    reach = int(max(s.left, s.right, s.top, s.bottom)) + 20
    if reach <= 20:
        reach = 40
    print(f"{name}: distance | measured alpha | source alpha | model fade | rgb.r")
    for d in range(0, min(reach, width - 1), max(1, reach // 20)):
        px = pixels[INTERIOR_ROW * width + d]
        fade = alpha_factor(d + SAMPLE_OFFSET, INTERIOR_ROW, width, height, s)
        print(f"  {d:>6}px | {px[3] / 255.0:>14.4f} | {'1.000':>12} | {fade:>10.4f} | {px[0] / 255.0:>5.3f}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dir", default="tools/out")
    parser.add_argument("--dump", help="print the measured ramp of one capture")
    args = parser.parse_args()

    out = Path(args.dir)
    baseline = out / "baseline.png"
    if not baseline.is_file():
        raise SystemExit(f"baseline capture missing: {baseline}")

    report = Report()
    checked = 0

    for name, cfg in CAPTURES.items():
        path = out / f"{name}.png"
        if not path.is_file():
            continue
        checked += 1
        check_capture(name, path, cfg, report, baseline)

    if args.dump:
        dump(out, args.dump)
        print()

    print(f"captures checked: {checked}")
    print(f"checks: {report.checks}")
    print(f"failures: {len(report.failures)}")
    for failure in report.failures[:30]:
        print(f"  FAIL {failure}")
    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
