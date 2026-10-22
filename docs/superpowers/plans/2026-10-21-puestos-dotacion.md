# Puestos de trabajo y calculadora de dotación — Plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convertir los puestos en datos editables con reglas de demanda por tramos de 30 min, derivar de ellos la cobertura, repartir personas por puesto y tramo, y calcular cuántas personas se necesitan.

**Architecture:** Un módulo puro nuevo (`demanda.py`) concentra el modelo de tramos; la base pasa a las versiones 4 y 5; el solver y la validación leen la demanda por tramo; el reparto de puestos es un CP-SAT por día; la calculadora combina una fórmula por horas con una búsqueda del mínimo de personas usando el mismo solver. La interfaz nueva vive en `ui_puestos.py` para no crecer `app.py`.

**Tech Stack:** Python 3.13/3.14, PySide6, OR-Tools CP-SAT, SQLite, openpyxl. Sin dependencias nuevas.

**Spec:** `docs/superpowers/specs/2026-10-21-puestos-dotacion-design.md`

## Global Constraints

- Interfaz y mensajes en español; no renombrar hojas ni etiquetas de los Excel existentes.
- Tramo = **30 min**, **48 tramos** por día; horas de reglas en múltiplos de 30 min (`inicio`, `fin` en minutos desde las 00:00; si `fin <= inicio` cruza medianoche).
- `tipo_dia` ∈ {`"LS"` (lunes a sábado), `"DF"` (domingo y festivo)}, el del día en que **empieza** la ventana.
- Franjas: M 06:00–12:00, T 12:00–18:00, N 18:00–06:00. Un turno cuenta en una franja si se solapa **≥ 3 h**.
- Margen de ausentismo por defecto **10 %** (parámetro `dotacion_margen_pct`).
- Pruebas: `.venv/bin/python test_turnos.py`, `.venv/bin/python test_gui.py` y el nuevo `.venv/bin/python test_puestos.py`; cada una imprime `OK`. Sin frameworks.
- Los datos no salen del equipo; `turnos.db` no se versiona. Cada commit termina con `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>`.
- Un puesto o turno en uso no se borra: se desactiva.

## Review Focus

1. **Ventana nocturna que cruza medianoche cuando cambia el tipo de día** (sábado de noche → domingo): la demanda del domingo de madrugada viene del sábado. Test en Task 1.
2. **Primer día de un periodo con una ventana que viene de la noche del periodo anterior:** debe contar la presencia de `previo`. Test en Task 8.
3. **Puesto sin reglas, o ventana obligatoria que ningún turno del catálogo cubre:** se avisa, no se rompe. Tests en Tasks 1 y 4.
4. **Borrar un puesto en uso y guardar a una persona sin ningún puesto permitido:** se desactiva / se rechaza con mensaje. Tests en Tasks 2 y 5.
5. **Demanda mayor que el personal (infactible):** el generador reporta faltantes sin lanzar error y la calculadora lo cuantifica o explica. Tests en Tasks 8 y 12.

---

## Estructura de archivos

| Archivo | Responsabilidad |
|---|---|
| `demanda.py` (nuevo) | Modelo puro de tramos: ventanas, demanda por fecha, franjas de un turno, cobertura derivada, huecos sin turno, estimación por horas |
| `dotacion.py` (nuevo) | Calculadora: estimación y búsqueda del mínimo de personas |
| `ui_puestos.py` (nuevo) | Widgets `TabPuestos` y `TabDotacion` |
| `test_puestos.py` (nuevo) | Pruebas del núcleo nuevo |
| `dominio.py` | `Puesto`, `Demanda`, campos nuevos en `Colaborador` y `Contexto` |
| `db.py` | Tablas y migración v4 y v5, CRUD de puestos y demanda, `contexto` |
| `solver.py`, `reglas.py`, `puestos.py`, `flujo.py`, `exportar.py`, `app.py` | Se adaptan en las tasks indicadas |

---

## FASE 1 — Puestos y demanda

### Task 1: Modelo de tramos y demanda (`demanda.py`)

**Files:** Create `demanda.py`, `test_puestos.py`. Modify `dominio.py` (agregar dataclasses).

