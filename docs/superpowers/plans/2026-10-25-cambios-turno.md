# Cambios de turno y permutas Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Registrar y auditar todo cambio manual del cuadro de Esterilización, con permutas limitadas por persona y periodo.

**Architecture:** Módulo puro `cambios.py` (sin Qt) escribe las celdas con `bd.set_celda` y deja una fila en la tabla `cambio_turno` (solo se agrega) más una línea en `cambios.log`. `paginas.py` pregunta el tipo antes de cada edición y delega en ese módulo. Deshacer pasa a ser «anular los registros de la última operación».

**Tech Stack:** Python 3, SQLite (`an/esterilizacion/db.py`), PySide6. Pruebas: scripts con `test_*` que imprimen `OK`.

**Spec:** `docs/superpowers/specs/2026-10-25-cambios-turno-design.md`

## Global Constraints

- Textos de interfaz en español; mantener estilo de `paginas.py`. Estilo visual solo con reglas de `ESTILO` en `an/nucleo/tema.py`, sin stylesheets por área.
- `cambio_turno` solo se agrega: anular llena `anulado_en` y `anulado_por`, nunca borra.
- Solo las permutas gastan cupo. Parámetro `limite_permutas`, por defecto `2`. Sobrepasarlo avisa y se aprueba como excepción; no bloquea.
- Periodo cerrado y vista Original: no se registra ni se edita.
- `servicio` vale siempre `'esterilizacion'`.
- No se registra lo que escribe el solver. No tocar `solver.py` ni `reglas.py`.
- `cambios.log` junto a `turnos.db` (nombres de personal: Ley 1581), ignorado en git.
- Un cambio de servicio exige motivo no vacío.

## Review Focus

- Permuta de una persona consigo misma o dos celdas iguales: se rechaza (`ErrorCambio`). Test en Task 2.
- Límite `0`: toda permuta exige excepción; y las permutas de otro periodo no cuentan en el cupo. Test en Task 2.
- Anular dos veces, o deshacer algo ya anulado desde la pestaña: no falla ni vuelve a escribir. Test en Task 2 y 3.
- Cambio de servicio con motivo vacío o en blanco: se rechaza. Test en Task 2.
- `cambios.log` no escribible (carpeta inexistente): el registro en la base sigue y no hay excepción. Test en Task 2.

---

### Task 1: Tabla `cambio_turno` y migración v6

**Files:**
- Modify: `an/esterilizacion/db.py` (`ESQUEMA`, `BD.__init__`, nuevo `_migrar_a_6`)
- Modify: `.gitignore`
- Modify: `docs/superpowers/specs/2026-10-25-cambios-turno-design.md` (§3 y §4, ver paso 5)
- Test: `tests/esterilizacion/test_cambios.py` (se crea aquí, crece en Task 2)

**Interfaces:**
- Produces: tabla `cambio_turno(id INTEGER PRIMARY KEY, periodo TEXT, servicio TEXT DEFAULT 'esterilizacion', tipo TEXT, registrado_en TEXT, usuario TEXT, colab_a INT, colab_b INT, celdas TEXT, motivo TEXT, excepcion INT DEFAULT 0, anulado_en TEXT, anulado_por TEXT)`. `celdas` es JSON `[[colab_id, "AAAA-MM-DD", antes, despues], ...]` y sirve para mostrar y para restaurar. Atributo `BD.ruta: str` con la ruta recibida.

- [ ] **Step 1: Write the failing test** en `tests/esterilizacion/test_cambios.py` (mismo encabezado `sys.path` y cierre `if __name__` que `test_puestos.py`):

