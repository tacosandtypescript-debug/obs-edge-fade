#include "edge-fade/edge-fade-properties.h"

#include "common/math-utils.h"
#include "common/obs-edge-fade-common.h"
#include "edge-fade/edge-fade-settings.h"

/*
 * The fade width has two front ends, and only one is visible at a time:
 *
 *   link off -> four independent sliders, Left / Right / Top / Bottom
 *   link on  -> a single "All borders" slider that writes the same width into
 *               all four sides
 *
 * The four sides stay the single source of truth for the shader; the global
 * slider is a convenience that keeps them equal. Both controls are therefore
 * mirrored into the settings on every change, so switching the checkbox never
 * jumps, resets or loses a value.
 *
 * Smoothness and Curve describe the shape of the fade, not its size, so they
 * stay visible in both modes.
 */

static void edge_fade_set_sides_visible(obs_properties_t *props, bool sides_visible)
{
	const char *names[] = {
		EDGE_FADE_SETTING_LEFT,
		EDGE_FADE_SETTING_RIGHT,
		EDGE_FADE_SETTING_TOP,
		EDGE_FADE_SETTING_BOTTOM,
	};

	for (size_t i = 0; i < OBS_COUNTOF(names); ++i) {
		obs_property_t *side = obs_properties_get(props, names[i]);

		if (side)
			obs_property_set_visible(side, sides_visible);
	}

	obs_property_t *uniform = obs_properties_get(props, EDGE_FADE_SETTING_UNIFORM);

	if (uniform)
		obs_property_set_visible(uniform, !sides_visible);
}

/**
 * Width the single "all borders" slider represents.
 *
 * The stored uniform is authoritative, but a scene saved before that setting
 * existed has OEF_EDGE_FADE_UNIFORM_UNSET: there the left side is used, which is
 * what the old "linked" behaviour did when it mirrored one side onto the others.
 */
static int edge_fade_stored_uniform(obs_data_t *data)
{
	int uniform = (int)obs_data_get_int(data, EDGE_FADE_SETTING_UNIFORM);

	return uniform < 0 ? (int)obs_data_get_int(data, EDGE_FADE_SETTING_LEFT) : uniform;
}

/**
 * Width the single "all borders" slider represents.
 *
 * While linked, the stored uniform value is what the slider shows, so it wins
 * outright: that is the value the user last picked globally. Only when nothing
 * has been stored yet (OEF_EDGE_FADE_UNIFORM_UNSET, i.e. a scene saved before the
 * setting existed) do the four sides decide, which reproduces the old behaviour
 * of mirroring one side onto the others.
 */
static int edge_fade_linked_width(obs_data_t *data, const struct edge_fade_settings *settings)
{
	if (obs_data_get_int(data, EDGE_FADE_SETTING_UNIFORM) >= 0)
		return settings->uniform;

	return settings->left;
}

static void edge_fade_read(obs_data_t *data, struct edge_fade_settings *settings)
{
	edge_fade_settings_defaults(settings);

	settings->linked = obs_data_get_bool(data, EDGE_FADE_SETTING_LINKED);
	settings->uniform = edge_fade_stored_uniform(data);
	settings->left = (int)obs_data_get_int(data, EDGE_FADE_SETTING_LEFT);
	settings->right = (int)obs_data_get_int(data, EDGE_FADE_SETTING_RIGHT);
	settings->top = (int)obs_data_get_int(data, EDGE_FADE_SETTING_TOP);
	settings->bottom = (int)obs_data_get_int(data, EDGE_FADE_SETTING_BOTTOM);
	settings->smoothness = (int)obs_data_get_int(data, EDGE_FADE_SETTING_SMOOTHNESS);
	settings->curve = (int)obs_data_get_int(data, EDGE_FADE_SETTING_CURVE);

	edge_fade_settings_clamp(settings);
}

