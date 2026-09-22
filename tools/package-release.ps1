# Assembles the installable plugin folder and the downloadable artefacts.
#
#   pwsh -NoProfile -File tools/package-release.ps1
#
# Produces:
#   dist/obs-edge-fade/bin/64bit/obs-edge-fade.dll   the installable tree
#   dist/obs-edge-fade/data/...
#   installer/out/OBS-Edge-Fade-Setup-<version>.exe  the standalone installer
#   release/obs-edge-fade-<version>-windows-x64.zip  the manual install archive
#
# Unzipping the archive into %ProgramData%\obs-studio\plugins\ (or running the
# installer) makes OBS pick the filter up on the next launch.

[CmdletBinding()]
param([string] $Dll = 'build_manual\obs-edge-fade.dll')

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dllPath = Join-Path $root $Dll
if (-not (Test-Path $dllPath)) { throw "plugin dll not found: $dllPath" }

$buildspec = Get-Content (Join-Path $root 'buildspec.json') -Raw | ConvertFrom-Json
$name = $buildspec.name
$version = $buildspec.version

$dist = Join-Path $root "dist\$name"
$binDir = Join-Path $dist 'bin\64bit'
$dataDir = Join-Path $dist 'data'

# Start clean so a removed resource never lingers in the archive.
if (Test-Path $dist) { Remove-Item -Recurse -Force $dist }
New-Item -ItemType Directory -Force -Path $binDir, $dataDir | Out-Null

Copy-Item $dllPath (Join-Path $binDir "$name.dll") -Force
Copy-Item (Join-Path $root 'data\*') $dataDir -Recurse -Force

$releaseDir = Join-Path $root 'release'
New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null
$archive = Join-Path $releaseDir "$name-$version-windows-x64.zip"
if (Test-Path $archive) { Remove-Item $archive -Force }

# The archive holds the plugin folder itself, so extracting it into the OBS
# plugins directory produces <plugins>\<name>\bin\64bit\<name>.dll.
Compress-Archive -Path $dist -DestinationPath $archive -CompressionLevel Optimal

$hash = (Get-FileHash $archive -Algorithm SHA256).Hash

Write-Host "version : $version"
Write-Host "dist    : $dist"
Write-Host "archive : $archive"
Write-Host "size    : $([math]::Round((Get-Item $archive).Length / 1KB, 1)) KB"
Write-Host "sha256  : $hash"
Write-Host ''
Write-Host 'contents:'
Get-ChildItem $dist -Recurse -File | ForEach-Object {
    Write-Host ("  {0} ({1} bytes)" -f $_.FullName.Substring($dist.Length + 1), $_.Length)
}

# --- standalone installer -------------------------------------------------
# Built from the payload that was just refreshed, so the two can never drift.
Write-Host ''
Write-Host 'building the installer...'
& (Join-Path $PSScriptRoot 'build-installer.ps1')