```python
def test_esquema_v6():
    bd = db.BD()
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 6
    cols = [r["name"] for r in bd.c.execute("PRAGMA table_info(cambio_turno)")]
    assert cols == ["id", "periodo", "servicio", "tipo", "registrado_en", "usuario", "colab_a", "colab_b",
                    "celdas", "motivo", "excepcion", "anulado_en", "anulado_por"]

def test_migra_v5_a_v6():
    ruta = tempfile.mkdtemp() + "/t.db"
    bd = db.BD(ruta); bd.c.execute("DROP TABLE cambio_turno"); bd.c.execute("PRAGMA user_version = 5")
    bd.guardar_cuadro("2026-10-01/2026-10-31", {(1, date(2026, 10, 5)): "M"}); bd.c.commit(); bd.c.close()
    bd = db.BD(ruta)
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 6
    assert bd.asignaciones("2026-10-01/2026-10-31") == {(1, date(2026, 10, 5)): "M"}
    assert bd.c.execute("SELECT count(*) FROM cambio_turno").fetchone()[0] == 0
    assert bd.ruta == ruta
```

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python tests/esterilizacion/test_cambios.py`
Expected: FAIL (`user_version` es 5).

- [ ] **Step 3: Implement.** En `ESQUEMA` agregar la tabla (una cadena más concatenada, como las anteriores). En `BD.__init__` guardar `self.ruta = ruta`, poner `PRAGMA user_version = 6` en la rama de base nueva, y añadir tras el bloque `== 4` otro `if ... == 5: self._migrar_a_6()`. `_migrar_a_6` hace `CREATE TABLE IF NOT EXISTS cambio_turno ...`, `PRAGMA user_version = 6` y `commit`, igual que `_migrar_a_5`. En `.gitignore` agregar `cambios.log`.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python tests/esterilizacion/test_cambios.py` → `OK`. Correr también `tests/esterilizacion/test_puestos.py` → `OK` (no debe romperse la migración).

- [ ] **Step 5: Ajustar el spec a lo decidido en el plan.** En §3 reemplazar los campos `fecha_a, antes_a, despues_a, fecha_b, antes_b, despues_b` por `celdas TEXT` (JSON `[[colab, fecha, antes, despues], ...]`) y decir por qué: una sola columna sirve para restaurar un lote. En §4 cambiar «devuelve `Aviso(...)`» por «lanza `LimiteExcedido(ids)` salvo `excepcion=True`», y decir que `permuta`, `servicio` y `ajuste` devuelven la lista de ids creados.

- [ ] **Step 6: Commit**

```bash
git add an/esterilizacion/db.py .gitignore tests/esterilizacion/test_cambios.py docs/superpowers/specs/2026-10-25-cambios-turno-design.md
git commit -m "Tabla cambio_turno y migración v6" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Dominio puro `cambios.py`

**Files:**
- Create: `an/esterilizacion/cambios.py`
- Test: `tests/esterilizacion/test_cambios.py`

**Interfaces:**
- Consumes: `BD.ruta`, `BD.set_celda(mes, cid, fecha, codigo)`, `BD.asignaciones(mes, version)`, `BD.restaurar(mes, cids, fechas)`, `BD.periodo_cerrado(k)`, `BD.param`.
- Produces (todas toman `bd` primero; `celdas` = `[(colab_id, fecha: date, código)]` con el código nuevo; todas devuelven `list[int]` de ids salvo indicación):
  - `class ErrorCambio(Exception)`; `class LimiteExcedido(ErrorCambio)` con atributo `ids: list[int]` (colaboradores sobre el límite).
  - `permuta(bd, periodo, a, fa, b, fb, motivo, usuario, excepcion=False)`: `a`/`b` son ids de colaborador, `fa`/`fb` fechas. Intercambia lo que hay en las dos celdas.
  - `servicio(bd, periodo, celdas, motivo, usuario)`: una fila por colaborador distinto en `celdas`. `motivo` vacío o en blanco → `ErrorCambio`.
  - `ajuste(bd, periodo, celdas, motivo, usuario)`: una sola fila para todas las celdas.
  - `anular(bd, id_, usuario) -> bool`: `False` si ya estaba anulado.
  - `restaurar_celdas(bd, periodo, celdas_antes)`: `celdas_antes = [(colab_id, fecha, antes)]`; deja `cambios` igual que `deshacer` hacía hoy (si `original` coincide con `antes`, `bd.restaurar`; si no, `set_celda`).
  - `cupo(bd, periodo, colab) -> tuple[int, int]` = `(usadas, límite)`; límite = `int(bd.param("limite_permutas", 2))`.
  - `excedidos(bd, periodo, colabs) -> list[int]`: los que ya están en su límite.
  - `listar(bd, periodo) -> list[dict]`: más recientes primero; cada dict trae las columnas y `celdas` ya decodificado (fechas como `date`).
- Reglas: periodo cerrado → `ErrorCambio`. Usuario vacío se guarda como `"—"`. Cada escritura añade una línea a `Path(bd.ruta).with_name("cambios.log")` salvo si `bd.ruta == ":memory:"`; un `OSError` al escribir se ignora. Cupo: cada participante (A o B) de una permuta no anulada del periodo gasta 1. Anular llama a `restaurar_celdas` con los `antes`; si el periodo se cerró después, lanza `ErrorCambio`.

- [ ] **Step 1: Write the failing tests** (`K = "2026-10-01/2026-10-31"`, `d1, d2 = date(2026,10,5), date(2026,10,6)`; cuadro base `{(1,d1):"M",(2,d1):"T",(1,d2):"L"}` en `bd = db.BD()` con `bd.guardar_cuadro(K, base)`; `u = "coord"`):

```python
def test_permuta_intercambia_registra_y_gasta_cupo():
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "pedido", u)
    c = bd.asignaciones(K); assert c[(1, d1)] == "T" and c[(2, d1)] == "M"
    assert cambios.cupo(bd, K, 1) == (1, 2) and cambios.cupo(bd, K, 2) == (1, 2)
    fila = cambios.listar(bd, K)[0]
    assert fila["tipo"] == "permuta" and fila["usuario"] == u and fila["motivo"] == "pedido" and fila["servicio"] == "esterilizacion"
    assert fila["celdas"] == [(1, d1, "M", "T"), (2, d1, "T", "M")]
