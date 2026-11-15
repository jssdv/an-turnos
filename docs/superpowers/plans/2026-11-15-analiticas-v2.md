# Analíticas v2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add trend lines, schedule stability, fatigue history, absence patterns with a risk warning, and a print and Excel report to Analíticas.

**Architecture:** Every metric is a read-only function in `an/turnos/analitica.py`. Each one is returned as a new key of `GET /api/areas/{a}/analiticas`. The front end draws them with hand SVG components in a new `web/src/componentes/Graficos.tsx`. Inicio already calls `/analiticas` for the current period, so its new tiles read the same response.

**Tech Stack:** Python 3.13, FastAPI, SQLite, openpyxl, React 19, Tailwind 4. No new dependencies.

**Spec:** `docs/superpowers/specs/2026-11-15-analiticas-v2-design.md`

## Global Constraints

- UI text and messages are in Spanish. Do not rename existing Excel sheets or labels.
- Thresholds are data: read with `bd.param(clave, defecto)`, list them in `RANGOS_PARAMETROS` (`an/web/rutas_catalogos.py:15`), and show them in `NUM` and `GRUPOS` (`web/src/pantallas/Parametros.tsx:14,38`) under a new group «Analíticas».
  - `aviso_corto_horas`: default 48, range 1–336.
  - `max_dias_seguidos`: default 6, range 1–14.
  - `descanso_corto_horas`: default 12, range 1–24.
- Count only people with `p.en_solver`, as the existing metrics do.
- Bradford and weekday patterns count only unplanned absences, so «Vacaciones» and «Libre solicitado» are left out.
- The per-person Bradford table carries this exact note: «Indicador de patrones; no usar para sanciones».
- Every behaviour change leaves an assert test in `tests/turnos/test_analitica.py`. These tests run as plain functions with `bd = db.BD()`, like the existing ones.
- One branch and one PR per task. Push, open a PR to main, and merge when CI is green.
- Never commit `turnos.db` or staff data.

## Review Focus

1. **Range with no periods or no people:** every new function returns empty structures, not a `max()` or division error. Add `test_*_vacio` to each task.
2. **Period never published:** stability skips it instead of showing 0 %. Pinned in Task 2.
3. **Shift that crosses midnight** (a night shift): the short-rest and notice calculations use `dominio.intervalo`, not the calendar date. Pinned in Tasks 2 and 3.
4. **Absence spell crossing the range edge:** spells are clipped to `[ini, fin]` like `_ausencias`, so one spell is not counted twice. Pinned in Task 4.
5. **Inicio when nothing is at risk or tired:** the tiles show a calm state («Sin días de riesgo»), not an empty or alarming one. Checked in the browser in Tasks 3 and 4.

---

### Task 1: Trend lines (frontend only)

**Files:**
- Create: `web/src/componentes/Graficos.tsx`
- Create: `web/pruebas/graficos.test.ts`
- Modify: `web/src/pantallas/Analiticas.tsx`. Move `Barras` (L25-44) out, extend `Datos`, and add 3 charts.

**Interfaces:**
- Produces:
  - `Barras({ titulo, unidad, datos }: { titulo: string; unidad: string; datos: [string, number][] })`. Unchanged and moved.
  - `Linea({ titulo, unidad, etiquetas, series }: { titulo: string; unidad: string; etiquetas: string[]; series: { nombre: string; valores: number[] }[] })`
  - `trazo(valores: number[], ancho: number, alto: number, max: number): string`. Pure SVG path builder, exported for the test.

- [ ] **Step 1: Write a failing test in `web/pruebas/graficos.test.ts`.**
  - `trazo([0, 5, 10], 100, 50, 10) === "M0,50 L50,25 L100,0"`
  - `trazo([3], 100, 50, 0) === "M0,50"` (one point with max 0 must not produce NaN)
- [ ] **Step 2: Run `cd web && npm test` and confirm it fails because the import is missing.**
- [ ] **Step 3: Implement `Graficos.tsx`.**
  - `Linea` renders an `<svg role="img" aria-label={titulo}>` with a fixed `viewBox`, `trazo` for each series, and a legend that shows each series name next to a colour swatch.
  - Series colours come from brand/utility tokens, so no raw hex values.
  - Show sparse x labels (first, middle and last) and the max value on the y axis.
  - With no data, render «Sin datos en el rango.», like `Barras`.
