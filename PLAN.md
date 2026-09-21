# Plan de desarrollo — OBS Edge Fade

> **Estado:** filtro implementado; pendientes la validación en OBS real y el primer release  
> **Plataforma inicial:** Windows 10/11 x64  
> **OBS objetivo inicial:** OBS Studio 32.2.x (32.2.2 fijado)  
> **Arquitectura:** 1 plugin nativo / 1 filtro de video  
> **Prioridad:** GPU-first, bajo consumo, estabilidad y compatibilidad con la cadena de filtros de OBS  
> **Licencia:** GPL-2.0-or-later

---

# 1. Visión del proyecto

**OBS Edge Fade** es un plugin nativo para OBS Studio que añade **un único filtro de video**:

**Edge Fade** — desvanece progresivamente el alpha de una fuente cerca de uno o varios de sus bordes.

El usuario instala un solo plugin y OBS registra un único filtro. Ese filtro debe poder usarse solo, combinarse con filtros nativos y de terceros, y repetirse en la misma cadena sin efectos secundarios.

Ejemplo de registro:

```text
OBS Edge Fade
└── OBS Edge Fade - Edge Fade
```

Ejemplo de uso:

```text
Webcam
├── Corrección de color (filtro nativo)
└── OBS Edge Fade - Edge Fade
```

---

# 2. Alcance

## 2.1 Dentro de alcance (v1)

El plugin debe:

- instalarse como un único módulo de OBS;
- registrar un único filtro de video;
- desvanecer cada borde de forma independiente o vinculada;
- controlar la transición con suavidad y curva;
- funcionar sobre fuentes de cámara, capturadora, juego, pantalla, navegador, imagen, media y escenas anidadas cuando OBS permita su filtrado;
- mantener la transparencia correctamente;
- funcionar con fuentes que cambian de resolución;
- permitir modificar parámetros en vivo desde las propiedades del filtro;
- guardar y restaurar su configuración dentro de las escenas de OBS;
- soportar cadenas de filtros;
- mantener comportamiento correcto al duplicar fuentes o escenas;
- preservar el color de la fuente;
- liberar todos los recursos gráficos al eliminar el filtro o cerrar OBS.

## 2.2 Fuera de alcance de v1

La primera versión NO debe incluir:

- glow;
- outline;
- chromatic aberration;
- LUT;
- color correction;
- máscaras de imagen;
- animaciones;
- keyframes;
- presets globales complejos;
- interfaz Qt personalizada;
- docks;
- frontend toolbar;
- sistema de cuentas;
- telemetría;
- actualización automática;
- servicios externos.

Estas funciones pueden estudiarse para versiones posteriores sin contaminar la arquitectura inicial.

---

# 3. Estado actual

## 3.1 Lo que ya existe

```text
src/plugin-main.c            registra un único obs_source_info
src/common/                  log, math-utils.h, color-space, shader-loader,
                             obs-edge-fade-common.h
src/edge-fade/               filter + settings + properties
data/effects/                edge-fade.effect (single pass)
data/locale/                 en-US.ini, es-ES.ini
tests/unit/                  test-edge-fade-settings.c
docs/                        arquitectura, pipeline, rendimiento, pruebas
scripts/install-local.ps1    build + instalación local
CMakeLists.txt + presets     windows-x64, windows-ci-x64
buildspec.json               OBS 32.2.2 y obs-deps fijados
.github/                     workflows de build, checks y release
```

## 3.2 Filtro implementado

| Aspecto | Estado |
|---|---|
| Registro del filtro | hecho |
| Settings, defaults y clamp | hecho |
| Propiedades nativas (Properties API) | hecho |
| Shader single-pass | hecho |
| Bypass | hecho |
| Espacios de color | hecho |
| Localización en-US / es-ES | hecho |
| Pruebas unitarias libobs-free | hechas |
| Documentación | hecha |

## 3.3 Pendiente