def test_permuta_sobre_limite_exige_excepcion():
    bd.set_param("limite_permutas", 1); cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.excedidos(bd, K, [1, 2, 3]) == [1, 2]
    with raises(LimiteExcedido) as e: cambios.permuta(bd, K, 1, d2, 2, d2, "", u)
    assert e.value.ids == [1, 2]
    cambios.permuta(bd, K, 1, d2, 2, d2, "", u, excepcion=True)
    assert [f["excepcion"] for f in cambios.listar(bd, K)] == [1, 0]   # la excepción es la más reciente
def test_limite_cero_y_otro_periodo_no_cuenta():
    bd.set_param("limite_permutas", 0); assert cambios.excedidos(bd, K, [1]) == [1]
    bd.set_param("limite_permutas", 1); cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.cupo(bd, "2026-11-01/2026-11-30", 1) == (0, 1)
def test_servicio_y_ajuste_no_gastan_cupo():
    ids = cambios.servicio(bd, K, [(1, d1, "L"), (2, d1, "L")], "falta personal", u); assert len(ids) == 2
    cambios.ajuste(bd, K, [(1, d2, "M"), (2, d2, "M")], "Lote: 2 celdas → M", u)
    assert cambios.cupo(bd, K, 1) == (0, 2) and len(cambios.listar(bd, K)) == 3   # lote = una fila
def test_servicio_sin_motivo_se_rechaza():
    for m in ("", "   "): with raises(ErrorCambio): cambios.servicio(bd, K, [(1, d1, "L")], m, u)
    assert bd.asignaciones(K)[(1, d1)] == "M"
def test_permuta_consigo_misma_se_rechaza():   # misma persona o misma celda
    with raises(ErrorCambio): cambios.permuta(bd, K, 1, d1, 1, d2, "", u)
def test_anular_restaura_conserva_fila_y_es_idempotente():
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.anular(bd, i, u) is True and bd.asignaciones(K)[(1, d1)] == "M"
    assert cambios.cupo(bd, K, 1) == (0, 2)
    fila = cambios.listar(bd, K)[0]; assert fila["anulado_por"] == u and fila["anulado_en"]
    assert cambios.anular(bd, i, u) is False
def test_periodo_cerrado_rechaza():
    bd.cerrar_periodo(K, [])
    with raises(ErrorCambio): cambios.ajuste(bd, K, [(1, d1, "L")], "", u)
def test_log_en_archivo_y_tolera_fallo():
    ruta = tempfile.mkdtemp() + "/t.db"; b = db.BD(ruta); b.guardar_cuadro(K, base)
    cambios.ajuste(b, K, [(1, d1, "L")], "x", u)
    assert "ajuste" in (Path(ruta).with_name("cambios.log")).read_text(encoding="utf-8")
    b.ruta = "/no/existe/t.db"; cambios.ajuste(b, K, [(1, d2, "M")], "y", u)   # no lanza
