if(CMAKE_SOURCE_DIR STREQUAL CMAKE_CURRENT_SOURCE_DIR)
  cmake_minimum_required(VERSION 3.28...3.30)
  project(obs-edge-fade-tests C)
endif()

enable_testing()

set(CMAKE_C_STANDARD 17)
set(CMAKE_C_STANDARD_REQUIRED ON)

set(OSS_SRC "${CMAKE_CURRENT_SOURCE_DIR}/../../src")

function(oss_add_unit_test name)
  add_executable(${name} ${name}.c ${ARGN})
  target_include_directories(${name} PRIVATE "${OSS_SRC}" "${CMAKE_CURRENT_SOURCE_DIR}")
  if(MSVC)
    target_compile_options(${name} PRIVATE /W3 /WX)
  else()
    target_compile_options(${name} PRIVATE -Wall -Wextra -Werror)
    # libm is a separate library on Linux and macOS; MSVC keeps it in the CRT.
    target_link_libraries(${name} PRIVATE m)
  endif()
  add_test(NAME ${name} COMMAND ${name})
endfunction()

oss_add_unit_test(
  test-edge-fade-settings
  "${OSS_SRC}/edge-fade/edge-fade-settings.c"
)