| Aspecto | Estado |
|---|---|
| Validación visual en un OBS real | pendiente |
| Validación HDR / color spaces en hardware real | pendiente |
| Rendimiento y fugas medidos | pendiente |
| Hardening (resize, duplicado, cierre de OBS, settings corruptos) | pendiente |
| Release 0.1.0 (paquete, notas, checksums, capturas) | pendiente |

El detalle de cada bloque pendiente está en la sección 16 (roadmap).

---

# 4. Decisiones técnicas

Se implementa en **C**, siguiendo de cerca la arquitectura de los filtros nativos de OBS.

Razones:

- libobs expone una API C;
- los filtros oficiales de OBS sirven como referencia directa;
- reduce abstracciones innecesarias;
- minimiza dependencias;
- mantiene el binario pequeño;
- hace más fácil revisar fugas, ciclos de vida y graphics context.

Para v1:

```text
ENABLE_FRONTEND_API = OFF
ENABLE_QT           = OFF
```

El filtro no necesita Qt para mostrar sliders, checkboxes ni listas: usa la Properties API nativa de OBS.

La única dependencia es libobs:

```cmake
find_package(libobs REQUIRED)

target_link_libraries(
    ${CMAKE_PROJECT_NAME}
    PRIVATE
    OBS::libobs
)
```

---

# 5. Arquitectura general

```text
OBS
│
├── libobs
│
│
└── obs-edge-fade.dll
    │
    └── Edge Fade Filter
        └── GPU shader single-pass (edge-fade.effect)
```

Un único módulo, un único filtro, un único efecto.

---

# 6. Registro del plugin

`obs_module_load()` debe ser extremadamente pequeño.

Responsabilidad:

```text
OBS carga DLL
    ↓
obs_module_load()
    ↓
register_edge_fade_filter()
    ↓
return true
```

No debe contener lógica de renderizado.

Implementación conceptual:

```c
bool obs_module_load(void)
{
    obs_register_source(&edge_fade_filter_info);

    oss_log_info("Plugin loaded (version %s)", PLUGIN_VERSION);
    return true;
}
```

`oss_log_info()` ya añade el prefijo `[OBS Edge Fade] `, así que el mensaje no debe repetirlo.

---

# 7. Definición del filtro

El filtro es un:

```c
OBS_SOURCE_TYPE_FILTER
```

y declara como mínimo:

```text
.id
.type
.output_flags
.get_name
.create
.destroy
.update
.get_properties
.get_defaults
.video_render
.video_get_color_space
```

Además:

```text
.get_width
.get_height
```

`get_width`/`get_height` devuelven las dimensiones del target, porque el filtro no cambia el tamaño de la imagen. Deben ser baratas y no ejecutar lógica GPU.

El filtro declara:

```text
OBS_SOURCE_VIDEO
OBS_SOURCE_SRGB
```

Identificadores estables desde el primer commit:

```text
OEF_PLUGIN_ID           "obs-edge-fade"
OEF_FILTER_ID_EDGE_FADE "obs_source_style_edge_fade"
```

El ID del filtro se conserva tal cual para que las escenas que ya lo usaban sigan cargando. No debe cambiarse sin una migración explícita.

---

# 8. Parámetros y settings

## 8.1 Controles

```text
Edge Fade

[ ] Vincular lados

Izquierda       0–1000 px
Derecha         0–1000 px
Superior        0–1000 px
Inferior        0–1000 px

Suavidad        0–100 %

Curva
- Linear
- Smooth
- Soft
```

Todos los textos visibles salen de `obs_module_text()`; no se hardcodea ningún string en `edge-fade-properties.c`.

## 8.2 Settings persistidos

```text
edge_fade.linked
edge_fade.left
edge_fade.right
edge_fade.top
edge_fade.bottom
edge_fade.smoothness
edge_fade.curve
```

Estos nombres viven en las escenas guardadas: no cambian sin migración.

## 8.3 Valores por defecto

```text
linked       true
left         0
right        0
top          0
bottom       0
smoothness   50
curve        Smooth
```

## 8.4 Clamp

