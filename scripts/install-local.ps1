<#
.SYNOPSIS
Builds obs-edge-fade and installs it into the local OBS plugins folder.

.DESCRIPTION
Runs the Windows CMake preset, builds the requested configuration and installs
the plugin. Without -InstallPrefix the template default prefix is used, which is
%ALLUSERSPROFILE%\obs-studio\plugins, so OBS picks the plugin up on the next
launch.

.PARAMETER Configuration
CMake build configuration. Defaults to RelWithDebInfo.

.PARAMETER InstallPrefix
Optional install prefix. Leave empty to install into the OBS plugins folder.

.PARAMETER SkipConfigure
Skip the configure step when the build folder is already configured.

.PARAMETER SkipBuild
Skip the build step and only install an existing build.

.EXAMPLE
./scripts/install-local.ps1
./scripts/install-local.ps1 -Configuration Debug
./scripts/install-local.ps1 -SkipConfigure -InstallPrefix ./release
#>

[CmdletBinding()]
param(
    [ValidateSet('RelWithDebInfo', 'Debug', 'Release', 'MinSizeRel')]
    [string] $Configuration = 'RelWithDebInfo',

    [string] $InstallPrefix = '',

    [switch] $SkipConfigure,
    [switch] $SkipBuild
)

$ErrorActionPreference = 'Stop'

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')
Push-Location $projectRoot

try {
    if (-not $SkipConfigure) {
        Write-Host 'Configuring obs-edge-fade...'
        cmake --preset windows-x64
        if ($LASTEXITCODE -ne 0) { throw 'cmake configure failed' }
    }

    if (-not $SkipBuild) {
        Write-Host "Building obs-edge-fade ($Configuration)..."
        cmake --build --preset windows-x64 --config $Configuration --parallel
        if ($LASTEXITCODE -ne 0) { throw 'cmake build failed' }
    }

    Write-Host 'Installing obs-edge-fade...'
    if ($InstallPrefix) {
        cmake --install build_x64 --config $Configuration --prefix $InstallPrefix
    }
    else {
        cmake --install build_x64 --config $Configuration
    }
    if ($LASTEXITCODE -ne 0) { throw 'cmake install failed' }

    if ($InstallPrefix) {
        Write-Host "Installed into $InstallPrefix"
    }
    else {
        $plugins = Join-Path $env:ALLUSERSPROFILE 'obs-studio\plugins'
        Write-Host "Installed into $plugins\obs-edge-fade"
    }

    Write-Host 'Restart OBS to load the new build.'
}
finally {
    Pop-Location
}
