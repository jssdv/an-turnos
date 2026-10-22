# CLAUDE.md

**An~** — desktop app (Spanish UI) for the Central de Esterilización: staff + absences, monthly shift grid generated with OR-Tools CP-SAT, daily post assignment, training sessions, hours and Colombian surcharges (CST). Used by a non-technical coordinator on a locked-down Windows PC (no admin, no installs). Long-term direction (general shift management, more services, linked admin processes): `docs/VISION.md`. Sister of `../ASIGSEMRADIO` (Radiología); the two apps share no code, only ideas.

## Commands
- Dev env: `python3 -m venv .venv && .venv/bin/pip install PySide6-Essentials openpyxl ortools` (or double-click `An.command`).
- Run GUI: `.venv/bin/python app.py` (data in `turnos.db` next to `app.py`).
- Tests: `.venv/bin/python test_turnos.py` (prints `OK`, ~2 min: solves full months) and `.venv/bin/python test_puestos.py` (posts, demand, assignment, staffing).
- GUI test without display: `.venv/bin/python test_gui.py` (offscreen; CRUD of staff, shifts and posts, staffing tab). Also useful: `QT_QPA_PLATFORM=offscreen` + `app.Ventana(tmp_db_path)` + `grab()` for screenshots.
- Windows zip: `./empaquetar.sh` → `dist/An.zip`; `./empaquetar.sh prueba` → `dist/PruebaPC.zip` (checks Qt + OR-Tools run on the target PC).

## Architecture
Pure core, Qt only calls it.
- `dominio.py` — `Turno` (editable catalog: times, paid/unpaid pauses, `cubre` M/T/N), `Colaborador`, `Novedad`, `Contexto` (`bloqueo()` = why someone can't work a shift), Colombian holidays (`festivos`, Ley Emiliani).
- `db.py` — SQLite. `asignacion` has two versions per month: `original` (published) and `cambios` (working copy; manual edits are `fijo`). `publicar`, `restaurar`, `diferencias`.
- `reglas.py` — validation of a grid `{(colab_id, fecha): código}`: slot coverage (`faltantes_dia`), 12 h rest, study/absence/permitted shifts, weekly day off.
- `solver.py` — CP-SAT month model. Coverage per slot from posts' demand (penalty, or hard with `estricto`). Hard: rest, weekly day off, absences, max consecutive nights, fixed cells. Soft: hours per art. 165 window, rotation, equity (carries previous months via `flujo.acumulado`).
- `demanda.py` — pure slot model (48 × 30 min per day): posts' demand rules → demand per date, shift franjas, `cobertura_derivada`, hour estimate. `dotacion.py` — staffing estimate and `verificar_minimo` (bisection with the solver, `estricto=True`).
- `puestos.py` — `asignar_tramos`: per-day CP-SAT assigning people to posts by blocks of slots (allowed posts, continuity, rotation); labels for «Mostrar puesto». `capacitacion.py` — one training per week (Monday, else next business day).
- `recargos.py` — splits each paid segment by night/holiday/extra; tariffs are rows with `desde` dates (dominical 80→90→100 %, night start 21:00→19:00).
- `flujo.py` — month orchestration (modes `cero` / `respetar` / `semana`). `exportar.py` — 3 Excel files, never overwrites (`v2`, `v3`…). `app.py` — PySide6 window; solver runs in a `QThread`.

## Agreed rules
- Coverage comes from posts' demand rules (default seed: 4 day posts + Guardia noche ×2 Mon–Sat; Autoclave and Lavado + guardia on Sun/holiday; Ropa desirable). Restricted person: no nights, only post 3. Refuerzo is outside the solver.
- Hours: art. 165 CST average over N weeks (default 3) vs 42 h/week; unpaid pauses don't count. Legal figures are editable data — confirm with RR. HH./legal.
- Keep Spanish labels. `turnos.db`, `errores.log` are git-ignored.
