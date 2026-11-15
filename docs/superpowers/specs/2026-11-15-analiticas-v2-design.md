# Analíticas v2: tendencias, estabilidad, fatiga y patrones de ausencia

## Context

Analíticas (`web/src/pantallas/Analiticas.tsx`, `an/turnos/analitica.py`, `GET /api/areas/{a}/analiticas`) shows ausentismo, cobertura, cambios, horas extra, recargos, equidad and banco as KPI tiles, 2 SVG bar charts and tables. Gaps found:
- `ausentismo.por_mes`, `simultaneos.serie`, `banco.serie` are computed and sent but never drawn.
- Nothing measures schedule **stability** (changes after publishing, notice given), **fatigue history** across months, or **absence patterns**.
- Management has no report out of Analíticas (no print, no Excel).

Web inspo: fatigue research (quick returns, 3+ nights in a row), fair-workweek studies (last-minute changes, notice ≥ 14 days), Bradford factor S²×D (useful for patterns, risky for discipline).

User decisions: audience = coordinator daily **and** management monthly; all four blocks; report = print **and** Excel; Bradford = team view **and** per-person.

## Approach (my calls)

- All metrics in `an/turnos/analitica.py`, returned by the same `/analiticas` endpoint (`an/web/rutas_areas.py:176`). Read-only, like today.
- Charts: hand SVG (decision in `docs/PLAN_WEB.md:60`). Move `Barras` out of `Analiticas.tsx` into `web/src/componentes/Graficos.tsx` and add `Linea` (multi-series line, `role="img"` + `aria-label`, table fallback stays below). No new deps.
- Thresholds are params with defaults in `PARAMETROS_POR_DEFECTO` (`an/web/rutas_areas.py`) and in each `bd.param(clave, defecto)` call, like the other rule params (not `PARAMETROS_BASE`, which only seeds a few), editable in Parámetros: `aviso_corto_horas` = 48, `max_dias_seguidos` = 6, `descanso_corto_horas` = 12 (reuse `reglas.DESCANSO_MIN` as default).
- `validar` (`an/turnos/reglas.py:91`) already alerts <12 h rests and night runs per period; fatigue here is history across the range, not new alerts.

## PRs, in order

### 1. Tendencias
- `Graficos.tsx`: `Barras` (moved) + `Linea`.
- Analíticas: 3 line charts — ausentismo por mes (stack by tipo → one line per tipo), ausentes a la vez por día (`simultaneos.serie`), banco favor/deuda (`banco.serie`).
- Frontend only. Test: `web/pruebas/` unit for the scale/path helper of `Linea`.

### 2. Estabilidad del cuadro
`estabilidad(bd, ini, fin)` per periodo:
- `celdas_cambiadas` / `celdas_total` → % changed after publishing: diff `original` vs `cambios` (`bd.diferencias`, used at `an/turnos/flujo.py:210`). Only periodos with `publicado_en`.
- `aviso_corto`: cells in non-anulled `cambio_turno` rows where `fecha_celda − registrado_en < aviso_corto_horas` (celdas JSON, `an/turnos/cambios.py:105`).
- `publicado_con_dias`: start of periodo − `publicado_en` (fair-workweek ≥ 14).
- `cubre_mas`: per person, count of `servicio` changes where they took the shift (colab_b / cells going L→turno).
- UI: KPI tile «Cambios tras publicar %», table per periodo, bar chart «Quién cubre más».

### 3. Fatiga
`fatiga(bd, ini, fin)` per person over all periodos in range (cuadro `cambios`):
- `max_dias_seguidos`, `rachas_largas` (runs > param), `max_noches_seguidas`, `descansos_cortos` (consecutive shifts with gap < param, via `reglas.intervalo`), `fines_trabajados` (Sat or Sun worked), `horas_4_sem_max`.
- UI: table sorted by a simple flag count (no opaque score), bars for fines trabajados. Inicio: tile «Personas con señales de fatiga» for the current periodo linking to Analíticas.

### 4. Patrones de ausencia y riesgo
`patrones_ausencia(bd, ini, fin)`, reusing `_ausencias` (`analitica.py:10`) grouped into spells (consecutive days, same person + tipo):
- `por_dia_semana` (Mon–Sun, % of person-days), `tras_festivo` (spells starting the day after a festivo or Monday after one).
- Bradford: team distribution (buckets 0–49, 50–199, 200–499, 500+) **and** per-person table (spells, days, score). Per-person shown with a fixed note: «Indicador de patrones; no usar para sanciones». Same visibility as the existing ausentismo-por-persona table.
- `riesgo_proximo`: for the next 14 days of the current cuadro, days where `reglas.margen_dia` ≤ 0 in some franja **and** weekday absence rate above the team mean. Shown on Inicio as «Días de riesgo» with dates.
- Exclude «Vacaciones» and «Libre solicitado» from Bradford/weekday patterns (planned absences); include Incapacidad and Licencia.

### 5. Reporte para gerencia
- Print: `@media print` styles in Analíticas (hide sidebar/filters, charts stay, one block per page break) + «Imprimir» button.
- Excel: `GET /api/areas/{a}/analiticas.xlsx?desde&hasta` in `an/web/rutas_exportes.py` (pattern of `banco_xlsx` at L94), `exportar_analiticas` in `an/turnos/exportar.py` reusing `_encabezado`/`_ancho`; one sheet per block. Button in Reportes and in Analíticas.

## Critical files
- `an/turnos/analitica.py`, `an/web/rutas_areas.py`, `an/web/rutas_exportes.py`, `an/turnos/exportar.py`, `an/turnos/db.py` (params)
- `web/src/pantallas/Analiticas.tsx`, `web/src/pantallas/Inicio.tsx`, `web/src/pantallas/Reportes.tsx`, new `web/src/componentes/Graficos.tsx`, Parámetros screen
- Tests: `tests/turnos/test_analitica.py`, `tests/web/test_exportes.py`

## Process
- First step of execution: copy this design to `docs/superpowers/specs/2026-11-15-analiticas-v2-design.md`, then write the implementation plan (superpowers:writing-plans).
- One branch + PR per block; push → PR to main → merge with green CI (memory rule).
- Update `docs/ESTADO.md` and `docs/HOJA_DE_RUTA.md` «Hecho recientemente» at the end.

## Verification
- Each metric: one assert-based test in `tests/turnos/test_analitica.py` with a tiny hand-built cuadro (e.g. 7 days in a row → `max_dias_seguidos == 7`; a change registered 10 h before the cell → `aviso_corto == 1`; 3 one-day incapacidades → Bradford 3²×3 = 27).
- Excel: test in `tests/web/test_exportes.py` that the download opens with expected sheet names.
- `pytest` without `test_turnos.py` (~2 min) + `cd web && npm test && npm run build`.
- Browser: `web/demo.sh` / preview, open Analíticas and Inicio with demo data, screenshot charts, check console, check 375 px width and print preview.
