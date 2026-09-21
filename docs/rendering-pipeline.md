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
`Smoothness` (0-100 %) decides how much of the fade extent is used by the
transition: 0 concentrates it near the edge and 100 stretches it across the whole
extent. `Curve` selects the falloff shape (Linear, Smooth, Soft) and the final
factor is the minimum of the four sides, which keeps corners smooth.

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

## Alpha and blending

The filter modifies alpha, never visible RGB. Composition uses the native
premultiplied representation:

~~~c
gs_blend_state_push();
gs_blend_function(GS_BLEND_ONE, GS_BLEND_INVSRCALPHA);
/* draw */
gs_blend_state_pop();
~~~
