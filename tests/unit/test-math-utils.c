#include "oss-test.h"

#include "common/math-utils.h"

int main(void)
{
	OSS_TEST_CHECK(oss_clampi(5, 0, 3) == 3);
	OSS_TEST_CHECK(oss_clampi(-1, 0, 3) == 0);
	OSS_TEST_CHECK(oss_clampi(2, 0, 3) == 2);
	OSS_TEST_CHECK_NEAR(oss_clampf(5.0f, 0.0f, 3.0f), 3.0, 1e-6);

	float x = 0.0f;
	float y = 0.0f;

	oss_angle_distance_to_xy(0.0f, 10.0f, &x, &y);
	OSS_TEST_CHECK_NEAR(x, 10.0, 1e-4);
	OSS_TEST_CHECK_NEAR(y, 0.0, 1e-4);

	oss_angle_distance_to_xy(90.0f, 10.0f, &x, &y);
	OSS_TEST_CHECK_NEAR(x, 0.0, 1e-4);
	OSS_TEST_CHECK_NEAR(y, 10.0, 1e-4);

	float angle = 0.0f;
	float distance = 0.0f;

	oss_xy_to_angle_distance(0.0f, 10.0f, &angle, &distance);
	OSS_TEST_CHECK_NEAR(distance, 10.0, 1e-4);
	OSS_TEST_CHECK_NEAR(angle, 90.0, 1e-3);

	oss_xy_to_angle_distance(10.0f, 0.0f, &angle, &distance);
	OSS_TEST_CHECK_NEAR(angle, 0.0, 1e-3);

	oss_xy_to_angle_distance(-10.0f, 0.0f, &angle, &distance);
	OSS_TEST_CHECK_NEAR(angle, 180.0, 1e-3);

	return OSS_TEST_REPORT();
}
