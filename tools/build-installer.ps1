# Builds the standalone installer executable.
#
#   pwsh -NoProfile -File tools/build-installer.ps1
#
# The plugin payload (dist/obs-edge-fade) is embedded in the executable as
# resources, so the result is a single file with no dependency other than the
# .NET Framework that ships with Windows.
#
# Produces installer/out/OBS-Edge-Fade-Setup-<version>.exe

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$payloadRoot = Join-Path $root 'dist\obs-edge-fade'
if (-not (Test-Path $payloadRoot)) {
    throw "payload not found at $payloadRoot; run tools/package-release.ps1 first"
}

$buildspec = Get-Content (Join-Path $root 'buildspec.json') -Raw | ConvertFrom-Json
$version = $buildspec.version
$assemblyVersion = ($version -split '\.')
while ($assemblyVersion.Count -lt 3) { $assemblyVersion += '0' }
$assemblyVersion = ($assemblyVersion[0..2] -join '.')

# Same order as PayloadRelativePaths in installer/Installer.cs.
$payloadFiles = @(
    'bin\64bit\obs-edge-fade.dll'
    'data\effects\edge-fade.effect'
    'data\locale\en-US.ini'
    'data\locale\es-ES.ini'
)

$outDir = Join-Path $root 'installer\out'
$objDir = Join-Path $root 'installer\obj'
if (Test-Path $objDir) { Remove-Item -Recurse -Force $objDir }
New-Item -ItemType Directory -Force -Path $outDir, $objDir | Out-Null

# --- embedded payload -----------------------------------------------------
# The payload becomes a generated C# file: .NET Framework's csc has no /embed:
# and its /resource:name,path cannot cope with quoted paths, so a source file is
# the only option that survives spaces in the build path.
Write-Host 'generating the payload source...'
& (Join-Path $PSScriptRoot 'make-installer-payload.ps1')
$payloadSource = Join-Path $root 'installer\Payload.g.cs'
if (-not (Test-Path $payloadSource)) { throw "payload source was not generated: $payloadSource" }

# --- attribute file -------------------------------------------------------
$attributes = Join-Path $objDir 'AssemblyInfo.cs'
@"
using System.Reflection;
using System.Runtime.InteropServices;

[assembly: AssemblyTitle("OBS Edge Fade Setup")]
[assembly: AssemblyDescription("Installer for the OBS Edge Fade plugin for OBS Studio")]
[assembly: AssemblyProduct("OBS Edge Fade")]
[assembly: AssemblyCompany("OBS Edge Fade contributors")]
[assembly: AssemblyCopyright("GPL-2.0-or-later")]
[assembly: ComVisible(false)]
[assembly: Guid("2f7c1f5e-6a4d-4c8b-9f0a-7d3b1c5e8a94")]
[assembly: AssemblyVersion("$assemblyVersion")]
[assembly: AssemblyFileVersion("$assemblyVersion")]
"@ | Set-Content $attributes -Encoding UTF8

$exeName = "OBS-Edge-Fade-Setup-$version.exe"
$exePath = Join-Path $outDir $exeName
if (Test-Path $exePath) { Remove-Item $exePath -Force }

# --- compile --------------------------------------------------------------
$csc = Join-Path $env:SystemRoot 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path $csc)) {
    $csc = Join-Path $env:SystemRoot 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path $csc)) { throw 'the .NET Framework C# compiler (csc.exe) was not found' }

$source = Join-Path $root 'installer\Installer.cs'

# csc is driven by a response file: PowerShell 7 does not quote arguments for
# native executables and csc's own parser disagrees with quoted /resource paths,
# so the response file removes the shell from the equation.
$arguments = New-Object System.Collections.Generic.List[string]
$arguments.Add('/nologo')
$arguments.Add('/target:winexe')
$arguments.Add('/platform:anycpu')
$arguments.Add('/optimize+')
$arguments.Add('/warnaserror+')
$arguments.Add("/out:`"$exePath`"")
$arguments.Add('/reference:System.Windows.Forms.dll')
$arguments.Add('/reference:System.Drawing.dll')

$icon = Join-Path $root 'installer\app.ico'
if (Test-Path $icon) { $arguments.Add("/win32icon:`"$icon`"") }

$arguments.Add("`"$source`"")
$arguments.Add("`"$payloadSource`"")
$arguments.Add("`"$attributes`"")

$responseFile = Join-Path $objDir 'csc.rsp'
Set-Content -Path $responseFile -Value ($arguments -join "`r`n") -Encoding UTF8

Write-Host 'compiling...'
$psi = New-Object System.Diagnostics.ProcessStartInfo
$psi.FileName = $csc
$psi.Arguments = "@`"$responseFile`""
$psi.RedirectStandardOutput = $true
$psi.RedirectStandardError = $true
$psi.UseShellExecute = $false
$psi.WorkingDirectory = $root

$process = [System.Diagnostics.Process]::Start($psi)
$output = $process.StandardOutput.ReadToEnd() + $process.StandardError.ReadToEnd()
$process.WaitForExit()

Set-Content -Path (Join-Path $objDir 'build.log') -Value $output -Encoding UTF8
$output -split "`r?`n" | Where-Object { $_ } | ForEach-Object { Write-Host "  $_" }

if ($process.ExitCode -ne 0 -or -not (Test-Path $exePath)) {
    throw "compile failed with exit code $($process.ExitCode); see $(Join-Path $objDir 'build.log')"
}

$hash = (Get-FileHash $exePath -Algorithm SHA256).Hash
Write-Host ''
Write-Host "installer : $exePath"
Write-Host "version   : $version"
Write-Host "size      : $([math]::Round((Get-Item $exePath).Length / 1KB, 1)) KB"
Write-Host "sha256    : $hash"
