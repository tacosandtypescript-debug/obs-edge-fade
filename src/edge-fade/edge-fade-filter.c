#include "edge-fade/edge-fade-filter.h"

#include <graphics/vec2.h>
#include <graphics/vec4.h>

#include "common/color-space.h"
#include "common/log.h"
#include "common/obs-edge-fade-common.h"
#include "common/shader-loader.h"
#include "edge-fade/edge-fade-properties.h"
#include "edge-fade/edge-fade-settings.h"

struct edge_fade_filter {
	obs_source_t *context;

	gs_effect_t *effect;

	gs_eparam_t *param_source_size;
	gs_eparam_t *param_fade;
	gs_eparam_t *param_smoothness;
	gs_eparam_t *param_curve_mode;

	struct edge_fade_settings settings;
};

static const char *edge_fade_get_name(void *type_data)
{
	UNUSED_PARAMETER(type_data);

	return obs_module_text("EdgeFadeFilterName");
}

static void edge_fade_get_defaults(obs_data_t *settings)
{
	struct edge_fade_settings defaults;

	edge_fade_settings_defaults(&defaults);

	obs_data_set_default_bool(settings, EDGE_FADE_SETTING_LINKED, defaults.linked);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_UNIFORM, OEF_EDGE_FADE_UNIFORM_UNSET);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_LEFT, defaults.left);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_RIGHT, defaults.right);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_TOP, defaults.top);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_BOTTOM, defaults.bottom);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_SMOOTHNESS, defaults.smoothness);
	obs_data_set_default_int(settings, EDGE_FADE_SETTING_CURVE, defaults.curve);
}

static void edge_fade_update(void *data, obs_data_t *settings)
{
	struct edge_fade_filter *filter = data;
	const struct edge_fade_settings previous = filter->settings;

	filter->settings.linked = obs_data_get_bool(settings, EDGE_FADE_SETTING_LINKED);

	/*
	 * The shared "all borders" value is authoritative while linked: a scene
	 * saved before that setting existed stores OEF_EDGE_FADE_UNIFORM_UNSET, and
	 * then the left side seeds it, which is what the old linked mode did.
	 */
	int uniform = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_UNIFORM);
	if (uniform < 0)
		uniform = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_LEFT);
	filter->settings.uniform = uniform;

	filter->settings.left = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_LEFT);
	filter->settings.right = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_RIGHT);
	filter->settings.top = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_TOP);
	filter->settings.bottom = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_BOTTOM);
	filter->settings.smoothness = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_SMOOTHNESS);
	filter->settings.curve = (int)obs_data_get_int(settings, EDGE_FADE_SETTING_CURVE);

	edge_fade_settings_apply_link(&filter->settings, &previous);
	edge_fade_settings_clamp(&filter->settings);
}

static void *edge_fade_create(obs_data_t *settings, obs_source_t *context)
{
	struct edge_fade_filter *filter = bzalloc(sizeof(*filter));

	filter->context = context;
	edge_fade_update(filter, settings);

	obs_enter_graphics();
	filter->effect = oss_load_effect("effects/edge-fade.effect");
	if (filter->effect) {
		filter->param_source_size = gs_effect_get_param_by_name(filter->effect, "source_size");
		filter->param_fade = gs_effect_get_param_by_name(filter->effect, "fade");
		filter->param_smoothness = gs_effect_get_param_by_name(filter->effect, "smoothness");
		filter->param_curve_mode = gs_effect_get_param_by_name(filter->effect, "curve_mode");

		if (!filter->param_source_size || !filter->param_fade || !filter->param_smoothness ||
		    !filter->param_curve_mode) {
			oss_log_error("Edge Fade effect is missing required parameters, filter will bypass");
			gs_effect_destroy(filter->effect);
			filter->effect = NULL;
		}
	}
	obs_leave_graphics();

	if (!filter->effect)
		oss_log_warning("Edge Fade effect could not be loaded, filter will bypass");

	oss_log_debug("Edge Fade filter created");

	return filter;
}

