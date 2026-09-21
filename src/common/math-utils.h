#pragma once

#ifdef __cplusplus
extern "C" {
#endif

/** Small numeric helpers shared by the filter and its settings logic. */

static inline int oss_clampi(int value, int min_value, int max_value)
{
	return value < min_value ? min_value : (value > max_value ? max_value : value);
}

#ifdef __cplusplus
}
#endif
