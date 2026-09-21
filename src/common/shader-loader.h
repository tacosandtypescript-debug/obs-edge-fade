#pragma once

#include <obs-module.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Loads an effect from the module's data directory, for example
 * "effects/edge-fade.effect". Enters the graphics context internally and logs
 * any failure. Returns NULL so callers can fall back to bypass.
 */
gs_effect_t *oss_load_effect(const char *relative_path);

#ifdef __cplusplus
}
#endif
