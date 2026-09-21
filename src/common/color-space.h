#pragma once

#include <obs-module.h>

#ifdef __cplusplus
extern "C" {
#endif

/** Color spaces the plugin can process while keeping source RGB intact. */
const enum gs_color_space *oss_supported_color_spaces(size_t *count);

bool oss_is_supported_color_space(enum gs_color_space space);

/** Resolves the color space of a filter target, falling back to SDR when unknown. */
enum gs_color_space oss_filter_color_space(obs_source_t *filter_context, size_t count,
					   const enum gs_color_space *preferred_spaces);

/** Color format that matches a color space. */
enum gs_color_format oss_format_for_space(enum gs_color_space space);

#ifdef __cplusplus
}
#endif
