# Testing

<!-- markdownlint-disable MD013 -->

## Unit tests

Pure logic is separated from libobs so it can be tested without a GPU or the OBS
runtime. The suite lives in `tests/unit` and uses a tiny dependency-free
harness (`oss-test.h`).

~~~powershell
cmake -S tests/unit -B build_tests
cmake --build build_tests
ctest --test-dir build_tests --output-on-failure
~~~

Covered today:

- `math-utils`: clamp helpers and the shared numeric utilities.
- `edge-fade-settings`: defaults, linked sides, clamping of the sides, smoothness
  and curve, and bypass.

## Visual fixtures

Use at least: an opaque rectangle, a transparent circle, a checkerboard alpha,
thin lines, 1 px borders, a 4K image and a 64x64 image. Compare expected versus
rendered output and store reference captures.

## Resolution matrix

~~~text
64x64
320x240
640x480
1280x720
1920x1080
2560x1440
3840x2160
~~~

## Frame rates

Test 30, 60 and 120 FPS. The plugin must not contain frame-rate dependent logic.

## Stress tests

- 10 sources with Edge Fade
- Edge Fade combined with native filters across multiple scenes

Measure GPU frame time, rendering lag, VRAM, stability and memory growth.

## Leak test

Repeat create / change settings / destroy 100+ times and watch CPU memory, VRAM,
handles and effects.

## Colour and HDR

Exercise SDR source to SDR canvas, SDR source to HDR canvas, HDR source to HDR
canvas, and chains with native filters. Do not claim full HDR compatibility until
these pass visual review.

## Pending visual validation

The shader assumes `v_in.uv * source_size` has its origin at the top-left corner
with y growing downwards. Confirm on a real render that:

- Edge Fade maps `left`/`right`/`top`/`bottom` to the expected sides.
- Corners where two adjacent sides meet fade without a hard band, because the
  strongest fade of the four sides wins.
- The Edge Fade `smoothness` and `curve` model matches the intended UX; the
  formula is documented in `edge-fade.effect`.