```

(`raises` = `pytest.raises` no está disponible: definir un helper de 4 líneas en el archivo de pruebas, como hacen los otros tests con `try/except`.)

- [ ] **Step 2: Run to verify it fails**

Run: `.venv/bin/python tests/esterilizacion/test_cambios.py`
Expected: FAIL (`cambios` no existe).

- [ ] **Step 3: Implement `an/esterilizacion/cambios.py`** con las firmas de Interfaces. Un único helper interno `_registrar(bd, periodo, tipo, usuario, celdas, motivo, colab_a, colab_b, excepcion)` valida periodo cerrado, lee `antes` de `bd.asignaciones(periodo)` (por defecto `"L"`), escribe cada celda nueva con `bd.set_celda`, inserta la fila con `registrado_en = datetime.now().isoformat(timespec="seconds")` y escribe el log. `permuta` arma las dos celdas cruzadas y valida `a != b` y `(a, fa) != (b, fb)`. `anular` lee `celdas`, llama `restaurar_celdas` con los `antes` y luego marca la fila.

- [ ] **Step 4: Run to verify it passes**

Run: `.venv/bin/python tests/esterilizacion/test_cambios.py` → `OK`.

- [ ] **Step 5: Commit**

```bash
git add an/esterilizacion/cambios.py tests/esterilizacion/test_cambios.py
git commit -m "Dominio de cambios: permuta, servicio, ajuste, anular y cupo" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Preguntar el tipo al editar y registrar desde el cuadro

**Files:**
- Modify: `an/nucleo/shell.py` (`Ventana.__init__`: `self.usuario = usuario`)
- Modify: `an/esterilizacion/paginas.py` (`_aplicar` ~l.463, `_celda_editada` ~l.476, `_mover_celda` ~l.488, `_menu_lote` ~l.500, `deshacer` ~l.511, y la pila `_deshacer`)
- Test: `tests/esterilizacion/test_gui.py`

**Interfaces:**
- Consumes: todo `cambios.*` de Task 2.
- Produces:
  - `Turnos._pedir_tipo(self, opciones: tuple[str, ...], texto: str, aviso: str | None = None) -> tuple[str, str, bool] | None`: diálogo modal con un botón por opción (`"permuta"`, `"servicio"`, `"ajuste"`) y un campo de motivo (obligatorio solo si el tipo elegido es `servicio`; deshabilita el botón mientras esté vacío). Si `aviso` viene, se muestra en el diálogo y el botón `permuta` pasa a decir «Permuta (aprobar como excepción)» y devuelve `excepcion=True`. Devuelve `(tipo, motivo, excepcion)` o `None` si se cancela. Es el único punto que usan las pruebas para simular la decisión.
  - `Turnos._aplicar(self, cambios, texto, tipo="ajuste", motivo="", excepcion=False)`: `cambios = [(persona, fecha, código)]`. Con `permuta`, `cambios` trae exactamente dos celdas de dos personas y se llama `cambios.permuta`; con `servicio` y `ajuste` se llaman esas funciones. La pila `_deshacer` guarda, por operación, la lista de ids devueltos (reemplaza las tuplas `(id, fecha, antes)`). Mantiene el aviso de reglas rotas y `flujo.recalcular`. Si `cambios.py` lanza `ErrorCambio`, avisa con `"error"` y redibuja sin escribir.

- [ ] **Step 1: Write the failing tests** al inicio del bloque de cuadro de `test_gui.py`, justo después de definir `ver`; el resto de ese bloque sigue igual pero con `v._pedir_tipo = lambda *a, **k: ("ajuste", "", False)` antes del primer arrastre (así los arrastres, el lote y el `setText("T·2")` existentes siguen sin diálogo) y con `v.deshacer()` que ahora anula registros. Añadir:

```python
decide = lambda r: setattr(v, "_pedir_tipo", lambda ops, texto, aviso=None: r(ops, aviso))
visto = []
decide(lambda ops, aviso: (visto.append((ops, aviso)) or ("permuta", "pedido", False)))
v._mover_celda(ra, c1, rb, c1)                              # arrastrar entre dos personas
assert visto[-1][0] == ("permuta", "servicio", "ajuste") and visto[-1][1] is None
assert ver()[(a, d1)] == "T" and cambios.listar(v.bd, K)[0]["tipo"] == "permuta"
v.deshacer(); assert ver()[(a, d1)] == "M" and cambios.listar(v.bd, K)[0]["anulado_por"]
v.bd.set_param("limite_permutas", 0)
v._mover_celda(ra, c1, rb, c1)
assert visto[-1][1] and "excepción" in visto[-1][1].lower()   # con límite 0 trae el aviso
decide(lambda ops, aviso: ("permuta", "ok", True)); v._mover_celda(ra, c1, rb, c1)
assert cambios.listar(v.bd, K)[0]["excepcion"] == 1; v.deshacer(); v.bd.set_param("limite_permutas", 2)
decide(lambda ops, aviso: None); antes = ver(); v._mover_celda(ra, c1, rb, c1); assert ver() == antes   # cancelar no escribe
decide(lambda ops, aviso: (visto.append((ops, aviso)) or ("servicio", "falta personal", False)))
v.grilla.item(ra, c1).setText("L"); assert visto[-1][0] == ("servicio", "ajuste")      # escribir en una celda
assert cambios.listar(v.bd, K)[0]["tipo"] == "servicio" and ver().get((a, d1), "L") == "L"
v.deshacer(); assert ver()[(a, d1)] == "M"
n = len(cambios.listar(v.bd, K)); v._aplicar([(v._gente()[ra], d1, "L"), (v._gente()[rb], d1, "L")], "lote", motivo="Lote: 2 celdas → L")
assert len(cambios.listar(v.bd, K)) == n + 1                                         # lote = una fila
```

