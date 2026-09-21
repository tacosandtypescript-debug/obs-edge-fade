#include <obs-module.h>
#include <plugin-support.h>

#include "common/log.h"
#include "common/obs-edge-fade-common.h"
#include "edge-fade/edge-fade-filter.h"

OBS_DECLARE_MODULE()
OBS_MODULE_USE_DEFAULT_LOCALE(PLUGIN_NAME, "en-US")

bool obs_module_load(void)
{
	obs_register_source(&edge_fade_filter_info);

	oss_log_info("Plugin loaded (version %s)", PLUGIN_VERSION);

	return true;
}

void obs_module_unload(void)
{
	oss_log_info("Plugin unloaded");
}
