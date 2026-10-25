# Guía de uso

[← Volver al inicio](../README.md) · [Reglas](REGLAS.md) · [Hoja de ruta](HOJA_DE_RUTA.md)

Esta guía recorre un mes completo. Todo se hace dentro de An~; no hace falta tocar Excel hasta el final.

## Antes de empezar (una sola vez)

1. **Personal.** Pestaña **Personal** → *+ Nuevo colaborador*. A la derecha se llena la ficha:
   - **Jornada semanal** y **% de jornada**.
   - **Puede hacer**: desmarca los turnos que no puede cubrir (por ejemplo, quita NC y C a quien no hace noches).
   - **Puestos que puede ocupar**: marca solo los que corresponden (por ejemplo, solo el 3, sterrad y esto). Si marcas todos, puede ocupar cualquiera; debe quedar al menos uno.
   - **No disponible por estudio**: marca los bloques de mañana o tarde de cada día en que estudia.
   - **Activo**: desmárcalo para que no entre en los cuadros nuevos sin perder su historial.

   Para **editar**, haz clic en la persona de la lista, cambia la ficha y pulsa *Guardar*. Para **eliminar**, selecciónala y pulsa *Eliminar*: si nunca tuvo cuadros ni novedades se borra; si tiene historial queda **inactiva** (se ve con *Mostrar inactivos*) para no perder lo ya registrado.
2. **Turnos.** Pestaña **Parámetros → Turnos**. Selecciona un turno para editarlo o usa *+ Nuevo turno*:
   - **Empieza / Termina** (formato 24 h; si termina antes de empezar, cruza la medianoche).
   - **Pausa de almuerzo**: minutos y hora; marca *cuenta como trabajada* si es pagada. Abajo ves cuántas horas se cuentan.
   - **Cuenta en**: la app calcula sola si el turno cuenta en mañana, tarde o noche (se solapa al menos 3 h con esa franja) y lo muestra abajo.
   - Si se puede usar en domingo o festivo, si el generador puede asignarlo, el color y si está activo.

   *Eliminar* borra el turno si nunca se usó; si ya está en cuadros guardados queda inactivo. Mientras un turno de más de 6 h no tenga pausa, la app lo avisa.
3. **Puestos y su demanda.** Pestaña **Parámetros → Puestos**. Cada puesto dice **cuántas personas necesita y en qué horario**; de ahí sale la cobertura que exige el generador. Usa *+ Nuevo puesto* o selecciona uno para editarlo:
   - **Número, nombre, color y activo.**
   - **Reglas de demanda**, las que quieras por puesto: días (*lunes a sábado* o *domingo y festivo*), **desde** y **hasta** (múltiplos de 30 min; si «hasta» es menor que «desde», cruza la medianoche), **personas** y si es **obligatoria** o **deseable**.
   - Una regla **obligatoria** se exige al generar el cuadro; una **deseable** (por ejemplo, Ropa «si se puede») se busca si alcanza la gente, sin romper descansos ni el reparto parejo.
   - Un puesto puede pedir **varias personas** a la vez, con ventanas a mitad de franja (por ejemplo, 08:00–14:00) o de noche (18:00–06:00).

   Al guardar, la app avisa si **ningún turno del catálogo cubre** esa ventana («Ningún turno cubre 08:00–14:00») o si hay reglas solapadas (se suman). Un puesto sin reglas no exige nada. *Eliminar* borra el puesto si nunca se usó; si ya tiene reparto guardado queda inactivo.
4. **Reglas y esquema.** En **Parámetros → Cobertura y reglas** confirma las semanas de la ventana legal y las reglas de descanso, que vienen activas por defecto:
   - **Libre después de una noche**: 1 día.
   - **Días libres por semana**: mínimo 1.
   - **Fines de semana libres por esquema** (sábado y domingo): mínimo 1 por persona; el libre posterior a una noche cuenta.
   - **Máximo de noches en racha** (NC, L, NC, L…): 2 por defecto.
   - **Máximo de corridos (C) seguidos**: 2 por defecto; además el generador intenta evitar incluso los pares.
   - **Máximo del mismo turno (M, T…) seguido**: 3 por defecto (nunca 4 M seguidas).

   La pantalla agrupa estos valores en tarjetas: esquema y horas, descansos, límites de repetición y banco de horas.

   Además, el generador reparte parejo M, T, C y NC entre el personal y prefiere poner los libres en sábado o domingo.

   Si quieres romper una regla en un caso puntual, edita la celda a mano: el generador lo respeta y no lo marca como alerta.

