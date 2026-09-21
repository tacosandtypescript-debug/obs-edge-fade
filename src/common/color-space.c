#include "common/color-space.h"

static const enum gs_color_space oss_color_spaces[] = {
	GS_CS_SRGB,
	GS_CS_SRGB_16F,
	GS_CS_709_EXTENDED,
};

const enum gs_color_space *oss_supported_color_spaces(size_t *count)
{
	if (count)
		*count = OBS_COUNTOF(oss_color_spaces);

	return oss_color_spaces;
}

bool oss_is_supported_color_space(enum gs_color_space space)
{
	for (size_t i = 0; i < OBS_COUNTOF(oss_color_spaces); ++i) {
		if (oss_color_spaces[i] == space)
			return true;
	}

	return false;
}

enum gs_color_space oss_filter_color_space(obs_source_t *filter_context, size_t count,
					   const enum gs_color_space *preferred_spaces)
{
	obs_source_t *target = obs_filter_get_target(filter_context);

	if (!target)
		return GS_CS_SRGB;

	const enum gs_color_space source_space = obs_source_get_color_space(target, count, preferred_spaces);

	if (!oss_is_supported_color_space(source_space))
		return GS_CS_SRGB;

	return source_space;
}

enum gs_color_format oss_format_for_space(enum gs_color_space space)
{
	return gs_get_format_from_space(space);
}
