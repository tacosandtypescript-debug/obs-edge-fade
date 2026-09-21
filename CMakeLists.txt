cmake_minimum_required(VERSION 3.28...3.30)

include("${CMAKE_CURRENT_SOURCE_DIR}/cmake/common/bootstrap.cmake" NO_POLICY_SCOPE)

project(${_name} VERSION ${_version})

option(ENABLE_FRONTEND_API "Use obs-frontend-api for UI functionality" OFF)
option(ENABLE_QT "Use Qt functionality (unsupported by OBS Edge Fade)" OFF)
option(ENABLE_TESTS "Build libobs-free unit tests" OFF)

if(ENABLE_QT)
  message(FATAL_ERROR "OBS Edge Fade does not use Qt. Configure with -DENABLE_QT=OFF.")
endif()

include(compilerconfig)
include(defaults)
include(helpers)

add_library(${CMAKE_PROJECT_NAME} MODULE)

find_package(libobs REQUIRED)
target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE OBS::libobs)

if(ENABLE_FRONTEND_API)
  find_package(obs-frontend-api REQUIRED)
  target_link_libraries(${CMAKE_PROJECT_NAME} PRIVATE OBS::obs-frontend-api)
endif()

target_sources(
  ${CMAKE_PROJECT_NAME}
  PRIVATE
    src/plugin-main.c
    src/common/math-utils.c
    src/common/color-space.c
    src/common/shader-loader.c
    src/edge-fade/edge-fade-filter.c
    src/edge-fade/edge-fade-settings.c
    src/edge-fade/edge-fade-properties.c
)

target_include_directories(${CMAKE_PROJECT_NAME} PRIVATE "${CMAKE_CURRENT_SOURCE_DIR}/src")

set_target_properties_plugin(${CMAKE_PROJECT_NAME} PROPERTIES OUTPUT_NAME ${_name})

if(ENABLE_TESTS)
  enable_testing()
  add_subdirectory(tests/unit)
endif()