## Elegir el esquema (mes o semanas)

Algunos servicios programan por **mes** y otros por **semanas que arrancan un lunes**. En **Parámetros → Cobertura y reglas → Esquema de programación** elige:

- **Mes calendario**: arriba aparece el selector de mes y año.
- **Semanas completas desde un lunes** y su duración (4 por defecto): arriba aparece «Desde el lunes». Si eliges otro día, la app lo ajusta al lunes anterior y lo avisa.

Las flechas ◀ ▶ del encabezado avanzan o retroceden un periodo (un mes, o N semanas). Cada periodo tiene su propio cuadro, y la app cuida el descanso y el reparto entre un periodo y el siguiente. En el resto de esta guía, «mes» significa el periodo que hayas elegido.

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

### Dónde se ve la asignación (el puesto)

Cada celda del cuadro muestra el turno. Para ver **en qué puesto** está cada persona:

- Marca **Mostrar puesto** junto al selector *Ver*: las celdas pasan de `M` a `M·2`. El número es el del **puesto donde la persona pasa más tiempo** ese día y `A` significa **apoyo**, sin puesto ese día. La leyenda con los puestos activos está bajo la grilla.
- Pasa el cursor sobre una celda: el aviso lista los puestos con su horario («Autoclave 06:00–12:00; Lavado 12:00–18:00»), porque una persona puede cambiar de puesto dentro de su turno.
- La pestaña **Puestos y capacitación** muestra, por día, una columna por puesto con quién lo ocupa y en qué horario, más el apoyo y el grupo de pausa (P1/P2).
- En Excel, el archivo del cuadro trae la hoja **Cuadro con puestos** y el archivo de puestos, una hoja por semana.

Las noches también tienen puesto si defines uno de noche (por ejemplo, «Guardia noche»). El reparto respeta los **puestos permitidos** de cada persona y evita cambiar de puesto dentro del turno salvo que la demanda lo exija. Si escribes en una celda con el puesto visible, basta el código (`T`, o `T·2`, ambos valen). Los puestos se recalculan solos con cada cambio.

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

### 7. Cerrar el periodo y llevar el banco de horas

Con el periodo terminado, pulsa **Cerrar periodo**. An~ guarda, por persona, las horas **contratadas** y las **trabajadas**, y la diferencia entra al **banco de horas**:

- **Saldo positivo**: trabajó más de lo contratado, se le deben horas.
- **Saldo negativo**: trabajó menos, debe horas.

Un periodo cerrado queda en **solo lectura** (no se genera, edita, publica ni restaura) y el encabezado dice «CERRADO». Para corregirlo, **Reabrir periodo**: el cierre sale del banco y vuelve a poder editarse.

En la pestaña **Historial y banco de horas → Banco de horas** ves por persona el **saldo anterior** (periodos cerrados y movimientos), lo del **periodo actual** (proyectado mientras no lo cierres) y el **saldo total**, con el estado en texto («Se le deben 12 h», «Debe 8 h», «Al día») y en color. Al seleccionar a alguien, la lista de la derecha muestra cada cierre y cada movimiento.

Para registrar algo que no sale del cuadro:

| Concepto | Para qué | Cómo se anota |
|---|---|---|
| Saldo inicial | Arrancar con lo que ya se debía o se debe | Con signo (+ se le deben, − debe) |
| Compensado en descanso | Horas devueltas con tiempo libre | Escribe las horas en positivo: se restan |
| Pagado en nómina | Horas pagadas | Escribe las horas en positivo: se restan |
| Ajuste | Cualquier corrección | Con signo |

**Compensación automática.** Al generar el siguiente periodo, An~ ajusta la **meta de horas** de cada persona con su saldo anterior: a quien se le deben horas se le baja la meta (trabaja menos) y a quien las debe se le sube. Hay un tope por periodo en cada dirección, 12 h por defecto, que se cambia en **Parámetros → Cobertura y reglas → Banco de horas**; con 0 esa dirección se apaga. Al terminar, el aviso dice a quién se le compensó y cuántas horas. La compensación es una preferencia: la cobertura y las reglas de descanso siempre mandan, y el cierre del periodo sigue midiendo contra las horas contratadas reales.

Los cierres no se borran desde el banco; se deshacen reabriendo el periodo. Los movimientos manuales sí se pueden borrar.

