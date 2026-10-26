# Migración de la web a Untitled UI — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Que toda la web use componentes y tema de Untitled UI con nuestra marca, sin CSS Modules ni componentes propios salvo la grilla de turnos y los pasos del Cuadro.

**Architecture:** Componentes copiados de `untitleduico/react` (commit `1d410cb`, MIT) a `web/src/components/` con su estructura; las pantallas los usan directamente. Tailwind v4 lee `styles/theme.css` (de Untitled) y `tokens.css` (marca y turnos, generado desde FigCraft). Siete fases; cada una deja la web funcionando y es un commit.

**Tech Stack:** React 19, Vite, TypeScript, Tailwind CSS 4.3.3, React Aria, `@untitledui/icons`, FigCraft (MCP `figcraft-app`).

**Spec:** `docs/superpowers/specs/2026-10-26-untitled-ui-design.md`

## Global Constraints

- Requisito previo: `main` con el PR #20 y el retiro de Qt fusionados. Rama `untitled-ui` desde `main`. Al terminar: push → PR → fusionar con CI verde.
- Dependencias exactas (`--save-exact`): `tailwindcss@4.3.3`, `@tailwindcss/vite@4.3.3`, `react-aria-components@1.22.1`, `react-aria@3.53.1`, `tailwind-merge@3.7.0`, `tailwindcss-react-aria-components@2.2.0`, `tailwindcss-animate@1.0.7`, `@untitledui/icons@0.0.23`. Se desinstala `@base-ui/react`.
- Fuente de los componentes: `https://github.com/untitleduico/react` commit `1d410cb`; cada archivo copiado conserva su ruta relativa (`components/base/buttons/button.tsx` → `web/src/components/base/buttons/button.tsx`). Solo se copia lo que se usa.
- Look Untitled completo, sin modo oscuro (se borra `.dark-mode` del tema). Tipografía Inter (la empaquetada en `web/src/fuentes/`); Sora se borra.
- Escala de marca (FigCraft `brand_*` → `--an-brand-*` en `tokens.css`; `theme.css` declara `--color-brand-N: var(--an-brand-N)`, así no hay ciclo): 25 `#F6FBFB`, 50 `#EDF8F7`, 100 `#DAF1F0`, 200 `#B6E7E5`, 300 `#83D8D4`, 400 `#3FCAC4`, 500 `#1B9D97`, 600 `#0B7A75`, 700 `#085E5A`, 800 `#074946`, 900 `#053836`, 950 `#032322`. Turnos: `turno_M #FFE9A8`, `turno_T #CFE3FF`, `turno_C #CDEFD8`, `turno_NC #E0D6FA`.
- Colores literales solo en `web/src/tokens.css` y `web/src/styles/theme.css`. Texto ≥ 11 px. Contraste ≥ 4,5:1.
- Textos de la interfaz en español, iguales a los actuales salvo que un componente pida otra forma.
- Se conserva todo el comportamiento listado en el spec («Comportamiento que se conserva»).
- Verificación de cada tarea: `cd web && npm run build`; `.venv/bin/python checks/diseno.py`; `.venv/bin/python checks/tokens.py --verificar`; recorrido con `web/demo.sh` (usuarios `editor`, `lector`, `admin`, `nuevo` @demo.co, clave `clave-larga-1`) a 1280 px y 375 px.

## Review Focus

- Usuario «Solo consulta»: ningún botón de edición visible y el aviso de modo consulta presente en cada pantalla → comprobar con `lector@demo.co` en cada fase.
- Celular (375 px): la navegación lateral debe colapsar y el Cuadro desplazarse en horizontal sin desbordar la página → captura a 375 px en Tareas 3 y 6.
- Teclado: foco visible y orden lógico en formularios, modales y la grilla (React Aria lo da en sus piezas; la grilla es propia) → recorrer con Tab en Tareas 2, 4 y 6.
- Impresión del Cuadro: solo título y grilla, apaisado → vista previa de impresión en la Tarea 6.
- Carga lenta / error de API: «Cargando…», vacío y error con «Reintentar» siguen distinguiéndose → cortar la API (`kill` de uvicorn) y recargar en la Tarea 4.

