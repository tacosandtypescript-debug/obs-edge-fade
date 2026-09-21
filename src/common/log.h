#pragma once

#include <obs-module.h>

/** Consistent, greppable log prefix for every plugin message. */
#define OSS_LOG_PREFIX "[OBS Edge Fade] "

#define oss_log_info(...) blog(LOG_INFO, OSS_LOG_PREFIX __VA_ARGS__)
#define oss_log_warning(...) blog(LOG_WARNING, OSS_LOG_PREFIX __VA_ARGS__)
#define oss_log_error(...) blog(LOG_ERROR, OSS_LOG_PREFIX __VA_ARGS__)

/* Logging must never happen per frame. Keep debug output build-gated. */
#if defined(_DEBUG) || defined(OSS_ENABLE_DEBUG_LOGGING)
#define oss_log_debug(...) blog(LOG_DEBUG, OSS_LOG_PREFIX __VA_ARGS__)
#else
#define oss_log_debug(...) ((void)0)
#endif