### 8. Ver el historial de esquemas

**Historial y banco de horas → Historial de esquemas** lista todos los periodos con cuadro: días, estado (abierto o cerrado), personas, horas trabajadas, saldo del periodo al cerrarlo, cambios frente al original y alertas. Doble clic en uno lo abre en el cuadro, cambiando solo el selector de periodo.

### 9. Calcular cuántas personas se necesitan (Dotación)

La pestaña **Dotación** responde cuántas personas piden los puestos:

- **Estimación inmediata:** horas-persona de una semana tipo (6 días de lunes a sábado + 1 de domingo/festivo) ÷ la jornada media, con un **margen de ausentismo** (10 % por defecto) por vacaciones e incapacidades. Muestra las cifras por puesto y por franja, el personal activo y si **sobran o faltan** personas. La casilla *Incluir puestos deseables* suma esos puestos.
- **Verificar con el generador:** busca el **mínimo de personas** con el que existe un cuadro que cumple los puestos obligatorios **y** todas las reglas de descanso (libre tras noche, fines de semana libres, rachas) del periodo seleccionado. Corre en segundo plano, con barra de avance y botón *Cancelar*, y puede tardar un minuto. Si ninguna cantidad cumple, explica por qué (por ejemplo, que ningún turno cubre una ventana).

La verificación aplica el margen sobre el mínimo entero, así que puede dar una persona más que la estimación por horas.

### 10. Exportar

**Exportar Excel** pide una carpeta y guarda tres archivos:

| Archivo | Contenido |
|---|---|
| `CUADRO <MES AÑO>.xlsx` | Hojas *Cuadro* (con lo cambiado en amarillo), *Original* y *Cambios* |
| `PUESTOS <MES AÑO>.xlsx` | Una hoja por semana: una columna por puesto con quién lo ocupa y su horario, el apoyo y la capacitación |
| `HORAS Y RECARGOS <MES AÑO>.xlsx` | Horas por persona y categoría, horas por semana y el régimen aplicado |

Si el archivo ya existe, guarda `v2`, `v3`… y no sobrescribe nada.

### 11. Analíticas

La sección **Analíticas** (menú lateral, después de «Historial y banco de horas») resume varios meses de un vistazo y **no modifica nada**. Arriba eliges el mes inicial y el final (por defecto, los últimos 6 meses hasta el periodo en pantalla).

- **Ausentismo:** días de vacaciones, incapacidad, licencia y libres solicitados por mes y por persona, y el porcentaje sobre los días-persona del rango. No cuenta a refuerzos ni a personas inactivas.
- **Personas ausentes por día:** cuántas personas tienen novedad cada día; el punto rojo marca el máximo. Los días con ausentes **y** faltantes obligatorios aparecen como «Días en riesgo».
- **Cobertura por periodo:** días con **déficit** (falta gente frente a los puestos obligatorios), días con **exceso** (en algún momento hay más gente que la demanda de los puestos) y puestos obligatorios que quedan sin cubrir en el reparto.
- **Cambios de turno:** permutas, cambios de servicio y ajustes por periodo, sin contar los anulados, y cuántas fueron con excepción al límite.

Las analíticas de horas extra, recargos, equidad y banco de horas llegarán en próximas entregas.

## Preguntas frecuentes

**¿Por qué una celda no deja cambiar?** Los días de novedad (VAC, INC…), las filas de totales y la vista *Original* son de solo lectura; arrastrar sobre ellas avisa.

**La app dice que faltan personas en un día.** Las filas «Cobertura mañana/tarde/noche» de la grilla marcan `−n` y, al pasar el cursor, el horario exacto. Hay demasiadas novedades o restricciones, o la demanda de los puestos es mayor que el personal. Revisa **Novedades**, la pestaña **Dotación** o baja la demanda del puesto si es una decisión del servicio.

**¿Dónde quedan mis datos?** En `turnos.db`, junto a la app. Para respaldarlos, copia ese archivo.

**Quité a alguien y no desaparece.** Si tenía cuadros o novedades queda inactivo para conservar el historial; actívalo de nuevo con *Mostrar inactivos* y marcando *Activo*.

**Cambié un horario de turno y salieron alertas.** Es lo esperado: el cuadro existente se revalida con los horarios nuevos. Regenera el mes o la semana.

**¿Qué hago si algo falla?** El detalle queda en `errores.log`, junto a la app. Envíalo a quien mantiene An~.
