#pragma once

#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Stable internal plugin identifier. */
#define OEF_PLUGIN_ID "obs-edge-fade"

/**
 * Stable filter identifier. Scenes already saved with the filter keep loading,
 * so this must never change without an explicit settings migration.
 */
#define OEF_FILTER_ID_EDGE_FADE "obs_source_style_edge_fade"

/** Shared limits used to clamp user settings before touching the GPU. */
#define OEF_MAX_EDGE_FADE_PX 1000

/**
 * Marks the shared "all borders" width as not chosen yet, so the single slider
 * falls back to the left side. Only 0..OEF_MAX_EDGE_FADE_PX are real widths.
 */
#define OEF_EDGE_FADE_UNIFORM_UNSET (-1)

/** Edge fade curve modes. */
enum oef_edge_curve {
	OEF_EDGE_CURVE_LINEAR = 0,
	OEF_EDGE_CURVE_SMOOTH = 1,
	OEF_EDGE_CURVE_SOFT = 2,
};

#ifdef __cplusplus
}
#endif
