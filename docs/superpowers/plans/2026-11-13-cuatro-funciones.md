# Cuatro funciones: banco en Excel, agendas, ¿Quién cubre? — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Excel del banco de horas, agenda `.ics` e impresión por persona, y sugerencia de reemplazos para un turno sin cubrir.

**Architecture:** Lógica pura en `an/turnos` (probada sin web), rutas finas en `an/web`, botones en las pantallas existentes. Las descargas nuevas son `GET` directas (como `agenda_ics` de Radiología) para no tocar el `CHECK` de la tabla `exporte`. La importación del Excel actual (función 4 del diseño) queda fuera: falta el archivo de muestra.

**Tech Stack:** Python 3.13, FastAPI, openpyxl, SQLite; React 19 + TypeScript + Tailwind.

**Spec:** `docs/superpowers/specs/2026-11-13-cuatro-funciones-design.md`

## Global Constraints

- Textos de interfaz, mensajes y nombres de hojas en español.
- Reglas y tarifas como datos; sin constantes de negocio nuevas.
- Sin dependencias nuevas (ni Python ni npm).
- Nunca subir `turnos.db` ni datos del personal.
- Lectores (`contexto_area_lectura`) pueden descargar; solo editores registran cambios.
- Cada descarga marca `request.state.evento = "exportacion"` (auditoría).
- Pruebas: `.venv/bin/python -m pytest tests --ignore=tests/turnos/test_turnos.py` debe quedar verde.

## Review Focus

- Persona sin turnos en el periodo: el `.ics` sale válido y vacío (solo `VCALENDAR`), sin error. → Task 2.
- Nombre con tildes o `/`: el nombre de archivo se limpia con `analisis.nombre_archivo` y la cabecera usa `filename*=UTF-8''`. → Task 2.
- Banco sin cierres ni movimientos: el libro sale con encabezados y cero filas de movimientos, sin fallar. → Task 1.
- ¿Quién cubre? en un día donde el candidato tiene novedad (VAC/INC): nunca aparece. → Task 3.
- ¿Quién cubre? con periodo cerrado: el registro del cambio ya devuelve 409 vía `rutas_edicion.abierto`; la consulta de candidatos sí responde (solo lectura). → Task 3.

---

### Task 1: Excel del banco de horas

**Files:**
- Modify: `an/turnos/exportar.py` (al final)
- Modify: `an/web/rutas_exportes.py`
- Modify: `web/src/pantallas/Reportes.tsx`, `web/src/api/exportes.ts`
- Test: `tests/turnos/test_exportar_banco.py`, `tests/web/test_exportes.py`

**Interfaces:**
- Produces: `exportar.exportar_banco(carpeta, mes_txt: str, filas: list[dict], movimientos: list[tuple], nombres: dict[int, str]) -> Path`
  - `filas` = salida de `flujo.estado_banco` (`{id, nombre, anterior, periodo, total, cerrado}`).
  - `movimientos` = `bd.movimientos()` → `(id, colab_id, fecha, horas, concepto, nota)`.
  - Hoja «Saldos»: `Colaborador, Anterior, Periodo, Total, Estado` (Estado = «Cerrado»/«Proyectado»).
  - Hoja «Movimientos»: `Fecha, Colaborador, Horas, Concepto, Nota`.
  - Archivo `BANCO DE HORAS {MES_TXT}.xlsx` vía `ruta_libre`.
- Produces: `GET /api/areas/{area}/periodos/{id}/banco.xlsx`

- [ ] **Step 1: Write the failing test** `tests/turnos/test_exportar_banco.py`

```python
def test_banco_dos_hojas(tmp_path):
    filas = [{"id": 1, "nombre": "Ana", "anterior": 4.0, "periodo": -2.5, "total": 1.5, "cerrado": False}]
    movs = [(9, 1, date(2026, 10, 3), 4.0, "Ajuste", "")]
    r = exportar.exportar_banco(tmp_path, "octubre 2026", filas, movs, {1: "Ana"})
    wb = openpyxl.load_workbook(r)
    assert r.name == "BANCO DE HORAS OCTUBRE 2026.xlsx"
    assert [c.value for c in wb["Saldos"][2]] == ["Ana", 4.0, -2.5, 1.5, "Proyectado"]
    assert [c.value for c in wb["Movimientos"][2]][1:4] == ["Ana", 4.0, "Ajuste"]

def test_banco_vacio(tmp_path):
    wb = openpyxl.load_workbook(exportar.exportar_banco(tmp_path, "octubre 2026", [], [], {}))
    assert wb["Movimientos"].max_row == 1
```

