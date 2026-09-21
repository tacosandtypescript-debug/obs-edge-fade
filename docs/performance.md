# Performance

<!-- markdownlint-disable MD013 -->

The project defines budgets, not guarantees. Numbers are only claimed after
profiling on real hardware.

## Budget

| Filter | Render targets | Passes | Per-frame allocations |
|---|---|---|---|
| Edge Fade | 0 | 1 | 0 |

Edge Fade reserves no GPU storage of its own: it draws into the texture OBS
provides for the filter pass, so VRAM use does not grow with the settings.

## Mandatory optimisations

- Cache effect parameters; never call `gs_effect_get_param_by_name` per frame.
- Never recreate effects when a slider moves.
- Never load files per frame.
- Never allocate with `bmalloc` per frame.
- Never log per frame in normal builds.
- Never map textures or read pixels back to the CPU.
- Bypass when all four sides are 0.

## Profiling tools

Start with OBS Stats, Task Manager GPU engine and the OBS log. For deeper
analysis use PIX for Windows, GPUView / ETW or the Visual Studio profiler. Only
use RenderDoc when it is compatible and useful. Never optimise based on the
global Task Manager GPU percentage alone.
