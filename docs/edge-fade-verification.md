# Edge fade verification

<!-- markdownlint-disable MD013 -->

Record of the checks behind the fade fix. Everything below is reproducible with
the commands in [README.md](../README.md).

## What was wrong

### 1. The gradient was compressed, not progressive

`edge_factor()` fed `smoothness` into the *width* of the transition:

~~~hlsl
float start = extent * (1.0 - clamp(softness, 0.0, 1.0));
float width = max(extent - start, 0.0001);
float t = clamp((distance - start) / width, 0.0, 1.0);
~~~

`start` is where the ramp begins. With the default `smoothness` of 50 % and
`Left = 100 px`, the ramp therefore only covered the outer 50 px, and everything
from 50 px inwards stayed fully transparent. Measured on a 1920x1080 source with
one side at 100 px:

| distance | old alpha | new alpha |
|---|---|---|
| 0 px | 0.0000 | 0.0000 |
| 5 px | 0.0000 | 0.0042 |
| 10 px | 0.0000 | 0.0183 |
| 25 px | 0.0000 | 0.1299 |
| 50 px | 0.0000 | 0.5000 |
| 75 px | 0.5000 | 0.8701 |
| 95 px | 0.9720 | 0.9958 |
| 100 px | 1.0000 | 1.0000 |

The old curve produced no gradient at all over the first half of the configured
width and then jumped. That is the "not progressive / does not fade cleanly"
symptom. The new curve spans the whole configured width.

### 2. Smoothness could not shape the curve

It only moved `start`, so it could not make the transition softer or harder; at
its extremes it collapsed the ramp into the last few pixels, i.e. an almost
binary edge. It now blends the selected curve towards a flatter variant and
never moves the endpoints.

### 3. The three curves were nearly the same

Linear and Smooth were two different formulas (the third was a shortcut on the
same idea), and the list behaved as if it offered one shape under three names:

~~~hlsl
if (mode < 0.5) return t;                       // linear
if (mode < 1.5) return t * t * (3.0 - 2.0 * t); // smooth
return 1.0 - pow(1.0 - t, 3.0);                 // soft
~~~

They are now three separate families, each with a bounded slope, so no curve can
collapse into a hard edge:

| Curve | Formula |
|---|---|
| Linear | `t` |
| Smooth | `lerp(smoothstep(t), smootherstep(t), smoothness)` |
| Soft | `lerp(t*t, t*t*(2-t), smoothness)` |

At `smoothness = 50 %`:

| t (of the fade width) | Linear | Smooth | Soft |
|---|---|---|---|
| 0.10 | 0.100 | 0.018 | 0.015 |
| 0.25 | 0.250 | 0.130 | 0.086 |
| 0.50 | 0.500 | 0.500 | 0.312 |
| 0.75 | 0.750 | 0.870 | 0.633 |
| 0.90 | 0.900 | 0.982 | 0.851 |

The largest difference between any two of the three is 0.20 or more at every
smoothness value, so they are visibly distinct, and Soft is always the most
gradual (it stays below the other two across the whole band).

### 4. The fade darkened the colour

The filter multiplied its output by the fade factor *and* overrode the blend
state with `gs_blend_function(GS_BLEND_ONE, GS_BLEND_INVSRCALPHA)`. That applies
the source factor to the colour as well, so the colour contribution was
premultiplied a second time and the written alpha was squared, which also pulled
the border away from full transparency.

The override is gone; OBS's own filter pipeline already selects the correct
blend. Measured on a composited red source with `Left = 100`:

| distance | shown RGB | saturation |
|---|---|---|
| 10 px | (18, 0, 0) | fully saturated red |
| 25 px | (56, 0, 0) | fully saturated red |
| 50 px | (114, 0, 0) | fully saturated red |
| 75 px | (165, 0, 0) | fully saturated red |
| 150 px | (250, 0, 0) | fully saturated red |

No tint, no dark halo, no bright fringe at any fade severity.

## What was checked, and how

### Model checks (no GPU)

`python tools/verify-fade.py` mirrors the shader maths on the CPU.

