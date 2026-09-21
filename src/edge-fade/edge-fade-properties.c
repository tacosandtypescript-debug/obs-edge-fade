#include "edge-fade/edge-fade-properties.h"

#include "common/obs-edge-fade-common.h"
#include "edge-fade/edge-fade-settings.h"

obs_properties_t *edge_fade_build_properties(void)
{
	obs_properties_t *props = obs_properties_create();

	obs_properties_add_bool(props, EDGE_FADE_SETTING_LINKED, obs_module_text("EdgeFade.Linked"));

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

	return props;
}
