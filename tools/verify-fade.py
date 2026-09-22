#!/usr/bin/env python3
"""Reference model of the OBS Edge Fade pixel shader.

This is a CPU mirror of ``data/effects/edge-fade.effect`` used to validate the
alpha maths without a GPU. It implements both the previous (buggy) formula and
the current one so the difference can be inspected, and it runs the full test
matrix from the review request:

  * one side at a time, two sides, all four sides
  * small (10-20 px), medium (100-300 px) and large fade widths
  * 1920x1080, 1080x1920, square, and small sources
  * sources that already carry alpha
  * all sides at 0 (must be an exact pass-through)

Usage:
    python tools/verify-fade.py [--dump spec]

``--dump`` renders one configuration as a text map of the alpha factor.
"""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass

EPSILON = 1e-9


# ---------------------------------------------------------------------------
# Shader maths
# ---------------------------------------------------------------------------


def smoothstep01(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def smootherstep01(t: float) -> float:
    return t * t * t * (t * (t * 6.0 - 15.0) + 10.0)


def quartic01(t: float) -> float:
    return 1.0 - (1.0 - t) ** 4


def edge_curve_fixed(t: float, smoothness: float, mode: int) -> float:
    """Current shader: full-width band, endpoints pinned to 0 and 1."""
    t = min(max(t, 0.0), 1.0)
    s = min(max(smoothness, 0.0), 1.0)

    if mode == 0:
        return t

    if mode == 1:
        return smoothstep01(t) * (1.0 - s) + smootherstep01(t) * s

    return (t * t) * (1.0 - s) + (t * t * (2.0 - t)) * s

def edge_factor_fixed(distance: float, extent: float, smoothness: float, mode: int) -> float:
    if extent <= 0.0:
        return 1.0
    return edge_curve_fixed(distance / extent, smoothness, mode)


def edge_factor_previous(distance: float, extent: float, smoothness: float, mode: int) -> float:
    """Previous shader: smoothness shrank the band, so the gradient never used
    the configured width and alpha collapsed onto the very last pixels."""
    if extent <= 0.0:
        return 1.0

    start = extent * (1.0 - min(max(smoothness, 0.0), 1.0))
    width = max(extent - start, 0.0001)
    t = min(max((distance - start) / width, 0.0), 1.0)

    if mode < 0.5:
        return t
    if mode < 1.5:
        return t * t * (3.0 - 2.0 * t)
    return 1.0 - (1.0 - t) ** 3


# ---------------------------------------------------------------------------
# Filter configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FadeSettings:
    left: float = 0.0
    right: float = 0.0
    top: float = 0.0
    bottom: float = 0.0
    smoothness: float = 0.5  # 0..1, the setting divided by 100
    curve: int = 1  # 0 linear, 1 smooth, 2 soft

    @property
    def bypass(self) -> bool:
        return self.left == 0 and self.right == 0 and self.top == 0 and self.bottom == 0


def alpha_factor(x: float, y: float, width: float, height: float, s: FadeSettings,
                 shader: str = "fixed") -> float:
    """Edge fade factor for the pixel centre at (x, y) in pixel coordinates.

    y grows downwards from the top-left corner, matching
    ``position = uv * source_size`` in the shader.
    """
    factor = edge_factor_fixed if shader == "fixed" else edge_factor_previous

    left = factor(x, s.left, s.smoothness, s.curve)
    right = factor(width - x, s.right, s.smoothness, s.curve)
    top = factor(y, s.top, s.smoothness, s.curve)
    bottom = factor(height - y, s.bottom, s.smoothness, s.curve)

    return left * right * top * bottom


def pixel_center(i: int, n: int) -> float:
    """Pixel centre in pixel coordinates for texel i of n.

    ``uv = (i + 0.5) / n`` and ``position = uv * n``, so the first texel centre
    sits at 0.5 px from the border.
    """
    return i + 0.5


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------


class Report:
    def __init__(self) -> None:
        self.failures: list[str] = []
        self.checks = 0

    def check(self, condition: bool, message: str) -> bool:
        self.checks += 1
        if not condition:
            self.failures.append(message)
        return condition

    def close(self, a: float, b: float, tol: float, message: str) -> bool:
        return self.check(abs(a - b) <= tol, f"{message} ({a!r} vs {b!r})")


def row_alphas(width: int, height: int, s: FadeSettings, y: int, shader: str = "fixed") -> list[float]:
    return [alpha_factor(pixel_center(x, width), pixel_center(y, height), width, height, s, shader)
            for x in range(width)]


def col_alphas(width: int, height: int, s: FadeSettings, x: int, shader: str = "fixed") -> list[float]:
    return [alpha_factor(pixel_center(x, width), pixel_center(y, height), width, height, s, shader)
            for y in range(height)]


def test_endpoints(report: Report) -> None:
    """The border must be fully transparent and the interior untouched."""
    resolutions = [(1920, 1080), (1080, 1920), (1000, 1000), (320, 240), (64, 64)]
    widths = [0, 10, 20, 100, 300, 1000]
    modes = [0, 1, 2]
    smoothnesses = [0.0, 0.25, 0.5, 0.75, 1.0]

    for (w, h) in resolutions:
        for n in widths:
            if n > min(w, h):
                continue
            for mode in modes:
                for sm in smoothnesses:
                    s = FadeSettings(left=float(n), smoothness=sm, curve=mode)

                    if n == 0:
                        # A side at 0 is disabled: the whole row must be untouched.
                        report.check(all(v == 1.0 for v in row_alphas(w, h, s, h // 2)),
                                     f"disabled side modified the image: {w}x{h} mode={mode} s={sm}")
                        continue

                    # The first pixel centre sits half a pixel inside the border:
                    # the factor must be ~0, i.e. fully transparent.
                    first = row_alphas(w, h, s, h // 2)[0]
                    report.check(first <= 0.5 / max(n, 1) + EPSILON,
                                 f"left border not transparent: {w}x{h} n={n} mode={mode} s={sm} -> {first}")

                    # The pixel at the fade distance and beyond must be untouched.
                    if n + 1 < w:
                        inner = row_alphas(w, h, s, h // 2)
                        report.check(all(v == 1.0 for v in inner[n:]),
                                     f"interior modified: {w}x{h} n={n} mode={mode} s={sm}")

                    # Monotonic non-decreasing from the border inwards.
                    ramp = row_alphas(w, h, s, h // 2)[:n + 2]
                    report.check(all(b >= a - EPSILON for a, b in zip(ramp, ramp[1:])),
                                 f"left ramp not monotonic: {w}x{h} n={n} mode={mode} s={sm}")


def test_symmetry(report: Report) -> None:
    """All four sides must behave identically, and horizontal must match vertical."""
    w, h = 1920, 1080
    for mode in [0, 1, 2]:
        for n in [10, 100, 300]:
            for sm in [0.0, 0.5, 1.0]:
                left = FadeSettings(left=float(n), smoothness=sm, curve=mode)
                right = FadeSettings(right=float(n), smoothness=sm, curve=mode)
                top = FadeSettings(top=float(n), smoothness=sm, curve=mode)
                bottom = FadeSettings(bottom=float(n), smoothness=sm, curve=mode)

                left_ramp = row_alphas(w, h, left, h // 2)[:n + 1]
                right_ramp = row_alphas(w, h, right, h // 2)[::-1][:n + 1]
                top_ramp = col_alphas(w, h, top, w // 2)[:n + 1]
                bottom_ramp = col_alphas(w, h, bottom, w // 2)[::-1][:n + 1]

                for name, ramp in (("right", right_ramp), ("top", top_ramp), ("bottom", bottom_ramp)):
                    for i, (a, b) in enumerate(zip(left_ramp, ramp)):
                        report.close(a, b, 1e-9,
                                     f"{name} ramp differs from left at {i}: n={n} mode={mode} s={sm}")


def test_bypass(report: Report) -> None:
    """All sides at 0 must be an exact pass-through, including existing alpha."""
    w, h = 1920, 1080
    s = FadeSettings(0, 0, 0, 0)
    report.check(s.bypass, "all-zero settings must report bypass")

    for y in range(0, h, 97):
        for x in range(0, w, 89):
            report.check(alpha_factor(pixel_center(x, w), pixel_center(y, h), w, h, s) == 1.0,
                         f"bypass changed alpha at {x},{y}")

    # A source that already has alpha keeps exactly its own alpha.
    for existing in [0.0, 0.25, 0.5, 0.9, 1.0]:
        report.close(existing * alpha_factor(960.0, 540.0, w, h, s), existing, 1e-9,
                     "existing alpha modified during bypass")


def test_corners(report: Report) -> None:
    """Two crossing fades must fade the corner smoothly, with no band or jump."""
    w, h = 1920, 1080
    n = 300
    for mode in [0, 1, 2]:
        for sm in [0.0, 0.5, 1.0]:
            s = FadeSettings(left=float(n), top=float(n), smoothness=sm, curve=mode)

            corner = alpha_factor(pixel_center(0, w), pixel_center(0, h), w, h, s)
            report.check(corner <= 0.5 / n + EPSILON, f"corner not transparent: mode={mode} s={sm} -> {corner}")

            # Diagonal of the corner box: alpha never rises above the single-side
            # ramp and never falls below the product of both ramps.
            for i in range(0, 41):
                d = i / 40.0 * n
                value = alpha_factor(d, d, w, h, s)
                single = edge_factor_fixed(d, float(n), sm, mode)
                report.check(value <= single + EPSILON,
                             f"corner fades multiplied up: mode={mode} s={sm} d={d} {value} > {single}")
                report.check(abs(value - single * single) < 1e-9,
                             f"corner is not the product of both sides: mode={mode} s={sm} d={d}")

            # Stepping along the diagonal must not jump.
            steps = 2000
            previous = None
            for i in range(steps + 1):
                d = i / steps * n * 1.5
                value = alpha_factor(d, d, w, h, s)
                if previous is not None:
                    report.check(previous - value <= 0.05,
                                 f"diagonal jump of {previous - value} at d={d} mode={mode} s={sm}")
                previous = value


def test_curves_differ(report: Report) -> None:
    """Linear, Smooth and Soft must be genuinely different shapes at every
    smoothness, not three names for one result."""
    n = 200
    samples = [i / n for i in range(n + 1)]
    smoothness_values = [0.0, 0.25, 0.5, 0.75, 1.0]

    for s in smoothness_values:
        curves = {
            mode: [edge_curve_fixed(t, s, mode) for t in samples]
            for mode in (0, 1, 2)
        }

        # Every pair of curves has to differ by a visible margin somewhere.
        for a in (0, 1, 2):
            for b in (a + 1, 2 + 1):
                if b > 2:
                    continue
                spread = max(abs(x - y) for x, y in zip(curves[a], curves[b]))
                report.check(
                    spread > 0.05,
                    f"curves {a} and {b} are nearly identical at smoothness {s}"
                    f" (max difference {spread:.4f})",
                )

        for mode, ramp in curves.items():
            report.close(ramp[0], 0.0, EPSILON, f"curve {mode} does not start at 0 (s={s})")
            report.close(ramp[-1], 1.0, 1e-12, f"curve {mode} does not end at 1 (s={s})")
            report.check(
                all(b >= a - EPSILON for a, b in zip(ramp, ramp[1:])),
                f"curve {mode} is not monotonic (s={s})",
            )

    # Soft has to be the gradual one: it must stay clearly below the other two
    # at the middle of the band, whatever the smoothness.
    for s in smoothness_values:
        mid = n // 2
        linear = edge_curve_fixed(samples[mid], s, 0)
        smooth = edge_curve_fixed(samples[mid], s, 1)
        soft = edge_curve_fixed(samples[mid], s, 2)
        report.check(
            soft < smooth - 0.05,
            f"soft ({soft:.3f}) is not gentler than smooth ({smooth:.3f}) mid-band at s={s}",
        )
        report.check(
            soft < linear - 0.05,
            f"soft ({soft:.3f}) is not gentler than linear ({linear:.3f}) mid-band at s={s}",
        )

    # No curve may collapse into a hard edge: the steepest slope anywhere stays
    # bounded, and the border end never rises faster than the linear ramp would.
    h = 1.0 / 4096.0
    for s in smoothness_values:
        for mode in (0, 1, 2):
            steepest = max(
                (edge_curve_fixed(t + h, s, mode) - edge_curve_fixed(t, s, mode)) / h
                for t in samples[:-1]
            )
            report.check(
                steepest <= 2.0 + 1e-6,
                f"curve {mode} at s={s} has a slope of {steepest:.3f}, which is a hard edge",
            )


def test_smoothness_never_breaks_transparency(report: Report) -> None:
    """Every smoothness value keeps alpha 0 on the border and 1 at the extent."""
    for mode in [0, 1, 2]:
        for n in [10, 20, 100, 300, 1000]:
            for step in range(0, 101):
                sm = step / 100.0
                report.close(edge_curve_fixed(0.0, sm, mode), 0.0, EPSILON,
                             f"curve {mode} s={sm} is not 0 on the border")
                report.close(edge_curve_fixed(1.0, sm, mode), 1.0, 1e-12,
                             f"curve {mode} s={sm} is not 1 at the fade distance")
                report.check(edge_factor_fixed(0.0, float(n), sm, mode) == 0.0,
                             f"n={n} mode={mode} s={sm} border not transparent")


def test_fade_uses_full_width(report: Report) -> None:
    """The configured pixel value must be the real width of the gradient."""
    for mode in [0, 1, 2]:
        for sm in [0.0, 0.5, 1.0]:
            for n in [20, 100, 300]:
                # Half the configured width must be materially faded, not nearly
                # opaque: this is what "progressive" means for this filter.
                half = edge_curve_fixed(0.5, sm, mode)
                report.check(0.10 <= half <= 0.90,
                             f"fade is not progressive at half width: mode={mode} s={sm} -> {half}")

                # And it must not still be transparent past the extent.
                report.check(edge_curve_fixed(1.0, sm, mode) == 1.0,
                             f"fade extends past its width: mode={mode} s={sm}")


def test_resolution_independence(report: Report) -> None:
    """A fade of N px behaves the same on every resolution and aspect ratio."""
    cases = [(1920, 1080), (1080, 1920), (1080, 1080), (500, 500), (64, 64), (320, 240), (3840, 2160)]
    n = 100.0
    for mode in [0, 1, 2]:
        # Compare at texel centres, which is where the shader evaluates.
        reference = [edge_curve_fixed((i + 0.5) / n, 0.5, mode) for i in range(int(n))]
        for (w, h) in cases:
            if n >= w:
                continue
            ramp = row_alphas(w, h, FadeSettings(left=n, smoothness=0.5, curve=mode), h // 2)
            for i in range(int(n)):
                report.close(reference[i], ramp[i], 1e-9,
                             f"{w}x{h} ramp differs from the reference at texel {i} (mode={mode})")


def test_existing_alpha(report: Report) -> None:
    """Pre-existing alpha is reinforced, never inverted or boosted."""
    w, h = 800, 600
    n = 200.0
    for mode in [0, 1, 2]:
        for sm in [0.0, 0.5, 1.0]:
            s = FadeSettings(left=n, right=n, top=n, bottom=n, smoothness=sm, curve=mode)
            for existing in [0.0, 0.1, 0.5, 0.99, 1.0]:
                for (x, y) in [(0, 0), (1, 1), (5, 5), (50, 50), (100, 100), (400, 300), (799, 599)]:
                    f = alpha_factor(pixel_center(x, w), pixel_center(y, h), w, h, s)
                    result = existing * f
                    report.check(result <= existing + EPSILON,
                                 f"alpha boosted at {x},{y}: {existing} -> {result}")
                    report.check(0.0 <= result <= 1.0,
                                 f"alpha out of range at {x},{y}: {result}")


def test_previous_vs_fixed(report: Report) -> None:
    """Quantify what the fix changes, so the report can state it concretely."""
    n = 100.0
    print("  gradient profile, 100 px fade, 1920x1080, Smooth curve, smoothness 50%")
    print("  distance |  previous  |   fixed")
    print("  ---------+------------+----------")
    for d in [0, 5, 10, 25, 50, 75, 95, 100, 150]:
        prev = edge_factor_previous(d, n, 0.5, 1)
        fixed = edge_factor_fixed(d, n, 0.5, 1)
        print(f"  {d:>6}px | {prev:>10.4f} | {fixed:>8.4f}")

    # The old formula spent the whole budget in the last half of the band: the
    # first half of the configured fade produced no visible gradient at all.
    prev_half = edge_factor_previous(n / 2, n, 0.5, 1)
    fixed_half = edge_factor_fixed(n / 2, n, 0.5, 1)
    print(f"\n  at half the fade width: previous {prev_half:.4f} -> fixed {fixed_half:.4f}")
    report.check(prev_half == 0.0, "the previous curve should be fully transparent at half the band")
    report.check(fixed_half > 0.25, "the fixed curve should already be well past transparent at half the band")

    # The old formula compressed the whole transition into the outer half of the
    # configured width, so the usable gradient was half the size the user asked
    # for. Count how many pixels actually carry a visible ramp.
    def visible_width(ramp_fn) -> int:
        return sum(1 for d in range(int(n)) if 0.01 < ramp_fn(d) < 0.99)

    previous_width = visible_width(lambda d: edge_factor_previous(d, n, 0.5, 1))
    fixed_width = visible_width(lambda d: edge_factor_fixed(d, n, 0.5, 1))
    print(f"\n  visible transition: previous {previous_width}px of the configured {int(n)}px"
          f" -> fixed {fixed_width}px")
    report.check(previous_width <= n * 0.55,
                 "the previous curve should only use the outer half of the configured width")
    # The curve tapers to zero at the border and to one at the fade distance, so
    # the strict 1%..99% window is a little narrower than the configured width.
    report.check(fixed_width >= n * 0.80,
                 "the fixed curve should use the whole configured width")


def dump_spec(spec: str) -> None:
    """Render one configuration as a text map, e.g. 1920x1080,left=100,sm=50,curve=1"""
    parts = dict(p.split("=") for p in spec.split(",") if "=" in p)
    width = int(parts.get("w", 64))
    height = int(parts.get("h", 32))
    s = FadeSettings(
        left=float(parts.get("left", 0)),
        right=float(parts.get("right", 0)),
        top=float(parts.get("top", 0)),
        bottom=float(parts.get("bottom", 0)),
        smoothness=float(parts.get("sm", 50)) / 100.0,
        curve=int(parts.get("curve", 1)),
    )

    shades = " .:-=+*#%@"
    print(f"alpha factor map {width}x{height} {s}")
    for y in range(height):
        line = ""
        for x in range(width):
            v = alpha_factor(pixel_center(x, width), pixel_center(y, height), width, height, s)
            line += shades[min(int((1.0 - v) * len(shades)), len(shades) - 1)]
        print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dump", help="render one configuration as a text map")
    args = parser.parse_args()

    if args.dump:
        dump_spec(args.dump)
        return 0

    report = Report()

    test_bypass(report)
    test_endpoints(report)
    test_symmetry(report)
    test_corners(report)
    test_curves_differ(report)
    test_smoothness_never_breaks_transparency(report)
    test_fade_uses_full_width(report)
    test_resolution_independence(report)
    test_existing_alpha(report)

    print("Edge Fade reference maths")
    print("=========================")
    print()
    test_previous_vs_fixed(report)
    print()
    print(f"checks run: {report.checks}")
    print(f"failures:   {len(report.failures)}")
    for failure in report.failures[:40]:
        print(f"  FAIL {failure}")

    return 1 if report.failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
