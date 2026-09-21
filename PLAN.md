# Plan maestro de desarrollo — OBS Source Style

> **Estado:** Planeación técnica completa  
> **Plataforma inicial:** Windows 10/11 x64  
> **OBS objetivo inicial:** OBS Studio 32.2.x  
> **Arquitectura:** 1 plugin nativo / 3 filtros de video independientes  
> **Prioridad:** GPU-first, bajo consumo, modularidad, estabilidad y compatibilidad con la cadena de filtros de OBS

---

## 1. Visión del proyecto

**OBS Source Style** será un plugin nativo para OBS Studio que añade tres filtros visuales independientes:

1. **Edge Fade** — desvanece progresivamente uno o varios bordes de una fuente.
2. **Rounded Corners** — redondea las cuatro esquinas de una fuente.
3. **Drop Shadow** — genera una sombra externa configurable alrededor de una fuente.

El usuario instala **un solo plugin**, pero OBS registra **tres filtros distintos**. Cada filtro debe poder usarse por separado, combinarse con los otros dos o coexistir con filtros nativos y de terceros.

Ejemplo:

```text
OBS Source Style
├── OBS Style - Edge Fade
├── OBS Style - Rounded Corners
└── OBS Style - Drop Shadow
```

Ejemplo de uso:

```text
Webcam
├── OBS Style - Edge Fade
├── OBS Style - Rounded Corners
└── OBS Style - Drop Shadow
```

No existe dependencia funcional obligatoria entre los filtros.

---

# 2. Objetivos principales

## 2.1 Objetivos funcionales

El plugin debe:

- instalarse como un único módulo de OBS;
- registrar tres filtros de video independientes;
- funcionar sobre fuentes de cámara, capturadora, juego, pantalla, navegador, imagen, media y escenas anidadas cuando OBS permita su filtrado;
- mantener transparencia correctamente;
- funcionar con fuentes que cambian de resolución;
- permitir modificar parámetros en vivo desde las propiedades del filtro;
- guardar y restaurar la configuración de cada filtro dentro de las escenas de OBS;
- soportar cadenas de filtros;
- mantener comportamiento correcto al duplicar fuentes o escenas;
- preservar el color de la fuente;
- evitar recortes visuales no deseados;
- liberar todos los recursos gráficos al eliminar el filtro o cerrar OBS.

## 2.2 Objetivos técnicos

La versión 1 debe:

- usar **libobs** directamente;
- realizar el procesamiento visual en **GPU**;
- evitar procesamiento de píxeles en CPU;
- evitar transferencias GPU → CPU → GPU;
- evitar Qt;
- evitar `obs-frontend-api` mientras no sea necesario;
- evitar dependencias externas;
- usar la Properties API nativa de OBS;
- usar shaders `.effect`;
- reutilizar render targets;
- evitar asignaciones dinámicas de memoria por frame;
- soportar correctamente el graphics context de OBS;
- respetar espacios de color compatibles;
- manejar alpha premultiplicado de forma correcta;
- aplicar bypass cuando un filtro no necesita procesamiento.

---

# 3. Fuera de alcance de v1

La primera versión NO debe incluir:

- glow;
- outline;
- inner shadow;
- background blur;
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

# 4. Decisión tecnológica

## 4.1 Lenguaje

Se recomienda implementar la primera versión en **C**, siguiendo de cerca la arquitectura de los filtros nativos de OBS.

Razones:

- libobs expone una API C;
- los filtros oficiales de OBS sirven como referencia directa;
- reduce abstracciones innecesarias;
- minimiza dependencias;
- facilita comparar nuestra implementación con filtros oficiales;
- mantiene el binario pequeño;
- hace más fácil revisar fugas, ciclos de vida y graphics context.

No se prohíbe C++ en el futuro, pero **v1 no lo necesita**.

---

# 5. Base oficial de OBS

El proyecto debe partir del repositorio oficial:

```text
obsproject/obs-plugintemplate
```

El template oficial incluye:

- boilerplate del módulo;
- CMake;
- presets;
- integración de libobs;
- workflows de GitHub Actions;
- empaquetado de releases.

Para Windows, el template oficial mantiene soporte de compilación con Visual Studio y CMake.

La dependencia principal del proyecto será:

```cmake
find_package(libobs REQUIRED)

target_link_libraries(
    ${CMAKE_PROJECT_NAME}
    PRIVATE
    OBS::libobs
)
```

Para v1:

```text
ENABLE_FRONTEND_API = OFF
ENABLE_QT           = OFF
```

El plugin no necesita Qt para mostrar sliders, checkboxes, listas o controles de color.

---

# 6. Arquitectura general

```text
OBS
│
├── libobs
│
│
└── obs-source-style.dll
    │
    ├── Edge Fade Filter
    │   └── GPU shader
    │
    ├── Rounded Corners Filter
    │   └── GPU shader
    │
    └── Drop Shadow Filter
        ├── Source capture GPU texture
        ├── Shadow alpha/mask pass
        ├── Horizontal blur pass
        ├── Vertical blur pass
        └── Composite pass
```

---

# 7. Registro del plugin

`obs_module_load()` debe ser extremadamente pequeño.

Responsabilidad:

```text
OBS carga DLL
    ↓
obs_module_load()
    ↓
register_edge_fade_filter()
register_rounded_corners_filter()
register_drop_shadow_filter()
    ↓
return true
```

No debe contener lógica de renderizado.

Ejemplo conceptual:

```c
bool obs_module_load(void)
{
    obs_register_source(&edge_fade_filter_info);
    obs_register_source(&rounded_corners_filter_info);
    obs_register_source(&drop_shadow_filter_info);

    blog(LOG_INFO, "[OBS Source Style] loaded");
    return true;
}
```