- [ ] **Step 2: Run to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py`
Expected: FAIL (`_pedir_tipo` no existe / `cambios` sin importar).

- [ ] **Step 3: Implement.**
  - `shell.py`: `self.usuario = usuario` junto a `self.cambiar_usuario`.
  - `paginas.py`: importar `cambios` junto a `flujo` y demás módulos del paquete. `_aplicar` pasa a delegar según `tipo` (usuario = `self.v.usuario`); en `permuta` toma `a, fa` y `b, fb` de `cambios[0]` y `cambios[1]`; en los otros pasa `[(p.id, f, cod)]`. Meter en `_deshacer` la lista de ids.
  - `_mover_celda`: si las dos personas son distintas, calcular `cambios.excedidos(self.bd, k, [a.id, b.id])`, armar `aviso` con los nombres y `cupo` (p. ej. «Ana ya usó 2 de 2 en este periodo»), llamar `_pedir_tipo(("permuta","servicio","ajuste"), texto, aviso)` y, si responde, `_aplicar(..., tipo, motivo, excepcion)`. Si es la misma persona, `_aplicar` directo como ajuste, sin preguntar. Cancelar no escribe.
  - `_celda_editada`: `_pedir_tipo(("servicio","ajuste"), ...)`; si cancela, redibujar con `self._ver_cuadro()` para revertir lo escrito.
  - `_menu_lote`: `_aplicar(..., motivo=f"Lote: {n} celdas → {cod}")` como ajuste, sin preguntar.
  - `deshacer`: por cada id de la última entrada, `cambios.anular(self.bd, id_, self.v.usuario)` (ignora los ya anulados), luego `flujo.recalcular`, aviso y `_ver_cuadro`. Mantener las guardas de vista Original y periodo cerrado.
  - `_pedir_tipo`: `QDialog` con `QLineEdit` de motivo y `QPushButton` por opción; el estilo sale de `ESTILO` (botón `primario` para la opción recomendada: `permuta` o `servicio`).

- [ ] **Step 4: Run to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py` → `OK`. Correr `tests/esterilizacion/test_cambios.py` → `OK`.

- [ ] **Step 5: Commit**

```bash
git add an/nucleo/shell.py an/esterilizacion/paginas.py tests/esterilizacion/test_gui.py
git commit -m "Cuadro: preguntar permuta, servicio o ajuste y registrar cada edición" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Pestaña «Cambios registrados» y límite en Ajustes

**Files:**
- Modify: `an/esterilizacion/paginas.py` (panel inferior ~l.312-316, `_ver_cuadro` ~l.433-443, caja «Esquema y horas» ~l.1197, `refrescar` ~l.1268, `_guardar_reglas` ~l.1387)
- Test: `tests/esterilizacion/test_gui.py`

**Interfaces:**
- Consumes: `cambios.listar`, `cambios.anular`, `cambios.cupo`.
- Produces: pestaña 3 del `panel_inf` titulada `«Cambios registrados (n)»` (`n` = filas no anuladas del periodo) con atributos `self.t_registro` (tabla, columnas: Fecha, Tipo, Personas, Celdas, Motivo, Usuario), `self.f_tipo` (combo: Todos / Permuta / Servicio / Ajuste), `self.f_texto` (búsqueda por nombre de persona o usuario), `self.b_anular` y `self.l_cupos` (línea «Permutas usadas: Ana 1/2, Luis 2/2», solo personas con al menos una). Spin `self.s_limite` («Límite de permutas por persona y periodo», 0-20) en la caja «Esquema y horas» que guarda `limite_permutas`.

- [ ] **Step 1: Write the failing tests** (a continuación de las del Task 3 en `test_gui.py`):

```python
decide(lambda ops, aviso: ("permuta", "pedido", False)); v._mover_celda(ra, c1, rb, c1)
v._ver_cuadro()
assert v.panel_inf.tabText(2) == "Cambios registrados (1)" and v.t_registro.rowCount() == 1
assert v.t_registro.item(0, 1).text() == "Permuta" and "pedido" in v.t_registro.item(0, 4).text()
assert "1/2" in v.l_cupos.text()
v.f_tipo.setCurrentIndex(v.f_tipo.findData("servicio")); assert v.t_registro.rowCount() == 0
v.f_tipo.setCurrentIndex(0); v.f_texto.setText("zzz"); assert v.t_registro.rowCount() == 0; v.f_texto.setText("")
v.t_registro.selectRow(0); v.b_anular.click()
assert ver()[(a, d1)] == "M" and v.panel_inf.tabText(2) == "Cambios registrados (0)" and v.t_registro.rowCount() == 1  # la anulada sigue visible
assert v.t_registro.item(0, 0).font().strikeOut()
v.deshacer()                                  # ya estaba anulada: no falla
v.s_limite.setValue(5); v._guardar_reglas(); assert v.bd.param("limite_permutas") == "5"
```

- [ ] **Step 2: Run to verify it fails**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py`
Expected: FAIL (`t_registro` no existe).