Antes de enviar nada a la GPU:

```text
left, right, top, bottom   0 .. OEF_MAX_EDGE_FADE_PX (1000)
smoothness                 0 .. 100
curve                      OEF_EDGE_CURVE_LINEAR .. OEF_EDGE_CURVE_SOFT
```

El clamp protege tanto las propiedades como una escena JSON manipulada a mano.

## 8.5 Modo vinculado

Cuando `Vincular lados` está activo:

- cambiar cualquier lado copia ese valor a los otros tres;
- se detecta qué lado cambió comparando con los settings anteriores;
- no se generan loops de update.

---

# 9. Render

El filtro es **single-pass** y no necesita buffers intermedios.

Flujo:

```text
source texture
      ↓
pixel shader
      ↓
distancia a cada borde
      ↓
factor de fade por borde
      ↓
min(left, right, top, bottom)
      ↓
alpha_original × fade
      ↓
output
```

El mínimo de los cuatro factores es lo que mantiene las esquinas suaves: el borde que más desvanece manda.

## 9.1 Shader

Archivo:

```text
data/effects/edge-fade.effect
```

Uniforms:

```text
image
ViewProj

source_size
fade            (left, right, top, bottom) en píxeles
smoothness      0..1
curve_mode      0 linear, 1 smooth, 2 soft
```

Posiciones:

```text
position = v_in.uv * source_size
```

con origen en la esquina superior izquierda y `y` creciendo hacia abajo. Cada borde se mide como la distancia del píxel a ese borde.

## 9.2 API de OBS

```text
obs_filter_get_target()
obs_source_get_base_width()
obs_source_get_base_height()
obs_source_process_filter_begin_with_color_space()
obs_source_process_filter_end()
```

Se solicita:

```text
OBS_ALLOW_DIRECT_RENDERING
```

porque el filtro:

- no cambia resolución;
- no necesita multipass;
- no necesita buffer intermedio.

---

# 10. Bypass y manejo de errores

El filtro llama a:

```text
obs_source_skip_video_filter()
```

cuando:

- los cuatro lados son `0` (el filtro no puede alterar la imagen);
- el efecto no se pudo cargar;
- no hay target o su tamaño es inválido.

Reglas:

- un shader que falla produce `blog(LOG_ERROR, ...)` y bypass, nunca un frame negro;
- un efecto que no carga produce un warning y bypass;
- ninguna ruta de error debe crashear ni dejar el estado gráfico corrupto.

Logging (siempre con el prefijo `[OBS Edge Fade] `):

```text
[OBS Edge Fade] Plugin loaded (version 0.1.0)
[OBS Edge Fade] Edge Fade effect could not be loaded, filter will bypass
[OBS Edge Fade] Edge Fade effect is missing required parameters, filter will bypass
```

Nunca se registra un log por frame en builds normales.

---

# 11. Espacios de color y HDR

El filtro no asume que todo es `GS_RGBA` SDR.

Se consulta el color space del siguiente elemento de la cadena:

```c
obs_source_t *target = obs_filter_get_target(filter->context);
```

con esta lista de espacios soportados:

```text
GS_CS_SRGB
GS_CS_SRGB_16F
GS_CS_709_EXTENDED
```

Ruta:

```text
obs_source_get_color_space()
        ↓
gs_get_format_from_space()
        ↓
obs_source_process_filter_begin_with_color_space()
```

El filtro implementa:

```text
video_get_color_space
```

para propagar el espacio apropiado.

### Regla de diseño

El filtro modifica **alpha**, no color.

La fuente RGB debe mantenerse intacta siempre.

No se afirmará compatibilidad HDR completa hasta superar las pruebas visuales de la sección 17.7.

---

# 12. Alpha y blending

El filtro conserva la transparencia.

La composición utiliza el estado de blending de la representación premultiplicada de OBS:

```c
gs_blend_state_push();

gs_blend_function(
    GS_BLEND_ONE,
    GS_BLEND_INVSRCALPHA
);

/* draw */

gs_blend_state_pop();
```