- [ ] **Step 4: Run `npm test`. It should pass.**
- [ ] **Step 5: Add the three charts to Analíticas.**
  - Extend `Datos` with `ausentismo.por_mes: Record<string, Record<string, number>>`, `simultaneos.serie: [string, number][]` and `banco.serie: [string, number, number][]`.
  - Add a two-column grid after the existing bars:
    - «Ausencias por mes»: one series per entry of `TIPOS`, labelled `MM/AA`.
    - «Ausentes a la vez»: daily series.
    - «Banco de horas»: two series, «A favor» and «En deuda».
- [ ] **Step 6: Run `npm run build` and check it passes. Then check in the browser with demo data:** charts visible, no console errors, no horizontal scroll at 375 px.
- [ ] **Step 7: Commit on branch `analiticas-tendencias`, then open a PR and merge it.**

### Task 2: Schedule stability

**Files:**
- Modify: `an/turnos/analitica.py`. Add `estabilidad`.
- Modify: `an/web/rutas_areas.py:176-183`. Add the `"estabilidad"` key and read `publicado_en`.
- Modify: `an/web/rutas_catalogos.py:15`, `web/src/pantallas/Parametros.tsx`. Add `aviso_corto_horas` and the «Analíticas» group.
- Modify: `web/src/pantallas/Analiticas.tsx`
- Test: `tests/turnos/test_analitica.py`

**Interfaces:**
- Produces: `estabilidad(bd, ini: date, fin: date, publicados: dict[str, datetime]) -> dict`
  - The return value is `{"periodos": [{"periodo": str, "celdas_cambiadas": int, "celdas_total": int, "pct": float, "aviso_corto": int, "dias_anticipacion": int | None}], "cubre_mas": {nombre: int}}`.
  - `publicados` maps a period key to its `publicado_en`. The core `BD` has no `periodo` table, so the route builds the dict with `SELECT clave, publicado_en FROM periodo` and passes it in.

- [ ] **Step 1: Write failing tests.**
  - `test_estabilidad_pct_y_sin_publicar`:
    - Save a 7-day cuadro with 3 people, all working `M`: `celdas_total == 21`.
    - Call `bd.set_celda` on 2 cells, then pass `publicados={K: datetime(...)}`. Expect `celdas_cambiadas == 2` and `pct ≈ 2/21*100`.
    - With `publicados={}`, the period does not appear in `periodos`.
  - `test_estabilidad_aviso_corto`:
    - Call `cambios.servicio(bd, K, [(cid, D, "T")], "prueba", "u")` (`cambios.py:138`) for a cell dated D.
    - Patch `registrado_en` in `cambio_turno` to `D-1 20:00`. The shift `M` on D starts less than 48 h later, so `aviso_corto == 1`.
    - Move it to `D-5`: `aviso_corto == 0`.
    - Anulled rows do not count.
  - `test_estabilidad_dias_anticipacion`: published 10 days before the period starts, so `dias_anticipacion == 10`.
  - `test_estabilidad_cubre_mas`: a `servicio` change that gives B a shift on a day B had `L` makes `cubre_mas == {"B": 1}`.
  - `test_estabilidad_vacio`: `db.BD()` returns `{"periodos": [], "cubre_mas": {}}`.
- [ ] **Step 2: Run `pytest tests/turnos/test_analitica.py -k estabilidad -v` and confirm it fails.**
- [ ] **Step 3: Implement `estabilidad`.**
  - `celdas_total`: number of (person × day) cells of `en_solver` people in the period.
  - `celdas_cambiadas`: `len(bd.diferencias(k))`.
  - Notice: for each non-anulled row of `cambios.listar(bd, k)` and each cell `[cid, fecha, antes, despues, …]`, take the start of `despues`, or of `antes` if `despues` is `L`, via `dominio.intervalo(ctx.turnos[cod], fecha)[0]`. Use midnight if both are `L`. The cell counts when `inicio − registrado_en < timedelta(hours=int(bd.param("aviso_corto_horas", 48)))`.
  - `cubre_mas`: cells of `servicio` rows that go from `L` to a turno, counted per person.
