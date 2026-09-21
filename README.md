# OBS Edge Fade

<!-- markdownlint-disable MD013 -->

OBS Edge Fade is a native OBS Studio plugin that ships a single GPU video
filter, **OBS Edge Fade - Edge Fade**, which fades the alpha of a source
progressively near one or more of its edges.

The filter is GPU-only, Qt-free and depends only on libobs.

> **Status:** 0.1.0 in development. Edge Fade ships its single-pass GPU shader:
> per-side fades with smoothness and curve, and a bypass whenever every side is
> zero. The full development plan lives in [PLAN.md](PLAN.md) (Spanish).

## Requirements

- Windows 10/11 x64
- OBS Studio 32.2.x (32.2.2 is the pinned, targeted release)
- To build: Visual Studio 2022, CMake 3.28+ and network access for the first configure

## Installation

1. Download the release archive for Windows x64.
2. Extract the `obs-edge-fade` folder into the OBS plugins directory, for example
   `%ProgramData%\obs-studio\plugins\obs-edge-fade`.
3. Restart OBS.

The filter then appears in the **Filters** dialog of any source as:

~~~text
OBS Edge Fade - Edge Fade
~~~

## Edge Fade

Reduces the alpha of the source progressively near its edges. Each side can be
controlled independently or linked, with adjustable smoothness and curve. The
filter keeps the source size, leaves the interior alpha untouched and never
modifies visible RGB.

| Setting | Type | Default |
|---|---|---|
| Link sides | bool | enabled |
| Left, Right, Top, Bottom | slider, 0-1000 px | 0 |
| Smoothness | slider, 0-100 % | 50 |
| Curve | list: Linear / Smooth / Soft | Smooth |

With all four sides at 0 the filter bypasses itself and the source passes
through unchanged.

## Screenshots

Screenshots are added with the first functional release.

## Troubleshooting

- **The filter list has no OBS Edge Fade entry.** Confirm the DLL is under
  `<obs-plugins>\obs-edge-fade\bin\64bit\obs-edge-fade.dll` and check the OBS log
  for `[OBS Edge Fade]` lines.
- **The effect fails to load.** Verify that the `data` folder was copied next to
  the DLL; the plugin falls back to a pass-through and logs a warning.
- **HDR sources look different.** HDR compatibility is still being validated;
  see [docs/testing.md](docs/testing.md).

## Building from source

~~~powershell
cmake --preset windows-x64
cmake --build --preset windows-x64 --config RelWithDebInfo
cmake --install build_x64 --config RelWithDebInfo --prefix .\release
~~~

The first configure downloads the pinned obs-deps and OBS sources, then builds
libobs. The pinned versions live in [buildspec.json](buildspec.json).
Unit tests are libobs-free and can be built on their own:

~~~powershell
cmake -S tests/unit -B build_tests
cmake --build build_tests
ctest --test-dir build_tests --output-on-failure
~~~

For an end-to-end validation on Windows, run [docs/manual-test-plan.md](docs/manual-test-plan.md)
and use `scripts/install-local.ps1` to install the build into OBS.

## Documentation

- [docs/architecture.md](docs/architecture.md)
- [docs/rendering-pipeline.md](docs/rendering-pipeline.md)
- [docs/performance.md](docs/performance.md)
- [docs/testing.md](docs/testing.md)
- [docs/manual-test-plan.md](docs/manual-test-plan.md)
- [docs/test-results-template.md](docs/test-results-template.md)
- [docs/release-process.md](docs/release-process.md)

## License

GPL-2.0-or-later. See [LICENSE](LICENSE).