**Interfaces:**
- Produces en `dominio.py`: `Puesto(id:int, numero:int, nombre:str, color:str="FFFFFF", activo:bool=True)`; `Demanda(puesto_id:int, tipo_dia:str, inicio:int, fin:int, personas:int, obligatorio:bool=True, id:int=None)`; `Contexto.puestos: dict[int, Puesto]` y `Contexto.demandas: list[Demanda]` (ambos con default vacío).
- Produces en `demanda.py`: `TRAMOS_DIA = 48`; `tramos_ventana(inicio:int, fin:int) -> list[tuple[int,int]]` (pares `(dia_offset, tramo)`, offset 1 = día siguiente); `franjas_de(turno) -> tuple[str,...]`; `turno_tramos(turno) -> list[tuple[int,int]]`; `demanda_fecha(ctx, fecha) -> tuple[list[int], list[int]]` (obligatoria y deseable por tramo, 48 enteros cada una); `cobertura_derivada(demandas) -> dict` (`{"LS": {"M":n,"T":n,"N":n}, "DF": {...}}`, la mayor demanda simultánea **obligatoria** por franja); `huecos_sin_turno(demandas, turnos) -> list[tuple[int,int]]`; `horas_persona_semana(demandas, obligatorio:bool=True) -> float` (6 días LS + 1 DF); `estimar_personas(demandas, jornada_media:float, margen:float, incluir_deseables:bool=False) -> dict` con `horas_semana`, `personas`, `por_puesto` ({puesto_id: horas}), `por_franja` ({"M","T","N": horas}).

- [ ] **Step 1: Escribir las pruebas** en `test_puestos.py` (sigue el estilo de `test_turnos.py`: funciones `test_*`, `__main__` que las ejecuta e imprime `OK`):
  - `test_tramos_ventana`: `tramos_ventana(360, 720) == [(0, t) for t in range(12, 24)]`; `tramos_ventana(1080, 360)` tiene 24 pares, empieza en `(0, 36)` y termina en `(1, 11)`.
  - `test_franjas_de`: `Turno("M7","",420,780)` → `("M",)`; `Turno("C","",360,1080)` → `("M","T")`; `Turno("NC","",1080,360)` → `("N",)`.
  - `test_demanda_cruza_medianoche_y_tipo_de_dia` (Review Focus 1): puesto «Guardia» con `LS`, 18:00–06:00, 2 personas, y `DF`, 18:00–06:00, 1 persona. Sábado 17-oct-2026: `obl[40] == 2` (22:00 hoy). Domingo 18-oct: `obl[2] == 2` (madrugada que viene del sábado, tipo `LS`) y `obl[40] == 1`.
  - `test_cobertura_derivada_conserva_el_4_4_2`: con las demandas por defecto de la Task 2 se obtiene `{"LS": {"M":4,"T":4,"N":2}, "DF": {"M":2,"T":2,"N":2}}` (esta prueba se completa en la Task 2; aquí se prueba con un caso a mano: Lavado `LS` 06–18 ×2 + Autoclave `LS` 08–14 ×1 → `{"M":3,"T":3,"N":0}`).
  - `test_huecos_sin_turno`: demanda `LS` 08:00–14:00 con solo los turnos M (06–12) y T (12–18) activos → `[]`; con solo NC → `[(480, 840)]`; un turno con `dom_fest=False` no cubre demanda `DF`.
  - `test_estimar_personas`: Lavado `LS` 06–18 ×2 y `DF` 06–12 ×1 → `horas_semana == 150`; con jornada 42 y margen 0,10 → `personas == 4` (3,97 redondeado hacia arriba); `incluir_deseables=True` suma las reglas deseables.

- [ ] **Step 2:** Ejecutar `.venv/bin/python test_puestos.py` → FALLA (`ModuleNotFoundError: demanda`).
- [ ] **Step 3:** Implementar las dataclasses y `demanda.py` con las firmas de Interfaces. `demanda_fecha` suma las ventanas con `ctx.tipo_dia(fecha)` en offset 0 y las de `fecha - 1 día` (con su propio `tipo_dia`) en offset 1. `estimar_personas` redondea hacia arriba con `math.ceil`.
- [ ] **Step 4:** Ejecutar `.venv/bin/python test_puestos.py` → `OK`.
- [ ] **Step 5:** `git add demanda.py dominio.py test_puestos.py && git commit -m "feat: slot-based demand model"`.

### Task 2: Base de datos v4 — puestos, demanda, migración y contexto

