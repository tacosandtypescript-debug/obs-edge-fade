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
	OSS_TEST_CHECK(edge_fade_settings_is_bypass(&settings));

	/* linking mirrors the side the user just changed onto the other three */
	struct edge_fade_settings previous = settings;

	settings.right = 40;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.left == 40 && settings.right == 40 && settings.top == 40 && settings.bottom == 40);
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
	edge_fade_settings_defaults(NULL);
	edge_fade_settings_clamp(NULL);
	edge_fade_settings_apply_link(NULL, NULL);

	/* sides are clamped to the documented range */
	settings.left = -10;
	settings.right = OEF_MAX_EDGE_FADE_PX + 99999;
	settings.top = OEF_MAX_EDGE_FADE_PX;
	edge_fade_settings_clamp(&settings);
	OSS_TEST_CHECK(settings.left == 0);
	OSS_TEST_CHECK(settings.right == OEF_MAX_EDGE_FADE_PX);
	OSS_TEST_CHECK(settings.top == OEF_MAX_EDGE_FADE_PX);

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