---

# 8. Definición de los filtros

Cada filtro será un:

```c
OBS_SOURCE_TYPE_FILTER
```

y tendrá como mínimo:

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

Cuando sea necesario también:

```text
.video_tick
.get_width
.get_height
```

Los filtros de video deben declarar:

```text
OBS_SOURCE_VIDEO
```

y la implementación debe contemplar:

```text
OBS_SOURCE_SRGB
```

cuando corresponda al camino de color elegido.

---

# 9. Graphics context

Las funciones de gráficos de OBS solo pueden utilizarse dentro de un graphics context válido.

OBS ya entra automáticamente en el graphics context durante:

```text
obs_source_info.video_render
```

Por lo tanto, dentro de `video_render()` no se debe envolver innecesariamente cada operación en:

```c
obs_enter_graphics();
obs_leave_graphics();
```

Sin embargo, creación y destrucción de recursos gráficos fuera del callback de render sí debe hacerse correctamente:

```c
obs_enter_graphics();

effect = gs_effect_create_from_file(...);

obs_leave_graphics();
```

y:

```c
obs_enter_graphics();

gs_effect_destroy(effect);

obs_leave_graphics();
```

La misma regla se aplica a:

- `gs_texrender_t`;
- samplers;
- texturas;
- otros recursos GPU.

---

# 10. Carga de shaders

Los shaders se almacenarán dentro de los datos del módulo.

Ruta conceptual:

```text
data/effects/
```

Se localizarán mediante:

```c
char *path = obs_module_file("effects/edge-fade.effect");
```

Luego:

```c
gs_effect_create_from_file(path, &error);
```

Los parámetros se resolverán una sola vez al crear el filtro:

```c
gs_effect_get_param_by_name(...)
```

No se debe llamar repetidamente a `gs_effect_get_param_by_name()` en cada frame si el parámetro puede cachearse.

---

# 11. Política GPU-first

## Prohibido en el camino normal de render

```text
gs_texture_map()
copiar frame a RAM
procesar píxeles con CPU
volver a subir textura
```

El flujo normal debe ser:

```text
OBS source
    ↓
GPU texture
    ↓
shader / render target
    ↓
GPU texture
    ↓
OBS compositor
```

El CPU solo debe:

- leer settings;
- calcular parámetros pequeños;
- actualizar uniforms;
- calcular dimensiones;
- administrar lifecycle;
- registrar mensajes;
- controlar bypass.

---

# 12. Espacios de color y HDR

El filtro no debe asumir que todo es `GS_RGBA` SDR.

Se debe consultar el color space del siguiente elemento de la cadena:

```c
obs_source_t *target = obs_filter_get_target(filter->context);
```

y usar una lista de espacios soportados similar a filtros nativos actuales:

```c
GS_CS_SRGB
GS_CS_SRGB_16F
GS_CS_709_EXTENDED
```

La ruta recomendada para filtros simples será:

```text
obs_source_get_color_space()
        ↓
gs_get_format_from_space()
        ↓
obs_source_process_filter_begin_with_color_space()
```

Cada filtro debe implementar:

```text
video_get_color_space
```

para propagar el espacio apropiado.

### Regla de diseño

Los filtros deben modificar principalmente **alpha/geometría visual**, no hacer corrección de color.

La fuente RGB debe mantenerse intacta siempre que sea posible.

---

# 13. Alpha y blending

Los filtros deben conservar transparencia.

La composición debe utilizar un estado de blending apropiado para la representación de OBS, siguiendo patrones de filtros oficiales:

```c
gs_blend_state_push();

gs_blend_function(
    GS_BLEND_ONE,
    GS_BLEND_INVSRCALPHA
);

/* draw */

gs_blend_state_pop();
```

Nunca dejar un estado global de blending modificado después del render.

Toda modificación de estado gráfico debe seguir el patrón:

```text
push
change
render
pop
```

---

# 14. FILTRO 1 — Edge Fade

## 14.1 Objetivo

Reducir progresivamente el alpha de la fuente cerca de sus bordes.

Ejemplo:

```text
Original
██████████████████
██████████████████
██████████████████

Edge Fade
░▒▓████████████▓▒░
░▒▓████████████▓▒░
░▒▓████████████▓▒░
```

---

## 14.2 Controles

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

Los límites finales pueden ajustarse durante pruebas de UX.

---

## 14.3 Settings

```text
edge_fade.linked
edge_fade.left
edge_fade.right
edge_fade.top
edge_fade.bottom
edge_fade.smoothness
edge_fade.curve
```

---

## 14.4 Render

Este filtro debe ser **single-pass**.

Flujo:

```text
source texture
      ↓
pixel shader
      ↓
calcular distancia a cada borde
      ↓
calcular factor de fade
      ↓
combinar los cuatro factores
      ↓
alpha_original × fade
      ↓
output
```

No requiere render targets adicionales.

---

## 14.5 API de OBS

Usar:

```text
obs_filter_get_target()
obs_source_get_base_width()
obs_source_get_base_height()
obs_source_process_filter_begin_with_color_space()
obs_source_process_filter_end()
```

Cuando sea posible:

```text
OBS_ALLOW_DIRECT_RENDERING
```

porque el filtro:

- no cambia resolución;
- no necesita acceso multipass;
- no necesita buffer intermedio.

---

## 14.6 Shader

Archivo:

```text
data/effects/edge-fade.effect
```

Uniforms sugeridos:

```text
image
ViewProj

source_size
source_size_inv

fade_left
fade_right
fade_top
fade_bottom

smoothness
curve_mode
```