**Files:** Modify `db.py`, `dominio.py` (`Colaborador.puestos_permitidos: tuple = None`, ids de puesto), `test_puestos.py`.

**Interfaces:**
- Consumes: Task 1 (`Puesto`, `Demanda`, `cobertura_derivada`).
- Produces en `BD`: `puestos(solo_activos:bool=False) -> dict[int, Puesto]`; `guardar_puesto(p:Puesto) -> int`; `borrar_puesto(id:int) -> str` (`"borrado"` o `"desactivado"`); `demandas(puesto_id:int=None) -> list[Demanda]`; `reemplazar_demandas(puesto_id:int, demandas:list[Demanda]) -> None`; `guardar_colaborador` y `colaboradores` leen y escriben `puestos_permitidos` (tabla `persona_puesto`; `None` = puede todos, nunca una tupla vacía). `BD.contexto(año)` llena `puestos`, `demandas` y **deriva** `cobertura` con `cobertura_derivada` de las demandas obligatorias de puestos activos. `PRAGMA user_version = 4`.

- [ ] **Step 1: Pruebas** en `test_puestos.py`:
  - `test_semilla_y_cobertura_derivada`: `BD()` nueva tiene 6 puestos (1 Lavado, 2 Autoclave, 3 Sterrad y esto, 4 Cuarto estéril, 5 Ropa, 6 Guardia noche), 9 demandas (LS: 4 obligatorias de 06:00–18:00 ×1 en los puestos 1–4, Ropa deseable ×1 y Guardia noche 18:00–06:00 ×2; DF: Autoclave y Lavado 06:00–18:00 ×1 y Guardia noche ×2) y `bd.contexto(2026).cobertura == {"LS": {"M":4,"T":4,"N":2}, "DF": {"M":2,"T":2,"N":2}}`.
  - `test_migracion_v3_a_v4`: crear una base con el esquema v3 (copiar de una `BD` nueva, borrar las tablas nuevas y poner `user_version=3` con `cobertura` {LS 5/4/2, DF 2/2/2} y una persona con `puesto_fijo=3`), reabrir: el excedente de 1 persona de mañana de `LS` queda como `personas=2` del primer puesto (Autoclave), la persona tiene `puestos_permitidos == (id del puesto 3,)`.
  - `test_borrar_puesto_en_uso` (Review Focus 4): con una fila en `puesto_dia` de número 2, `borrar_puesto(id_autoclave) == "desactivado"` y desaparece de `puestos(solo_activos=True)`; un puesto nuevo sin uso devuelve `"borrado"`.
  - `test_puestos_permitidos_roundtrip`: guardar `Colaborador(..., puestos_permitidos=(1,2))`, leer igual; `None` se conserva como `None`.

- [ ] **Step 2:** Ejecutar → FALLA.
- [ ] **Step 3:** Implementar. Tablas: `puesto(id, numero, nombre, color, activo)`, `demanda(id, puesto_id, tipo_dia, inicio, fin, personas, obligatorio)`, `persona_puesto(colab_id, puesto_id)`. `_migrar_a_4` crea las tablas y siembra los puestos y demandas desde la tabla `cobertura` con el algoritmo del spec §9 (reparto por prioridad 2,1,3,4; excedente al primero; fusión de reglas adyacentes iguales; Ropa deseable en `LS`; Guardia noche con la cantidad de la franja N). La base nueva usa la misma función de siembra con `COBERTURA_BASE`. La cadena de migraciones sigue el patrón `_migrar_a_3`.
- [ ] **Step 4:** Ejecutar `test_puestos.py`, `test_turnos.py` y `test_gui.py` → `OK` (ningún cambio de comportamiento visible).
- [ ] **Step 5:** Commit `feat: posts and demand tables with v4 migration`.

### Task 3: Estimación de dotación (`dotacion.py`)

**Files:** Create `dotacion.py`. Modify `test_puestos.py`.

**Interfaces:**
- Consumes: `demanda.estimar_personas`, `BD.demandas`, `BD.colaboradores`, `BD.param`.
- Produces: `estimar(bd, incluir_deseables:bool=False) -> dict` con las claves de `estimar_personas` más `activos:int` (personal con `en_solver`), `jornada_media:float`, `margen:float`, `diferencia:int` (`activos - personas`; negativo = faltan).