Nunca se deja un estado global de blending modificado después del render.

Toda modificación de estado gráfico sigue el patrón:

```text
push
change
render
pop
```

---

# 13. Rendimiento

No se fijan números artificiales como garantía antes de medir. Sí se define un presupuesto.

## 13.1 Presupuesto

```text
1 pass
0 buffers intermedios
0 allocations GPU propias
0 allocations/frame
0 CPU pixel processing
```

El filtro no reserva memoria GPU propia: dibuja en la textura que OBS le entrega para el pass del filtro. El consumo de VRAM no crece con los settings.

## 13.2 Optimizaciones obligatorias

- cachear effect parameters;
- no recrear effects al actualizar sliders;
- no cargar archivos en cada frame;
- no hacer `bmalloc()` por frame;
- no hacer logging por frame;
- no mapear texturas ni leer píxeles de vuelta a la CPU;
- bypass cuando los cuatro lados son `0`.

## 13.3 Herramientas de rendimiento

Primero:

```text
OBS Stats
Task Manager / GPU engine
OBS logs
```

Para análisis detallado:

```text
PIX for Windows
GPUView / ETW
Visual Studio profiler
RenderDoc solo cuando sea compatible y útil
```

No optimizar basándose únicamente en el porcentaje total de GPU del Administrador de tareas.

---

# 14. Estructura del repositorio

```text
obs-edge-fade/
│
├── .github/
│   ├── actions/
│   │   └── build-plugin/
│   └── workflows/
│       ├── build.yml
│       ├── checks.yml
│       └── release.yml
│
├── cmake/
│   ├── common/
│   └── windows/
│
├── data/
│   ├── effects/
│   │   └── edge-fade.effect
│   │
│   └── locale/
│       ├── en-US.ini
│       └── es-ES.ini
│
├── docs/
│   ├── architecture.md
│   ├── rendering-pipeline.md
│   ├── performance.md
│   ├── testing.md
│   ├── manual-test-plan.md
│   ├── test-results-template.md
│   └── release-process.md
│
├── scripts/
│   └── install-local.ps1
│
├── src/
│   ├── plugin-main.c
│   │
│   ├── common/
│   │   ├── obs-edge-fade-common.h
│   │   ├── log.h
│   │   ├── math-utils.h
│   │   ├── color-space.c
│   │   ├── color-space.h
│   │   ├── shader-loader.c
│   │   └── shader-loader.h
│   │
│   └── edge-fade/
│       ├── edge-fade-filter.c
│       ├── edge-fade-filter.h
│       ├── edge-fade-settings.c
│       ├── edge-fade-settings.h
│       ├── edge-fade-properties.c
│       └── edge-fade-properties.h
│
├── tests/
│   ├── unit/
│   │   ├── oss-test.h
│   │   └── test-edge-fade-settings.c
│   │
│   └── fixtures/
│       ├── opaque.png
│       ├── transparency.png
│       └── alpha-shape.png
│
├── CMakeLists.txt
├── CMakePresets.json
├── buildspec.json
├── LICENSE
├── README.md
├── CHANGELOG.md
└── PLAN.md
```

---

# 15. Responsabilidad de `src/common`

## `obs-edge-fade-common.h`

Constantes compartidas mínimas:

- plugin ID;
- filter ID;
- versión;
- límites comunes (`OEF_MAX_EDGE_FADE_PX`);
- enums compartidos (`enum oef_edge_curve`).

No convertirlo en un “god header”.

## `log.h`

Prefijo consistente:

```text
[OBS Edge Fade]
```

Niveles:

```text
LOG_INFO
LOG_WARNING
LOG_ERROR
LOG_DEBUG
```

Los macros `oss_log_*` ya incluyen el prefijo. No imprimir logs por frame.

## `math-utils.h`

Solo matemáticas reutilizables y pequeñas:

- clamp entero en línea (`oss_clampi`), compartido por los ajustes del filtro.

## `color-space.*`