---

## 14.7 Bypass

Si:

```text
left   == 0
right  == 0
top    == 0
bottom == 0
```

el filtro debe evitar trabajo visual innecesario.

Cuando OBS permita bypass del filtro, utilizar:

```text
obs_source_skip_video_filter()
```

---

## 14.8 Criterios de aceptación

- no cambia tamaño de la fuente;
- no altera RGB visible;
- alpha interior permanece intacto;
- cada borde funciona independientemente;
- vincular lados funciona;
- no aparecen líneas de 1 px;
- no hay parpadeo al modificar sliders;
- funciona en 720p, 1080p, 1440p y 4K;
- funciona con fuentes transparentes;
- coste GPU objetivo: mínimo / un solo pass.

---

# 15. FILTRO 2 — Rounded Corners

## 15.1 Objetivo

Aplicar una máscara de rectángulo redondeado directamente mediante shader.

No usar:

- PNG;
- máscaras externas;
- texturas auxiliares;
- CPU.

---

## 15.2 Controles

```text
Rounded Corners

[✓] Vincular esquinas

Radio general

Superior izquierda
Superior derecha
Inferior izquierda
Inferior derecha

Suavidad / Antialiasing
```

---

## 15.3 Settings

```text
rounded.linked
rounded.radius_all
rounded.radius_tl
rounded.radius_tr
rounded.radius_bl
rounded.radius_br
rounded.softness
```

---

## 15.4 Render

Single-pass.

```text
source texture
       ↓
UV / pixel coordinates
       ↓
signed distance to rounded rectangle
       ↓
anti-aliased alpha mask
       ↓
source alpha × mask
       ↓
output
```

---

## 15.5 Técnica recomendada

Usar una función matemática de **signed distance field (SDF)** para rectángulo con radios por esquina.

Ventajas:

- ninguna textura de máscara;
- radios modificables en tiempo real;
- antialiasing controlable;
- un solo fragment shader;
- bajo consumo de VRAM;
- resolución independiente.

---

## 15.6 Clamping

Los radios no deben superar valores geométricamente inválidos.

Antes de enviar uniforms:

```text
max_radius <= min(width, height) / 2
```

Si los radios individuales interfieren entre sí, el módulo matemático debe normalizarlos.

No permitir artefactos cuando:

```text
radius_tl + radius_tr > width
```

o equivalentes verticales.

---

## 15.7 API de OBS

Igual que Edge Fade:

```text
obs_source_process_filter_begin_with_color_space()
OBS_ALLOW_DIRECT_RENDERING
obs_source_process_filter_end()
```

El filtro no necesita cambiar tamaño.

---

## 15.8 Shader

```text
data/effects/rounded-corners.effect
```

Uniforms:

```text
image
ViewProj

source_size
source_size_inv

radius_tl
radius_tr
radius_bl
radius_br

softness
```

---

## 15.9 Bypass

Si los cuatro radios son `0`:

```text
obs_source_skip_video_filter()
```

---

## 15.10 Criterios de aceptación

- bordes limpios;
- antialiasing sin dientes;
- radios independientes;
- cambio instantáneo;
- transparencia correcta;
- no cambia resolución;
- no distorsiona imagen;
- no usa buffers intermedios;
- un solo pass de GPU.

---

# 16. FILTRO 3 — Drop Shadow

Este será el módulo técnicamente más complejo.

---

## 16.1 Objetivo

Generar una sombra externa basada en el alpha real de la fuente.

Debe funcionar correctamente con:

- imágenes rectangulares;
- imágenes transparentes;
- cámaras ya recortadas;
- Rounded Corners aplicado antes;
- Edge Fade aplicado antes;
- fuentes browser con alpha.

La sombra debe seguir el alpha que recibe dentro de la cadena.

---

## 16.2 Controles

```text
Drop Shadow

Color
Opacidad       0–100 %

Modo de posición:
- Ángulo + Distancia
- Offset X/Y

Ángulo         0–360°
Distancia      0–500 px

Offset X       -500–500 px
Offset Y       -500–500 px

Blur           0–200 px
Spread         0–100 px

Calidad
- Performance
- Balanced
- High
```

La versión inicial puede ocultar `Calidad` hasta que el algoritmo esté validado.

---

# 17. Problema fundamental de Drop Shadow

Una sombra existe fuera de los límites originales.

Ejemplo:

```text
Original:
┌──────────────┐
│    source    │
└──────────────┘

Con sombra:
┌──────────────┐
│    source    │▒▒
└──────────────┘▒▒
  ▒▒▒▒▒▒▒▒▒▒▒▒▒▒
```

Si el output conserva exactamente el tamaño original, la sombra será recortada.

Por ello Drop Shadow deberá poder reportar una salida mayor mediante:

```text
.get_width
.get_height
```

siguiendo el patrón de filtros nativos que modifican dimensiones.

---

# 18. Padding de sombra

Calcular cuatro paddings:

```text
padding_left
padding_right
padding_top
padding_bottom
```

Basados en:

```text
blur radius
spread
offset_x
offset_y
```

Conceptualmente:

```text
base_padding = blur_extent + spread

left   = base_padding + max(0, -offset_x)
right  = base_padding + max(0,  offset_x)
top    = base_padding + max(0, -offset_y)
bottom = base_padding + max(0,  offset_y)
```

La fórmula exacta se validará con el kernel real del blur.

Salida:

```text
output_width =
    source_width +
    padding_left +
    padding_right

output_height =
    source_height +
    padding_top +
    padding_bottom
```

---

# 19. Coordenadas de Drop Shadow

La imagen original debe desplazarse dentro del nuevo canvas:

