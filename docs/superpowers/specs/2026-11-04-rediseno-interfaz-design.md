# Rediseño de la interfaz de An (estilo del mockup «Cuadro de Turnos»)

## Context

El usuario quiere que toda la app se vea como el mockup enviado: barra lateral flotante con íconos y contadores, encabezado de página en tarjeta (ícono + título + subtítulo + píldoras de filtro a la derecha), fila de acciones con íconos (principal verde primero, rojas al final), pasos 1-2-3 en tarjetas, ayuda plegable, contenido en tarjetas blancas sobre un fondo degradado suave. Debe repetirse el mismo orden, simetría y alineación en **todos los menús**.

Decisiones del usuario:
- Todo el mockup **menos el modo oscuro**: se agregan Inicio, Reportes, campana, tarjeta «Ver tutorial», botón flotante de ayuda y avatar.
- Marca: sigue siendo **«An»** (logo nuevo al estilo del mockup, nombre del área debajo).
- FigCraft: **todas las pantallas** se dibujan en `docs/diseno/An_UI.figcraft` antes de codificarlas.
- Fondo: **degradado suave + tarjetas blancas sólidas** (no vidrio).
- Inicio = resumen del periodo; campana = avisos calculados (sin tabla nueva); Reportes = descargas Excel; tutorial = guía paso a paso (la abre también el botón flotante).

Supuestos míos (corregibles): avatar con **iniciales** (no hay fotos en la BD); «Requerimiento» queda en el menú entre Ausencias y Reportes; las áreas de Radiología usan el mismo marco con sus secciones.

Hoy el front ya tiene la estructura (acciones del periodo en fila, `Pasos`, `Ayuda`, `Seccion`, `Pagina`) en `web/src/pantallas/Cuadro.tsx`, `AccionesPeriodo.tsx`, `comun.tsx`, `Disposicion.tsx`. El cambio es de marco, estilo y cuatro piezas nuevas; la lógica de cada pantalla no cambia.

## Ajuste pedido tras el diseño

Tooltips (al pasar el mouse y con el foco) en los botones de acción, en un «?» junto a cada campo de Parámetros y en cada celda de Requerimiento.

## Orden del menú

Inicio · Cuadro de turnos · Solicitudes (contador) · Personal · Ausencias · Requerimiento · Reportes · Parámetros · Analíticas · Usuarios (solo admin).

## Sistema visual (una sola regla para todas las pantallas)

- **Marco:** fondo degradado tenue (tokens nuevos `fondo_1`/`fondo_2` en FigCraft → `tokens.css`). Barra lateral = tarjeta blanca flotante (radio 24, sombra suave, 280 px, botón «‹» para plegar a solo íconos). Ítem activo: píldora verde clara con barra izquierda. Abajo: tarjeta «Tu equipo, siempre en el mejor turno · Ver tutorial» y tarjeta de usuario (avatar con iniciales, nombre, rol, ícono salir).
- **Encabezado de página** (`Pagina` rehecho): tarjeta con fila 1 = [ícono en recuadro][título + subtítulo] … [píldoras de filtro][acción secundaria, p. ej. Exportar]; fila 2 opcional = acciones (primaria verde rellena primero, secundarias blancas con ícono, destructivas rosa/rojo al final). Campana fija arriba a la derecha, fuera de la tarjeta. Altura de controles uniforme (40 px), separación 12 px, todo alineado a la misma línea base.
- **Tarjetas:** blancas, radio 16, sombra suave, relleno 20; tablas dentro de tarjeta; `Ayuda` como tarjeta blanca con «Mostrar ⌄» a la derecha.
- **Botones:** se ajusta `web/src/components/base/buttons/button.tsx` (radio xl, alto md, sombra suave, variante primaria con degradado de marca) para que el cambio llegue a todas las pantallas sin tocarlas una a una. Íconos de `@untitledui/icons` (ya instalado): Generar `Stars02`, Reasignar `SwitchHorizontal01`, Publicar `Send01`, Cerrar `Lock01`, Nuevo `CalendarPlus01`, Restaurar `RefreshCcw01`, Eliminar `Trash01`, Exportar `Download01`.
- Colores solo desde tokens (regla de `checks/diseno.py`); texto ≥ 11 px, contraste 4,5:1.

## Pasos

### 0. Rama y spec
- Rama `rediseno-interfaz` desde `main` (el commit `fb04849` de `reasignar-explora` no está en `main`; queda en su rama).
- Copiar este plan a `docs/superpowers/specs/2026-11-04-rediseno-interfaz-design.md` y commitear.