---

### Task 1: Base — dependencias, tema y tokens

**Files:**
- Modify: `web/package.json`, `web/vite.config.ts`, `web/src/main.tsx`, `docs/diseno/An_UI.figcraft` (colección «Color»), `checks/tokens.py`, `checks/diseno.py`, `tests/checks/test_tokens.py`, `tests/checks/test_diseno.py`, `web/src/tokens.css` (generado)
- Create: `web/src/styles/theme.css`, `web/src/styles/typography.css`, `web/src/styles/globals.css` (copiados; cabecera `/* De untitleduico/react@1d410cb (MIT). Cambios: sin .dark-mode, marca desde tokens.css. */`), `web/src/utils/cx.ts` (y los utils/hooks que pidan los componentes)

**Interfaces:**
- Produces: clases Tailwind de Untitled (`bg-primary`, `text-secondary`, `border-primary`, `bg-brand-solid`, …), `--an-brand-*`, `--turno-*`, `cx()` en `web/src/utils/cx.ts`.

- [ ] **Step 1: Tests de los checks que fallan**
  - `test_tokens.py`: `tokens.leer_variables(FIGCRAFT)` tiene exactamente las claves `brand_25…brand_950` y `turno_M/T/C/NC`; `tokens.css({"brand_600": "#0B7A75"}) == ":root {\n  --an-brand-600: #0B7A75;\n}\n"` y `{"turno_M": …}` → `--turno-M`.
  - `test_diseno.py`: un `styles/theme.css` con `#fff` no da «color literal»; un `a.module.css` con `#fff` sí; par `text-white` sobre `bg-brand-600` pasa.
- [ ] **Step 2:** `pytest -q tests/checks` → FAIL.
- [ ] **Step 3: FigCraft** — con `figcraft-app`: `variable.delete` de las 42 variables actuales y `variable.create` de las 16 nuevas con los valores de Global Constraints; `save_file`.
- [ ] **Step 4: `checks/tokens.py`** — `css(tokens)` escribe `brand_*` como `--an-brand-*` y `turno_*` como `--turno-*`. `checks/diseno.py`: `IGNORAR` de colores literales incluye `styles/theme.css`; `PARES` (sobre los valores de `tokens.css`) = blanco sobre `an-brand-600` y `an-brand-700`, y `#181D27` (gray-900 de Untitled) sobre cada `turno-*`; el blanco y ese gris quedan como constantes del check.
- [ ] **Step 5:** `python checks/tokens.py` (regenera) y `pytest -q tests/checks` → PASS.
- [ ] **Step 6: Dependencias y Vite** — instalar las de Global Constraints; `vite.config.ts` con `tailwindcss()`; `main.tsx` importa `./tokens.css`, `./styles/globals.css` (que importa `tailwindcss`, `theme.css`, `typography.css` y los plugins). En `theme.css` las líneas `--color-brand-N: rgb(...)` pasan a `--color-brand-N: var(--an-brand-N)`.
- [ ] **Step 7: Convivencia** — los CSS Modules siguen hasta la Tarea 7; `estilos.css` pasa sus reglas globales a `@layer base` para que las utilidades ganen. La app se ve con fondo y fuente de Untitled y nada se rompe.
- [ ] **Step 8:** Verificación global; commit `Base de Untitled UI: Tailwind, React Aria, tema y marca desde FigCraft`.

### Task 2: Componentes base

**Files:**
- Create (copiados de `1d410cb`): `components/base/buttons/button.tsx`, `components/base/input/*`, `components/base/select/*`, `components/base/checkbox/checkbox.tsx`, `components/base/toggle/toggle.tsx`, `components/base/textarea/textarea.tsx`, `components/base/badges/*`, `components/base/tooltip/tooltip.tsx`, `components/base/dropdown/dropdown.tsx`, `components/application/modals/modal.tsx`, `components/application/empty-state/empty-state.tsx`, `components/application/loading-indicator/loading-indicator.tsx`, `components/foundations/featured-icon/*`, y sus dependencias internas.
- Modify: todos los usos de `Boton`, `Campo`/`Seleccion`, `Casilla`, `Dialogo`, `Aviso`, `Progreso` en `web/src/pantallas/*.tsx`.
- Delete: `componentes/{Boton,Campo,Dialogo,Aviso,Progreso}.tsx` y sus `.module.css`.

