# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Desktop app (Spanish UI) that turns the monthly radiologist roster (`Asignación Radiólogos <Mes> 2026.xlsx`, sheet `Cambios …`) into the weekly assignment workbook (`SEMANA dd AL dd DE MES.xlsx`). Used by a non-technical coordinator on a locked-down Windows PC (no admin, no installs).

Roadmap toward a full scheduling system (QGenda-style, stages 1–6): `docs/PROYECTO.md`. Read it before starting new feature work; each stage gets its own design doc in `docs/` before coding.

## Commands

- Dev env: `python3 -m venv .venv && .venv/bin/pip install PySide6-Essentials openpyxl` (or double-click `Planilla Semanal.command` on Mac, which does it and opens the app).
- Run GUI: `.venv/bin/python app/app.py`
- CLI: `.venv/bin/python app/generar_semana.py "<mensual>.xlsx" YYYY-MM-DD [salida.xlsx]` (date = Monday).
- Tests: `.venv/bin/python tests/test_generar_semana.py` (prints `OK`; uses `ejemplos/Cuadro Octubre 2026 (prueba con fechas).xlsx`).
- GUI smoke test without display: `QT_QPA_PLATFORM=offscreen`, `app.preparar_app([])` + `app.Ventana()`. Monkeypatch `app.QSettings` to an ini in a temp dir so the user's saved settings are not overwritten.
- Windows package: `./empaquetar.sh` → `dist/PlanillaSemanal.zip` (Python 3.13 embeddable + win_amd64 wheels, launched by `Planilla Semanal.bat` → `pythonw.exe app\app.py`). `./empaquetar.sh prueba` builds a minimal hello-window zip to test a corporate PC.

## Layout

- `app/` — everything that ships: `app.py` (GUI), `generar_semana.py` (core), `analisis.py`, `plantilla_semana.xlsx`.
- `tests/`, `ejemplos/` (dated October roster + the hand-made week 12–18 for comparison), `docs/`, `dist/` (build output, ignored).

## Architecture

- `generar_semana.py` — core, no GUI. `cargar_mensual` → `lunes_disponibles` → `construir(ws, lunes)` returns `(workbook, resumen, datos)`; `ruta_libre` picks `SEMANA … .xlsx`, then `v2`, `v3`… (never overwrites). User-fixable problems raise `ErrorPlanilla` (message shown verbatim in the GUI).
  - Shift-code → service/slot mapping: `CODIGOS`, `FILAS_ECO`/`FILAS_CJ` (ECO grid rows), `SLOTS` (standard weekday slots for reading services), `IGNORAR`. Unknown codes are reported, not published.
  - Reading sheets are rebuilt from scratch copying styles from `plantilla_semana.xlsx`; ECO is a fixed grid filled in place. Disponibilidad rule (`linea_tiempo`): uncovered hours go to the `disp` doctor — before 7 am the previous day's, after that the same day's.
- `analisis.py` — pure functions on the roster/workbook: `alertas` (rest rules mirroring the roster's "prueba turg/nurg/CCC" rows; hours from sheet `Nom-Hrs`), `equidad` (week hours + month totals read from header columns `JORNADA`, `TOTAL`, `HORAS A`, `PNTE`, `NC`, `FDS`, `D`, `Fes`), `agenda_por_medico`/`ics`/`exportar_agendas`, `comparar_libros` (diff vs the latest saved version of the same week; changed cells yellow + `Cambios` sheet). Also `revisar_cuadro` (overlapping shifts, incomplete names, unknown codes with location), `equidad_meses` (sums monthly metrics across several roster files) and `html_planilla` (printable HTML, shares `texto_celda`/`color_hex` with the GUI preview).
- `app.py` — PySide6 window: sidebar sections (Resumen with KPI cards + weekly coverage grid, Vista previa, Alertas, Equidad, Agendas, Cambios). Preview renders the in-memory workbook that will be saved (no separate model), lazily when its section is shown, using the workbook theme colors (`analisis.paleta_tema`). `QFileSystemWatcher` reloads the roster when Excel saves it; drag-and-drop and shortcuts (Ctrl+O/G/P, Alt+←/→, Ctrl+1..6, F5). Settings via `QSettings`; unexpected errors go to `app/errores.log`.

## Roster requirements / agreed rules

- Row 3 of `Cambios …` must hold full dates (format `d`); weeks are matched by exact date, never by day number. Values are read with `data_only=True`, so the roster must have been saved by Excel (openpyxl-saved files have no cached formula values).
- Contingencia, vacaciones, asignación de estudios and free-text notes stay blank (manual); full names everywhere; densitometría includes Sunday; `Z` and hemodinamia are not published.
- Keep Spanish sheet names, headings and labels exactly as written. `~$…xlsx` are Excel lock files: ignore.