### 1. FigCraft (todas las pantallas) — `docs/diseno/An_UI.figcraft`
Con `mcp__figcraft-app__*` (app abierta, el usuario puede mirar; si no responde, `mcp__figcraft__*` headless):
1. Variables de color nuevas (fondo, sombra, píldora activa, rosa destructivo) en la colección «Color»; `python checks/tokens.py` las pasa a `web/src/tokens.css`.
2. Componentes: barra lateral (ítem normal/activo/con contador, tarjeta tutorial, tarjeta usuario), encabezado de página, botón (primario/secundario/destructivo con ícono), píldora-select, tarjeta de paso, tarjeta, tabla, panel de campana, ventana de tutorial, botón flotante.
3. **Cuadro de turnos primero** (1440×900, igual al mockup) → captura a `docs/diseno/rediseno/cuadro.png` → **pausa para que el usuario lo apruebe**.
4. Luego un marco por pantalla con datos de muestra: Ingresar, Cambiar clave, Inicio, Solicitudes, Personal, Ausencias, Requerimiento, Reportes, Parámetros, Analíticas, Usuarios, Radiología (resumen), + campana abierta, tutorial, ventana de confirmación y vista móvil (375 px) del marco. Capturas en `docs/diseno/rediseno/*.png`.

### 2. Marco y piezas comunes (código)
- `web/src/pantallas/Disposicion.tsx`: barra lateral nueva (reusar `NavList` y `MobileNavigationHeader`; plegado guardado en `localStorage` con try/catch), tarjeta tutorial, tarjeta usuario con `Avatar` de `components/base/avatar` (iniciales), campana, botón flotante. Contador de Solicitudes = no cumplidas del periodo vigente.
- `web/src/components/foundations/logo/an-logo.tsx`: logo nuevo.
- `web/src/pantallas/comun.tsx`: `Pagina` acepta `icono`, `filtros` y `acciones`; `Seccion` y `Ayuda` con el estilo nuevo; `Ventana` con radio/sombra nuevos.
- `web/src/components/base/buttons/button.tsx`, `styles/theme.css` (radios/sombras), `styles/globals.css` (fondo del `body`).

### 3. Piezas nuevas
- **Inicio** `web/src/pantallas/Inicio.tsx`, ruta `/areas/:area/inicio` (el índice del área redirige aquí): periodo vigente, `Pasos` (sacarlo de `Cuadro.tsx` a `comun.tsx` para reusarlo), tarjetas de alertas rojas, solicitudes no cumplidas, cobertura y horas extra (de `/analiticas`), ausencias de hoy, accesos rápidos. Solo lee endpoints existentes.
- **Reportes** `web/src/pantallas/Reportes.tsx`, ruta `reportes`: selector de periodo + tarjetas Cuadro / Puestos / Horas con descargar (reusa `Exportar.tsx` y `api/exportes.ts`) + Imprimir. En el cuadro queda el botón «Exportar».
- **Campana** `web/src/componentes/Campana.tsx`: popover (React Aria, ya instalado) con avisos calculados al abrir: alertas rojas del periodo, solicitudes no cumplidas, ausencias que empiezan esta semana, última generación terminada/fallida. Para lo último, endpoint nuevo de solo lectura `GET /api/areas/{a}/trabajos?limite=5` en `an/web/rutas_trabajos.py` (+ prueba en `tests/web/`, + `npm run tipos`). Número = cantidad de avisos.
- **Tutorial** `web/src/componentes/Tutorial.tsx`: `Ventana` con 6 pasos (crear periodo, generar, revisar alertas, cambiar celdas, publicar, exportar) con imagen de cada uno (capturas de FigCraft en `web/public/tutorial/`), anterior/siguiente. Lo abren la tarjeta de la barra y el botón flotante (que además muestra la `Ayuda` de la pantalla actual).

### 4. Pantallas (mismo patrón en cada una)
Cada pantalla pasa a `Pagina` con ícono, filtros a la derecha y acciones en la fila 2, contenido en `Seccion`. Patrón aplicado a: `Cuadro.tsx` (+ `AccionesPeriodo.tsx`, `Generar.tsx` con íconos; «Ver puestos» como píldora; estado «Publicado» como píldora), `Solicitudes`, `Personal`, `Novedades`, `Puestos`/`MatrizRequerimiento`, `Parametros`, `Analiticas`, `Usuarios`, `Radiologia`/`RadiologiaVistas`, `Ingresar`, `CambiarClave`. `componentes/Planilla.tsx`: encabezado de días, columna «N sem» y filas de presentes como el mockup.

### 5. Cierre
- `docs/ESTADO.md` (cambios recientes), `CLAUDE.md` si cambian rutas o capas, capturas nuevas en `docs/diseno/`.
- PR a `main`; `cd web && npm run build` y `grep -l "Ver tutorial" web/dist/assets/*.js` (memoria: entrega = main + `web/dist` recompilado).

## Verificación
- `cd web && npm run build` (incluye `tsc`).
- `python checks/diseno.py`, `python checks/tokens.py --verificar`, `python checks/reglas.py`.
- `.venv/bin/python -m pytest tests --ignore=tests/turnos/test_turnos.py` (incluye la prueba del endpoint de trabajos).
- `web/demo.sh` + panel del navegador: recorrer cada menú, captura de cada pantalla y compararla con su marco de FigCraft; revisar 1440 px y 375 px (sin scroll horizontal del marco), teclado (tab por la barra, campana y tutorial), y que Generar → Publicar sigan funcionando.

## Ejecución
Secuencial en esta sesión: los pasos comparten `comun.tsx`, `Disposicion.tsx` y el archivo FigCraft, así que no se reparten en sesiones paralelas. Puntos de control con el usuario: después del marco del Cuadro en FigCraft (paso 1.3) y antes del PR.
