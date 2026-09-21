#pragma once

#include <stdio.h>

/* Minimal dependency-free test harness. One test executable per file. */

static int oss_test_checks = 0;
static int oss_test_failures = 0;

#define OSS_TEST_CHECK(condition) \
	do { \
		++oss_test_checks; \
		if (!(condition)) { \
			++oss_test_failures; \
			fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, #condition); \
		} \
	} while (0)

#define OSS_TEST_CHECK_NEAR(actual, expected, tolerance) \
	do { \
		++oss_test_checks; \
		const double oss_test_actual = (double)(actual); \
		const double oss_test_expected = (double)(expected); \
		const double oss_test_tolerance = (double)(tolerance); \
		const double oss_test_delta = oss_test_actual - oss_test_expected; \
		if (!(oss_test_delta <= oss_test_tolerance && -oss_test_delta <= oss_test_tolerance)) { \
			++oss_test_failures; \
			fprintf(stderr, "FAIL %s:%d: %s ~= %s (got %f, expected %f)\n", __FILE__, __LINE__, #actual, \
				#expected, oss_test_actual, oss_test_expected); \
		} \
	} while (0)

#define OSS_TEST_REPORT() (oss_test_failures == 0 ? 0 : 1)