Centralizar:

- espacios soportados;
- consulta del color space del target;
- formato derivado del color space.

## `shader-loader.*`

Centralizar:

- construir la ruta con `obs_module_file`;
- cargar el efecto con `gs_effect_create_from_file`;
- reportar errores y liberar los strings de error;
- devolver `NULL` para que el filtro pueda hacer bypass.

No ocultar todo libobs detrás de wrappers gigantes.

---

# 16. Roadmap

## FASE A — Validación visual en un OBS real

Objetivo:

```text
confirmar que el filtro se ve como se espera
```

Tareas:

- comprobar la orientación de `uv * size` (origen arriba-izquierda, `y` hacia abajo);
- confirmar Izquierda / Derecha / Superior / Inferior;
- validar el modelo de Suavidad y de las tres curvas;
- comprobar que no aparecen líneas de 1 px;
- comprobar que las esquinas con dos lados activos no muestran bandas duras;
- comprobar que el alpha interior no se toca.

Criterio de salida: las secciones 2 y 3 del [plan de pruebas manual](docs/manual-test-plan.md) pasan.

---

## FASE B — Color y HDR

Tareas:

- probar SRGB;
- probar SRGB 16F;
- probar extended 709;
- probar cambios de canvas;
- probar cadenas con filtros nativos HDR;
- corregir cualquier conversión indebida.

Criterio de salida: la sección 6 del plan manual pasa y el RGB de la fuente queda intacto.

---

## FASE C — Rendimiento y fugas

Tareas:

- medir 720p, 1080p, 1440p y 4K;
- medir 30, 60 y 120 FPS;
- stress con 10 fuentes;
- bucle de crear / cambiar settings / eliminar 100+ veces observando memoria CPU, VRAM y handles.

Criterio de salida: un solo pass confirmado, VRAM plana y sin crecimiento de memoria ni handles.

---

## FASE D — Hardening

Pruebas:

- source removal;
- source resize en vivo;
- scene switch;
- duplicate;
- enable/disable;
- cambios rápidos de sliders;
- cierre de OBS;
- reapertura del perfil;
- shader ausente o corrupto;
- settings corruptos en el JSON de la escena.

Criterio de salida: cero crash y cero fugas en todos los casos.

---

## FASE E — Release 0.1.0

Generar:

```text
Windows x64 package
README
CHANGELOG
release notes
checksums
capturas
GitHub Release
```

Criterio de salida: release publicado y reproducible con el proceso de [docs/release-process.md](docs/release-process.md).

---

# 17. Pruebas

## 17.1 Pruebas unitarias

Suite libobs-free en `tests/unit` con el harness `oss-test.h`:

```powershell
cmake -S tests/unit -B build_tests
cmake --build build_tests
ctest --test-dir build_tests --output-on-failure
```

Cubierto:

```text
math-utils.h          clamp entero en línea
edge-fade-settings    defaults, vínculo, clamp, bypass
```

El render GPU requiere pruebas de integración.

## 17.2 Pruebas visuales

Fixtures:

```text
opaque rectangle
transparent circle
checkerboard alpha
thin lines
1px borders
4K image
small 64×64 image
```

Comparar:

```text
expected
vs
render
```

Idealmente almacenar capturas de referencia.

## 17.3 Matriz de resolución

```text
64×64
320×240
640×480
1280×720
1920×1080
2560×1440
3840×2160
```

## 17.4 FPS

```text
30 FPS
60 FPS
120 FPS
```

El plugin no debe contener lógica dependiente del frame rate.

## 17.5 Stress tests

```text
10 fuentes × Edge Fade
Edge Fade combinado con filtros nativos en varias escenas
```

Medir:

- GPU frame time;
- rendering lag;
- VRAM;
- estabilidad;
- crecimiento de memoria.

## 17.6 Prueba de fugas

Secuencia repetida 100+ veces:

```text
crear filtro
cambiar settings
eliminar filtro
```

Verificar: memoria CPU, VRAM, handles y effects.