**Interfaces:**
- Produces: equivalencias usadas en todas las pantallas:
  - `Boton variante=primario|secundario|peligro|texto` → `<Button color="primary|secondary|primary-destructive|link-color" size="sm">`
  - `Campo etiqueta ayuda error` → `<Input label hint isInvalid>` (número, fecha, contraseña: `type`); `Seleccion` → `<Select label>` (opciones como `items`) o `NativeSelect` si existe en el commit.
  - `Casilla` → `<Checkbox label>`; `Dialogo` → `<Modal>`/`<Dialog>`; `Aviso nivel` → `<Alert>` propio mínimo en `components/application/alerts/alert.tsx` (Untitled gratis no trae alerta en línea: se arma con `FeaturedIcon` + texto + clases de color `bg-utility-*`), `role="alert"` para error y aviso; `Progreso` → `<ProgressBar>`/`LoadingIndicator`.

- [ ] **Step 1:** Copiar los archivos y sus imports internos; `npm run build` compila.
- [ ] **Step 2:** Reemplazar los usos pantalla por pantalla con las equivalencias; borrar los componentes viejos.
- [ ] **Step 3:** Recorrido con los 4 usuarios: formularios guardan, validaciones muestran el error junto al campo, diálogos abren/cierran con Escape y devuelven el foco, Tab recorre en orden.
- [ ] **Step 4:** Verificación global; commit `Componentes base de Untitled UI`.

### Task 3: Estructura — navegación, encabezado, acceso

**Files:**
- Create: `components/application/app-navigation/*` (sidebar), `components/application/tabs/*` si se usan.
- Modify: `pantallas/Disposicion.tsx`, `pantallas/comun.tsx` (`Pagina`: encabezado Untitled con título, subtítulo, recuadro de ayuda y avisos), `pantallas/Ingresar.tsx`, `pantallas/CambiarClave.tsx`.
- Delete: `componentes/{Lateral,Tarjeta,Ayuda}.tsx` y sus `.module.css`, `pantallas/{Disposicion,Acceso}.module.css`.

**Interfaces:**
- Produces: `Pagina({ titulo, sub, ayuda, error, aviso, children })` con la misma firma que hoy; contenedor de sección `Seccion({ titulo, acciones, children })` en `pantallas/comun.tsx` (reemplaza `Tarjeta`).

- [ ] **Step 1:** Sidebar con marca «An», área, secciones (mismos nombres y rutas), rol y «Salir»; selector de área si hay más de una; colapsa a menú en < 1024 px.
- [ ] **Step 2:** `Pagina`/`Seccion` y recuadro de ayuda (mismo comportamiento: abierto la primera vez, recuerda si se cerró).
- [ ] **Step 3:** Ingresar (panel de bienvenida + formulario) y Cambiar clave con componentes Untitled.
- [ ] **Step 4:** Capturas 1280/375 px; verificación global; commit `Estructura con Untitled UI: navegación, páginas y acceso`.

### Task 4: Pantallas de catálogo

**Files:**
- Create: `components/application/table/table.tsx` (y deps).
- Modify: `pantallas/{Personal,Novedades,Puestos,Solicitudes,Parametros,Usuarios}.tsx`.
- Delete: `componentes/Tabla.tsx`, `Tabla.module.css`, `pantallas/Formulario.module.css` cuando quede sin uso.

**Interfaces:**
- Consumes: `Pagina`, `Seccion` (Tarea 3); equivalencias de la Tarea 2.
- Produces: tabla con estados `cargando` / vacío (`EmptyState` con texto y acción) / error, usada también en Analíticas y Cuadro.

