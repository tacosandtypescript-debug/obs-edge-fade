#include "common/math-utils.h"

#include <math.h>

void oss_angle_distance_to_xy(float angle_degrees, float distance, float *out_x, float *out_y)
{
	const float radians = oss_deg_to_rad(angle_degrees);

	if (out_x)
		*out_x = cosf(radians) * distance;
	if (out_y)
		*out_y = sinf(radians) * distance;
}

void oss_xy_to_angle_distance(float x, float y, float *out_angle_degrees, float *out_distance)
{
	const float distance = sqrtf(x * x + y * y);

	if (out_distance)
		*out_distance = distance;

	if (out_angle_degrees) {
		float angle = atan2f(y, x) * 57.29577951308232f;

		if (angle < 0.0f)
			angle += 360.0f;

		*out_angle_degrees = angle;
	}
}

static float oss_radius_pair_limit(float first, float second, float limit)
{
	const float sum = first + second;

	if (sum <= limit)
		return 1.0f;

	return limit / sum;
}

void oss_normalize_corner_radii(float width, float height, float *top_left, float *top_right, float *bottom_left,
				float *bottom_right)
{
	if (!top_left || !top_right || !bottom_left || !bottom_right)
		return;

	*top_left = *top_left < 0.0f ? 0.0f : *top_left;
	*top_right = *top_right < 0.0f ? 0.0f : *top_right;
	*bottom_left = *bottom_left < 0.0f ? 0.0f : *bottom_left;
	*bottom_right = *bottom_right < 0.0f ? 0.0f : *bottom_right;

	const float safe_width = width > 1.0f ? width : 1.0f;
	const float safe_height = height > 1.0f ? height : 1.0f;

	/* A radius larger than half the smaller side cannot describe a corner. */
	const float max_radius = fminf(safe_width, safe_height) * 0.5f;

	*top_left = fminf(*top_left, max_radius);
	*top_right = fminf(*top_right, max_radius);
	*bottom_left = fminf(*bottom_left, max_radius);
	*bottom_right = fminf(*bottom_right, max_radius);

	float scale = 1.0f;

	scale = fminf(scale, oss_radius_pair_limit(*top_left, *top_right, safe_width));
	scale = fminf(scale, oss_radius_pair_limit(*bottom_left, *bottom_right, safe_width));
	scale = fminf(scale, oss_radius_pair_limit(*top_left, *bottom_left, safe_height));
	scale = fminf(scale, oss_radius_pair_limit(*top_right, *bottom_right, safe_height));

	if (scale < 1.0f) {
		*top_left *= scale;
		*top_right *= scale;
		*bottom_left *= scale;
		*bottom_right *= scale;
	}
}