static void edge_fade_destroy(void *data)
{
	struct edge_fade_filter *filter = data;

	if (!filter)
		return;

	if (filter->effect) {
		obs_enter_graphics();
		gs_effect_destroy(filter->effect);
		obs_leave_graphics();
	}

	bfree(filter);
}

static obs_properties_t *edge_fade_get_properties(void *data)
{
	UNUSED_PARAMETER(data);

	return edge_fade_build_properties();
}

static uint32_t edge_fade_get_width(void *data)
{
	struct edge_fade_filter *filter = data;

	if (!filter)
		return 0;

	obs_source_t *target = obs_filter_get_target(filter->context);

	return target ? obs_source_get_base_width(target) : 0;
}

static uint32_t edge_fade_get_height(void *data)
{
	struct edge_fade_filter *filter = data;

	if (!filter)
		return 0;

	obs_source_t *target = obs_filter_get_target(filter->context);

	return target ? obs_source_get_base_height(target) : 0;
}

static void edge_fade_video_render(void *data, gs_effect_t *effect)
{
	struct edge_fade_filter *filter = data;

	UNUSED_PARAMETER(effect);

	if (!filter->effect || edge_fade_settings_is_bypass(&filter->settings)) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	obs_source_t *target = obs_filter_get_target(filter->context);
	if (!target) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	const uint32_t width = obs_source_get_base_width(target);
	const uint32_t height = obs_source_get_base_height(target);
	if (width == 0 || height == 0) {
		obs_source_skip_video_filter(filter->context);
		return;
	}

	size_t space_count = 0;
	const enum gs_color_space *spaces = oss_supported_color_spaces(&space_count);
	const enum gs_color_space space = oss_filter_color_space(filter->context, space_count, spaces);
	const enum gs_color_format format = oss_format_for_space(space);

	if (!obs_source_process_filter_begin_with_color_space(filter->context, format, space,
							      OBS_ALLOW_DIRECT_RENDERING))
		return;

	struct vec2 source_size;
	struct vec4 fade;

	vec2_set(&source_size, (float)width, (float)height);
	vec4_set(&fade, (float)filter->settings.left, (float)filter->settings.right, (float)filter->settings.top,
		 (float)filter->settings.bottom);

	gs_effect_set_vec2(filter->param_source_size, &source_size);
	gs_effect_set_vec4(filter->param_fade, &fade);
	gs_effect_set_float(filter->param_smoothness, (float)filter->settings.smoothness / 100.0f);
	gs_effect_set_float(filter->param_curve_mode, (float)filter->settings.curve);

	/*
	 * The blend state is deliberately left alone. OBS already selects the
	 * correct blend for a filter pass before it draws, and the shader returns
	 * the source texture scaled by the fade factor, so alpha alone decides how
	 * visible a pixel is. Overriding it here used to premultiply the colour a
	 * second time (the dark halo along the gradient) and square the written
	 * alpha, which stopped the border from reaching full transparency.
	 */
	obs_source_process_filter_end(filter->context, filter->effect, width, height);
}

static enum gs_color_space edge_fade_video_get_color_space(void *data, size_t count,
							   const enum gs_color_space *preferred_spaces)
{
	struct edge_fade_filter *filter = data;

	return oss_filter_color_space(filter->context, count, preferred_spaces);
}

struct obs_source_info edge_fade_filter_info = {
	.id = OEF_FILTER_ID_EDGE_FADE,
	.type = OBS_SOURCE_TYPE_FILTER,
	.output_flags = OBS_SOURCE_VIDEO | OBS_SOURCE_SRGB,
	.get_name = edge_fade_get_name,
	.create = edge_fade_create,
	.destroy = edge_fade_destroy,
	.update = edge_fade_update,
	.get_defaults = edge_fade_get_defaults,
	.get_properties = edge_fade_get_properties,
	.get_width = edge_fade_get_width,
	.get_height = edge_fade_get_height,
	.video_render = edge_fade_video_render,
	.video_get_color_space = edge_fade_video_get_color_space,
};
