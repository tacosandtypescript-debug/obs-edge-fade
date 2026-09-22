# Rendering pipeline

<!-- markdownlint-disable MD013 -->

All processing stays on the GPU. The CPU only reads settings, computes small
parameters, manages lifetimes and chooses bypass.

## Edge Fade

Single pass, no extra buffer:

~~~text
source texture
  -> sample per-pixel distance to each edge
  -> combine the four fade factors
  -> alpha = source_alpha * fade
  -> output
~~~

The filter keeps the source size and leaves interior alpha untouched.

### The fade curve

A side configured with `N` pixels produces a factor that is **0 exactly on the
border** and **1 at `N` pixels inwards**, growing monotonically in between. The
transition therefore always spans the whole configured width; the
`VISIBLE -> FADE -> TRANSPARENT` ramp is the configured size, not a fraction of
it.

With `t = distance / fade_extent` clamped to `0..1`, the curve modes are:

| Curve | Factor | Shape |
|---|---|---|
| Linear | `t` | straight ramp |
| Smooth | `lerp(smoothstep(t), smootherstep(t), smoothness)` | S-curve |
| Soft | `lerp(t*t, t*t*(2-t), smoothness)` | gentlest of the three |

Every curve keeps `f(0) = 0` and `f(1) = 1`, so no combination of curve and
smoothness can stop the border from reaching full transparency or leak the fade
past its configured width. Every curve also has a bounded slope, so none of them
can collapse into a hard edge.

`Smoothness` (0-100 %) shapes the falloff inside the fade width. It does not
move the endpoints and does not change how wide the gradient is. Soft always
stays below the other two across the band, i.e. it is the most gradual.

### Combining the sides

The final factor is the **product** of the four side factors. Two crossing fades
can then only ever make a corner more transparent, which is what keeps corners
free of bands and halos:

~~~text
factor = left * right * top * bottom
~~~

A side at 0 contributes a factor of 1 and never touches the image.

### Colour and blending

Only alpha is rewritten. The shader returns `rgba * factor`, i.e. the
premultiplied form of the texture OBS hands to the filter, and the filter does
**not** override the blend state: OBS's own filter pipeline already selects the
correct premultiplied blend before the filter draws. Setting an explicit
`gs_blend_function(GS_BLEND_ONE, GS_BLEND_INVSRCALPHA)` here would premultiply
the colour a second time (the dark halo) and square the written alpha (so the
border stops reaching 0).

The effect receives these uniforms:

~~~text
image          filter source texture
ViewProj       OBS vertex transform
source_size    target size in pixels
fade           (left, right, top, bottom) in pixels
smoothness     settings value / 100
curve_mode     0 linear, 1 smooth, 2 soft
~~~

Positions come from `v_in.uv * source_size`, so the origin is the top-left corner
with y growing downwards and each side is measured as the distance from the
pixel to that edge.

The filter draws through the standard single-pass path:

~~~text
obs_filter_get_target()
obs_source_get_base_width() / obs_source_get_base_height()
obs_source_process_filter_begin_with_color_space()
obs_source_process_filter_end()
~~~

`OBS_ALLOW_DIRECT_RENDERING` is requested because the filter keeps the source
resolution and needs no intermediate buffer.

## Colour spaces

The filter does not assume SDR `GS_RGBA`. It queries the target through
`obs_source_get_color_space()` with the supported list:

~~~text
GS_CS_SRGB
GS_CS_SRGB_16F
GS_CS_709_EXTENDED
~~~

The matching format comes from `gs_get_format_from_space()` and is passed to
`obs_source_process_filter_begin_with_color_space()`. The filter implements
`video_get_color_space` so the space propagates down the chain.

OBS renders the filter through an sRGB pipeline, so the RGB channels of the
result are gamma encoded while alpha stays linear. The two are therefore not
expected to be numerically equal; what matters is that the fade removes coverage
without tinting or darkening the colour, which the end-to-end captures assert.

## Verifying the maths

`tools/verify-fade.py` mirrors this pipeline on the CPU and checks borders,
monotonicity, curve separation, corners, bypass, existing alpha and resolution
independence without a GPU. `tools/obs-e2e.py` plus `tools/check-captures.py`
run the real plugin inside OBS and compare the measured alpha of every
configured side with `baseline alpha * fade`.