- [ ] **Step 4: Run the tests. They should pass.**
- [ ] **Step 5: Route and settings.**
  - Add the key to the route.
  - Add `"aviso_corto_horas": (1, 336)` to `RANGOS_PARAMETROS`.
  - Add the `NUM` entry: «Cambio con poco aviso (horas)», with help text «Un cambio registrado con menos horas que esto antes del turno cuenta como de último momento.».
  - Add a new `GRUPOS` entry, «Analíticas».
  - Run `pytest tests/web/test_api.py tests/web/test_catalogos.py -q`.
- [ ] **Step 6: UI.**
  - Tile «Cambios tras publicar», showing the average `pct` and the note «N con poco aviso».
  - Section «Estabilidad del cuadro», a table with the columns Periodo, % cambiado, Celdas cambiadas, Con poco aviso and Publicado con (días).
  - `Barras` «Quién cubre más», unit «turnos».
- [ ] **Step 7: Build, check in the browser, then commit on branch `analiticas-estabilidad`, open a PR and merge it.**

### Task 3: Fatigue

**Files:**
- Modify: `an/turnos/analitica.py`. Add `fatiga`.
- Modify: `an/web/rutas_areas.py`, `an/web/rutas_catalogos.py:15`, `web/src/pantallas/Parametros.tsx`. Add `max_dias_seguidos` and `descanso_corto_horas`.
- Modify: `web/src/pantallas/Analiticas.tsx`, `web/src/pantallas/Inicio.tsx`
- Test: `tests/turnos/test_analitica.py`

**Interfaces:**
- Produces: `fatiga(bd, ini: date, fin: date) -> dict[str, dict]`
  - Keyed by `nombre`. Each value is `{"max_dias_seguidos": int, "rachas_largas": int, "max_noches_seguidas": int, "descansos_cortos": int, "fines_trabajados": int, "horas_4_sem_max": float, "senales": int}`.
  - `senales` counts these conditions:
    - `rachas_largas > 0`
    - `max_noches_seguidas > int(bd.param("max_noches_seguidas", 2))`
    - `descansos_cortos > 0`
    - `fines_trabajados` above the team mean + 1
- Consumes: the cuadro from `bd.asignaciones_rango(ini - timedelta(days=27), fin)`. The extra 27 days cover runs and the 4-week sum at the start of the range.

- [ ] **Step 1: Write failing tests.**
  - `test_fatiga_rachas`: A works `M` for 7 days in a row, so `max_dias_seguidos == 7` and `rachas_largas == 1` (default 6).
  - `test_fatiga_descanso_corto_cruza_medianoche`: in the base catalogue (`dominio.py:64-67`), `NC` ends at the start time of `M` on the next day. So A working `NC` on D and `M` on D+1 gives a gap of 0 h, and `descansos_cortos == 1`. `NC` followed by `L` adds 0. `T`→`M` is exactly 12 h, so it adds 0 by default, and 1 with `bd.set_param("descanso_corto_horas", 13)`.
  - `test_fatiga_noches`: three nights in the pattern N-L-N-L-N give `max_noches_seguidas == 3`. This is the same night-run rule as `reglas.validar:128-137` (step `libre_tras_noche + 1`), so reuse that logic rather than redefining it.
  - `test_fatiga_fines`: a weekend where A works Saturday or Sunday counts 1, and a fully free weekend counts 0.
  - `test_fatiga_vacio`: `db.BD()` returns `{}`.
- [ ] **Step 2: Run `pytest tests/turnos/test_analitica.py -k fatiga -v` and confirm it fails.**
- [ ] **Step 3: Implement `fatiga`.**
  - Short rest: for each pair of consecutive working days of one person, `intervalo(t_b, b)[0] − intervalo(t_a, a)[1] < hours(descanso_corto_horas)`.
  - `horas_4_sem_max`: the maximum over 28-day sliding windows that end inside the range, summing `turno.horas`.
  - Only days inside `[ini, fin]` count toward results. The 27 days before the range only seed runs and windows.
- [ ] **Step 4: Run the tests. They should pass.**
- [ ] **Step 5: Route key `"fatiga"`, plus the two settings, both in the «Analíticas» group.**
  - «Días seguidos de trabajo (aviso)»: help text «Rachas más largas que esto cuentan como señal de fatiga.».
  - «Descanso corto (horas)»: help text «Menos horas que esto entre dos turnos cuenta como regreso rápido.».
