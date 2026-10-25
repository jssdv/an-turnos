# Dashboard de analíticas (entrega 1) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Sección «Analíticas» de Esterilización con ausentismo, simultáneos, cobertura y cambios, en solo lectura.

**Architecture:** Módulo puro `an/esterilizacion/analitica.py` (sin Qt) calcula con `bd`; `an/nucleo/graficos.py` aporta widgets `QPainter`; `paginas.py` solo pinta. Sin migraciones ni dependencias.

**Tech Stack:** Python 3, PySide6, sqlite3. Python del repo principal: `/Users/jss/Desktop/An/.venv/bin/python` (el worktree no tiene `.venv`).

**Spec:** `docs/superpowers/specs/2026-10-25-dashboard-analiticas-design.md`

## Global Constraints

- `user_version` sigue en 6; no escribir en la base; no dependencias nuevas.
- UI en español; estilos solo en `ESTILO` (`an/nucleo/tema.py`), colores de `C`.
- Cada prueba imprime `OK` al final; GUI con `QT_QPA_PLATFORM=offscreen` y `QSettings` apuntando a un ini temporal.
- Solo personas `en_solver`. No tocar `docs/diseno/An_UI.figcraft`. No fusionar a main ni hacer push.
- Ejecutar pruebas con `PY=/Users/jss/Desktop/An/.venv/bin/python`.

## Review Focus

- Rango sin novedades ni cuadro: todo devuelve ceros/listas vacías, sin excepción.
- Novedad que empieza antes o termina después del rango: se recorta (no cuenta días fuera).
- Dos novedades solapadas de la misma persona: un día cuenta una vez.
- Persona inactiva o refuerzo con novedad: no cuenta.
- Cambio anulado: no cuenta en `cambios_resumen`.

## File Structure

- Create `an/esterilizacion/analitica.py` — cálculo puro.
- Create `an/nucleo/graficos.py` — `Barras`, `Linea`.
- Modify `an/esterilizacion/paginas.py` — `_pestana_analiticas`, `_ver_analiticas`, registro en `secciones` y `refrescar`.
- Create `tests/esterilizacion/test_analitica.py`, `tests/nucleo/test_graficos.py`; extend `tests/esterilizacion/test_gui.py`.
- Modify `CLAUDE.md`, `docs/GUIA_USUARIO.md`.

### Task 1: Ausentismo y simultáneos

**Files:** Create `an/esterilizacion/analitica.py`, `tests/esterilizacion/test_analitica.py`

**Interfaces:**
- Produces:
  - `ausentismo(bd, ini: date, fin: date) -> dict` con claves `por_tipo {tipo: dias}`, `por_persona {nombre: {tipo: dias}}`, `por_mes {"AAAA-MM": {tipo: dias}}`, `pct: float` (0–100, días de ausencia / (días del rango × personas en_solver), 0 si no hay personas).
  - `simultaneos(bd, ini, fin) -> dict` con `serie [(fecha, n)]` (un punto por día del rango), `maximo: int`, `fecha_maximo: date|None` (None si maximo = 0), `dias_riesgo [date]`.
  - `_ausencias(bd, ini, fin) -> dict[(colab_id, fecha)] -> tipo` helper compartido: usa `bd.novedades()` y `bd.colaboradores()` (solo `en_solver`), recorta al rango, primera novedad gana por día.

- [ ] **Step 1: Escribir pruebas** en `tests/esterilizacion/test_analitica.py` (cabecera como `test_cambios.py`: `sys.path.insert` al raíz, `from an.esterilizacion import analitica, db`). Fixture `nuevo()` = `db.BD(":memory:")` con 3 colaboradores guardados con `bd.guardar_colaborador(Colaborador(id=None,...))` (revisar firma en `db.py`) y un refuerzo. Pruebas:
  - `test_ausentismo_recorta_y_no_duplica`: Vacaciones de A del 28-sep al 3-oct y una Licencia de A del 2 al 5-oct; rango 1–31 oct ⇒ `por_persona["A"]["Vacaciones"] == 3`, `["Licencia"] == 2` (el 2 y 3 los gana Vacaciones), `por_mes["2026-10"]` suma 5, `pct == round(5/(31*3)*100, 6)` con tolerancia.
  - `test_ausentismo_ignora_refuerzo_e_inactivo`: novedad del refuerzo ⇒ no aparece.
  - `test_ausentismo_vacio`: sin novedades ⇒ `por_tipo == {}`, `pct == 0`.
  - `test_simultaneos_maximo_y_riesgo`: A y B de vacaciones el 5-oct ⇒ `maximo == 2`, `fecha_maximo == date(2026,10,5)`, `len(serie) == 31`; con un cuadro guardado (`bd.guardar_cuadro(K, {...})`) donde ese día falta personal obligatorio ⇒ `date(2026,10,5) in dias_riesgo`; un día con déficit sin ausencias ⇒ no está en `dias_riesgo`.