- [ ] **Step 1: Prueba** `test_estimar_con_la_base`: con la semilla de la Task 2 y 13 personas de 42 h, `estimar(bd)` da `horas_semana` igual a (4 puestos × 12 h × 6 días + 2 puestos × 12 h × 1 día + guardia noche 2 × 12 h × 7 días) = 288 + 24 + 168 = **480**, `personas == 13` (480 ÷ (42 × 0,9) = 12,7 → 13), `diferencia == 0`; con `dotacion_margen_pct=0` → `personas == 12`.
- [ ] **Step 2:** Ejecutar → FALLA.
- [ ] **Step 3:** Implementar leyendo `dotacion_margen_pct` (default `"10"`) y promediando `horas_sem × pct` de las personas en solver.
- [ ] **Step 4:** Ejecutar → `OK`. **Step 5:** Commit `feat: staffing estimate`.

### Task 4: Pestaña Parámetros → Puestos

**Files:** Create `ui_puestos.py` (`TabPuestos`). Modify `app.py` (montar la pestaña; quitar la tarjeta «Cobertura requerida» y `s_cob`, `_guardar_reglas` ya no guarda cobertura), `test_gui.py`.

**Interfaces:**
- Consumes: Tasks 1–2.
- Produces: `TabPuestos(ventana: Ventana)`: lista de puestos (número, nombre, color, activo) a la izquierda y, a la derecha, formulario y tabla de reglas (tipo de día, desde, hasta, personas, obligatorio; botones «Agregar regla» y «Quitar regla»); botones Guardar, «+ Nuevo puesto» y Eliminar. Métodos públicos `refrescar()`, `nuevo()`, `guardar()`, `eliminar()`. Mismo patrón visual que la pestaña Turnos (tokens, estados vacíos con `con_vacio`).

- [ ] **Step 1: Prueba GUI** en `test_gui.py` (`test_puestos_ui`): crear un puesto «Esterilización de lencería» con una regla `LS` 08:00–14:00 ×2 obligatoria → `bd.demandas(id)` tiene esa regla y `ventana.ctx.cobertura["LS"]["M"]` pasa a incluir 2 personas más en el pico de 08:00–12:00; editarla a 3 personas y guardar; eliminar un puesto sin uso lo borra y con uso lo desactiva (mensaje «inactivo»). Una ventana con inicio igual a fin muestra el error «El puesto no puede empezar y terminar a la misma hora.» y no guarda. Con solo el turno NC activo, guardar una regla de mañana muestra el aviso «Ningún turno cubre 08:00–14:00» (Review Focus 3) y **sí guarda**. Un puesto sin reglas se guarda y la lista lo marca «Sin demanda». Dos reglas solapadas del mismo puesto y tipo de día se guardan con el aviso «Las reglas solapadas se suman».
- [ ] **Step 2:** Ejecutar `test_gui.py` → FALLA. **Step 3:** Implementar `TabPuestos`; validar `personas >= 1` y minutos múltiplos de 30 (los `QTimeEdit` usan paso de 30 min); el aviso usa `demanda.huecos_sin_turno` con los turnos activos y `solver=True`.
- [ ] **Step 4:** Ejecutar `test_gui.py` y `test_turnos.py` → `OK`. **Step 5:** Commit `feat: posts editor in parameters`.

### Task 5: Puestos permitidos en la ficha de personal

**Files:** Modify `app.py` (ficha de Personal: casillas por puesto activo reemplazan el combo «Puesto fijo»), `db.py` (derivar `puesto_fijo` del número del puesto cuando hay uno solo permitido, para que `puestos.asignar` actual siga funcionando), `test_gui.py`.

**Interfaces:** Consumes Task 2 (`Colaborador.puestos_permitidos`). Produces: en la ficha, `p_puestos_cbs: dict[int, QCheckBox]` (puesto id → casilla).

- [ ] **Step 1: Prueba** `test_puestos_permitidos_en_ficha`: marcar solo el puesto 3 → guardado `puestos_permitidos == (id3,)` y `puesto_fijo == 3`; marcar todos → `None`; no marcar ninguno → error «Marca al menos un puesto que pueda ocupar.» y no guarda (Review Focus 4).
- [ ] **Step 2–4:** Fallar, implementar (mismo patrón que `p_perm_cbs`), pasar. **Step 5:** Commit `feat: allowed posts per person`.

### Task 6: Pestaña Dotación (estimación)