```text
source_origin_x = padding_left
source_origin_y = padding_top
```

La sombra:

```text
shadow_origin_x =
    padding_left + offset_x

shadow_origin_y =
    padding_top + offset_y
```

Esto debe formar parte de un módulo dedicado de layout.

No mezclar esta lógica directamente en el shader.

---

# 20. Pipeline GPU de Drop Shadow

Pipeline recomendado:

```text
NEXT FILTER / SOURCE
        ↓
[Pass 0] Capture source to GPU texture
        ↓
source_rt
        ↓
[Pass 1] Generate alpha/spread mask
        ↓
mask_rt
        ↓
[Pass 2] Horizontal blur
        ↓
blur_a_rt
        ↓
[Pass 3] Vertical blur
        ↓
blur_b_rt
        ↓
[Pass 4] Composite
        ├── shadow texture
        └── original source
        ↓
OBS output
```

Todo permanece en GPU.

---

# 21. Captura GPU de la entrada

Para el filtro multipass se necesita una textura del resultado del siguiente elemento de la cadena.

Usar:

```text
obs_filter_get_target()
```

El target representa el siguiente elemento de la cadena de filtros.

El patrón debe inspirarse en filtros oficiales que capturan una fuente mediante:

```text
gs_texrender_reset()
gs_texrender_begin_with_color_space()
gs_clear()
gs_ortho()
obs_source_video_render()
gs_texrender_end()
gs_texrender_get_texture()
```

Se debe diferenciar correctamente entre:

- parent;
- target;
- custom draw;
- async source.

No llamar directamente al parent de forma que se vuelva a ejecutar el filtro y cree recursión.

---

# 22. Render targets

Drop Shadow utilizará objetos reutilizables:

```text
gs_texrender_t *source_rt;
gs_texrender_t *mask_rt;
gs_texrender_t *blur_rt_a;
gs_texrender_t *blur_rt_b;
```

No recrearlos por frame.

Solo recrear almacenamiento interno cuando:

- cambia width;
- cambia height;
- cambia color format;
- cambia color space de una forma que requiera otro formato.

`gs_texrender_begin()` ya puede reutilizar el target mientras la dimensión sea la misma.

Siempre ejecutar:

```text
gs_texrender_reset()
```

antes de reutilizar el texrender para un nuevo frame.

---

# 23. Blur

## 23.1 Prohibido

No usar un kernel 2D enorme como:

```text
31 × 31
```

porque multiplicaría muestras por píxel.

---

## 23.2 Estrategia

Usar **blur separable**:

```text
Horizontal blur
+
Vertical blur
```

Complejidad aproximada:

```text
O(2N)
```

frente a:

```text
O(N²)
```

de un kernel bidimensional equivalente.

---

# 24. Optimización futura del blur

La arquitectura debe permitir posteriormente:

### Opción A — Gaussian separable

Máxima fidelidad.

### Opción B — Dual Kawase

Adecuado para radios grandes y potencialmente más eficiente.

### Opción C — Downsampled blur

Para radios altos:

```text
mask
 ↓
downsample
 ↓
blur
 ↓
upsample
 ↓
composite
```

La v1 debe priorizar corrección visual y después medir.

No elegir algoritmos más complejos sin profiling.

---

# 25. Spread

`Spread` debe expandir el alpha antes del blur.

No debe implementarse como un blur adicional.

Opciones:

- SDF / distancia aproximada;
- max sampling reducido;
- transformación matemática de máscara.

La estrategia final debe priorizar:

```text
calidad
+
pocas muestras
+
estabilidad
```

---

# 26. Casos rápidos de Drop Shadow

Implementar fast paths.

## Caso 1

```text
opacity == 0
```

Resultado:

```text
bypass completo
```

## Caso 2

```text
blur == 0
spread == 0
```

No ejecutar los passes de blur.

## Caso 3

```text
blur == 0
spread > 0
```

Solo mask/spread + composite.

## Caso 4

```text
blur > 0
```

Ejecutar pipeline completo.

---

# 27. Color de sombra

El shadow shader utilizará:

```text
shadow_color.rgb
shadow_opacity
mask_alpha
```

La sombra no debe alterar los colores de la fuente original.

---

# 28. Efectos `.effect`

Estructura:

```text
data/
└── effects/
    ├── edge-fade.effect
    ├── rounded-corners.effect
    ├── shadow-mask.effect
    ├── blur-horizontal.effect
    ├── blur-vertical.effect
    └── shadow-composite.effect
```

Si posteriormente se demuestra que H/V blur puede compartir un mismo shader parametrizado, se puede reducir a:

```text
blur.effect
```

No fusionar todos los efectos en un único archivo gigante.

---

# 29. Estructura completa del repositorio

