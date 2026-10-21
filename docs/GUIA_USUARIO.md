# Guía de uso

[← Volver al inicio](../README.md) · [Reglas](REGLAS.md) · [Hoja de ruta](HOJA_DE_RUTA.md)

Esta guía recorre un mes completo. Todo se hace dentro de An~; no hace falta tocar Excel hasta el final.

## Antes de empezar (una sola vez)

1. **Personal.** Pestaña **Personal** → *+ Nuevo colaborador*. A la derecha se llena la ficha:
   - **Jornada semanal** y **% de jornada**.
   - **Puede hacer**: desmarca los turnos que no puede cubrir (por ejemplo, quita NC y C a quien no hace noches).
   - **Puesto fijo**: por ejemplo el 3 (sterrad y esto).
   - **No disponible por estudio**: marca los bloques de mañana o tarde de cada día en que estudia.
   - **Activo**: desmárcalo para que no entre en los cuadros nuevos sin perder su historial.

   Para **editar**, haz clic en la persona de la lista, cambia la ficha y pulsa *Guardar*. Para **eliminar**, selecciónala y pulsa *Eliminar*: si nunca tuvo cuadros ni novedades se borra; si tiene historial queda **inactiva** (se ve con *Mostrar inactivos*) para no perder lo ya registrado.
2. **Turnos.** Pestaña **Parámetros → Turnos**. Selecciona un turno para editarlo o usa *+ Nuevo turno*:
   - **Empieza / Termina** (formato 24 h; si termina antes de empezar, cruza la medianoche).
   - **Pausa de almuerzo**: minutos y hora; marca *cuenta como trabajada* si es pagada. Abajo ves cuántas horas se cuentan.
   - **Cubre**: qué franjas (mañana, tarde, noche) cuenta para la cobertura.
   - Si se puede usar en domingo o festivo, si el generador puede asignarlo, el color y si está activo.

   *Eliminar* borra el turno si nunca se usó; si ya está en cuadros guardados queda inactivo. Mientras un turno de más de 6 h no tenga pausa, la app lo avisa.
3. **Cobertura y reglas.** En **Parámetros → Cobertura y reglas** confirma cuántas personas se necesitan por franja, las semanas de la ventana legal y el máximo de noches seguidas.

## Cada mes

### 1. Registrar las novedades

Pestaña **Novedades**: elige colaborador, tipo (vacaciones, incapacidad, licencia, libre solicitado) y fechas. Las novedades bloquean esos días y bajan las horas contratadas del periodo.

### 2. Generar el cuadro

Pestaña **Cuadro** → elige el mes → **Generar… → Generar desde cero**. En unos segundos aparece el cuadro con colores por turno. Debajo de la grilla:

- **Cubiertos mañana / tarde / noche** muestra `hay/requeridos` por día. En rojo, si falta alguien.
- **Alertas** lista lo que incumple una regla (por ejemplo menos de 12 h entre dos turnos).

### 3. Ajustar

Hay tres formas, todas sobre la versión *Cambios*:

- **Escribir:** doble clic en una celda y el código del turno (`M`, `T`, `C`, `NC`), o `L` para libre.
- **Arrastrar y soltar:** arrastra una celda sobre otra para **intercambiarlas**, sea de otra persona o de otro día. El pie de la grilla lo recuerda.
- **En lote:** selecciona varias celdas (con Mayús o Ctrl), clic derecho y elige el turno o «L · libre» para todas a la vez.

Cada cambio:

- queda como **fijo** (el generador ya no lo mueve) y en **amarillo** frente al original,
- se revalida al instante y avisa si rompe una regla, sin impedírtelo,
- se puede **deshacer con Ctrl+Z** (hasta que generes, publiques o restaures).

Los días de estudio aparecen en **morado** sobre las celdas libres, y al pasar el cursor dice si es de mañana o tarde. El listado **Cambios respecto al original** muestra cada diferencia (persona, fecha, antes → después).

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

**¿Por qué una celda no deja cambiar?** Los días de novedad (VAC, INC…), las filas de totales y la vista *Original* son de solo lectura; arrastrar sobre ellas avisa.

**La app dice que faltan personas en un día.** Hay demasiadas novedades o restricciones ese día. Revisa **Novedades**, o baja la cobertura requerida si es una decisión del servicio.

**¿Dónde quedan mis datos?** En `turnos.db`, junto a la app. Para respaldarlos, copia ese archivo.

**Quité a alguien y no desaparece.** Si tenía cuadros o novedades queda inactivo para conservar el historial; actívalo de nuevo con *Mostrar inactivos* y marcando *Activo*.

**Cambié un horario de turno y salieron alertas.** Es lo esperado: el cuadro existente se revalida con los horarios nuevos. Regenera el mes o la semana.

**¿Qué hago si algo falla?** El detalle queda en `errores.log`, junto a la app. Envíalo a quien mantiene An~.
