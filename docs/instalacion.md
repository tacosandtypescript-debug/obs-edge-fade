# Instalar en otro PC

<!-- markdownlint-disable MD013 -->

Requiere **Windows 10/11 x64** y **OBS Studio 32.2.x**. No hace falta compilar
nada ni tener ninguna herramienta instalada.

Hay dos formas. La primera es la recomendada.

## Opción A: el instalador (recomendado)

### 1. Descargar

En el otro PC abre:

<https://github.com/tacosandtypescript-debug/obs-edge-fade/releases/latest>

y baja **`OBS-Edge-Fade-Setup-0.2.0.exe`**.

### 2. Ejecutarlo

Doble clic. No hace falta ejecutar como administrador: el instalador escribe en
la carpeta de plugins de OBS, que es escribible por usuarios normales. Si en tu
equipo hiciera falta, te pedirá permisos él solo.

### 3. Pulsar "Instalar"

La ventana hace todo y va contando lo que hace:

~~~text
OBS Edge Fade 0.2.0 - installer

OBS found: C:\Program Files\obs-studio\bin\64bit\obs64.exe
Target:   C:\ProgramData\obs-studio\plugins\obs-edge-fade (OBS plugins folder)

  wrote bin\64bit\obs-edge-fade.dll (17920 bytes)
  wrote data\effects\edge-fade.effect (4477 bytes)
  wrote data\locale\en-US.ini (431 bytes)
  wrote data\locale\es-ES.ini (482 bytes)

Installed and verified.
~~~

El instalador localiza OBS, elige la carpeta correcta, copia los ficheros y
**comprueba byte a byte** lo que acaba de escribir. Si algo falla, lo dice.

Si OBS estaba abierto, te ofrecerá cerrarlo. Sólo carga plugins al arrancar, así
que hay que reiniciarlo (guarda antes cualquier grabación en curso).

### 4. Usar el filtro

Abre OBS, selecciona una fuente, pulsa **Filtros**, y abajo a la izquierda
**+** → **`OBS Edge Fade - Edge Fade`**.

Ajusta **Todos los bordes** con *Vincular* activado, o desmarca *Vincular* para
controlar cada borde por separado.

### Desinstalar

Vuelve a ejecutar el mismo `.exe` con:

~~~powershell
.\OBS-Edge-Fade-Setup-0.2.0.exe /uninstall
~~~

O abre el instalador y usa el mismo botón, que en modo desinstalación borra la
carpeta. También hay modo silencioso, útil para automatizar:

~~~powershell
.\OBS-Edge-Fade-Setup-0.2.0.exe /silent            # instalar sin ventana
.\OBS-Edge-Fade-Setup-0.2.0.exe /silent /uninstall # desinstalar sin ventana
~~~

El código de salida es `0` si fue bien.

## Opción B: a mano, con el ZIP

Si prefieres no ejecutar un `.exe`, baja
`obs-edge-fade-0.2.0-windows-x64.zip` del mismo release:

1. Descomprímelo. Dentro hay una carpeta llamada `obs-edge-fade`.
2. Pulsa `Win + R`, escribe `%ProgramData%\obs-studio\plugins` y Enter.
3. Copia ahí la carpeta `obs-edge-fade` completa.

> **El error más común:** lo que se copia es **esa carpeta**, no los ficheros de
> dentro. Si copias `bin` y `data` sueltos en `plugins\`, OBS no encuentra nada.

Debe quedar exactamente así:

~~~text
%ProgramData%\obs-studio\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\effects\edge-fade.effect
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\locale\en-US.ini
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\locale\es-ES.ini
~~~

Reinicia OBS.

## Comprobar que quedó bien

Sin abrir OBS, pega esto en PowerShell:

~~~powershell
$p = "$env:ProgramData\obs-studio\plugins\obs-edge-fade"
"dll  : " + (Test-Path "$p\bin\64bit\obs-edge-fade.dll")
"data : " + (Test-Path "$p\data\effects\edge-fade.effect")
~~~

Las dos líneas deben decir `True`.

Si clonaste el repositorio en esa PC, hay un comprobador más completo que
además lee el log de OBS:

~~~powershell
pwsh -File tools/check-install.ps1
~~~

## Cómo saber que OBS lo cargó

En OBS: **Ayuda → Archivos de log → Ver log actual**. Busca `Edge Fade`; debe
aparecer:

~~~text
[OBS Edge Fade] Plugin loaded (version 0.2.0)
~~~

## Problemas frecuentes

### El plugin no aparece en la lista de filtros

| Causa | Comprobación |
|---|---|
| OBS no se reinició | Ciérralo del todo (mira que no quede en la bandeja del sistema) y ábrelo otra vez. |
| La carpeta está un nivel mal | Debe ser `...\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll`, no `...\plugins\bin\64bit\...`. |
| OBS en modo seguro | En modo seguro no se cargan plugins de terceros. Reinícialo en modo normal. |
| Versión de OBS distinta | El plugin está compilado contra OBS 32.2.x. Otra versión puede necesitar recompilarlo. |

### Windows bloqueó el fichero

Si Windows marca el `.exe` o el ZIP como descargado de internet:

1. Clic derecho → **Propiedades**.
2. Abajo, marca **Desbloquear** → **Aceptar**.

O en PowerShell:

~~~powershell
Unblock-File .\OBS-Edge-Fade-Setup-0.2.0.exe
~~~

### El filtro aparece pero el fade se ve raro

Comprueba el log: si dice `Edge Fade effect could not be loaded, filter will
bypass`, falta `data\effects\edge-fade.effect`. Pasa cuando se copió sólo el
DLL. Vuelve a instalar con el instalador, que copia la carpeta completa.

### No hay permisos para escribir en ProgramData

Usa la carpeta por usuario. Copia `obs-edge-fade` a:

~~~text
%APPDATA%\obs-studio\plugins\
~~~

OBS lee las dos ubicaciones, así que funciona igual.

## Cómo está hecho el instalador

Por si quieres regenerarlo:

- `installer/Installer.cs` — el instalador. Un único ejecutable .NET sin
  dependencias: usa el .NET Framework que ya viene con Windows.
- `tools/make-installer-payload.ps1` — genera `installer/Payload.g.cs` con los
  ficheros del plugin.
- `tools/make-icon.ps1` — genera el icono.
- `tools/build-installer.ps1` — compila el `.exe`.
- `tools/package-release.ps1` — hace el ZIP y el `.exe` de una vez.

~~~powershell
pwsh -File tools/package-release.ps1
~~~

Los ficheros del plugin van **dentro** del `.exe`, así que no puede desincronizarse
con lo que hay en `dist/`: cada compilación los vuelve a leer.