- [ ] **Step 6: UI.**
  - Section «Señales de fatiga» in Analíticas: a table sorted by `senales` desc, then name, with the columns Persona, Señales, Días seguidos (máx.), Noches seguidas (máx.), Descansos cortos, Fines trabajados and Horas en 4 semanas (máx.).
  - `Barras` «Fines de semana trabajados».
  - Inicio:
    - Extend `Resumen` with `fatiga`.
    - Add the tile «Fatiga», showing the count of people with `senales > 0` and the note «personas con señales este periodo», or «Sin señales».
    - The tile has tone `aviso` when the count is above 0 and links to `${r}/analiticas`.
- [ ] **Step 7: Build, check in the browser (including the calm Inicio state), then commit on branch `analiticas-fatiga`, open a PR and merge it.**

### Task 4: Absence patterns and risk

**Files:**
- Modify: `an/turnos/analitica.py`. Add `_rachas_ausencia`, `patrones_ausencia` and `riesgo_proximo`.
- Modify: `an/web/rutas_areas.py`, `web/src/pantallas/Analiticas.tsx`, `web/src/pantallas/Inicio.tsx`
- Test: `tests/turnos/test_analitica.py`

**Interfaces:**
- Produces:
  - `_rachas_ausencia(bd, ini, fin) -> list[tuple[int, str, date, date]]`
    - Each tuple is `(colab_id, tipo, desde, hasta)`: runs of consecutive days with the same person and tipo, built from `_ausencias` and so already clipped to the range.
    - Only unplanned tipos are kept: `NO_PLANEADAS = ("Incapacidad", "Licencia")`. Define it as a module constant.
  - `patrones_ausencia(bd, ini, fin) -> dict`
    - `"por_dia_semana": [float × 7]`: % of person-days absent for Monday to Sunday.
    - `"tras_festivo": int`: spells whose `desde` is the day after a festivo, or a Monday after a festive Sunday or Monday.
    - `"bradford": {"equipo": {"0-49": n, "50-199": n, "200-499": n, "500+": n}, "por_persona": {nombre: {"rachas": S, "dias": D, "puntaje": S*S*D}}}`
  - `riesgo_proximo(bd, hoy: date, dias: int = 14) -> list[dict]`
    - Each item is `{"fecha": date, "franjas": [str], "tasa": float, "media": float}`.
    - A day qualifies when it is in a saved cuadro, `reglas.margen_dia(...)` is ≤ 0 in some franja, and the unplanned absence rate for its weekday over the 365 days before `hoy` is above the mean of all 7 weekdays.

- [ ] **Step 1: Write failing tests.**
  - `test_bradford`:
    - Three 1-day Incapacidad absences for A give `puntaje == 27` (3²×3).
    - One 3-day Incapacidad absence for B gives 9.
    - Vacaciones for C do not appear.
    - `equipo == {"0-49": 3, ...}`. A, B and C all fall in 0–49; C counts with 0.
  - `test_rachas_recorta_borde`: an Incapacidad from 28/09 to 03/10 with the range starting 01/10 gives one spell of 3 days.
  - `test_por_dia_semana`: Incapacidad on 3 Mondays gives the Monday value as the highest and Tuesday as 0.
  - `test_riesgo_proximo`:
    - Build history with Incapacidad absences on past Mondays.
    - Make a cuadro where next Monday has exactly the obligatory staff, so the margin is 0.
    - Next Monday is in the result. A Tuesday with margin 0 but no history is not.
  - `test_patrones_vacio`: `db.BD()` returns `por_dia_semana == [0]*7`, `bradford.por_persona == {}`, and `riesgo_proximo(...) == []`.
- [ ] **Step 2: Run `pytest tests/turnos/test_analitica.py -k "bradford or rachas or dia_semana or riesgo or patrones" -v` and confirm it fails.**
- [ ] **Step 3: Implement the three functions.**
  - Weekday rate: absent person-days on that weekday ÷ (number of that weekday in the window × people).
  - Use `ctx.fest` for festivos.
- [ ] **Step 4: Run the tests. They should pass.**
- [ ] **Step 5: Route keys.**
  - `"patrones"`: `patrones_ausencia(desde, hasta)`
  - `"riesgo"`: `riesgo_proximo(ctx.bd, date.today())`