- [ ] **Step 3: Implement.** Armar la pestaña en el mismo bloque donde se crean `alertas` y `lista_cambios` usando `tabla([...])`/`llenar` de `nucleo/widgets.py`. `_ver_cuadro` llena la tabla desde `cambios.listar(self.bd, k)` aplicando los dos filtros en Python (el texto busca en los nombres de las personas de `celdas`, vía `self.nombres`, y en `usuario`), tacha con la fuente las filas anuladas y actualiza título de pestaña y `l_cupos`. `b_anular` llama `cambios.anular`, `flujo.recalcular(self.bd, *self.periodo(), self.ctx)`, aviso y `_ver_cuadro`; queda deshabilitado en vista Original, con periodo cerrado, o sin selección o fila ya anulada. Cada cambio de filtro vuelve a llenar la tabla.

- [ ] **Step 4: Run to verify it passes**

Run: `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py` → `OK`. Comprobar a ojo con `Ventana(...).grab()` (como indica CLAUDE.md) que la pestaña no rompe el ancho de la ventana.

- [ ] **Step 5: Commit**

```bash
git add an/esterilizacion/paginas.py tests/esterilizacion/test_gui.py
git commit -m "Pestaña de cambios registrados, anulación y límite de permutas en Ajustes" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Documentación

**Files:**
- Modify: `CLAUDE.md` (comandos de pruebas y reglas de Esterilización)
- Modify: `docs/HOJA_DE_RUTA.md` (fila «Cambios y solicitudes»)
- Modify: `docs/superpowers/specs/2026-10-25-cambios-turno-design.md` (estado)

- [ ] **Step 1:** En `CLAUDE.md`, añadir `tests/esterilizacion/test_cambios.py` a la lista de pruebas, `cambios.py` a la lista de módulos de `an/esterilizacion/`, y una línea en «Esterilización: agreed rules»: las ediciones manuales se registran en `cambio_turno` y `cambios.log`; solo las permutas gastan el cupo `limite_permutas`.
- [ ] **Step 2:** En `docs/HOJA_DE_RUTA.md`, cambiar la fila «Cambios y solicitudes» a «Solicitudes» (queda pendiente, es la pieza S) y mencionar los cambios en «Hecho recientemente» con enlace al spec y a este plan.
- [ ] **Step 3:** En el spec, cambiar «Estado: diseño aprobado… pendiente de plan» por «implementado» con enlace al plan.
- [ ] **Step 4: Verificación final**

Run: `.venv/bin/python tests/esterilizacion/test_cambios.py`, `.venv/bin/python tests/esterilizacion/test_puestos.py`, `QT_QPA_PLATFORM=offscreen .venv/bin/python tests/esterilizacion/test_gui.py`, `.venv/bin/python tests/nucleo/test_nucleo.py`
Expected: cada uno imprime `OK`. (`test_turnos.py` tarda ~2 min y no toca estas rutas; correrlo una vez al final.)

- [ ] **Step 5: Commit**

```bash
git add CLAUDE.md docs
git commit -m "Docs: cambios de turno y permutas" -m "Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>"
```