/** Copies a width into all four sides and into the shared uniform entry. */
static void edge_fade_write_sides(obs_data_t *data, int width)
{
	obs_data_set_int(data, EDGE_FADE_SETTING_UNIFORM, width);
	obs_data_set_int(data, EDGE_FADE_SETTING_LEFT, width);
	obs_data_set_int(data, EDGE_FADE_SETTING_RIGHT, width);
	obs_data_set_int(data, EDGE_FADE_SETTING_TOP, width);
	obs_data_set_int(data, EDGE_FADE_SETTING_BOTTOM, width);
}

/**
 * Runs for every property change in this filter. It must not call back into
 * obs_properties_apply_settings(): libobs re-enters the modified callbacks from
 * there. Returning true makes the dialog re-read every control from the settings
 * object, which is what makes the swap and the preview update immediate.
 */
static bool edge_fade_modified(obs_properties_t *props, obs_property_t *property, obs_data_t *data)
{
	UNUSED_PARAMETER(property);

	struct edge_fade_settings settings;
	edge_fade_read(data, &settings);

	edge_fade_set_sides_visible(props, !settings.linked);

	if (!settings.linked)
		return true;

	/*
	 * Linked. The global value wins while it is stored; otherwise the four sides
	 * seed it (a scene saved before that setting existed). Writing the result
	 * back keeps the four hidden sliders and the global one equal, so switching
	 * the checkbox back never jumps.
	 */
	int width = oss_clampi(edge_fade_linked_width(data, &settings), 0, OEF_MAX_EDGE_FADE_PX);

	if (settings.uniform != width || settings.left != width || settings.right != width ||
	    settings.top != width || settings.bottom != width)
		edge_fade_write_sides(data, width);

	return true;
}

obs_properties_t *edge_fade_build_properties(void)
{
	obs_properties_t *props = obs_properties_create();

	obs_property_t *linked =
		obs_properties_add_bool(props, EDGE_FADE_SETTING_LINKED, obs_module_text("EdgeFade.Linked"));
	obs_property_set_long_description(linked, obs_module_text("EdgeFade.Linked.Description"));

	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_UNIFORM, obs_module_text("EdgeFade.AllBorders"), 0,
				      OEF_MAX_EDGE_FADE_PX, 1);

	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_LEFT, obs_module_text("EdgeFade.Left"), 0,
				      OEF_MAX_EDGE_FADE_PX, 1);
	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_RIGHT, obs_module_text("EdgeFade.Right"), 0,
				      OEF_MAX_EDGE_FADE_PX, 1);
	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_TOP, obs_module_text("EdgeFade.Top"), 0,
				      OEF_MAX_EDGE_FADE_PX, 1);
	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_BOTTOM, obs_module_text("EdgeFade.Bottom"), 0,
				      OEF_MAX_EDGE_FADE_PX, 1);

	obs_properties_add_int_slider(props, EDGE_FADE_SETTING_SMOOTHNESS, obs_module_text("EdgeFade.Smoothness"), 0,
				      100, 1);

	obs_property_t *curve = obs_properties_add_list(props, EDGE_FADE_SETTING_CURVE,
							obs_module_text("EdgeFade.Curve"), OBS_COMBO_TYPE_LIST,
							OBS_COMBO_FORMAT_INT);

	obs_property_list_add_int(curve, obs_module_text("EdgeFade.Curve.Linear"), OEF_EDGE_CURVE_LINEAR);
	obs_property_list_add_int(curve, obs_module_text("EdgeFade.Curve.Smooth"), OEF_EDGE_CURVE_SMOOTH);
	obs_property_list_add_int(curve, obs_module_text("EdgeFade.Curve.Soft"), OEF_EDGE_CURVE_SOFT);

	/* Both groups need the callback so the swap happens whichever one moves. */
	obs_property_set_modified_callback(linked, edge_fade_modified);
	obs_property_set_modified_callback(obs_properties_get(props, EDGE_FADE_SETTING_UNIFORM),
					   edge_fade_modified);

	return props;
}

