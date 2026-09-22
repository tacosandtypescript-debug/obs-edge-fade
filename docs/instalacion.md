# Instalar en otro PC

<!-- markdownlint-disable MD013 -->

Requiere **Windows 10/11 x64** y **OBS Studio 32.2.x**. No hace falta compilar
nada ni instalar herramientas: el plugin ya viene compilado.

## 1. Descargar

En el otro PC abre:

<https://github.com/tacosandtypescript-debug/obs-edge-fade/releases/latest>

y baja **`obs-edge-fade-0.2.0-windows-x64.zip`**.

También sirve clonar el repositorio y usar la carpeta `dist/obs-edge-fade`, que
es exactamente lo mismo.

## 2. Descomprimir

Descomprime el ZIP. Dentro hay una única carpeta llamada `obs-edge-fade`.

> **Importante:** lo que se copia es esa carpeta, no los ficheros sueltos. Si
> copias `bin` y `data` directamente en `plugins\`, OBS no encuentra el plugin.

## 3. Copiar a OBS

1. Pulsa `Win + R`, escribe `%ProgramData%\obs-studio\plugins` y pulsa Enter.
   Se abre la carpeta de plugins de OBS (si no existe, créala).
2. Copia dentro la carpeta `obs-edge-fade` completa.
3. Debe quedar exactamente así:

~~~text
%ProgramData%\obs-studio\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\effects\edge-fade.effect
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\locale\en-US.ini
%ProgramData%\obs-studio\plugins\obs-edge-fade\data\locale\es-ES.ini
~~~

Si Windows pide permisos de administrador para escribir ahí, acepta. Si no te
deja, mira la sección "Si no tienes permisos" más abajo.

## 4. Comprobar que quedó bien

Copia y pega esto en PowerShell (no hace falta ser administrador):

~~~powershell
$p = "$env:ProgramData\obs-studio\plugins\obs-edge-fade"
"dll  : " + (Test-Path "$p\bin\64bit\obs-edge-fade.dll")
"data : " + (Test-Path "$p\data\effects\edge-fade.effect")
"locale: " + (Test-Path "$p\data\locale\es-ES.ini")
~~~

Las tres líneas tienen que decir `True`. Si alguna dice `False`, la carpeta está
en el sitio equivocado: revisa el paso 3.

También puedes usar el verificador del repositorio, que además arranca OBS y
confirma que el filtro se registra:

~~~powershell
python tools/install-to-obs.py --dll dist\obs-edge-fade\bin\64bit\obs-edge-fade.dll
~~~

## 5. Reiniciar OBS

Cierra OBS por completo (si estaba abierto) y vuelve a abrirlo. OBS sólo carga
plugins al arrancar.

## 6. Usar el filtro

1. Selecciona una fuente en OBS (una cámara, una imagen, una captura...).
2. Pulsa **Filtros**.
3. Abajo a la izquierda, **+** → **`OBS Edge Fade - Edge Fade`**.
4. Ajusta **Todos los bordes** (con *Vincular* activado) o desmarca *Vincular*
   para controlar cada borde por separado.

## Cómo saber que cargó

En OBS: **Ayuda → Archivos de log → Ver log actual**. Busca `Edge Fade`; debe
aparecer:

~~~text
[OBS Edge Fade] Plugin loaded (version 0.2.0)
~~~

Si en su lugar ves algo como `Failed to load module` o no aparece nada, ve a la
sección de problemas.

## Problemas frecuentes

### El plugin no aparece en la lista de filtros

| Causa | Comprobación |
|---|---|
| La carpeta está en el sitio equivocado | Debe ser `...\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll`. Si tienes `...\plugins\bin\64bit\...` falta el nivel de la carpeta. |
| OBS no se reinició | Ciérralo del todo (revisa que no quede en la bandeja del sistema) y ábrelo otra vez. |
| Versión de OBS distinta | El log dirá algo sobre el módulo. El plugin está compilado contra OBS 32.2.x. |
| OBS en modo seguro | Si OBS arrancó en modo seguro, los plugins de terceros no se cargan. Reinícialo en modo normal. |

### Windows bloqueó el DLL

Si el ZIP se descargó de internet, Windows puede marcarlo. Desbloquéalo:

1. Clic derecho en el ZIP **antes** de descomprimirlo → **Propiedades**.
2. Abajo, marca **Desbloquear** → **Aceptar**.
3. Descomprime otra vez.

Si ya lo descomprimiste, haz lo mismo con `obs-edge-fade.dll`, o en PowerShell:

~~~powershell
Unblock-File "$env:ProgramData\obs-studio\plugins\obs-edge-fade\bin\64bit\obs-edge-fade.dll"
~~~

### Si no tienes permisos para escribir en ProgramData

Instálalo sólo para tu usuario. Copia la carpeta `obs-edge-fade` a:

~~~text
%APPDATA%\obs-studio\plugins\
~~~

OBS lee las dos ubicaciones, así que funciona igual.

### El filtro aparece pero el fade se ve raro

Comprueba el log: si dice `Edge Fade effect could not be loaded, filter will
bypass`, falta el fichero `data\effects\edge-fade.effect`. Suele pasar cuando se
copió sólo el DLL. Copia la carpeta `data` junto a `bin`.

## Desinstalar

Borra la carpeta:

~~~text
%ProgramData%\obs-studio\plugins\obs-edge-fade
~~~

y reinicia OBS. Las escenas que usaban el filtro mostrarán un aviso de filtro
desconocido hasta que lo quites de sus listas de filtros.