## 17.7 Color y HDR

```text
SDR source → SDR canvas
SDR source → HDR canvas
HDR source → HDR canvas
cadenas con filtros nativos
```

No afirmar compatibilidad HDR completa hasta superar la revisión visual.

---

# 18. Compatibilidad con fuentes

Matriz mínima:

| Fuente | Edge Fade |
|---|---|
| Image | Sí |
| Media Source | Sí |
| Browser | Sí |
| Video Capture | Sí |
| Game Capture | Sí |
| Display Capture | Sí |
| Window Capture | Sí |
| Nested Scene | Sí |
| Transparent PNG | Sí |

“Sí” significa objetivo de compatibilidad, sujeto a las reglas normales de libobs.

---

# 19. Build, CMake y CI

## 19.1 CMake

Mantener el CMake simple.

Raíz:

```text
CMakeLists.txt
CMakePresets.json
buildspec.json
```

Agregar todos los módulos explícitamente con:

```cmake
target_sources(...)
```

Organizar archivos en source groups si ayuda en Visual Studio.

No añadir gestores de paquetes externos para v1.

## 19.2 Build de Windows

```powershell
cmake --preset windows-x64
cmake --build --preset windows-x64 --config RelWithDebInfo
cmake --install build_x64 --config RelWithDebInfo --prefix .\release
```

Objetivo:

```text
Windows x64
Release / RelWithDebInfo
Visual Studio 2022
CMake 3.28+
```

El primer configure descarga las dependencias fijadas y compila libobs, por lo que necesita red.

Para instalar en el OBS local:

```powershell
./scripts/install-local.ps1
```

## 19.3 CI

GitHub Actions ejecuta como mínimo:

```text
configure
build
format check
unit tests
artifact
```

Pull Requests:

```text
build obligatorio
warnings tratados seriamente
```

Release:

```text
tag semver
→ build
→ package
→ draft release
```

---

# 20. Dependencias de OBS

`buildspec.json` fija una versión compatible de OBS:

```text
OBS Studio 32.2.2
obs-deps 2026-07-15
```

Objetivo de compatibilidad:

```text
OBS 32.2.x
Windows 10/11 x64
```

No depender deliberadamente de funciones de master sin necesidad.

Cuando se actualice OBS:

1. elegir versión;
2. actualizar dependency pin;
3. verificar URL usada por el template;
4. verificar SHA256 del mismo artefacto;
5. limpiar `.deps` si corresponde;
6. recompilar;
7. ejecutar la matriz de pruebas.

---

# 21. Convenciones

## 21.1 Política de commits

Cada fase debe producir commits pequeños y verificables.

Ejemplos:

```text
feat(edge-fade): register initial filter
feat(edge-fade): add gpu fade shader
feat(edge-fade): add per-side fade settings
feat(edge-fade): add linked sides mode
feat(edge-fade): add smoothness and curve controls
perf(edge-fade): bypass when all sides are zero
fix(render): preserve premultiplied alpha
docs(edge-fade): document the single-pass pipeline
```

Evitar:

```text
update stuff
changes
final
fix
```

## 21.2 Versionado

SemVer:

```text
0.1.0
0.2.0
0.2.1
1.0.0
```

Antes de 1.0:

```text
API/settings aún pueden cambiar
```

## 21.3 Compatibilidad de settings e IDs

Los IDs de settings y el ID del filtro deben mantenerse estables.

Ejemplo:

```text
edge_fade.smoothness
obs_source_style_edge_fade
```

No cambiarlos después sin migración: las escenas existentes dependen de esos nombres.

## 21.4 Localización

`data/locale/en-US.ini`

y:

`data/locale/es-ES.ini`

Todos los textos visibles deben usar:

```text
obs_module_text()
```

La clave del nombre del filtro es `EdgeFadeFilterName`.

## 21.5 README mínimo

Debe contener:

- qué hace el plugin;
- Windows soportado;
- versión mínima probada de OBS;
- instalación;
- el filtro y sus parámetros;
- capturas;
- troubleshooting;
- build desde source;
- licencia.

