# Cambios de turno y permutas — diseño

[← Volver al inicio](../../../README.md) · [Visión](../../VISION.md) · [Arquitectura](../../ARQUITECTURA.md) · [Hoja de ruta](../../HOJA_DE_RUTA.md)

Estado: **diseño aprobado** (25/10/2026), pendiente de plan. Primera de cuatro piezas: **C** (este documento), **S** (solicitudes personales como deseo para el solver), **D** (dashboard) y **V** (varios servicios, fuera de este ciclo).

## 1. Qué se quiere lograr

Hoy toda edición del cuadro (escribir en una celda, arrastrar, lote) cambia `asignacion` sin dejar constancia de quién, cuándo ni por qué. La coordinación necesita **registrar los cambios de turno**, **limitar las permutas** entre compañeros y **auditar** todo lo que se edita a mano.

**Criterios de éxito**
- Cada edición manual del cuadro deja una fila en un registro de auditoría con usuario, fecha y hora.
- Se distingue la **permuta** (dos personas, a petición de compañeros) del **cambio de servicio** (una persona, decidido por la coordinación por necesidad) y del **ajuste** (edición sin más).
- Solo las permutas gastan cupo. El límite es por persona y periodo, editable, y se puede aprobar una excepción.
- Un cambio registrado se puede anular y la fila queda visible.

**Fuera de alcance:** que los compañeros pidan cambios (no hay login de colaboradores), exportar el registro a Excel, varios servicios (V), el dashboard (D, que usará este registro para la métrica «cambios»), y registrar lo que escribe el solver (ya queda en `asignacion` y en el historial de generaciones).

## 2. Decisiones tomadas con el usuario

| Tema | Decisión |
|---|---|
| Quién registra | Solo la coordinación, en esta app |
| Qué cuenta para el límite | Solo permutas; servicio y ajuste no gastan cupo |
| Medida del límite | Por persona y por periodo (el mes o las N semanas que ya usa la app), número editable, por defecto 2 |
| Al pasarse del límite | Avisa y la coordinación aprueba como excepción; no bloquea |
| Edición directa | Pregunta el tipo en vez de ser silenciosa |
| Auditoría | Todo cambio manual queda registrado, también los ajustes |
| Servicio | Solo Esterilización; `servicio` queda como campo fijo `esterilizacion` para no bloquear V |

## 3. Datos

Migración **v6** (como `_migrar_a_5`; también se agrega a `ESQUEMA` para bases nuevas):

```sql
CREATE TABLE cambio_turno (
  id INTEGER PRIMARY KEY, periodo TEXT, servicio TEXT DEFAULT 'esterilizacion',
  tipo TEXT,                       -- 'permuta' | 'servicio' | 'ajuste'
  registrado_en TEXT, usuario TEXT,
  colab_a INT, colab_b INT,        -- colab_b solo en permutas
  celdas TEXT,                     -- JSON [[colab_id, fecha, antes, despues], ...]: sirve para mostrar y para anular un lote
  motivo TEXT, excepcion INT DEFAULT 0,
  anulado_en TEXT, anulado_por TEXT);
```

La tabla solo crece: anular llena `anulado_en` y `anulado_por`, no borra. El parámetro `limite_permutas` (por defecto `2`) se lee con `bd.param("limite_permutas", 2)`, sin sembrarlo.

## 4. Dominio puro: `an/esterilizacion/cambios.py`

Sin Qt, en el estilo de `flujo.py`. Todas las funciones toman `bd` y el `usuario` actual.

- `permuta(bd, periodo, a, fa, b, fb, motivo, usuario, excepcion=False)`: intercambia las dos celdas con `bd.set_celda` (que las marca `fijo`) y guarda la fila. Si alguien está en su límite y `excepcion` es falso, no escribe y lanza `LimiteExcedido(ids)`. Las tres funciones de registro devuelven la lista de ids creados.
- `servicio(bd, periodo, colab, fecha, codigo, motivo, usuario)`: motivo obligatorio. Una fila por persona afectada.
- `ajuste(bd, periodo, celdas, motivo, usuario)`: `celdas` = `[(colab, fecha, código)]`. Una sola fila por operación; si son varias celdas (lote), el detalle va en `motivo` («Lote: 12 celdas → L»).
- `cupo(bd, periodo, colab)` → `(usadas, límite)`. Cuenta permutas no anuladas en que la persona es A o B.
- `anular(bd, id, usuario)`: restaura las celdas a `antes_*`, llena `anulado_*`.
- `listar(bd, periodo)`: filas para la interfaz.
- Cada escritura agrega una línea a `cambios.log` junto a `errores.log` (ignorado en git). Si el archivo no se puede escribir, la fila en la base sigue valiendo.

Rechaza (con error claro) periodo cerrado y vista Original. Después de escribir, el llamador ejecuta `flujo.recalcular`, como ya hace `_aplicar`. `reglas` y el solver no cambian.

## 5. Interfaz (`paginas.py`)

- **Arrastrar** (`_mover_celda`): entre dos personas distintas abre una pregunta con **Permuta** (motivo; si hay exceso, muestra «Ana ya usó 2 de 2» y «Aprobar como excepción»), **Cambio de servicio** (motivo obligatorio, una fila por persona) y **Solo ajuste**. Misma persona en dos fechas: ajuste directo, sin pregunta.
- **Escribir en una celda** (`_celda_editada`): pregunta **Cambio de servicio** o **Solo ajuste**.
- **Lote** (`_menu_lote`): un ajuste, sin pregunta.
- **Pestaña «Cambios registrados (n)»** en el panel inferior: fecha, tipo, personas, antes → después, motivo, usuario. Filtros por tipo, persona y usuario. Botón «Anular». Fila anulada tachada. Línea de cupos («Ana 1/2, Luis 2/2»).
- **Ajustes:** campo «Límite de permutas por persona y periodo».
- **Deshacer** (Ctrl+Z): si el último cambio estaba registrado, también lo anula, para que lista y cuadro no diverjan.
- El usuario sale del usuario local ya elegido al arrancar (`an/nucleo/usuarios.py`).

## 6. Pruebas

- `tests/esterilizacion/test_cambios.py` (puro, imprime `OK`): cada tipo deja fila; permuta dentro y fuera del límite, con y sin excepción; servicio y ajuste no gastan cupo; lote deja una fila; anular restaura y conserva la fila; periodo cerrado rechaza; migración v5 → v6 conserva datos.
- Añadir a `tests/esterilizacion/test_gui.py`: arrastrar entre dos personas abre la pregunta y registra la permuta; deshacer anula.

## 7. Privacidad

Tabla y `cambios.log` contienen nombres del personal. Quedan junto a `turnos.db`. `cambios.log` hay que añadirlo a `.gitignore` (hoy solo están `errores.log` y `turnos.db`) (Ley 1581).