| Area | Cases |
|---|---|
| Border transparency and interior passthrough | 1920x1080, 1080x1920, 1000x1000, 320x240, 64x64 x fades 0/10/20/100/300/1000 px x 3 curves x 5 smoothness values |
| Smoothness never breaks transparency | every integer 0-100 for 3 curves x 5 fade widths |
| Curve separation | every pair of curves must differ by more than 0.05 at every smoothness, and Soft must stay the gentlest |
| No hard edge | the steepest slope of any curve stays below 2.0 |
| Progressiveness | 0.10 <= alpha <= 0.90 at half the configured width |
| Corners | product of both sides, monotonic diagonal, no jump > 0.05 |
| Symmetry | left/right/top/bottom and horizontal vs vertical identical |
| Bypass | all four sides at 0 is an exact pass-through, including existing alpha |
| Resolution independence | 64x64 to 3840x2160 reproduce the same ramp |

Result: **38241 checks, 0 failures.**

### End-to-end checks (real OBS Studio)

`python tools/obs-e2e.py --dll <dll> --matrix` drives a real OBS Studio through
obs-websocket: it installs the plugin, builds the scene, sets each configuration
and screenshots the source, which returns the texture the filter chain produced
including alpha. `python tools/check-captures.py` then compares every pixel of
every configured side with

~~~text
expected alpha = baseline alpha * fade
~~~

where the baseline is the same pattern captured without the filter.

| # | Case | # | Case |
|---|---|---|---|
| 1 | Only Left, 100 px | 9 | Medium values, 100 px |
| 2 | Only Right, 100 px | 10 | Large values, 300 px |
| 3 | Only Top, 100 px | 11 | Curve Linear |
| 4 | Only Bottom, 100 px | 12 | Curve Smooth |
| 5 | Left + Right | 13 | Curve Soft |
| 6 | Top + Bottom | 14 | Smoothness 0 and 100 |
| 7 | All four sides | 15 | Filter installed, all sides 0 (bypass) |
| 8 | Small values, 20 px | 16 | No filter at all (baseline) |

Result: **16 captures, 404 checks, 0 failures.** Largest deviation between
measured alpha and `baseline alpha * fade` was 0.012, i.e. 8-bit quantisation
plus one step.

Source dimensions are covered by the model matrix (64x64 up to 3840x2160,
including 1080x1920 portrait and square sources) because the shader only ever
compares distances against the configured fade, which the model reproduces
exactly for every resolution.

### Unit tests

`pwsh -File tools/run-unit-tests.ps1` builds `tests/unit` with `/W3 /WX` and runs
it: settings defaults, linked sides (both the global-slider and the per-side
paths, plus re-linking), clamping, bypass and the NULL guards.
Result: **0 failures.**

### Filter dialog (real OBS widgets)

`pwsh -File tools/obs-ui-stage.ps1` followed by `python tools/obs-ui-check.py`
read the actual properties dialog through Windows UI Automation, so the widget
tree OBS built is inspected rather than a model of it. OBS only creates a row
when its property is visible, so a row being present or absent proves the
visibility switch.

| State | Expected rows | Measured |
|---|---|---|
| Link on | `All borders`, `Smoothness`, `Curve`; no per-side rows | matches |
| Link off | `Left`, `Right`, `Top`, `Bottom`, `Smoothness`, `Curve`; no `All borders` | matches |
| Link on again | single slider back, keeping its value | matches |

Result: **10 checks, 0 failures**, including that the global slider holds the
value it was given and that the four sliders come back at that same width.

## Accepted limitations

- A fade wider than the source cannot reach full opacity inside the image. The
  gradient stays monotonic and degrades to a partial fade; nothing breaks.
- Overlapping opposite fades (for example `Left + Right` wider than the source)
  leave a fully transparent band in the middle where both fades reach 0. That is
  the configured result, not an artefact.
- HDR and colour-space behaviour still needs the manual matrix in
  [manual-test-plan.md](manual-test-plan.md); the automated checks run on SDR.
