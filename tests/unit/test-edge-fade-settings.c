#include "oss-test.h"

#include "common/math-utils.h"
#include "common/obs-edge-fade-common.h"
#include "edge-fade/edge-fade-settings.h"

int main(void)
{
	/* defaults: linked, no fade at all, mid smoothness and the smooth curve */
	struct edge_fade_settings settings;

	edge_fade_settings_defaults(&settings);
	OSS_TEST_CHECK(settings.linked);
	OSS_TEST_CHECK(settings.smoothness == 50);
	OSS_TEST_CHECK(settings.curve == OEF_EDGE_CURVE_SMOOTH);
	OSS_TEST_CHECK(settings.uniform == 0);
	OSS_TEST_CHECK(edge_fade_settings_sides_equal(&settings));
	OSS_TEST_CHECK(edge_fade_settings_is_bypass(&settings));

	/*
	 * The single "all borders" slider: moving it copies its value into the
	 * four sides, whatever they held before.
	 */
	settings.left = 10;
	settings.right = 20;
	settings.top = 30;
	settings.bottom = 40;
	settings.uniform = 130;

	struct edge_fade_settings before = settings;

	before.uniform = 0;
	edge_fade_settings_apply_link(&settings, &before);
	OSS_TEST_CHECK(settings.left == 130 && settings.right == 130 && settings.top == 130 &&
		       settings.bottom == 130);
	OSS_TEST_CHECK(settings.uniform == 130);

	/* ... and it keeps doing so when the global value changes again */
	before = settings;
	settings.uniform = 160;
	edge_fade_settings_apply_link(&settings, &before);
	OSS_TEST_CHECK(settings.left == 160 && settings.right == 160 && settings.top == 160 &&
		       settings.bottom == 160);
	OSS_TEST_CHECK(settings.uniform == 160);

	/* with the sides already equal, the global value follows them */
	edge_fade_settings_defaults(&settings);
	settings.left = settings.right = settings.top = settings.bottom = 77;
	settings.uniform = 0;
	OSS_TEST_CHECK(edge_fade_settings_sides_equal(&settings));
	OSS_TEST_CHECK(edge_fade_settings_resolve_uniform(&settings) == 77);

	/* unlinked settings resolve to the stored global value */
	edge_fade_settings_defaults(&settings);
	settings.linked = false;
	settings.left = 10;
	settings.right = 20;
	settings.uniform = 300;
	OSS_TEST_CHECK(!edge_fade_settings_sides_equal(&settings));
	OSS_TEST_CHECK(edge_fade_settings_resolve_uniform(&settings) == 300);

	/* unlinked data is never rewritten, so the four sliders keep their values */
	before = settings;
	settings.left = 11;
	edge_fade_settings_apply_link(&settings, &before);
	OSS_TEST_CHECK(settings.left == 11 && settings.right == 20 && settings.top == 0 && settings.bottom == 0);

	/* linking mirrors the side the user just changed onto the other three */
	edge_fade_settings_defaults(&settings);
	struct edge_fade_settings previous = settings;

	settings.right = 40;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.left == 40 && settings.right == 40 && settings.top == 40 && settings.bottom == 40);
	OSS_TEST_CHECK(settings.uniform == 40);
	OSS_TEST_CHECK(!edge_fade_settings_is_bypass(&settings));

	/* linking follows whichever side changed, not only the left one */
	edge_fade_settings_defaults(&settings);
	previous = settings;
	settings.top = 25;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.left == 25 && settings.right == 25 && settings.top == 25 && settings.bottom == 25);

	/* a fresh load has no previous state, so the left side seeds the others */
	edge_fade_settings_defaults(&settings);
	settings.left = 12;
	edge_fade_settings_apply_link(&settings, NULL);
	OSS_TEST_CHECK(settings.right == 12 && settings.top == 12 && settings.bottom == 12);

	/* unlinking keeps every side independent */
	settings.linked = false;
	settings.left = 5;
	settings.right = 6;
	settings.top = 7;
	settings.bottom = 8;
	previous = settings;
	settings.left = 9;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.right == 6 && settings.top == 7 && settings.bottom == 8);

	/* invalid input is rejected instead of reaching the GPU */
	OSS_TEST_CHECK(edge_fade_settings_is_bypass(NULL));
	OSS_TEST_CHECK(!edge_fade_settings_sides_equal(NULL));
	OSS_TEST_CHECK(edge_fade_settings_resolve_uniform(NULL) == 0);
	edge_fade_settings_defaults(NULL);
	edge_fade_settings_clamp(NULL);
	edge_fade_settings_apply_link(NULL, NULL);

	/* sides are clamped to the documented range */
	settings.left = -10;
	settings.right = OEF_MAX_EDGE_FADE_PX + 99999;
	settings.top = OEF_MAX_EDGE_FADE_PX;
	settings.uniform = -50;
	edge_fade_settings_clamp(&settings);
	OSS_TEST_CHECK(settings.left == 0);
	OSS_TEST_CHECK(settings.right == OEF_MAX_EDGE_FADE_PX);
	OSS_TEST_CHECK(settings.top == OEF_MAX_EDGE_FADE_PX);
	OSS_TEST_CHECK(settings.uniform == 0);

	/* smoothness and curve are clamped to their ranges */
	settings.smoothness = 500;
	settings.curve = 99;
	edge_fade_settings_clamp(&settings);
	OSS_TEST_CHECK(settings.smoothness == 100);
	OSS_TEST_CHECK(settings.curve == OEF_EDGE_CURVE_SOFT);

	settings.smoothness = -4;
	settings.curve = -1;
	edge_fade_settings_clamp(&settings);
	OSS_TEST_CHECK(settings.smoothness == 0);
	OSS_TEST_CHECK(settings.curve == OEF_EDGE_CURVE_LINEAR);

	/* the shared clamp helper still backs the settings above */
	OSS_TEST_CHECK(oss_clampi(5, 0, 3) == 3);
	OSS_TEST_CHECK(oss_clampi(-1, 0, 3) == 0);
	OSS_TEST_CHECK(oss_clampi(2, 0, 3) == 2);

	return OSS_TEST_REPORT();
}
