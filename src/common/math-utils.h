#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** Small, reusable math helpers shared by the three filters. */

static inline float oss_clampf(float value, float min_value, float max_value)
{
	return value < min_value ? min_value : (value > max_value ? max_value : value);
}

static inline int oss_clampi(int value, int min_value, int max_value)
{
	return value < min_value ? min_value : (value > max_value ? max_value : value);
}

static inline float oss_deg_to_rad(float degrees)
{
	return degrees * 0.01745329251994329577f;
}

static inline float oss_lerp(float a, float b, float t)
{
	return a + (b - a) * t;
}

/**
 * Converts an angle (degrees) and a distance into an X/Y offset.
 * Screen coordinates are used, so positive Y points down.
 */
void oss_angle_distance_to_xy(float angle_degrees, float distance, float *out_x, float *out_y);

/** Converts an X/Y offset back into an angle (0-360 degrees) and a distance. */
void oss_xy_to_angle_distance(float x, float y, float *out_angle_degrees, float *out_distance);

/**
 * Normalises per-corner radii before they reach the shader: negative values
 * become zero, a single radius is limited to half of the smaller side, and
 * overlapping radii are scaled down proportionally following the CSS
 * border-radius override rules.
 */
void oss_normalize_corner_radii(float width, float height, float *top_left, float *top_right, float *bottom_left,
				float *bottom_right);

#ifdef __cplusplus
}
#endif