- [ ] **Step 2:** `.venv/bin/python -m pytest tests/turnos/test_exportar_banco.py -v` → FAIL (`exportar_banco` no existe).
- [ ] **Step 3:** Implement `exportar_banco` reusing `_encabezado`, `_ancho`, `poner_texto`, `ruta_libre`. Fecha de movimiento en `dd/mm/aaaa`.
- [ ] **Step 4:** Test → PASS.
- [ ] **Step 5:** Route `banco_xlsx(id, request, ctx=Depends(contexto_area_lectura))` in `rutas_exportes.py`: 404 si no hay periodo; arma `flujo.estado_banco(bd, inicio, fin)` + `bd.movimientos()`; escribe en `tempfile.TemporaryDirectory`; responde `Response(..., media_type=XLSX)` con la misma cabecera `Content-Disposition` que `descargar` (extraer esa línea a `_adjunto(nombre)` y usarla en ambas).
- [ ] **Step 6:** Test web en `tests/web/test_exportes.py`:

```python
def test_banco_lector_descarga():
    with entorno() as e:
        if e is None:
            return
        r = sesion(e, "lector@a.co").get(ruta(e).replace("/exportes", "/banco.xlsx"))
        assert r.status_code == 200 and r.headers["content-type"] == XLSX
        assert openpyxl.load_workbook(BytesIO(r.content)).sheetnames == ["Saldos", "Movimientos"]
```

- [ ] **Step 7:** Reportes: cuarta tarjeta «Banco de horas» («Saldo de horas por persona y movimientos manuales.»). No usa `exportes.crear`; descarga directa con `window.location` o `<a download>` al endpoint. Agregar `exportes.banco(area, periodo)` → URL.
- [ ] **Step 8:** Suite completa verde; `cd web && npx tsc --noEmit` sin errores.
- [ ] **Step 9:** Commit `Reportes: Excel del banco de horas (saldos y movimientos)`.

### Task 2: Agenda .ics por persona e impresión filtrada

**Files:**
- Modify: `an/turnos/exportar.py`
- Modify: `an/web/rutas_exportes.py`
- Modify: `web/src/pantallas/Reportes.tsx`, `web/src/pantallas/Cuadro.tsx`, `web/src/api/exportes.ts`
- Test: `tests/turnos/test_exportar_banco.py` (renombrar a `test_exportar_nuevos.py`), `tests/web/test_exportes.py`

**Interfaces:**
- Consumes: `an.radiologia.analisis.ics(nombre, eventos)`, `analisis.nombre_archivo(nombre)`, `dominio.intervalo(turno, fecha)`.
- Produces: `exportar.eventos_persona(ctx, cuadro: dict, colab_id: int, fechas: list[date]) -> list[tuple[datetime, datetime, str]]` — un evento por día con turno; `desc` = `f"{codigo} · {turno.nombre}"`; L y códigos desconocidos se omiten.
- Produces: `GET /api/areas/{area}/periodos/{id}/agendas/{colab_id}.ics` (404 si la persona no está en el cuadro) y `GET .../agendas.zip` (un `.ics` por persona `en_solver`, nombre `{nombre_archivo(nombre)}.ics`, zip `AGENDAS {MES_TXT}.zip`).

- [ ] **Step 1: Failing tests**

```python
def test_eventos_persona_omite_libres():
    # ctx con turno M 07:00-13:00; cuadro {(1, d1): "M", (1, d2): "L"}
    ev = exportar.eventos_persona(ctx, cuadro, 1, [d1, d2])
    assert ev == [(datetime(2026, 10, 5, 7), datetime(2026, 10, 5, 13), "M · Mañana")]

def test_ics_vacio_es_valido():
    assert analisis.ics("Ana", []).startswith("BEGIN:VCALENDAR") and "VEVENT" not in analisis.ics("Ana", [])
```

Web: `GET .../agendas/{e.colab['A']}.ics` → 200, `text/calendar`, cuerpo contiene `BEGIN:VEVENT` dos veces (fixture tiene M y T); `GET .../agendas/999999.ics` → 404; `GET .../agendas.zip` → 200 y `zipfile` con un `.ics`.

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `eventos_persona` y las dos rutas (`zipfile.ZipFile` sobre `BytesIO`; reusar `_adjunto`).
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Reportes: tarjeta «Agendas» con «Todas (.zip)» y un selector de persona que baja su `.ics` o abre «Imprimir su horario» → `/areas/{a}/cuadro/{p}?imprimir=1&persona={id}`.
- [ ] **Step 6:** Cuadro.tsx: si `busqueda.get("persona")`, filtrar filas a esa persona antes de imprimir (el efecto de `?imprimir=1` ya existe; no limpiar `persona` hasta después de `window.print()`, luego `setBusqueda({})`).
- [ ] **Step 7:** Verificar en el navegador (`web/demo.sh`, preview): descarga `.ics`, zip y vista de impresión con una sola fila. Suite + `tsc` verdes.
- [ ] **Step 8:** Commit `Agendas: .ics por persona, zip del periodo e impresión del horario de una persona`.