---

# 22. Reglas de arquitectura para agentes de desarrollo

1. No crear archivos gigantes.
2. No fusionar features distintas en una sola implementación.
3. No hacer un “universal filter”.
4. No mover procesamiento visual a CPU.
5. No añadir Qt sin una necesidad aprobada.
6. No añadir dependencias externas innecesarias.
7. No duplicar helpers reales.
8. No abstraer prematuramente código que solo usa un módulo.
9. Mantener las APIs de libobs visibles y fáciles de auditar.
10. Cada cambio gráfico debe manejar correctamente el graphics context.
11. Toda creación GPU debe tener destrucción simétrica.
12. Toda modificación de estado gráfico debe restaurarse.
13. Toda ruta de error debe preferir bypass a crash.
14. Ningún log por frame en builds normales.

---

# 23. Criterio de “terminado” para v1

La v1 puede declararse lista únicamente cuando:

### Plugin

- un solo instalable;
- un filtro visible;
- carga limpia;
- descarga limpia.

### Edge Fade

- cuatro lados independientes;
- modo vinculado;
- suavidad;
- tres curvas;
- alpha interior intacto;
- GPU single-pass;
- bypass.

### General

- SDR probado;
- color spaces contemplados;
- alpha correcto;
- 4K probado;
- resize en vivo;
- múltiples fuentes;
- cero crash;
- cero fugas observadas;
- CI verde;
- release x64 generado.

---

# 24. Flujo final esperado

```text
                        ┌──────────────────────┐
                        │     OBS / libobs     │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │      Edge Fade       │
                        │                      │
                        │      1 GPU pass      │
                        └──────────┬───────────┘
                                   │
                                   ▼
                        ┌──────────────────────┐
                        │  compositor de OBS   │
                        └──────────────────────┘
```

---

# 25. Referencias oficiales consultadas

## OBS Studio documentation

- Source API / filtros:  
  https://docs.obsproject.com/reference-sources

- Rendering Graphics:  
  https://docs.obsproject.com/graphics

- Effects / shaders:  
  https://docs.obsproject.com/reference-libobs-graphics-effects

- Properties API:  
  https://docs.obsproject.com/reference-properties

- Graphics API:  
  https://docs.obsproject.com/reference-libobs-graphics

## Código oficial de OBS utilizado como referencia

- Plugin template:  
  https://github.com/obsproject/obs-plugintemplate

- OBS Studio source:  
  https://github.com/obsproject/obs-studio

- `obs-filters`:  
  https://github.com/obsproject/obs-studio/tree/master/plugins/obs-filters

- `scale-filter.c`:  
  https://github.com/obsproject/obs-studio/blob/master/plugins/obs-filters/scale-filter.c

- `scroll-filter.c` — filtro single-pass sencillo:  
  https://github.com/obsproject/obs-studio/blob/master/plugins/obs-filters/scroll-filter.c

## Release objetivo consultado

- OBS Studio 32.2.2:  
  https://github.com/obsproject/obs-studio/releases

- Descarga oficial OBS:  
  https://obsproject.com/download

---

# 26. Resumen técnico definitivo

La arquitectura elegida para OBS Edge Fade es:

```text
1 DLL
1 filtro de video
C + libobs
sin Qt
sin frontend API
sin dependencias externas
GPU-first
```

Render:

```text
Edge Fade
→ shader single-pass
→ alpha × factor de fade
→ sin buffers intermedios
```

La prioridad de desarrollo es:

```text
CORRECTNESS
    ↓
STABILITY
    ↓
GPU PIPELINE
    ↓
MODULARITY
    ↓
PROFILING
    ↓
OPTIMIZATION
```

No se debe sacrificar estabilidad de OBS por intentar ahorrar microsegundos prematuramente.

La v1 debe concentrarse exclusivamente en que **este efecto sea sólido, visualmente correcto, de bajo consumo y fácil de mantener**.