**Files:** Modify `ui_puestos.py` (`TabDotacion`), `app.py` (pestaña principal «Dotación» antes de «Parámetros»), `test_gui.py`.

**Interfaces:** Produces `TabDotacion(ventana)` con casilla «Incluir puestos deseables», margen (`QSpinBox` 0–50 % ligado a `dotacion_margen_pct`), cifras (horas-persona por semana, personas necesarias, personal activo, diferencia con texto «Faltan 2» o «Sobran 1»), y tablas por puesto y por franja. Se actualiza en vivo al cambiar el margen o la casilla y en `refrescar()`.

- [ ] **Step 1: Prueba** `test_tab_dotacion`: con la semilla, la cifra mostrada es 13 personas y «Al día»; subir el margen a 20 % muestra «Faltan 2»; la tabla por franja suma lo mismo que las horas totales.
- [ ] **Step 2–4:** Fallar, implementar, pasar. **Step 5:** Commit `feat: staffing tab with hour-based estimate`.

---

## FASE 2 — Cobertura por tramos

### Task 7: `Turno.cubre` calculado

**Files:** Modify `db.py` (`turnos()` asigna `cubre=franjas_de(turno)` ignorando la columna guardada), `app.py` (quitar las casillas de «Cubre» del formulario de turnos; el resumen muestra «Cuenta en: mañana, tarde»), `test_gui.py`, `test_turnos.py`.

- [ ] **Step 1: Pruebas:** `bd.turnos()["C"].cubre == ("M","T")`; un turno nuevo `M7` 07:00–13:00 guardado con cualquier valor previo queda `("M",)`; `test_gui` verifica que el formulario ya no tiene `t_cubre` y que el resumen menciona la franja.
- [ ] **Step 2–4:** Fallar, implementar, pasar con las tres suites. **Step 5:** Commit `feat: derive shift franjas from times`.

### Task 8: Solver con cobertura por tramos y deseables

**Files:** Modify `solver.py`, `test_turnos.py`.

**Interfaces:**
- Consumes: `demanda.demanda_fecha`, `demanda.turno_tramos`.
- Produces: `solver.generar(..., estricto:bool=False)`; con `estricto=True` la demanda obligatoria es restricción dura (sin variable `falta`) y la infactibilidad lanza `ErrorSolver`. `info["faltan"]` pasa a `[(fecha, tramo, n)]` (tramo = índice 0–47). Constantes `W_DESEABLE = 10` (por tramo cubierto).

- [ ] **Step 1: Pruebas** en `test_turnos.py`:
  - `test_cobertura_por_tramos_con_turno_parcial`: puesto con demanda `LS` 07:00–13:00 ×1 y turnos M7 (07:00–13:00) y NC → con 3 personas, todo día de lunes a sábado tiene a alguien en M7 y `info["faltan"] == []`.
  - `test_primer_dia_cuenta_la_noche_previa` (Review Focus 2): demanda de madrugada (00:00–06:00 ×1, `LS`) y `previo={(1, dia_anterior): "NC"}` → el día 1 del periodo no genera faltante en esos tramos aunque nadie más cubra la madrugada.
  - `test_deseable_se_busca_sin_romper_reglas`: con una regla deseable de Ropa y personal de sobra, el cuadro cubre la mayoría de los tramos deseables; con personal justo, no aparece alerta de descanso ni de rachas.
  - `test_demanda_mayor_que_el_personal` (Review Focus 5): 2 personas y demanda obligatoria de 6 simultáneas → `generar` no lanza error, `info["faltan"]` no está vacío; con `estricto=True` lanza `ErrorSolver`.
  - `test_mes_completo` existente sigue pasando y su resolución tarda **≤ 20 s** (si no, aplicar la optimización de agrupar tramos consecutivos iguales y documentarlo en `ARQUITECTURA.md`).
- [ ] **Step 2–4:** Fallar, implementar (por día y tramo: presencia = suma de variables de turnos que cubren ese tramo hoy más los de ayer que lo cubren con offset 1, más constantes de `previo` en el primer día), pasar. Eliminar el término de sobrante por franja anterior. **Step 5:** Commit `feat: slot-level coverage in the solver`.

### Task 9: Validación, grilla y Excel con cobertura por tramos