```text
obs-source-style/
│
├── .github/
│   ├── actions/
│   └── workflows/
│       ├── build.yml
│       ├── checks.yml
│       └── release.yml
│
├── cmake/
│   └── ...
│
├── data/
│   ├── effects/
│   │   ├── edge-fade.effect
│   │   ├── rounded-corners.effect
│   │   ├── shadow-mask.effect
│   │   ├── blur.effect
│   │   └── shadow-composite.effect
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
│   └── release-process.md
│
├── src/
│   ├── plugin-main.c
│   │
│   ├── common/
│   │   ├── obs-style-common.h
│   │   ├── log.h
│   │   ├── math-utils.c
│   │   ├── math-utils.h
│   │   ├── color-space.c
│   │   ├── color-space.h
│   │   ├── shader-loader.c
│   │   ├── shader-loader.h
│   │   ├── render-target.c
│   │   ├── render-target.h
│   │   ├── filter-dimensions.c
│   │   └── filter-dimensions.h
│   │
│   ├── edge-fade/
│   │   ├── edge-fade-filter.c
│   │   ├── edge-fade-filter.h
│   │   ├── edge-fade-settings.c
│   │   ├── edge-fade-settings.h
│   │   ├── edge-fade-properties.c
│   │   └── edge-fade-properties.h
│   │
│   ├── rounded-corners/
│   │   ├── rounded-corners-filter.c
│   │   ├── rounded-corners-filter.h
│   │   ├── rounded-corners-settings.c
│   │   ├── rounded-corners-settings.h
│   │   ├── rounded-corners-properties.c
│   │   └── rounded-corners-properties.h
│   │
│   └── drop-shadow/
│       ├── drop-shadow-filter.c
│       ├── drop-shadow-filter.h
│       ├── drop-shadow-settings.c
│       ├── drop-shadow-settings.h
│       ├── drop-shadow-properties.c
│       ├── drop-shadow-properties.h
│       ├── drop-shadow-layout.c
│       ├── drop-shadow-layout.h
│       ├── drop-shadow-renderer.c
│       └── drop-shadow-renderer.h
│
├── tests/
│   ├── unit/
│   │   ├── test-math-utils.c
│   │   ├── test-rounded-radii.c
│   │   ├── test-edge-fade-settings.c
│   │   └── test-shadow-layout.c
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

# 30. Responsabilidad de `src/common`

## `obs-style-common.h`

Constantes compartidas mínimas:

- plugin ID;
- versión;
- macros;
- límites comunes.

No convertirlo en un “god header”.

---

## `log.h`

Prefijo consistente:

```text
[OBS Source Style]
```

Niveles:

```text
LOG_INFO
LOG_WARNING
LOG_ERROR
LOG_DEBUG
```

No imprimir logs por frame.

---

## `math-utils.*`

Solo matemáticas reutilizables:

- clamp;
- grados → radianes;
- angle/distance → X/Y;
- normalización;
- helpers de radios.

---

## `color-space.*`

Centralizar:

- preferred spaces;
- consulta del target;
- format derivado del color space;
- helpers reutilizados por los tres filtros.

---

## `shader-loader.*`

Centralizar:

- construir ruta con `obs_module_file`;
- cargar efecto;
- reportar errores;
- liberar error strings.

No ocultar todo libobs detrás de wrappers gigantes.

---

## `render-target.*`

Wrapper pequeño para:

```text
create
destroy
reset
ensure format
get texture
```

Solo usado donde aporte claridad.

Principal consumidor: Drop Shadow.

---

## `filter-dimensions.*`

Helpers de:

- dimensiones válidas;
- padding;
- overflow;
- límites máximos;
- escalado seguro.

---

# 31. Separación por feature

Cada feature debe contener:

```text
filter
settings
properties
```

y Drop Shadow además:

```text
layout
renderer
```

Esto permite trabajar en cada filtro sin modificar los demás.

---

# 32. Estructuras internas sugeridas

## Edge Fade

```c
struct edge_fade_filter {
    obs_source_t *context;

    gs_effect_t *effect;

    gs_eparam_t *param_image;
    gs_eparam_t *param_source_size;
    gs_eparam_t *param_fades;
    gs_eparam_t *param_smoothness;
    gs_eparam_t *param_curve;

    struct edge_fade_settings settings;
};
```

---

## Rounded Corners

```c
struct rounded_corners_filter {
    obs_source_t *context;

    gs_effect_t *effect;

    gs_eparam_t *param_image;
    gs_eparam_t *param_source_size;
    gs_eparam_t *param_radii;
    gs_eparam_t *param_softness;

    struct rounded_corners_settings settings;
};
```

---

## Drop Shadow

```c
struct drop_shadow_filter {
    obs_source_t *context;

    struct drop_shadow_settings settings;
    struct drop_shadow_layout layout;

    struct drop_shadow_renderer renderer;

    uint32_t source_width;
    uint32_t source_height;

    uint32_t output_width;
    uint32_t output_height;

    enum gs_color_space color_space;
    enum gs_color_format color_format;
};
```

---

# 33. Properties API

Usar controles nativos:

```text
obs_properties_add_bool
obs_properties_add_int_slider
obs_properties_add_float_slider
obs_properties_add_list
obs_properties_add_color_alpha
obs_properties_add_button
```

No Qt.

Ventajas:

- integración visual nativa;
- menos RAM;
- menos tamaño;
- menor superficie de bugs;
- menos dependencias;
- OBS administra la ventana.

---

# 34. UI — Edge Fade

Orden recomendado:

```text
[ ] Vincular lados

Izquierda
Derecha
Superior
Inferior

Suavidad

Curva
```

Cuando `Vincular lados` está activo:

- modificar cualquiera actualiza los cuatro valores;
- opcionalmente ocultar sliders individuales y mostrar uno global;
- evitar loops de update.

---

# 35. UI — Rounded Corners

```text
[✓] Vincular esquinas

Radio

--- si se desvincula ---

Superior izquierda
Superior derecha
Inferior izquierda
Inferior derecha

Suavidad
```

---

# 36. UI — Drop Shadow

```text
Color
Opacidad

Ángulo
Distancia

[ ] Posicionamiento avanzado

X
Y

