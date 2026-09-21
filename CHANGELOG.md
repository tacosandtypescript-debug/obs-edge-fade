# Changelog

All notable changes to OBS Edge Fade are documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project adheres to [Semantic Versioning](https://semver.org/).

## [Unreleased]

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
