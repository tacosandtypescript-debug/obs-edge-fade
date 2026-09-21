#include "edge-fade/edge-fade-settings.h"

#include "common/math-utils.h"
#include "common/obs-edge-fade-common.h"

void edge_fade_settings_defaults(struct edge_fade_settings *settings)
{
	if (!settings)
		return;

	settings->linked = true;
	settings->left = 0;
	settings->right = 0;
	settings->top = 0;
	settings->bottom = 0;
	settings->smoothness = 50;
	settings->curve = OEF_EDGE_CURVE_SMOOTH;
}

void edge_fade_settings_clamp(struct edge_fade_settings *settings)
{
	if (!settings)
		return;

	settings->left = oss_clampi(settings->left, 0, OEF_MAX_EDGE_FADE_PX);
	settings->right = oss_clampi(settings->right, 0, OEF_MAX_EDGE_FADE_PX);
	settings->top = oss_clampi(settings->top, 0, OEF_MAX_EDGE_FADE_PX);
	settings->bottom = oss_clampi(settings->bottom, 0, OEF_MAX_EDGE_FADE_PX);
	settings->smoothness = oss_clampi(settings->smoothness, 0, 100);
	settings->curve = oss_clampi(settings->curve, OEF_EDGE_CURVE_LINEAR, OEF_EDGE_CURVE_SOFT);
}

void edge_fade_settings_apply_link(struct edge_fade_settings *settings, const struct edge_fade_settings *previous)
{
	if (!settings || !settings->linked)
		return;

	int source = settings->left;
	bool changed = false;

	if (previous) {
		if (previous->left != settings->left) {
			source = settings->left;
			changed = true;
		} else if (previous->right != settings->right) {
			source = settings->right;
			changed = true;
		} else if (previous->top != settings->top) {
			source = settings->top;
			changed = true;
		} else if (previous->bottom != settings->bottom) {
			source = settings->bottom;
			changed = true;
		}
	}

	if (!changed)
		source = settings->left;

	settings->left = source;
	settings->right = source;
	settings->top = source;
	settings->bottom = source;
}

bool edge_fade_settings_is_bypass(const struct edge_fade_settings *settings)
{
	if (!settings)
		return true;

	return settings->left == 0 && settings->right == 0 && settings->top == 0 && settings->bottom == 0;
}
