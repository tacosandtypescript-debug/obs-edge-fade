# Local helper: builds and runs the libobs-free unit tests with the MSVC
# toolchain from the developer environment (the Visual Studio generator is not
# usable on machines whose Windows SDK lacks its MSBuild integration).
#
#   pwsh -NoProfile -File tools/run-unit-tests.ps1

[CmdletBinding()]
param(
    [string] $Configuration = 'Release'
)

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$vcvars = 'C:\Program Files (x86)\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat'
$outDir = Join-Path $root 'build_tests'
$log = Join-Path $root 'unit-tests.log'

New-Item -ItemType Directory -Force -Path $outDir | Out-Null

$opt = if ($Configuration -eq 'Debug') { '/Od /MDd /Zi /DDEBUG /D_DEBUG' } else { '/O2 /MD' }

$steps = @(
    "call `"$vcvars`" >nul"
    "cd /d `"$root`""
    "cl /nologo /TC /std:c17 /W3 /WX /Zc:preprocessor /utf-8 /Brepro $opt " +
        "/I`"$root\src`" /I`"$root\tests\unit`" " +
        "/Fo`"$outDir\\`" /Fe`"$outDir\test-edge-fade-settings.exe`" " +
        "tests\unit\test-edge-fade-settings.c src\edge-fade\edge-fade-settings.c"
    "if errorlevel 1 exit /b 1"
    "`"$outDir\test-edge-fade-settings.exe`""
)

$script = Join-Path $env:TEMP 'oef-unit-tests.cmd'
Set-Content -Path $script -Value ($steps -join "`r`n") -Encoding OEM

$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = "$env:ComSpec"
$psi.Arguments = "/v:on /c `"$script`""
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.WorkingDirectory = $root

$process = [System.Diagnostics.Process]::Start($psi)
$stdout = $process.StandardOutput.ReadToEnd()
$stderr = $process.StandardError.ReadToEnd()
$process.WaitForExit()

$all = $stdout + $stderr
Set-Content -Path $log -Value $all -Encoding UTF8
Write-Host $all
Write-Host "unit tests exit=$($process.ExitCode)"
exit $process.ExitCode
