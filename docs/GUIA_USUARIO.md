# Guía de uso

[← Volver al inicio](../README.md) · [Reglas](REGLAS.md) · [Hoja de ruta](HOJA_DE_RUTA.md)

Esta guía recorre un mes completo. Todo se hace dentro de Cuadrante; no hace falta tocar Excel hasta el final.

## Antes de empezar (una sola vez)

1. **Personal.** Pestaña **Personal** → *Nuevo*. Para cada colaborador indica tipo, horas por semana y, si aplica:
   - **Turnos permitidos**: por ejemplo `M, T` para quien no hace noches.
   - **Puesto fijo**: por ejemplo el 3 (sterrad y esto).
   - **Horario de estudio**: `Lun M, Jue M, Vie, Mar T` (la letra es la franja; sin letra, todo el día).
2. **Turnos.** Pestaña **Parámetros → Turnos**. Revisa que los horarios sean los reales y define la **pausa de almuerzo** de los turnos de 12 h (minutos, hora y si es pagada). Mientras falte, la app lo avisa.
3. **Cobertura y reglas.** En **Parámetros → Cobertura y reglas** confirma cuántas personas se necesitan por franja, las semanas de la ventana legal y el máximo de noches seguidas.

## Cada mes

### 1. Registrar las novedades

Pestaña **Novedades**: elige colaborador, tipo (vacaciones, incapacidad, licencia, libre solicitado) y fechas. Las novedades bloquean esos días y bajan las horas contratadas del periodo.

### 2. Generar el cuadro

Pestaña **Cuadro** → elige el mes → **Generar… → Generar desde cero**. En unos segundos aparece el cuadro con colores por turno. Debajo de la grilla:

- **Cubiertos mañana / tarde / noche** muestra `hay/requeridos` por día. En rojo, si falta alguien.
- **Alertas** lista lo que incumple una regla (por ejemplo menos de 12 h entre dos turnos).

### 3. Ajustar

Haz doble clic en una celda y escribe el código del turno (`M`, `T`, `C`, `NC`) o `L` para libre. Cuadrante:

- guarda el cambio como **fijo** (el solver ya no lo mueve),
- lo marca en **amarillo** frente al original,
- revalida y avisa si rompe una regla, sin impedírtelo.

El listado **Cambios respecto al original** muestra cada diferencia (persona, fecha, antes → después).

### 4. Cuando llega una novedad tarde

Regístrala en **Novedades** y usa **Generar…**:

| Opción | Cuándo usarla |
|---|---|
| **Regenerar solo una semana…** | Lo más seguro: lo demás del mes no cambia. |
| **Regenerar respetando mis cambios** | Rehace el mes completo pero conserva tus ediciones manuales. Puede mover otras celdas. |
| **Generar desde cero** | Descarta todo. Pide confirmación si hay cambios. |

### 5. Publicar y restaurar

- **Publicar como original** congela el cuadro actual como versión oficial.
- **Restaurar desde original…** devuelve todas las celdas al original.
- El selector **Ver** alterna entre *Cambios* (editable) y *Original* (solo lectura).

### 6. Revisar puestos, capacitación y horas

- **Puestos y capacitación**: quién ocupa cada puesto cada día, el grupo de pausa (P1 sale primero, P2 cubre) y las sesiones de capacitación del mes.
- **Horas y recargos**: contratadas, trabajadas, pendientes y adicionales por persona, horas extra, nocturnas y dominicales/festivas, y días de descanso trabajados. Una persona con 3 o más domingos/festivos queda marcada como *habitual*.

### 7. Exportar

**Exportar Excel** pide una carpeta y guarda tres archivos:

| Archivo | Contenido |
|---|---|
| `CUADRO <MES AÑO>.xlsx` | Hojas *Cuadro* (con lo cambiado en amarillo), *Original* y *Cambios* |
| `PUESTOS <MES AÑO>.xlsx` | Una hoja por semana con puestos, noche y capacitación |
| `HORAS Y RECARGOS <MES AÑO>.xlsx` | Horas por persona y categoría, horas por semana y el régimen aplicado |

Si el archivo ya existe, guarda `v2`, `v3`… y no sobrescribe nada.

## Preguntas frecuentes

**¿Por qué una celda no deja cambiar?** Los días de novedad (VAC, INC…) y la vista *Original* son de solo lectura.

**La app dice que faltan personas en un día.** Hay demasiadas novedades o restricciones ese día. Revisa **Novedades**, o baja la cobertura requerida si es una decisión del servicio.

**¿Dónde quedan mis datos?** En `turnos.db`, junto a la app. Para respaldarlos, copia ese archivo.

**Cambié un horario de turno y salieron alertas.** Es lo esperado: el cuadro existente se revalida con los horarios nuevos. Regenera el mes o la semana.

**¿Qué hago si algo falla?** El detalle queda en `errores.log`, junto a la app. Envíalo a quien mantiene Cuadrante.