- [ ] **Step 6: UI in Analíticas, section «Patrones de ausencia (no planeadas)».**
  - Bar chart by weekday («Lun» to «Dom», unit «%»).
  - Line «N ausencias empezaron el día después de un festivo».
  - Bradford team table with the 4 buckets.
  - Bradford per-person table with the columns Persona, Ausencias, Días and Puntaje, and the fixed note from Global Constraints shown above the table.
- [ ] **Step 7: UI in Inicio.**
  - Show the block only when `riesgo.length > 0`.
  - Use an `Alert color="warning"` that reads «Días con riesgo de faltar gente: lun 17/11 (mañana), …». The franja names come from `FRANJA_NOMBRE`, so mirror them in TS or send the names from the API.
  - Add the button «Ver cuadro».
  - With no risk days, show nothing.
- [ ] **Step 8: Build, check in the browser, then commit on branch `analiticas-patrones`, open a PR and merge it.**

### Task 5: Report for management (print + Excel)

**Files:**
- Modify: `an/turnos/exportar.py`. Add `exportar_analiticas`.
- Modify: `an/web/rutas_exportes.py`. Add `GET /areas/{area}/analiticas.xlsx`.
- Modify: `an/web/rutas_areas.py`. Extract the dict from `analiticas()` into `datos_analiticas(bd, desde, hasta) -> dict` so the route and Excel share it.
- Modify: `web/src/pantallas/Analiticas.tsx`, `web/src/pantallas/Reportes.tsx`
- Test: `tests/web/test_exportes.py`

**Interfaces:**
- Consumes: the keys of Tasks 1–4.
- Produces:
  - `exportar_analiticas(carpeta, etiqueta: str, datos: dict, nombres_tipos: list[str]) -> Path`
  - Sheets, in this order: «Resumen», «Ausentismo», «Cobertura», «Cambios», «Estabilidad», «Horas extra», «Recargos», «Equidad», «Fatiga», «Patrones», «Banco».

- [ ] **Step 1: Write a failing test, `test_analiticas_xlsx`.**
  - Use the API fixture (pattern of `test_banco_lector_descarga` at L163).
  - A read-only user (`lector`) downloads `/api/areas/{a}/analiticas.xlsx?desde=2026-10-01&hasta=2026-10-31`.
  - `load_workbook(...).sheetnames` equals the list above.
  - A range of more than `MAX_DIAS_ANALITICAS` returns 422.
- [ ] **Step 2: Run `pytest tests/web/test_exportes.py -k analiticas -v` and confirm it fails.**
- [ ] **Step 3: Implement the export.**
  - Write the sheets with `_encabezado` and `_ancho` (`exportar.py:32,38`).
  - The «Resumen» sheet lists the tile values: ausentismo %, ausentes a la vez máx., días con déficit, cambios, % cambiado tras publicar, personas con señales de fatiga.
  - The route uses the `contexto_area_lectura` dependency, sets `request.state.evento = "exportacion"`, and builds the file name from `flujo.etiqueta`-style text `Analiticas_<desde>_<hasta>.xlsx` via `_adjunto`.
- [ ] **Step 4: Run the test. It should pass.**
- [ ] **Step 5: Print view.**
  - Add the «Imprimir» and «Descargar Excel» buttons to the Analíticas header actions.
  - Hide the filters with `print:hidden` and show the range in the title (`hidden print:inline`, as in `Cuadro.tsx:298`).
  - Add `break-inside-avoid` on each `Seccion`.
  - Confirm the app shell (sidebar, bell) is already hidden in print. If it is not, add `print:hidden` there.
  - Reportes gets a card «Analíticas del rango» with month inputs and the Excel download.
- [ ] **Step 6: Build and check in the browser.** Use the print preview (`window.print` emulation via `matchMedia` or a screenshot with print media), check the charts are visible and nothing is cut off, and confirm the Excel download returns 200.
- [ ] **Step 7: Update the docs.**
  - `docs/ESTADO.md`: add an entry under «Cambios recientes».
  - `docs/HOJA_DE_RUTA.md`: add an entry under «Hecho recientemente».
  - `README.md`: update the Informes bullet.
  - Then commit on branch `analiticas-reporte`, open a PR and merge it.

## Final check

- `pytest --ignore=tests/turnos/test_turnos.py -q` passes.
- `cd web && npm test && npm run build` passes.
- In the browser, Analíticas and Inicio work with demo data at desktop width and at 375 px, with no console errors.