- [ ] **Step 2:** `PY tests/esterilizacion/test_analitica.py` → falla por `analitica` inexistente.
- [ ] **Step 3: Implementar** `_ausencias`, `ausentismo`, `simultaneos`. `dias_riesgo`: cuadro = `bd.asignaciones_rango(ini, fin)`; fechas = días del rango con alguna asignación; `reglas.faltantes_periodo(ctx, cuadro, fechas)` con `ctx = bd.contexto(ini.year)`; día en riesgo si algún `faltante_max > 0` en alguna franja **y** `serie` de ese día > 0.
- [ ] **Step 4:** correr la prueba → `OK`.
- [ ] **Step 5:** `git add an/esterilizacion/analitica.py tests/esterilizacion/test_analitica.py && git commit -m "Analítica: ausentismo y simultáneos"` (+ línea Co-Authored-By del sistema).

### Task 2: Cobertura y cambios

**Files:** Modify `an/esterilizacion/analitica.py`, `tests/esterilizacion/test_analitica.py`

**Interfaces:**
- Consumes: `flujo.desde_clave`, `flujo.fechas`, `bd.periodos()`, `bd.asignaciones(k)`, `bd.asignacion_puesto(k)`, `bd.catalogo_puestos()`, `reglas.faltantes_dia`, `puestos.alertas_reparto(ctx, filas, fechas, catalogo)`, `demanda.demanda_fecha`, `cambios.listar(bd, k)`.
- Produces:
  - `cobertura(bd, ini, fin) -> list[dict]`: un dict por periodo con cuadro cuyo rango intersecta `[ini, fin]`, ordenado por inicio: `{"periodo": k, "dias_deficit": int, "dias_exceso": int, "puestos_sin_cubrir": int}`. Se evalúan todos los días del periodo (no solo la intersección). Déficit = algún `faltantes_dia(...)[fr][0] > 0`. Exceso = algún tramo con presentes > `obl+des` de `demanda_fecha` (presentes: quienes empiezan hoy, más la madrugada de las noches de ayer salvo el primer día, como `faltantes_dia`; implementar `_presentes(ctx, cuadro, fecha, con_ayer)` reutilizando `dem.turno_tramos`).
  - `cambios_resumen(bd, ini, fin) -> dict[str, dict]`: `{periodo: {"permuta","servicio","ajuste","excepciones"}}` para periodos de `bd.periodos()` que intersectan el rango; omite filas con `anulado_en`; `excepciones` cuenta filas con `excepcion` truthy.

- [ ] **Step 1: Pruebas:**
  - `test_cobertura_deficit_y_exceso`: demanda por defecto de la BD; cuadro de un periodo corto (p. ej. 2026-10-05/2026-10-11) donde un día no tiene a nadie (déficit) y otro tiene muchos turnos «M» (exceso) ⇒ `dias_deficit >= 1`, `dias_exceso >= 1`; periodo fuera del rango no aparece.
  - `test_cobertura_sin_cuadro`: `[]`.
  - `test_cambios_resumen_excluye_anulados`: crear una permuta y un ajuste con `cambios.permuta/ajuste`, anular uno con `cambios.anular` ⇒ solo el vigente cuenta; una permuta con `excepcion=True` suma en `excepciones`.
  - `test_cambios_sin_filas`: `{}`.
- [ ] **Step 2:** correr → fallan.
- [ ] **Step 3:** Implementar ambas. `puestos_sin_cubrir = len(puestos.alertas_reparto(ctx, bd.asignacion_puesto(k), fechas, bd.catalogo_puestos()))` (0 si no hay filas de puesto).
- [ ] **Step 4:** correr → `OK` (y las pruebas de la Task 1 siguen pasando).
- [ ] **Step 5:** commit «Analítica: cobertura y cambios».

### Task 3: Gráficos del núcleo

**Files:** Create `an/nucleo/graficos.py`, `tests/nucleo/test_graficos.py`

**Interfaces:**
- Produces:
  - `class Barras(QWidget)`: `__init__(self, horizontal=False, apilado=False)`; `poner(self, datos: list[tuple[str, dict[str, float]]])` y repinta. Colores de serie por orden desde `[C["acento"], C["info"], C["warn_insignia"], C["error"], C["ok"]]`. Leyenda si hay más de una serie. `setMinimumHeight(180)`.
  - `class Linea(QWidget)`: `poner(self, puntos: list[tuple[str, float]])`; marca el valor máximo con un punto `C["error"]` y su etiqueta. `setMinimumHeight(160)`.
  - Con lista vacía (o todo cero) pintan «Sin datos» en `C["atenuado"]`. Atributo `vacio: bool` refleja el estado (para pruebas).

