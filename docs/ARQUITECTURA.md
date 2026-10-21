# Arquitectura

Principios: núcleo en Python puro y sin interfaz; reglas y tarifas como **datos**, no código; Excel como formato de intercambio; todo portátil y sin permisos de administrador; el solver propone y la persona decide.

## Módulos

| Archivo | Responsabilidad |
|---|---|
| `dominio.py` | `Turno` (catálogo editable, pausas, `cubre` M/T/N), `Colaborador`, `Novedad`, `Contexto` (`bloqueo()` explica por qué alguien no puede hacer un turno), festivos de Colombia (Ley Emiliani) |
| `db.py` | SQLite con migraciones por `PRAGMA user_version`. Cuadro en dos versiones por mes (`original`, `cambios`) |
| `reglas.py` | Validación pura de un cuadro `{(colab_id, fecha): código}` |
| `solver.py` | Modelo CP-SAT del mes |
| `puestos.py` | Reparto de puestos: fijos, luego corridos, luego medias jornadas |
| `capacitacion.py` | Sesiones semanales |
| `recargos.py` | Horas por categoría y ventana del art. 165 |
| `flujo.py` | Orquestación (`cero`, `respetar`, `semana`) y acumulado de equidad |
| `exportar.py` | Tres libros Excel sin sobrescribir |
| `app.py` | Ventana PySide6; el solver corre en un `QThread` |

## Datos (SQLite)

`turno`, `cobertura`, `colaborador`, `novedad`, `asignacion` (mes, versión, colaborador, fecha, turno, origen, `fijo`), `puesto_dia`, `capacitacion`, `tarifa`, `parametro`. La base se crea sola en `turnos.db` junto a la app.

## Solver

Variable `x[persona, día, turno]` con L más los turnos del catálogo marcados para el solver.

**Duras:** una opción por persona y día; descanso de 12 h (transiciones prohibidas calculadas con los horarios reales); al menos un día libre por semana completa; novedades, estudio y turnos permitidos; tope de noches seguidas; celdas fijas por edición manual; continuidad con el mes anterior.

**Objetivo:** faltante de cobertura (peso muy alto) y sobrante; desviación de horas por ventana del art. 165; cambios de turno día a día; noche antes de estudio de mañana; noches y domingos/festivos en semanas seguidas; equidad de noches, domingos/festivos y corridos incluyendo meses anteriores.

Si hay celdas fijas imposibles, el error lo indica y sugiere «Restaurar».

## Versiones del cuadro

`original` se congela al generar desde cero o al publicar. Las ediciones manuales y las regeneraciones parciales solo tocan `cambios`. La grilla marca en amarillo lo distinto y el Excel trae las hojas `Cuadro`, `Original` y `Cambios`.

## Empaquetado

`empaquetar.sh` baja el Python embebido oficial y las ruedas de Windows (PySide6, openpyxl, OR-Tools) y arma una carpeta con un `.bat`. Pesa unos 400 MB descomprimida (144 MB en zip). El modo `prueba` valida Qt y OR-Tools en el PC destino.
