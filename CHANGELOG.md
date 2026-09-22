# Changelog

All notable changes to OBS Edge Fade are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [0.2.0] - 2026-09-21

First release with the corrected fade maths, the linked-borders UI and a
prebuilt Windows binary.

### Changed

- **Link sides now swaps the controls instead of duplicating them.** With the
  link on, the four per-side sliders are hidden and a single **All borders**
  slider drives Left, Right, Top and Bottom at once; with the link off the four
  independent sliders come back holding the width the global slider had.
  Smoothness and Curve are unrelated to the fade size and stay visible in both
  modes. Both groups are mirrored into the settings on every change, so toggling
  the link never jumps, resets or loses a value, and the preview updates on the
  same frame.
- `smoothness` is documented as a shape control only; it can no longer change
  where the gradient starts or stops.
- `cmake`: the Windows SDK version is no longer hard-coded in
  `CMakePresets.json`, the dependency helper accepts non-Visual-Studio
  generators, and `scripts/build-ninja.ps1` builds through Ninja for machines
  whose Windows SDK lacks the MSBuild integration the VS generator needs.

### Fixed

- **The edge gradient was compressed instead of progressive.** `smoothness`
  multiplied into the fade *width*, so at the default 50 % a 100 px fade only
  ramped over the outer ~50 px and the rest of the configured width stayed fully
  transparent. Measured, the ramp sat at 0.00 alpha until 50 px inwards and then
  jumped to 1.00 within 3 px. The transition now always spans the whole
  configured width: 0 on the border, 1 at the fade distance.
- **Smoothness could not change the gradient shape.** It only moved the start of
  the ramp, so at the extremes it produced an abrupt, almost binary edge. It now
  blends the selected curve towards a flatter variant without moving the
  endpoints.
- **The three curves were interchangeable.** Linear, Smooth and Soft shared one
  formula with a shortcut exponent. They are now three separate bounded-slope
  families: a straight ramp, the smoothstep/smootherstep pair, and a gentler
  quadratic pair that stays below the other two across the whole band.
- **The fade darkened the colour.** The filter multiplied its output by the fade
  *and* blended with an explicit `ONE`/`INVSRCALPHA` source factor, so the colour
  contribution was premultiplied a second time (a dark halo along the gradient)
  and the written alpha was squared, which pulled the border away from full
  transparency. The filter now leaves blending to OBS's own filter pipeline.
- Border alpha now reaches 0 exactly: every curve keeps `f(0) = 0`.

### Added

- Prebuilt Windows x64 plugin in `dist/obs-edge-fade`, published as a release
  archive so no build is needed to install it.
- `tools/verify-fade.py`: CPU mirror of the shader maths that validates the fade
  independently of any GPU.
- `tools/make-test-pattern.py`, `tools/obs-e2e.py` and `tools/check-captures.py`:
  end-to-end harness that drives a real OBS Studio through obs-websocket,
  screenshots the filtered source and compares the measured alpha with
  `baseline alpha * fade`.
- `tools/obs-ui-check.py`, `tools/obs-ui-stage.ps1`, `tools/obs-ui-cleanup.ps1`:
  read the real filter dialog through Windows UI Automation to verify the
  linked/unlinked control swap.
- `tools/install-to-obs.py`, `tools/package-release.ps1`,
  `tools/run-unit-tests.ps1`, `tools/local-build-cl.ps1`.

## [0.1.0] - Unreleased

### Added

- Standalone native module (`obs-edge-fade.dll`) that registers the Edge Fade
  video filter.
- Stable filter ID `obs_source_style_edge_fade`, kept unchanged from the
  original multi-filter plugin so scenes that already use the filter keep
  loading.
- Native Properties API UI for the filter (no Qt).
- Shared common layer: logging, math helpers, colour-space helpers and shader
  loader.
- Settings logic with a libobs-free unit test suite (math helpers and edge-fade
  settings).
- `data/effects/edge-fade.effect` and en-US/es-ES localisation.
- GPU render pipeline: effect loading through the shared shader loader,
  colour-space aware `obs_source_process_filter_begin_with_color_space`/
  `obs_source_process_filter_end`, blend-state push/pop and bypass fallback.
- Single-pass alpha fade with independent or linked sides, smoothness and
  linear/smooth/soft curves, with bypass when every side is zero.
- Windows x64 CMake build pinned to OBS Studio 32.2.2.
- GitHub Actions: Windows build artifact, formatting checks and unit tests,
  draft releases.

### Notes

- Extracted from the `obs-source-style` plugin, which also shipped Rounded
  Corners and Drop Shadow. This repository keeps the Edge Fade filter only.