Blur
Spread
```

Si se habilita modo avanzado:

```text
X/Y
```

se convierten en fuente de verdad.

Si no:

```text
angle/distance
```

se convierten en fuente de verdad.

No mantener dos estados contradictorios.

---

# 37. Valores por defecto

## Edge Fade

```text
Left         0
Right        0
Top          0
Bottom       0
Linked       true
Smoothness   50
Curve        Smooth
```

## Rounded Corners

```text
Radius all   24 px
Linked       true
Softness     auto / 1 px equivalente
```

## Drop Shadow

```text
Color        Black
Opacity      35 %
Angle        45°
Distance     10 px
Blur         16 px
Spread       0 px
```

Los valores deben refinarse visualmente.

---

# 38. Settings lifecycle

Implementar por filtro:

```text
get_defaults()
create()
update()
destroy()
```

Regla:

```text
create
    ↓
cargar recursos GPU
    ↓
aplicar settings
```

`update()`:

- solo actualizar datos;
- no recrear shaders por mover un slider;
- marcar dirty flags cuando una propiedad requiere recalcular layout.

---

# 39. Dirty flags

Especialmente para Drop Shadow:

```text
layout_dirty
resources_dirty
parameters_dirty
```

Ejemplo:

```text
Opacity cambia
→ parameters_dirty

Offset cambia
→ layout_dirty

Source resolution cambia
→ resources_dirty + layout_dirty
```

Evita recalcular innecesariamente.

---

# 40. Cambios de resolución en vivo

En `video_tick()` o al principio de `video_render()`:

```text
target width
target height
```

comparar con valores anteriores.

Si cambian:

```text
recalculate dimensions
mark render targets dirty
```

Casos:

- Browser source cambia resolución;
- media source cambia contenido;
- capturadora cambia de modo;
- escena anidada cambia dimensiones;
- cadena de filtros anterior cambia output.

---

# 41. `get_width()` y `get_height()`

## Edge Fade

Debe devolver las dimensiones del target.

## Rounded Corners

Debe devolver las dimensiones del target.

## Drop Shadow

Debe devolver:

```text
source + padding
```

Estas funciones deben ser baratas.

No ejecutar lógica GPU dentro de ellas.

---

# 42. Orden de filtros

Los filtros son independientes, por lo que el usuario puede ordenarlos libremente.

Sin embargo, los resultados cambian.

Ejemplo recomendado:

```text
Edge Fade
↓
Rounded Corners
↓
Drop Shadow
```

Así la sombra utiliza el alpha final producido por los filtros anteriores.

No forzar el orden desde el plugin.

Documentarlo.

---

# 43. Compatibilidad con otras fuentes

Matriz mínima:

| Fuente | Edge Fade | Rounded | Shadow |
|---|---|---|---|
| Image | Sí | Sí | Sí |
| Media Source | Sí | Sí | Sí |
| Browser | Sí | Sí | Sí |
| Video Capture | Sí | Sí | Sí |
| Game Capture | Sí | Sí | Sí |
| Display Capture | Sí | Sí | Sí |
| Window Capture | Sí | Sí | Sí |
| Nested Scene | Sí | Sí | Sí |
| Transparent PNG | Sí | Sí | Sí |

“Sí” significa objetivo de compatibilidad, sujeto a las reglas normales de libobs.

---

# 44. Compatibilidad SDR/HDR

Probar:

```text
SDR source → SDR canvas
SDR source → HDR canvas
HDR source → HDR canvas
HDR source → SDR processing path si OBS lo permite
```

No afirmar compatibilidad HDR completa hasta superar pruebas visuales.

El diseño debe evitar que los filtros geométricos transformen RGB innecesariamente.

---

# 45. Rendimiento esperado

No fijar números artificiales como garantía antes de medir.

Sí definir presupuestos.

## Edge Fade

Objetivo:

```text
1 pass
0 render targets adicionales
0 allocations/frame
```

## Rounded Corners

Objetivo:

```text
1 pass
0 render targets adicionales
0 allocations/frame
```

## Drop Shadow

Objetivo:

```text
1 source capture
0–3 processing passes según settings
1 composite pass
render targets persistentes
0 CPU pixel processing
0 allocations/frame en steady state
```

---

# 46. Optimizaciones obligatorias

- cachear effect parameters;
- no recrear effects al actualizar sliders;
- no cargar archivos en cada frame;
- no hacer `bmalloc()` por frame;
- no hacer logging por frame;
- no mapear texturas;
- reutilizar `gs_texrender_t`;
- bypass cuando el efecto no altera imagen;
- evitar passes de blur si blur=0;
- evitar spread si spread=0;
- no solicitar más padding del necesario;
- limitar valores extremos para impedir texturas absurdamente grandes.

---

# 47. Protección de memoria GPU

Drop Shadow podría accidentalmente solicitar buffers gigantes.

Ejemplo:

```text
4K source
+
500 px blur
+
500 px offset
```

Debe existir un límite razonable.

Validar:

```text
output_width
output_height
pixel_count
```

antes de crear render targets.

En caso de valores inválidos:

```text
clamp
o
bypass + warning
```

Nunca bloquear OBS intentando asignar texturas gigantes.

---

# 48. Manejo de errores

Si falla un shader:

```text
blog(LOG_ERROR, ...)
```

y el filtro debe:

```text
bypass
```

en lugar de:

- renderizar negro;
- crashear;
- dejar OBS en estado gráfico corrupto.

Si falla un render target:

```text
skip filter
```

y registrar un warning controlado.

---

# 49. Logging

Ejemplos válidos:

```text
[OBS Source Style] Plugin loaded
[OBS Source Style] Failed to load edge-fade.effect
[OBS Source Style] Drop Shadow render target allocation failed
```

No:

```text
Frame 1
Frame 2
Frame 3
...
```

---

# 50. Thread safety

El pipeline visual vive principalmente en el render thread.

No crear threads de trabajo en v1.

No existe ninguna tarea que justifique:

- worker pool;
- async processing;
- background renderer.

Los settings deben copiarse a estructuras internas seguras para ser utilizados en render.

---

# 51. Pruebas unitarias

Lo que sí puede probarse fuera del GPU:

### Rounded

```text
radius clamp
radius normalization
linked settings
```

### Edge Fade

```text
settings normalization
linked values
```

### Shadow

```text
angle → XY
XY → angle/distance
padding calculation
output dimensions
maximum limits
negative offsets
```

El render GPU requiere pruebas de integración.

---

# 52. Pruebas visuales

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

---

# 53. Test matrix de resolución

```text
64×64
320×240
640×480
1280×720
1920×1080
2560×1440
3840×2160
```

---

# 54. FPS

Probar:

```text
30 FPS
60 FPS
120 FPS
```

El plugin no debe contener lógica dependiente del frame rate.

---

# 55. Stress tests

Casos:

```text
10 fuentes × Rounded Corners
10 fuentes × Edge Fade
5 fuentes × Drop Shadow
3 filtros combinados × múltiples escenas
```

Medir:

- GPU frame time;
- rendering lag;
- VRAM;
- estabilidad;
- crecimiento de memoria.

---

# 56. Prueba de fugas

Secuencia repetida:

```text
crear filtro
cambiar settings
eliminar filtro
crear filtro
eliminar filtro
```

100+ veces.

Verificar:

- memoria CPU;
- VRAM;
- handles;
- effects;
- texrenders.

---

# 57. Herramientas de rendimiento

La metodología debe usar herramientas reales.

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

No optimizar basándose únicamente en porcentaje total de GPU del Administrador de tareas.

---

# 58. CMake

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

---

# 59. Build de Windows

Objetivo inicial:

```text
Windows x64
Release / RelWithDebInfo
```

Base compatible con:

```text
Visual Studio
CMake
official OBS plugin template
```

El template oficial actual declara Visual Studio 2022 como entorno soportado para plugins.

---

# 60. OBS objetivo

A fecha de esta planeación, la versión estable oficial consultada es:

```text
OBS Studio 32.2.2
```

publicada en agosto de 2026.

Objetivo inicial:

```text
OBS 32.2.x
Windows 10/11 x64
```

No depender deliberadamente de funciones de master sin necesidad.

---

# 61. Dependencias de OBS

`buildspec.json` debe fijar una versión compatible de OBS.

No copiar ciegamente el `buildspec.json` de una versión antigua del template.

Cuando se actualice OBS:

1. elegir versión;
2. actualizar dependency pin;
3. verificar URL usada por el template;
4. verificar SHA256 del mismo artefacto;
5. limpiar `.deps` si corresponde;
6. recompilar;
7. ejecutar test matrix.

---

# 62. CI

GitHub Actions debe ejecutar como mínimo:

```text
configure
build
format check
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