### Task 3: ¿Quién cubre?

**Files:**
- Create: `an/turnos/cubrir.py`
- Modify: `an/web/rutas_edicion.py`
- Modify: `web/src/pantallas/Cuadro.tsx` (+ `web/src/api/cambios.ts`)
- Test: `tests/turnos/test_cubrir.py`, `tests/web/test_edicion.py`

**Interfaces:**
- Consumes: `reglas.validar(ctx, cuadro, fechas, fijos, previo)`, `ctx.bloqueo(colab, turno, fecha)`, `ctx.turnos`, `ctx.colabs`.
- Produces: `cubrir.candidatos(ctx, cuadro: dict, fechas: list[date], fecha: date, codigo: str, fijos=(), previo=None, limite: int = 5) -> list[dict]`
  - Cada dict: `{colab_id, nombre, avisos: list[str], turnos_iguales: int, minutos: int}`.
  - Candidato = persona `en_solver`, libre (`L` o sin celda) ese día, `ctx.bloqueo(...)` es None.
  - Con el turno puesto en una copia del cuadro: se descarta si `validar` da algún `error` **nuevo** para esa persona (comparar textos contra la validación sin el cambio); los `aviso` nuevos van a `avisos`.
  - Orden: `(len(avisos), minutos, turnos_iguales, nombre)` ascendente. `minutos` = suma de `ctx.turnos[c].duracion` de la persona en `fechas`; `turnos_iguales` = cuántas veces ya tiene `codigo` en `fechas`.
  - `codigo` desconocido → `ValueError("«X» no es un turno")`.
  - ponytail: valida el periodo entero por candidato (O(personas × periodo)); si tarda con >60 personas, validar solo la ventana de ±3 días.
- Produces: `GET /api/areas/{area}/periodos/{id}/cubrir?fecha=YYYY-MM-DD&turno=M` → lista anterior. Lectura (`contexto_area_lectura`); 422 si fecha fuera del periodo o turno inválido.
- La asignación usa el endpoint existente `POST .../cambios` con `tipo: "servicio"`, una celda y `motivo: "Cubre a …"`.

- [ ] **Step 1: Failing tests** `tests/turnos/test_cubrir.py` (ctx de prueba armado como en `test_cambios.py` / `test_puestos.py`):

```python
def test_descarta_novedad_y_ocupados(): ...
    # Ana con VAC el día, Beto con T ese día, Carla libre → solo Carla
    assert [c["nombre"] for c in cubrir.candidatos(ctx, cuadro, dias, d, "M")] == ["Carla"]

def test_descarta_descanso_12h():
    # Carla hizo N el día anterior → M hoy rompe 12 h → no aparece
    assert cubrir.candidatos(ctx, cuadro, dias, d, "M") == []

def test_ordena_por_menos_horas():
    # Dani con 3 turnos en el periodo, Eva con 1 → Eva primero
    assert [c["nombre"] for c in cubrir.candidatos(ctx, cuadro, dias, d, "M")][:2] == ["Eva", "Dani"]

def test_turno_desconocido():
    with raises(ValueError): cubrir.candidatos(ctx, cuadro, dias, d, "ZZ")
```

- [ ] **Step 2:** Run → FAIL.
- [ ] **Step 3:** Implement `cubrir.candidatos`.
- [ ] **Step 4:** Run → PASS.
- [ ] **Step 5:** Route + test web: `GET .../cubrir?fecha=2026-10-07&turno=M` como lector → 200 y lista; `fecha=2026-12-01` → 422.
- [ ] **Step 6:** Cuadro.tsx: en el menú/acciones de una celda vacía de un día con alerta de cobertura (`vista.diaMalo` o error del día), botón «¿Quién cubre?» → ventana con selector de turno (por defecto el primero cuyo `cubre` incluye la franja faltante), lista de hasta 5 con «12 h · 2 M en el periodo» y sus avisos, y botón «Asignar» que llama al `POST cambios` existente con `If-Match` y recarga. Solo editores ven «Asignar».
- [ ] **Step 7:** Verificar en el navegador con la demo: provocar un faltante, abrir la ventana, asignar, ver que el cambio aparece en Cambios y la alerta se va. Suite + `tsc` verdes.
- [ ] **Step 8:** Commit `Cuadro: «¿Quién cubre?» sugiere reemplazos que cumplen las reglas`.

### Task 4: Documentación

- [ ] Agregar las tres funciones a `README.md` (Funciones → Edición/Informes) y a `docs/ESTADO.md`; mover «Excel del banco» y «Agendas» fuera de candidatas en `docs/HOJA_DE_RUTA.md`. Dejar «Importar el Excel actual» como pendiente con la nota «falta archivo de muestra».
- [ ] Commit `Docs: banco en Excel, agendas y ¿Quién cubre?`.
