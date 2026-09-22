# Removes the throwaway scene tools/obs-ui-stage.ps1 creates.
#
#   pwsh -NoProfile -File tools/obs-ui-cleanup.ps1

[CmdletBinding()]
param()

$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path

$cfgRoot = Join-Path $env:APPDATA 'obs-studio'
$wsCfg = Join-Path $cfgRoot 'plugin_config\obs-websocket\config.json'
$wsBackup = if (Test-Path $wsCfg) { Get-Content $wsCfg -Raw } else { $null }
New-Item -ItemType Directory -Force -Path (Split-Path $wsCfg -Parent) | Out-Null
@{ alerts_enabled = $false; auth_required = $false; first_load = $false; server_enabled = $true
   server_password = ''; server_port = 4455 } | ConvertTo-Json | Set-Content $wsCfg -Encoding UTF8

$sentinel = Join-Path $cfgRoot '.sentinel'
if (Test-Path $sentinel) { Get-ChildItem $sentinel -Filter 'run_*' | Remove-Item -Force -ErrorAction SilentlyContinue }

$obsExe = 'C:\Program Files\obs-studio\bin\64bit\obs64.exe'
Start-Process $obsExe -ArgumentList '--disable-updater', '--disable-shutdown-check', '--minimize-to-tray' `
    -WorkingDirectory (Split-Path $obsExe -Parent) | Out-Null

for ($i = 0; $i -lt 60; $i++) {
    if (Get-NetTCPConnection -LocalPort 4455 -State Listen -ErrorAction SilentlyContinue) { break }
    Start-Sleep -Seconds 2
}
Start-Sleep -Seconds 8

$cleanup = Join-Path $env:TEMP 'oef-ui-cleanup.py'
@"
import importlib.util, sys
spec = importlib.util.spec_from_file_location('e2e', r'$root\tools\obs-e2e.py')
e2e = importlib.util.module_from_spec(spec); sys.modules['e2e'] = e2e; spec.loader.exec_module(e2e)
obs = e2e.Obs(e2e.connect())
scenes = [s['sceneName'] for s in obs.request('GetSceneList')['scenes']]
for name in ('oef_ui_check', 'oef_e2e'):
    if name not in scenes:
        continue
    for item in obs.request('GetSceneItemList', {'sceneName': name}, optional=True).get('sceneItems', []):
        obs.request('RemoveInput', {'inputName': item['sourceName']}, optional=True)
    obs.request('RemoveScene', {'sceneName': name}, optional=True)
    print('removed scene:', name)
rest = [s for s in scenes if s not in ('oef_ui_check', 'oef_e2e')]
if rest:
    obs.request('SetCurrentProgramScene', {'sceneName': rest[0]}, optional=True)
print('scenes now:', [s['sceneName'] for s in obs.request('GetSceneList')['scenes']])
"@ | Set-Content $cleanup -Encoding UTF8
python $cleanup

if ($wsBackup) { Set-Content $wsCfg $wsBackup -Encoding UTF8 }

Get-Process obs64 -ErrorAction SilentlyContinue | ForEach-Object { $_.CloseMainWindow() | Out-Null }
Start-Sleep -Seconds 12
Get-Process obs64 -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue

New-Item -ItemType Directory -Force -Path 'C:\Users\KTZ' | Out-Null
foreach ($dir in @('C:\Users\KTZ\oef-ui', 'C:\Users\KTZ\oef-portable')) {
    if (Test-Path $dir) { Remove-Item -Recurse -Force $dir; Write-Host "removed $dir" }
}

Write-Host 'cleanup done'
