#include "common/shader-loader.h"

#include "common/log.h"

gs_effect_t *oss_load_effect(const char *relative_path)
{
	if (!relative_path)
		return NULL;

	char *path = obs_module_file(relative_path);
	if (!path) {
		oss_log_error("Could not resolve module file '%s'", relative_path);
		return NULL;
	}

	char *error = NULL;

	obs_enter_graphics();
	gs_effect_t *effect = gs_effect_create_from_file(path, &error);
	obs_leave_graphics();

	if (!effect)
		oss_log_error("Failed to load effect '%s': %s", relative_path, error ? error : "unknown error");

	bfree(error);
	bfree(path);

	return effect;
}