# 63. Versionado

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

---

# 64. Compatibilidad de settings

Los IDs de settings deben mantenerse estables.

Ejemplo:

```text
rounded.radius_tl
```

No cambiar después arbitrariamente a:

```text
rounded.topLeftRadius
```

sin migración.

Las escenas existentes dependen de esos nombres.

---

# 65. IDs de filtros

Definir desde el inicio IDs internos estables.

Ejemplo:

```text
obs_source_style_edge_fade
obs_source_style_rounded_corners
obs_source_style_drop_shadow
```

No usar nombres genéricos que puedan colisionar.

---

# 66. Localización

`data/locale/en-US.ini`

y:

`data/locale/es-ES.ini`

Todos los textos visibles deben usar:

```text
obs_module_text()
```

No hardcodear strings visibles en inglés dentro de `properties.c`.

---

# 67. README mínimo

Debe contener:

- qué hace el plugin;
- Windows soportado;
- versión mínima probada de OBS;
- instalación;
- los tres filtros;
- orden recomendado;
- capturas;
- troubleshooting;
- build desde source;
- licencia.

---

# 68. Fases de desarrollo

## FASE 0 — Bootstrap

Objetivo:

```text
plugin compila
OBS lo carga
OBS lo descarga sin crash
```

Tareas:

- crear desde template;
- nombre e IDs definitivos;
- CMake;
- locale;
- logging;
- build x64;
- CI inicial.

**Criterio de salida:** DLL cargada correctamente.

---

## FASE 1 — Base común

Implementar:

```text
shader-loader
color-space helpers
math-utils
logging
```

Crear un filtro passthrough temporal para validar:

```text
filter chain
color space
alpha
```

**Criterio de salida:** pipeline común probado.

---

## FASE 2 — Rounded Corners

Implementar:

- settings;
- properties;
- SDF shader;
- cuatro radios;
- linked mode;
- bypass;
- SDR/color-space path.

**Criterio de salida:** filtro estable sin render targets.

---

## FASE 3 — Edge Fade

Implementar:

- cuatro lados;
- linked mode;
- smoothness;
- curve;
- shader;
- bypass.

**Criterio de salida:** filtro independiente y estable.

---

## FASE 4 — Drop Shadow layout

Sin blur todavía.

Implementar:

- offset;
- angle;
- distance;
- padding;
- output dimensions;
- get_width/get_height;
- source position;
- sombra sólida.

**Criterio de salida:** sombra externa nunca recortada.

---

## FASE 5 — Drop Shadow render targets

Implementar:

- source_rt;
- mask_rt;
- lifecycle;
- size changes;
- color format changes;
- target rendering.

**Criterio de salida:** fuente capturada a GPU texture sin CPU readback.

---

## FASE 6 — Blur

Implementar:

- horizontal pass;
- vertical pass;
- blur radius;
- fast path blur=0;
- tests 1080p/4K.