**Files:** Modify `reglas.py` (reemplaza `cobertura_dia` por `faltantes_dia`), `app.py` (filas de cobertura de la grilla y leyenda), `exportar.py` (celdas rojas), `test_turnos.py`, `test_gui.py`.

**Interfaces:** Produces `reglas.faltantes_dia(ctx, cuadro, fecha) -> dict[str, tuple[int, list[tuple[int,int,int]]]]`: por franja `"M"|"T"|"N"`, `(faltante_máximo, [(tramo_ini, tramo_fin, falta), ...])` agrupando tramos consecutivos con la misma falta. `validar` emite un error por día y franja con faltante con texto «dd/mm: faltan N en <franja> (08:00–10:00)».

- [ ] **Step 1: Pruebas:** con demanda ×2 en 08:00–12:00 y una sola persona en M, `faltantes_dia(...)["M"] == (1, [(16, 24, 1)])`; `validar` genera el error con el rango; la grilla muestra «ok» o «−1» en las tres filas y el tooltip lista el rango; `exportar_cuadro` pinta de rojo la misma celda.
- [ ] **Step 2–4:** Fallar, implementar, pasar con las tres suites. **Step 5:** Commit `feat: slot coverage in validation, grid and Excel`.

---

## FASE 3 — Reparto por tramo

### Task 10: Reparto de puestos por persona y tramo + base v5

**Files:** Modify `puestos.py` (reescribir `asignar`), `db.py` (tabla `asignacion_puesto` y migración v5 de las filas antiguas de `puesto_dia`), `test_puestos.py`.

**Interfaces:**
- Consumes: Tasks 1–2, `Colaborador.puestos_permitidos`, `Contexto.demandas`.
- Produces: `AsignacionPuesto = namedtuple("AsignacionPuesto", "fecha colab_id puesto_id desde hasta pausa")` (`desde`/`hasta` en minutos del día; `puesto_id` 0 = apoyo); `puestos.asignar(ctx, cuadro, fechas) -> list[AsignacionPuesto]`; `BD.guardar_asignacion_puesto(periodo, filas)` y `BD.asignacion_puesto(periodo) -> list[AsignacionPuesto]`; `puestos.por_persona(filas) -> dict[(colab_id, fecha), int]` devuelve el **número** del puesto donde la persona pasa más tramos (0 = apoyo).

- [ ] **Step 1: Pruebas:**
  - `test_asignar_cubre_la_demanda_por_tramo`: 3 personas (una C, una M, una T) y un puesto con demanda 06:00–18:00 ×1 y otro 12:00–18:00 ×1 → cada tramo de demanda tiene al menos las personas requeridas y nadie ocupa dos puestos en el mismo tramo.
  - `test_respeta_puestos_permitidos`: la persona con solo el puesto 3 nunca queda en otro.
  - `test_varias_personas_en_un_puesto`: Lavado ×2 → dos personas simultáneas en el puesto.
  - `test_corrido_conserva_el_puesto_si_puede`: un C con dos puestos posibles cambia de puesto solo cuando la demanda lo exige.
  - `test_apoyo_cuando_sobra_gente`: persona de más → `puesto_id == 0`.
  - `test_migracion_v4_a_v5_conserva_el_reparto`: una fila antigua `(fecha, "M", puesto 2, colab 1, pausa 1)` pasa a `AsignacionPuesto(fecha, 1, id_autoclave, 360, 720, 1)`.
- [ ] **Step 2–4:** Fallar; implementar `asignar` como un CP-SAT por día (variables persona × puesto × tramo para los tramos en que la persona está presente; una persona por puesto-tramo, demanda obligatoria dura salvo faltante inevitable, deseables suaves, penalización por cambiar de puesto, por repetir el del día anterior y por desequilibrio acumulado); pasar. El grupo de pausa se asigna como hoy (`(posición + fecha.toordinal()) % 2 + 1`). **Step 5:** Commit `feat: per-slot post assignment`.

### Task 11: Consumidores del reparto (flujo, cuadro, pestaña Puestos y Excel)

**Files:** Modify `flujo.py` (`recalcular` guarda `asignacion_puesto`), `app.py` (`_ver_cuadro` y `_ver_puestos` leen el reparto nuevo; «Mostrar puesto» usa `por_persona`), `exportar.py` (`exportar_puestos` y la hoja «Cuadro con puestos»), `test_turnos.py`, `test_gui.py`.

