# CMake Windows build dependencies module

include_guard(GLOBAL)

include(buildspec_common)

# _check_dependencies_windows: Set up Windows slice for _check_dependencies.
# OBS Edge Fade builds libobs without Qt or frontend-API dependencies, so only
# the pre-built obs-deps and the OBS sources are required.
function(_check_dependencies_windows)
  # CMAKE_VS_PLATFORM_NAME only exists for Visual Studio generators. Ninja and
  # NMake builds still target x64 here, so fall back to the host architecture
  # instead of producing an empty "windows-" platform key.
  if(CMAKE_VS_PLATFORM_NAME)
    set(arch ${CMAKE_VS_PLATFORM_NAME})
  else()
    set(arch x64)
  endif()
  set(platform windows-${arch})

  set(dependencies_dir "${CMAKE_CURRENT_SOURCE_DIR}/.deps")
  set(prebuilt_filename "windows-deps-VERSION-ARCH-REVISION.zip")
  set(prebuilt_destination "obs-deps-VERSION-ARCH")
  set(obs-studio_filename "VERSION.zip")
  set(obs-studio_destination "obs-studio-VERSION")
  set(dependencies_list prebuilt obs-studio)

  _check_dependencies()
endfunction()

_check_dependencies_windows()
