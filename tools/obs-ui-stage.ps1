# Prepares OBS for the filter-dialog check in tools/obs-ui-check.py:
# installs the freshly built plugin, starts OBS, builds a throwaway scene with the
# Edge Fade filter through obs-websocket and opens the Filters dialog.
#
#   pwsh -NoProfile -File tools/obs-ui-stage.ps1
#
# Then run:  python tools/obs-ui-check.py
#
# The scene is added to whatever profile and scene collection the user already
# has; user.ini and the collection files are never rewritten. The plugin source
# files are copied into the OBS plugin folder, so re-run tools/install-to-obs.py
# afterwards if you want the same build to stay installed.

[CmdletBinding()]
param([string] $Dll = 'build_manual\obs-edge-fade.dll')

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$dllPath = Join-Path $root $Dll
if (-not (Test-Path $dllPath)) { throw "plugin dll not found: $dllPath" }

$programData = Join-Path $env:ALLUSERSPROFILE 'obs-studio\plugins\obs-edge-fade'
if (-not (Test-Path $programData)) { throw 'run tools/install-to-obs.py first to install the plugin' }

Copy-Item $dllPath (Join-Path $programData 'bin\64bit\obs-edge-fade.dll') -Force
Copy-Item (Join-Path $root 'data\*') (Join-Path $programData 'data') -Recurse -Force

$cfgRoot = Join-Path $env:APPDATA 'obs-studio'
$wsCfg = Join-Path $cfgRoot 'plugin_config\obs-websocket\config.json'
$wsBackup = if (Test-Path $wsCfg) { Get-Content $wsCfg -Raw } else { $null }
New-Item -ItemType Directory -Force -Path (Split-Path $wsCfg -Parent) | Out-Null
@{ alerts_enabled = $false; auth_required = $false; first_load = $false; server_enabled = $true
   server_password = ''; server_port = 4455 } | ConvertTo-Json | Set-Content $wsCfg -Encoding UTF8

$sentinel = Join-Path $cfgRoot '.sentinel'
if (Test-Path $sentinel) { Get-ChildItem $sentinel -Filter 'run_*' | Remove-Item -Force -ErrorAction SilentlyContinue }

$obsExe = 'C:\Program Files\obs-studio\bin\64bit\obs64.exe'
Start-Process $obsExe -ArgumentList '--disable-updater', '--disable-shutdown-check' `
    -WorkingDirectory (Split-Path $obsExe -Parent) | Out-Null

Write-Host 'waiting for obs-websocket...'
for ($i = 0; $i -lt 60; $i++) {
    if (Get-NetTCPConnection -LocalPort 4455 -State Listen -ErrorAction SilentlyContinue) { break }
    Start-Sleep -Seconds 2
}
Start-Sleep -Seconds 6

Write-Host 'building the throwaway scene...'
$setupPath = Join-Path $env:TEMP 'oef-ui-stage.py'
@"
import importlib.util, sys
spec = importlib.util.spec_from_file_location('e2e', r'$root\tools\obs-e2e.py')
e2e = importlib.util.module_from_spec(spec); sys.modules['e2e'] = e2e; spec.loader.exec_module(e2e)
obs = e2e.Obs(e2e.connect())
obs.request('RemoveScene', {'sceneName': 'oef_ui_check'}, optional=True)
obs.request('CreateScene', {'sceneName': 'oef_ui_check'})
obs.request('CreateInput', {'sceneName': 'oef_ui_check', 'inputName': 'oef_ui_source',
                            'inputKind': 'color_source_v3',
                            'inputSettings': {'color': 4294901760, 'width': 1920, 'height': 1080},
                            'sceneItemEnabled': True})
obs.request('SetCurrentProgramScene', {'sceneName': 'oef_ui_check'})
obs.request('CreateSourceFilter', {'sourceName': 'oef_ui_source',
    'filterName': 'OBS Edge Fade - Edge Fade', 'filterKind': 'obs_source_style_edge_fade',
    'filterSettings': {'edge_fade.linked': True, 'edge_fade.uniform': -1, 'edge_fade.left': 0,
                       'edge_fade.right': 0, 'edge_fade.top': 0, 'edge_fade.bottom': 0,
                       'edge_fade.smoothness': 50, 'edge_fade.curve': 1}})
print('scene ready')
"@ | Set-Content $setupPath -Encoding UTF8
python $setupPath

Add-Type -AssemblyName System.Windows.Forms
$obs = Get-Process obs64 -ErrorAction SilentlyContinue | Where-Object { $_.MainWindowTitle } | Select-Object -First 1
if ($obs) {
    [void]([System.Windows.Forms.SendKeys]::SendWait('^f'))
    Start-Sleep -Seconds 3
}

if ($wsBackup) { Set-Content $wsCfg $wsBackup -Encoding UTF8 }

Write-Host ''
Write-Host 'OBS is ready with the Filters dialog open.'
Write-Host 'Now run:  python tools/obs-ui-check.py'
Write-Host 'Afterwards run tools/obs-ui-stage.ps1 --cleanup (or delete the oef_ui_check'
Write-Host 'scene in OBS) to remove the throwaway scene.'