- [ ] **Step 1: Prueba** (offscreen, `preparar_app([])`): `Barras().poner([])` ⇒ `vacio`; con `[("Oct", {"Vacaciones": 3, "Licencia": 1})]` ⇒ `not vacio`; ambos con `resize(400, 220)` y `grab()` devuelven pixmap no nulo, también `horizontal=True` y `apilado=True`; `Linea` con puntos y con `[]`. Imprime `OK`.
- [ ] **Step 2:** correr → falla (módulo inexistente).
- [ ] **Step 3:** Implementar con `paintEvent` (`QPainter`, antialiasing, fuente del widget); sin leer base ni parámetros.
- [ ] **Step 4:** correr → `OK`.
- [ ] **Step 5:** commit «Núcleo: gráficos de barras y línea».

### Task 4: Sección Analíticas

**Files:** Modify `an/esterilizacion/paginas.py` (`__init__` ~l.121-130, `refrescar` ~l.237-243, nuevo `_pestana_analiticas`/`_ver_analiticas`), `tests/esterilizacion/test_gui.py`

**Interfaces:**
- Consumes: Task 1–3; `tabla`, `llenar`, `con_vacio`, `ocupado`, `Tarjeta`-estilo de cifras (si `Tarjeta` exige clic, usar un `QFrame#tarjeta` con dos `QLabel` ya estilizados `cifra`/`detalle`; no añadir reglas nuevas si bastan las existentes).
- Produces: sección `("Analíticas", w)` registrada después de «Historial y banco de horas» (es decir, `_pestana_analiticas()` se llama justo después de `_pestana_banco()` en `__init__`). Atributos: `self.a_desde`, `self.a_hasta` (`QDateEdit` con formato `MM/yyyy`, mes inicial/final), `self.a_cifras` (dict nombre→`QLabel` de cifra), `self.a_graf` (dict con los widgets `Barras`/`Linea`), `self.t_aus` (ausentismo por persona), `self.t_cob`, `self.t_cam`. `_ver_analiticas()` se añade a la lista de `refrescar`; rango por defecto = 6 meses terminando en el mes de `self.periodo()`; los selectores se inicializan una vez (no se pisan en cada refresco: solo la primera vez o al cambiar de periodo no) — usar bandera `self._a_init`.

- [ ] **Step 1: Pruebas** al final de `test_gui.py` antes de `print("OK")`: con una BD temporal, una persona, una novedad en octubre 2026 y un cuadro guardado: `titulos = [t for t, _ in v.secciones]`; `titulos.index("Analíticas") == titulos.index("Historial y banco de horas") + 1`; tras `v.refrescar()` con rango fijado (`v.a_desde.setDate(...)`) la tabla `t_aus` tiene una fila con la persona y los días esperados; sin datos (BD nueva) `refrescar()` no falla; `v.v.grab()` no es nulo.
- [ ] **Step 2:** correr `PY tests/esterilizacion/test_gui.py` → falla.
- [ ] **Step 3:** Implementar. Layout: fila de selectores + 4 cifras (Ausentismo %, Máx. simultáneos, Días en déficit, Cambios), luego `QScrollArea` con paneles `QFrame#panel` (título `panel_t`, gráfico y tabla). Gráficos: ausentismo por mes apilado por tipo; serie diaria de ausentes (`Linea`); déficit/exceso por periodo (`Barras`); cambios por periodo apilado por tipo. `_ver_analiticas` corre bajo `with ocupado()` y llama solo a `analitica.*`. Cambios de selector reconectan a `_ver_analiticas`; si `desde > hasta` se intercambian.
- [ ] **Step 4:** correr `test_gui.py` → `OK`. Revisar visualmente una captura con `v.v.grab().save(<scratchpad>/analiticas.png)` y abrirla con Read.
- [ ] **Step 5:** commit «Esterilización: sección Analíticas».

### Task 5: Docs y regresión

**Files:** Modify `CLAUDE.md`, `docs/GUIA_USUARIO.md`, spec (estado)

- [ ] **Step 1:** `CLAUDE.md`: añadir `analitica.py` al layout de esterilización, `graficos.py` al de `an/nucleo/`, y las dos pruebas nuevas a la lista de tests. `GUIA_USUARIO.md`: apartado «Analíticas» (qué mide cada gráfico, rango de meses, que exceso/déficit se miden contra la demanda de los puestos, que es de solo lectura). Spec: estado → «entrega 1 implementada».
- [ ] **Step 2:** correr todas, cada una debe imprimir `OK`: `tests/esterilizacion/test_analitica.py`, `test_gui.py`, `test_cambios.py`, `test_puestos.py`, `test_turnos.py` (~2 min, en segundo plano), `tests/nucleo/test_graficos.py`, `tests/nucleo/test_nucleo.py`, `tests/radiologia/test_gui.py`, `tests/radiologia/test_generar_semana.py`.
- [ ] **Step 3:** commit «Docs: analíticas» y `git status` limpio.

## Self-review

Cobertura del spec: §3 → T1–T2; §4 → T3; §5 → T4; §6 → T1–T4 y regresión T5; §7 → T5. Firmas consistentes entre tareas (`ausentismo`, `simultaneos`, `cobertura`, `cambios_resumen`, `Barras.poner`, `Linea.poner`). Entregas 2 y 3 quedan fuera por acuerdo.
