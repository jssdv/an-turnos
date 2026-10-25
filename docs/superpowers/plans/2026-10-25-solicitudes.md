# Solicitudes personales Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** La coordinación registra solicitudes personales (libre / quiero turno / evitar turno) y el solver las cumple como deseo blando, informando cuáles no cumplió y por qué.

**Architecture:** Tabla `solicitud` (v7) → `Contexto.solicitudes` → penalidades en el objetivo de `solver._resolver`. Módulo puro `solicitudes.evaluar` calcula el estado desde el cuadro vigente. Pestaña «Solicitudes» y mensaje tras generar.

**Tech Stack:** Python, SQLite, OR-Tools CP-SAT, PySide6. Python: `/Users/jss/Desktop/An/.venv/bin/python`.

**Spec:** `docs/superpowers/specs/2026-10-25-solicitudes-design.md`

## Global Constraints

- Núcleo puro sin Qt; UI en español; estilos solo en `ESTILO`; `servicio` fijo `esterilizacion`.
- Migración con `user_version` = 7. Cada archivo de prueba imprime `OK` (patrón `test_*` + `__main__` como `tests/esterilizacion/test_cambios.py`).
- Pesos: `W_SOL = {"normal": 400, "alta": 4000}` por día; sin restricciones duras nuevas.
- Pruebas de GUI con `QT_QPA_PLATFORM=offscreen`. No tocar `docs/diseno/An_UI.figcraft`.

## Review Focus

- Solicitud con rango parcialmente fuera del periodo: solo cuentan los días dentro (test en Task 2).
- Persona sin turno `T` permitido pide `quiero T`: no rompe el modelo, motivo «turno no permitido» (Task 2).
- Solicitud `libre` sobre una celda fija con turno: gana la celda, motivo «edición manual» (Task 2).
- Persona desactivada con solicitudes: no entra al solver, no falla (Task 2).
- Solicitud `libre` imposible de cumplir por cobertura: el solver no lanza error, cede (Task 2).

---

### Task 1: Datos — `Solicitud`, tabla v7 y CRUD

**Files:**
- Modify: `an/esterilizacion/dominio.py` (dataclass `Solicitud`, campo `Contexto.solicitudes`, constantes `TIPOS_SOLICITUD`, `PRIORIDADES`)
- Modify: `an/esterilizacion/db.py` (tabla en `ESQUEMA`, `_migrar_a_7`, `user_version` 7, CRUD, `contexto`, `borrar_colaborador`)
- Modify: `tests/esterilizacion/test_cambios.py` (`test_esquema_v6`/migración: versión ahora 7)
- Create: `tests/esterilizacion/test_solicitudes.py`

**Interfaces:**
- Produces: `dominio.Solicitud(colab_id:int, tipo:str, desde:date, hasta:date, turno:str="", prioridad:str="normal", nota:str="", id:int=None)`; `TIPOS_SOLICITUD=("libre","quiero","evitar")`; `PRIORIDADES=("normal","alta")`; `Contexto.solicitudes: list` (default `[]`, después de `demandas`); `BD.guardar_solicitud(s, usuario="")`, `BD.borrar_solicitud(id)`, `BD.solicitudes()` → `list[Solicitud]` ordenadas por `desde`.

- [ ] **Step 1: Write failing tests** en `test_solicitudes.py`: `test_esquema_v7` (user_version == 7, columnas `id, servicio, colab_id, tipo, desde, hasta, turno, prioridad, nota, registrado_en, usuario`), `test_migra_v6_a_v7` (crear BD, `DROP TABLE solicitud`, `PRAGMA user_version=6`, reabrir con ruta de archivo temporal → versión 7 y tabla existe), `test_crud` (guardar, listar igual, `bd.contexto(2026).solicitudes` las trae, borrar; `borrar_colaborador` de quien tiene solicitud devuelve «desactivado»). Ajustar en `test_cambios.py` las aserciones de versión 6 a 7 (y que la migración v5 termine en 7).
- [ ] **Step 2: Run** `.venv/bin/python tests/esterilizacion/test_solicitudes.py` → falla (sin `Solicitud`).
- [ ] **Step 3: Implement** lo anterior; `_migrar_a_7` con `CREATE TABLE IF NOT EXISTS solicitud …` (estilo de `_migrar_a_6`), encadenada tras `== 6`; `registrado_en` = `datetime.now().isoformat(timespec="seconds")`; en `borrar_colaborador` incluir `solicitud` en el `UNION` de historia.
- [ ] **Step 4: Run** `test_solicitudes.py` y `test_cambios.py` → `OK`.
- [ ] **Step 5: Commit** `git commit -m "Datos de solicitudes personales (v7)"`.

### Task 2: Solver (deseo blando) y evaluación

**Files:**
- Modify: `an/esterilizacion/solver.py` (constante `W_SOL`, bloque de penalidades antes de `m.Minimize`)
- Create: `an/esterilizacion/solicitudes.py`
- Modify: `tests/esterilizacion/test_solicitudes.py`

