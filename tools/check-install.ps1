# Comprueba que OBS Edge Fade quedó bien instalado, sin arrancar OBS.
#
#   pwsh -NoProfile -File tools/check-install.ps1
#
# Sirve para ejecutarlo en el otro PC después de copiar la carpeta del plugin.
# Comprueba las dos ubicaciones que lee OBS (%ProgramData% y %APPDATA%), que
# estén todos los ficheros y que la versión coincida con la del repositorio.

[CmdletBinding()]
param([string] $ExpectedVersion = '')

$ErrorActionPreference = 'Stop'

$root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
if (-not $ExpectedVersion) {
    $ExpectedVersion = (Get-Content (Join-Path $root 'buildspec.json') -Raw | ConvertFrom-Json).version
}

$locations = @(
    @{ Name = 'todos los usuarios'; Path = Join-Path $env:ProgramData 'obs-studio\plugins\obs-edge-fade' }
    @{ Name = 'solo tu usuario'; Path = Join-Path $env:APPDATA 'obs-studio\plugins\obs-edge-fade' }
)

$required = @(
    'bin\64bit\obs-edge-fade.dll'
    'data\effects\edge-fade.effect'
    'data\locale\en-US.ini'
    'data\locale\es-ES.ini'
)

$found = @()
foreach ($location in $locations) {
    $dll = Join-Path $location.Path 'bin\64bit\obs-edge-fade.dll'
    if (Test-Path $dll) { $found += $location }
}

Write-Host "Buscando OBS Edge Fade $ExpectedVersion"
Write-Host ''

if ($found.Count -eq 0) {
    Write-Host 'RESULTADO: no encontrado.' -ForegroundColor Red
    Write-Host ''
    Write-Host 'Se han mirado estas ubicaciones:'
    foreach ($location in $locations) { Write-Host "  $($location.Path)" }
    Write-Host ''
    Write-Host 'Copia la carpeta obs-edge-fade (la que sale al descomprimir el ZIP)'
    Write-Host 'dentro de una de esas carpetas de plugins, de modo que quede:'
    Write-Host '  <plugins>\obs-edge-fade\bin\64bit\obs-edge-fade.dll'
    exit 1
}

$ok = $true
foreach ($location in $found) {
    Write-Host "Instalación ($($location.Name)): $($location.Path)"

    foreach ($relative in $required) {
        $file = Join-Path $location.Path $relative
        if (Test-Path $file) {
            Write-Host ("  ok    {0} ({1} bytes)" -f $relative, (Get-Item $file).Length)
        }
        else {
            Write-Host "  FALTA $relative" -ForegroundColor Red
            $ok = $false
        }
    }

    # El log de OBS es la prueba de que el plugin se carga de verdad.
    $logs = Join-Path $env:APPDATA 'obs-studio\logs'
    if (Test-Path $logs) {
        $latest = Get-ChildItem $logs -Filter '*.txt' | Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($latest) {
            $line = Select-String -Path $latest.FullName -Pattern '\[OBS Edge Fade\] Plugin loaded' |
                Select-Object -Last 1
            if ($line) {
                Write-Host "  log   $($line.Line.Trim())"
                if ($line.Line -notmatch [regex]::Escape($ExpectedVersion)) {
                    Write-Host "        (el repositorio tiene la $ExpectedVersion; puede ser una copia antigua)" -ForegroundColor Yellow
                }
            }
            else {
                Write-Host '  log   sin linea de carga todavia: abre OBS una vez y vuelve a ejecutar esto'
            }
        }
    }
    Write-Host ''
}

if ($ok) {
    Write-Host 'RESULTADO: instalado correctamente.' -ForegroundColor Green
    Write-Host 'Abre OBS y usa Filtros > + > "OBS Edge Fade - Edge Fade".'
    exit 0
}

Write-Host 'RESULTADO: faltan ficheros.' -ForegroundColor Red
Write-Host 'Vuelve a copiar la carpeta obs-edge-fade completa (bin y data).'
exit 1
