# Configures and builds obs-edge-fade with the Ninja Multi-Config generator.
# Must run inside the MSVC developer environment (vcvars64), otherwise CMake
# cannot find cl.exe and the Windows SDK.
#
#   pwsh -File .\scripts\build-ninja.ps1 -Configuration RelWithDebInfo -Install
#
# This is the fallback path for machines whose Windows SDK is missing the
# MSBuild integration component, which the Visual Studio generator needs.

[CmdletBinding()]
param(
    [ValidateSet('RelWithDebInfo', 'Debug', 'Release', 'MinSizeRel')]
    [string] $Configuration = 'RelWithDebInfo',

    [string] $InstallPrefix = '',
    [switch] $SkipConfigure,
    [switch] $Install
)

$ErrorActionPreference = 'Stop'

$vswhere = "${env:ProgramFiles(x86)}\Microsoft Visual Studio\Installer\vswhere.exe"
if (-not (Test-Path $vswhere)) { throw 'vswhere.exe not found; Visual Studio 2022 is required.' }

$vsPath = & $vswhere -latest -products * -property installationPath
if (-not $vsPath) { throw 'No Visual Studio installation found.' }

$vcvars = Join-Path $vsPath 'VC\Auxiliary\Build\vcvars64.bat'
if (-not (Test-Path $vcvars)) { throw "vcvars64.bat not found at $vcvars" }

$ninja = Get-Command ninja -ErrorAction SilentlyContinue
if (-not $ninja) {
    $pyScripts = & python -c "import sysconfig; print(sysconfig.get_path('scripts'))" 2>$null
    if ($pyScripts -and (Test-Path (Join-Path $pyScripts 'ninja.exe'))) {
        $ninja = Get-Item (Join-Path $pyScripts 'ninja.exe')
    }
}
if (-not $ninja) { throw 'ninja.exe not found. Install it with: python -m pip install ninja' }
$ninjaDir = Split-Path $ninja.Source -Parent

$projectRoot = Resolve-Path (Join-Path $PSScriptRoot '..')

# One cmd line, so vcvars64 and every following command share an environment:
# separate processes would lose INCLUDE/LIB again. Parentheses in the project
# path make cmd's "&&" chaining unreliable, so the steps are newline separated.
$steps = @(
    "call `"$vcvars`" >nul"
    "set `"PATH=$ninjaDir;%PATH%`""
    "cd /d `"$projectRoot`""
)

if (-not $SkipConfigure) {
    $steps += 'cmake --preset ninja-x64'
    $steps += 'if errorlevel 1 exit /b 1'
}

$steps += "cmake --build --preset ninja-x64 --config $Configuration --parallel"
$steps += 'if errorlevel 1 exit /b 1'

if ($Install) {
    if ($InstallPrefix) {
        $steps += "cmake --install build_x64 --config $Configuration --prefix `"$InstallPrefix`""
    }
    else {
        $steps += "cmake --install build_x64 --config $Configuration"
    }
    $steps += 'if errorlevel 1 exit /b 1'
}

$command = $steps -join "`r`n"
$logFile = Join-Path $projectRoot 'build-ninja.log'
Push-Location $projectRoot
try {
    cmd /v:on /c "$command > `"$logFile`" 2>&1"
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}

if (Test-Path $logFile) { Get-Content $logFile -Tail 40 } else { Write-Warning "no log written to $logFile" }
Write-Host "Full log: $logFile"
exit $exitCode