**Interfaces:**
- Consumes: `Solicitud`, `ctx.solicitudes` (Task 1); `por_pd[(p.id, d)]` = lista `(turno, var)` en `_resolver`.
- Produces: `solicitudes.Resultado(solicitud, estado, motivo, dias_fallidos)` (dataclass; `estado` ∈ `cumplida|parcial|no cumplida|fuera`, `motivo` str, `dias_fallidos` list[date]); `solicitudes.evaluar(ctx, cuadro, fechas, fijos=()) -> list[Resultado]`.

- [ ] **Step 1: Write failing tests**: con pocas personas (p. ej. 8 `Colaborador`, `fechas` de 14 días, `tiempo=10`): (a) `libre` normal en un día y `evitar NC` otro día → `evaluar` los da `cumplida`; (b) `quiero T` una semana: ningún turno distinto de T ni L esos días; (c) `libre` de la única persona restringida a un puesto que nadie más cubre cede: `solver.generar` no lanza, `evaluar` da `no cumplida` con motivo `cobertura o reglas`; (d) `alta` vs `normal` en conflicto (dos personas, un solo cupo): se cumple la alta; (e) `evaluar` unitario con cuadro armado a mano: motivos `tiene novedad`, `turno no permitido`, `libre obligatorio tras noche`, `edición manual` (fijos), `fuera` y rango parcial → solo cuentan días en `fechas`; (f) persona inactiva con solicitud no rompe `solver.generar`.
- [ ] **Step 2: Run** → falla.
- [ ] **Step 3: Implement solver**: por cada solicitud, para `p` en `P` con `p.id == s.colab_id`, y `d` en `fechas` con `s.desde <= d <= s.hasta`, sumar `W_SOL[s.prioridad] * v` para cada `(turno, v)` de `por_pd[p.id, d]` "malo" (`libre`: `turno != "L"`; `quiero`: `turno not in ("L", s.turno)`; `evitar`: `turno == s.turno`). Implement `evaluar`: cumplida por día con la misma lógica sobre `cuadro.get((id, d), "L")`; motivo del primer día fallido en orden: `ctx.novedad` → `ctx.bloqueo` con turno pedido (solo `quiero`; «turno no permitido») → `(id, d) in fijos` → noche anterior con `ctx.libre_tras_noche` y `dem.es_noche` → `cobertura o reglas`.
- [ ] **Step 4: Run** → `OK` (ajustar pesos solo si (d) o (a) fallan, dentro de los límites del spec).
- [ ] **Step 5: Run** `tests/esterilizacion/test_turnos.py` (~2 min, en segundo plano) → `OK`. Commit `"Solver y evaluación de solicitudes"`.

### Task 3: Interfaz, informe tras generar y documentación

**Files:**
- Modify: `an/esterilizacion/paginas.py` (`_pestana_solicitudes`, `_ver_solicitudes`, `_agregar_solicitud`, `_borrar_solicitud`, registro en `__init__` tras `_pestana_novedades` y en la lista de refresco junto a `_ver_novedades`; mensaje en `_generado`)
- Modify: `an/nucleo/tema.py` solo si hace falta una regla en `ESTILO` (preferible reutilizar las existentes)
- Modify: `tests/esterilizacion/test_gui.py`
- Modify: `CLAUDE.md`, `docs/GUIA_USUARIO.md`, estado del spec a «implementado»

**Interfaces:**
- Consumes: `BD.guardar_solicitud/borrar_solicitud/solicitudes`, `solicitudes.evaluar` (Tasks 1–2), `self.v.usuario`.

- [ ] **Step 1: Write failing GUI test** (al estilo del existente): la sección «Solicitudes» existe; agregar una `libre` desde los widgets crea una fila con Estado; borrar la deja vacía; tras `generar("cero")` con una `libre` imposible el último aviso menciona «no cumplida».
- [ ] **Step 2: Run** `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py` → falla.
- [ ] **Step 3: Implement** la pestaña siguiendo `_pestana_novedades` (tabla Colaborador · Tipo · Turno · Desde · Hasta · Prioridad · Estado · Nota; formulario con combo de turno habilitado solo en `quiero/evitar`; Estado «cumplida» / «parcial: motivo» / «no cumplida: motivo» / «fuera del periodo» vía `evaluar` sobre `self.bd.asignaciones(self.clave)` y `self.bd.fijos`). En `_generado`: si hay resultados `no cumplida`/`parcial`, agregar «N solicitud(es) no cumplida(s): Nombre dd/mm (motivo)…» (máx. 3) al aviso, también cuando la cobertura quedó completa (nivel `warn`).
- [ ] **Step 4: Run** test GUI, `test_cambios.py`, `test_puestos.py`, `tests/nucleo/test_nucleo.py`, `tests/radiologia/*` → `OK`.
- [ ] **Step 5: Docs**: CLAUDE.md (regla corta de solicitudes en «Esterilización: agreed rules» y el test nuevo en Commands), `docs/GUIA_USUARIO.md` (sección «Solicitudes»: cómo registrar, qué significan los estados, que no son garantía), estado del spec.
- [ ] **Step 6: Commit** `"Pestaña Solicitudes, informe tras generar y docs"`.
