# CMake operating system bootstrap module

include_guard(GLOBAL)

# OBS Edge Fade v1 targets Windows 10/11 x64 only. Fail early and clearly on
# any other host instead of silently picking up unsupported toolchain modules.
if(NOT CMAKE_HOST_SYSTEM_NAME STREQUAL "Windows")
  message(
    FATAL_ERROR
    "OBS Edge Fade currently supports Windows only. Detected host system: ${CMAKE_HOST_SYSTEM_NAME}."
  )
endif()

set(CMAKE_C_EXTENSIONS FALSE)
set(CMAKE_CXX_EXTENSIONS FALSE)
list(APPEND CMAKE_MODULE_PATH "${CMAKE_CURRENT_SOURCE_DIR}/cmake/windows")
set(OS_WINDOWS TRUE)