- [ ] **Step 1:** Cada pantalla con tabla Untitled y formulario en grilla (`grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] gap-3`); prioridad «Alta» como `Badge color="warning"`; estados como `Badge`.
- [ ] **Step 2:** Review Focus: lector sin edición; API caída → error con «Reintentar».
- [ ] **Step 3:** Verificación global; commit `Pantallas de catálogo con Untitled UI`.

### Task 5: Analíticas y Radiología

**Files:**
- Modify: `pantallas/Analiticas.tsx`, `pantallas/Radiologia.tsx`, `pantallas/RadiologiaVistas.tsx`.
- Delete: `pantallas/Radiologia.module.css` y lo que quede sin uso.

- [ ] **Step 1:** Cifras de resumen como tarjetas de métrica Untitled; tablas de la Tarea 4; Radiología: carga del archivo con `file-upload` de Untitled, vistas por semana con `Tabs`.
- [ ] **Step 2:** Recorrido con un área `--tipo radiologia` (subir `ejemplos/radiologia/*.xlsx`); verificación global; commit `Analíticas y Radiología con Untitled UI`.

### Task 6: Cuadro

**Files:**
- Modify: `componentes/Planilla.tsx`, `componentes/Ficha.tsx` (reescritos con Tailwind; misma API de props), `pantallas/{Cuadro,Generar,Exportar,AccionesPeriodo,RegistrarCambio,Cambios}.tsx`.
- Delete: `componentes/{Planilla,Ficha}.module.css`, `pantallas/{Cuadro,Generar,Exportar}.module.css`.

**Interfaces:**
- Consumes: `Planilla` y `Ficha` conservan sus props actuales (`dias`, `filas`, `celda`, `pie`, `editable`, `alAccionar`, `alSoltar`, `foco`, `columnaExtra`), así `Cuadro.tsx` no cambia su lógica.

- [ ] **Step 1:** `Ficha` con `--turno-*` y clases Tailwind; borde de alerta `ring-2 ring-error-solid`; marca «editada a mano».
- [ ] **Step 2:** `Planilla` con Tailwind: cabecera fija, columna de nombres fija, domingos en `bg-secondary`, desplazamiento horizontal propio.
- [ ] **Step 3:** Pasos, alertas agrupadas (Badge + lista), registrar cambio en `Modal`, generar con `ProgressBar`, exportar y acciones con `Dropdown`.
- [ ] **Step 4:** `performance.getEntriesByName("cuadro:maquetado-ms")` < 1000 ms en la demo (40 × 31); vista previa de impresión apaisada con solo título y grilla; 375 px con desplazamiento horizontal.
- [ ] **Step 5:** Verificación global; commit `Cuadro con Untitled UI`.

### Task 7: Limpieza y documentación

**Files:**
- Delete: todo `*.module.css` restante, `web/src/estilos.css` (lo que sobreviva — `@page`/`@media print`, `.saltar`, `.solo-lectores` — pasa a `styles/globals.css`), `web/src/fuentes/Sora-*`, `OFL-Sora.txt`, `web/src/componentes/` si quedó vacío, `@base-ui/react`.
- Modify: `docs/PLAN_WEB.md` (tabla de tecnologías y §7: Tailwind + Untitled UI; «Sin Tailwind» pasa a decisión revertida con fecha), `CLAUDE.md` (front: Untitled UI, dónde viven los componentes, cómo agregar uno desde `1d410cb`), `docs/diseno/` (capturas nuevas de cada pantalla).

- [ ] **Step 1:** `grep -rn "module.css\|@base-ui\|Sora\|var(--fondo)\|var(--acento)" web/src` → vacío.
- [ ] **Step 2:** Verificación global + `tests/web` + recorrido final con los 4 usuarios en todas las pantallas.
- [ ] **Step 3:** Commit `Limpieza tras la migración a Untitled UI`; push, PR (skill `pr`), fusionar con CI verde. Cerrar `prueba-tailwind` (`git push origin --delete prueba-tailwind`).
