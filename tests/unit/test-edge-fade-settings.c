#include "oss-test.h"

#include "common/obs-edge-fade-common.h"
#include "edge-fade/edge-fade-settings.h"

int main(void)
{
	struct edge_fade_settings settings;

	edge_fade_settings_defaults(&settings);
	OSS_TEST_CHECK(settings.linked);
	OSS_TEST_CHECK(settings.smoothness == 50);
	OSS_TEST_CHECK(settings.curve == OEF_EDGE_CURVE_SMOOTH);
	OSS_TEST_CHECK(edge_fade_settings_is_bypass(&settings));

	struct edge_fade_settings previous = settings;

	settings.right = 40;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.left == 40 && settings.right == 40 && settings.top == 40 && settings.bottom == 40);
	OSS_TEST_CHECK(!edge_fade_settings_is_bypass(&settings));

	settings.linked = false;
	settings.left = 5;
	settings.right = 6;
	settings.top = 7;
	settings.bottom = 8;
	previous = settings;
	settings.left = 9;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.right == 6);

	settings.left = -10;
	settings.right = 99999;
	edge_fade_settings_clamp(&settings);
	OSS_TEST_CHECK(settings.left == 0);
	OSS_TEST_CHECK(settings.right == OEF_MAX_EDGE_FADE_PX);

	/* linked follows whichever side changed, not only the left one */
	edge_fade_settings_defaults(&settings);
	previous = settings;
	settings.top = 25;
	edge_fade_settings_apply_link(&settings, &previous);
	OSS_TEST_CHECK(settings.left == 25 && settings.right == 25 && settings.top == 25 && settings.bottom == 25);

	/* smoothness and curve are clamped to their ranges */
	settings.linked = false;
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

	return OSS_TEST_REPORT();
}
