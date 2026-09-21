# Architecture

<!-- markdownlint-disable MD013 -->

OBS Edge Fade is one native module that registers a single video filter. There is
no shared renderer and no "universal filter": the filter owns its settings,
properties and render path.

## Module layout

~~~text
src/
  plugin-main.c                registers the single obs_source_info entry
  common/                      shared, low-level helpers
    obs-edge-fade-common.h     plugin ID, filter ID, limits, shared enums
    log.h                      prefixed logging macros
    math-utils.h               inline integer clamp helper
    color-space.*              supported spaces and target colour lookup
    shader-loader.*            obs_module_file + gs_effect_create_from_file
  edge-fade/                   filter + settings + properties
~~~

`common` holds only code that is genuinely shared. A helper used in a single
place belongs to the feature.

## Graphics context

Every graphics call runs inside a graphics context. OBS already provides one
during:

- `obs_source_info.video_render`
- `obs_source_info.create` / `destroy` only when the caller wraps them (the
  plugin does so explicitly)

The plugin never leaves global graphics state modified: blend state and any
other state change follows the push / change / render / pop pattern.

## Settings lifecycle

The filter implements:

~~~text
get_defaults()  -> obs_data defaults derived from the settings struct defaults
create()        -> allocate + apply settings + load the effect
update()        -> copy settings, mirror linked sides, clamp
destroy()       -> destroy the effect + free
~~~

`update()` never reloads the effect. A slider change only updates the settings
struct that the next frame reads.

## Bypass

`edge_fade_video_render()` skips the filter instead of drawing when:

| Condition | Reason |
|---|---|
| all four sides are 0 | the filter cannot change the image |
| the effect failed to load | the plugin logs a warning and passes the source through |
| the target or its size is missing | there is nothing valid to process |

## Rules for contributors

1. No giant files.
2. One feature folder per filter; do not merge features into one implementation.
3. Never move pixel work to the CPU.
4. No Qt, no frontend API, no external dependencies for v1.
5. Every GPU resource has a symmetric destroy.
6. Every error path prefers bypass over a crash.
7. No logging per frame in normal builds.