- [ ] **Step 1: Pruebas:** `flujo.recalcular` deja filas en `asignacion_puesto` del periodo; `etiqueta` en la grilla da `M·2` con el número del puesto principal; el aviso de la celda lista los cambios («Autoclave 06:00–12:00, Lavado 12:00–18:00»); `exportar_puestos` tiene una columna por puesto activo con nombre y ventana por persona.
- [ ] **Step 2–4:** Fallar, implementar (la tabla `puesto_dia` queda sin uso), pasar con las tres suites. **Step 5:** Commit `feat: show slot-level post assignment`.

---

## FASE 4 — Verificación con el generador

### Task 12: Búsqueda del mínimo de personas

**Files:** Modify `dotacion.py`, `test_puestos.py`.

**Interfaces:**
- Consumes: `solver.generar(..., estricto=True)`, `dotacion.estimar`.
- Produces: `dotacion.verificar_minimo(ctx, fechas, margen:float, activos:int, tiempo:int=8, progreso=None, cancelar=None) -> dict` con `minimo:int|None`, `con_margen:int|None`, `activos:int`, `diferencia:int|None`, `pruebas:list[tuple[int,bool]]`, `motivo:str|None`. `progreso(n, total)` y `cancelar() -> bool` son callbacks opcionales. Usa `dataclasses.replace(ctx, colabs=[personas genéricas de 42 h], novedades=[])`.

- [ ] **Step 1: Pruebas:** `test_biseccion_con_resolutor_simulado`: con `solver.generar` reemplazado por una función que lanza `ErrorSolver` si hay menos de 7 personas, `verificar_minimo` devuelve `minimo == 7` con a lo sumo 6 pruebas y respeta `cancelar` (devuelve lo hecho hasta ese momento); `test_sin_solucion_explica` (Review Focus 5): con una demanda imposible de cumplir con cualquier `N` hasta el tope, `minimo is None` y `motivo` explica «ninguna cantidad de personas cumple las reglas…»; `test_con_margen`: `con_margen == ceil(minimo / (1 - margen))`.
- [ ] **Step 2–4:** Fallar, implementar (cota inferior = `estimar_personas` sin margen; bisección entre esa cota y el doble; tope 60; supuesto de monotonía documentado en un comentario), pasar. **Step 5:** Commit `feat: minimum staffing search`.

### Task 13: Verificación en la pestaña Dotación

**Files:** Modify `ui_puestos.py`, `test_gui.py`.

**Interfaces:** `TabDotacion` gana el botón «Verificar con el generador» (corre en un `QThread` como `Trabajo`, con barra de avance y botón Cancelar), y un panel de resultado: «Mínimo con tus reglas: N · Con margen: M · Personal activo: A · Faltan/Sobran X», más el diagnóstico si no hay solución.

- [ ] **Step 1: Prueba** `test_verificar_en_la_interfaz`: con `verificar_minimo` simulado, el panel muestra los números, el botón se deshabilita mientras corre y se rehabilita al terminar; cancelar deja el aviso «Verificación cancelada».
- [ ] **Step 2–4:** Fallar, implementar, pasar con las tres suites. **Step 5:** Commit `feat: staffing verification in the UI`.

### Task 14: Documentación, capturas y cierre

**Files:** Modify `README.md`, `docs/GUIA_USUARIO.md`, `docs/REGLAS.md`, `docs/ARQUITECTURA.md`, `docs/HOJA_DE_RUTA.md`, `docs/VISION.md`, `CLAUDE.md`, capturas en `docs/img/`.

- [ ] **Step 1:** Actualizar la guía (cómo crear puestos y reglas, puestos permitidos, pestaña Dotación y su verificación), las reglas (obligatorio vs deseable, margen), la arquitectura (tramos, tablas v4/v5, `demanda.py`, `dotacion.py`, `ui_puestos.py`), el README (nueva fila de funciones y capturas de Puestos y Dotación) y la hoja de ruta (quitar lo hecho; añadir copia de seguridad, registro de cambios y Excel del banco como siguientes).
- [ ] **Step 2:** Regenerar las capturas con el script del repositorio.
- [ ] **Step 3:** Ejecutar `.venv/bin/python test_turnos.py`, `test_gui.py` y `test_puestos.py` → los tres imprimen `OK`.
- [ ] **Step 4:** Commit `docs: posts and staffing documentation` y push.