**Criterio de salida:** blur visual limpio y estable.

---

## FASE 7 — Spread + composite

Implementar:

- spread;
- color;
- opacity;
- final composition;
- premultiplied alpha;
- offsets extremos.

**Criterio de salida:** Drop Shadow funcional completo.

---

## FASE 8 — Color/HDR

Probar:

- SRGB;
- SRGB 16F;
- extended 709;
- cambios de canvas;
- cadenas mixtas.

Corregir cualquier conversión indebida.

---

## FASE 9 — Compatibilidad de cadena

Probar todas las combinaciones:

```text
Edge → Rounded → Shadow
Edge → Shadow → Rounded
Rounded → Edge → Shadow
Rounded → Shadow → Edge
Shadow → Rounded → Edge
Shadow → Edge → Rounded
```

También filtros nativos antes/después.

---

## FASE 10 — Performance

Medir.

Optimizar solo basándose en profiling.

Objetivos:

```text
0 CPU pixel processing
0 allocations/frame
single pass para Edge/Rounded
render targets persistentes para Shadow
```

---

## FASE 11 — Hardening

Pruebas:

- source removal;
- source resize;
- scene switch;
- duplicate;
- enable/disable;
- rapid slider changes;
- close OBS;
- reopen profile;
- corrupted/missing shader.

---

## FASE 12 — Release 0.1.0

Generar:

```text
Windows x64 package
README
CHANGELOG
release notes
checksums
GitHub Release
```

---

# 69. Política de commits

Cada fase debe producir commits pequeños y verificables.

Ejemplos:

```text
feat(edge-fade): register initial filter
feat(edge-fade): add gpu fade shader
feat(rounded): add per-corner radius settings
feat(shadow): add dynamic output padding
feat(shadow): add reusable gpu render targets
perf(shadow): bypass blur when radius is zero
fix(render): preserve premultiplied alpha
```

Evitar:

```text
update stuff
changes
final
fix
```

---

# 70. Reglas de arquitectura para agentes de desarrollo

1. No crear archivos gigantes.
2. No fusionar los tres filtros en una sola implementación.
3. No hacer un “universal filter”.
4. No mover procesamiento visual a CPU.
5. No añadir Qt sin una necesidad aprobada.
6. No añadir dependencias externas innecesarias.
7. No romper un filtro funcional al desarrollar otro.
8. No duplicar helpers reales.
9. No abstraer prematuramente código que solo usa un módulo.
10. Mantener las APIs de libobs visibles y fáciles de auditar.
11. Cada cambio gráfico debe manejar correctamente el graphics context.
12. Toda creación GPU debe tener destrucción simétrica.
13. Toda modificación de estado gráfico debe restaurarse.
14. Toda ruta de error debe preferir bypass a crash.
15. Ningún log por frame en builds normales.

---

# 71. Criterio de “terminado” para v1

La v1 puede declararse lista únicamente cuando:

### Plugin

- un solo instalable;
- tres filtros visibles;
- carga limpia;
- descarga limpia.

### Edge Fade

- cuatro lados;
- linked;
- smoothness;
- GPU single-pass;
- bypass.

### Rounded Corners

- cuatro radios;
- linked;
- antialiasing;
- GPU single-pass;
- bypass.

### Drop Shadow

- color;
- opacity;
- angle;
- distance;
- X/Y;
- blur;
- spread;
- padding externo;
- render targets GPU;
- no clipping;
- fast paths.

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

# 72. Flujo final esperado

```text
                       ┌──────────────────────┐
                       │     OBS / libobs     │
                       └──────────┬───────────┘
                                  │
                  ┌───────────────┼────────────────┐
                  │               │                │
                  ▼               ▼                ▼
          ┌──────────────┐ ┌──────────────┐ ┌───────────────┐
          │  Edge Fade   │ │   Rounded    │ │  Drop Shadow  │
          │              │ │   Corners    │ │               │
          │  1 GPU pass  │ │  1 GPU pass  │ │ GPU multipass │
          └──────────────┘ └──────────────┘ └───────┬───────┘
                                                    │
                       ┌────────────────────────────┼─────────────┐
                       ▼                            ▼             ▼
                 source texture                 blur H        blur V
                       │                            │             │
                       └────────────────────────────┴──────┬──────┘
                                                          ▼
                                                     composite
```

---

# 73. Referencias oficiales consultadas

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

- `scroll-filter.c`:  
  https://github.com/obsproject/obs-studio/blob/master/plugins/obs-filters/scroll-filter.c

- `gpu-delay.c` — referencia útil para captura GPU y `gs_texrender_t`:  
  https://github.com/obsproject/obs-studio/blob/master/plugins/obs-filters/gpu-delay.c

- `graphics.h` — API de `gs_texrender_t`:  
  https://github.com/obsproject/obs-studio/blob/master/libobs/graphics/graphics.h

- `texture-render.c`:  
  https://github.com/obsproject/obs-studio/blob/master/libobs/graphics/texture-render.c

## Release objetivo consultado

- OBS Studio 32.2.2:  
  https://github.com/obsproject/obs-studio/releases

- Descarga oficial OBS:  
  https://obsproject.com/download

---

# 74. Resumen técnico definitivo

La arquitectura elegida para OBS Source Style es:

```text
1 DLL
3 filtros independientes
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

Rounded Corners
→ shader SDF single-pass

Drop Shadow
→ captura GPU
→ máscara
→ blur horizontal
→ blur vertical
→ composite
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

La v1 debe concentrarse exclusivamente en que estos **tres efectos sean sólidos, independientes, visualmente correctos, de bajo consumo y fáciles de mantener**.
