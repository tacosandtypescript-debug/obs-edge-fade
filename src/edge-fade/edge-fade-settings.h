#pragma once

#include <stdbool.h>

#ifdef __cplusplus
extern "C" {
#endif

/**
 * Stable settings identifiers. Scenes persist these names, so they must never
 * change without an explicit migration.
 */
#define EDGE_FADE_SETTING_LINKED "edge_fade.linked"
#define EDGE_FADE_SETTING_LEFT "edge_fade.left"
#define EDGE_FADE_SETTING_RIGHT "edge_fade.right"
#define EDGE_FADE_SETTING_TOP "edge_fade.top"
#define EDGE_FADE_SETTING_BOTTOM "edge_fade.bottom"
#define EDGE_FADE_SETTING_SMOOTHNESS "edge_fade.smoothness"
#define EDGE_FADE_SETTING_CURVE "edge_fade.curve"

struct edge_fade_settings {
	bool linked;
	int left;
	int right;
	int top;
	int bottom;
	int smoothness; /* 0..100 percent */
	int curve;      /* enum oef_edge_curve */
};

void edge_fade_settings_defaults(struct edge_fade_settings *settings);
void edge_fade_settings_clamp(struct edge_fade_settings *settings);

/**
 * When linked, mirrors the side the user just changed to the other three.
 * Falls back to keeping all sides equal on a fresh load.
 */
void edge_fade_settings_apply_link(struct edge_fade_settings *settings, const struct edge_fade_settings *previous);

bool edge_fade_settings_is_bypass(const struct edge_fade_settings *settings);

#ifdef __cplusplus
}
#endif
