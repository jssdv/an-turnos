# Puestos de trabajo y calculadora de dotación — diseño

[← Volver al inicio](../../../README.md) · [Visión](../../VISION.md) · [Arquitectura](../../ARQUITECTURA.md) · [Hoja de ruta](../../HOJA_DE_RUTA.md)

Estado: **implementado** (21/10/2026), según el [plan](../plans/2026-10-21-puestos-dotacion.md). Diferencias respecto a este documento: el selector de turnos ya no pide «cubre» y el margen de la verificación se aplica al mínimo entero.

## 1. Qué se quiere lograr

La coordinación necesita **gestionar los puestos de trabajo** desde la app (crear, editar, eliminar) y **calcular cuántas personas hacen falta** para cubrir esos puestos y sus horarios.

Hoy los cinco puestos están fijos en el código (`puestos.py`) y la cobertura se escribe aparte como «4 mañana, 4 tarde, 2 noche», sin relación con los puestos. Algunos puestos necesitan varias personas, y varios tienen horarios que caen a mitad de franja (por ejemplo 08:00–14:00).

**Criterios de éxito**
- Crear o cambiar un puesto (personas requeridas, horario, tipo de día) cambia la cobertura exigida al generador, la validación y el reparto diario, sin tocar código.
- Un puesto puede pedir varias personas y una ventana horaria arbitraria (múltiplos de 30 min), también de noche.
- Se distingue lo **obligatorio** de lo **deseable** (por ejemplo, Ropa «si se puede»).
- La calculadora dice cuántas personas se necesitan, desglosado por puesto y franja, y compara con el personal activo (sobran o faltan).

**Fuera de alcance:** costos y presupuesto, simular contrataciones con restricciones distintas, relevos de almuerzo dentro de la demanda, otros servicios.

## 2. Decisiones tomadas con el usuario

| Tema | Decisión |
|---|---|
| Relación puesto–cobertura | La cobertura **sale de los puestos** (suma de su demanda); desaparece el «4+4+2» manual |
| Horarios de puestos | **Por tramos de 30 min** (los puestos reales caen a mitad de franja) |
| Varias personas por puesto | Campo «personas requeridas» en cada regla de demanda |
| Obligatorio / deseable | Cada regla es obligatoria o deseable |
| Calculadora | Estimación inmediata por horas **y** verificación con el generador (mínimo de personas factible) |
| Quién puede qué puesto | Lista de puestos permitidos por persona; «puesto fijo» es el caso de una lista de uno |

## 3. Modelo de datos

```
puesto          (id, numero, nombre, color, activo)
demanda         (id, puesto_id, tipo_dia 'LS'|'DF', inicio_min, fin_min, personas, obligatorio)
persona_puesto  (colab_id, puesto_id)            -- vacío = puede todos
```

- `inicio_min` y `fin_min` son minutos desde las 00:00, múltiplos de 30. Si `fin ≤ inicio` la ventana cruza medianoche.
- `tipo_dia` es el del día en que **empieza** la ventana (un puesto de noche del sábado cuenta como sábado hasta las 06:00 del domingo).
- Un puesto puede tener varias reglas, incluso solapadas (se suman). Ejemplo: Lavado, `LS`, 06:00–18:00, 2 personas, obligatorio; Lavado, `DF`, 06:00–12:00, 1 persona, obligatorio.
- `Turno.cubre` deja de editarse y **se calcula**: un turno cuenta en una franja (M 06–12, T 12–18, N 18–06) si se solapa con ella al menos 3 h. M7 (07:00–13:00) es M; C (06:00–18:00) es M y T; NC es N. Se sigue usando para detectar noches y corridos.

## 4. Tiempo y cobertura

- El día se divide en **48 tramos de 30 min**. La demanda del tramo `t` del día `d` es la suma de las reglas activas (obligatorias y, aparte, deseables) cuyo `tipo_dia` corresponde a `d` y cuya ventana contiene `t`.
- Un turno asignado el día `d` aporta una persona a cada tramo que cubre su horario real. Una noche que cruza medianoche aporta a los primeros tramos de `d+1`; para el primer día del periodo cuentan las noches del periodo anterior (`previo`), como ya ocurre con el descanso.
- Las pausas de almuerzo **no** restan cobertura en esta versión.

## 5. Generador

- Restricción por día y tramo: `personas presentes + falta ≥ demanda obligatoria`. La `falta` se penaliza con el peso actual de cobertura faltante, mayor que cualquier otro término.
- Los deseables suman un premio suave por tramo cubierto, siempre menor que equidad, descansos y rachas.
- El resto del modelo no cambia: descanso de 12 h, libre tras noche, rachas, reparto parejo, banco de horas.
- La validación (`reglas.validar`) y la grilla usan la misma demanda. Las filas «Cubiertos mañana/tarde/noche» pasan a indicar si el día cumple o cuántas personas faltan en el peor tramo de esa franja, y el aviso al pasar el cursor lista los tramos exactos.
- Si ningún turno del catálogo cubre una ventana obligatoria, la app lo avisa al guardar el puesto («Ningún turno cubre 08:00–14:00»).

## 6. Reparto de puestos por persona

Paso aparte, **por día**, con un modelo pequeño:
- Variables: persona × puesto × tramo (solo para tramos en que la persona está presente y puede ocupar ese puesto).
- Cada persona ocupa un puesto por tramo; cada puesto recibe al menos la demanda de ese tramo (obligatoria dura en lo posible; deseable suave).
- Se penaliza cambiar de puesto dentro del turno (un corrido suele quedarse en uno), repetir el puesto del día anterior y el desequilibrio de veces por puesto en el periodo, como hoy.
- Si el generador dejó personas de más, quedan como «apoyo». Si faltan, se asignan primero las demandas obligatorias de menor número de puesto.
- «Mostrar puesto» en el cuadro usa el puesto donde la persona pasa más tramos.

## 7. Calculadora de dotación

**Estimación inmediata (por horas).**
`horas-persona semanales = Σ tramos de la semana tipo (6 días LS + 1 DF) × demanda obligatoria × 0,5 h`
`personas = horas-persona ÷ (jornada media contratada × (1 − margen))`, con margen de ausentismo configurable (10 % por defecto). Se muestra por puesto y por franja, con y sin deseables.

**Verificación con el generador (por reglas).**
Busca el mínimo `N` de personas genéricas (jornada completa, sin restricciones) para el que existe un cuadro del periodo seleccionado que cumple la demanda obligatoria y todas las reglas. Se parte de la cota por horas y se prueba con bisección; cada prueba tiene un tope de tiempo y todo corre en segundo plano con avance y cancelación. Resultado: `N` mínimo, `N` con margen, personal activo y diferencia. Si no hay solución ni con un `N` grande, se explica qué regla choca.

## 8. Interfaz

- **Parámetros → Puestos:** lista de puestos y, a la derecha, el formulario (número, nombre, color, activo) con su tabla de reglas de demanda (tipo de día, desde, hasta, personas, obligatorio). Mismo patrón que Turnos: editar, crear, eliminar (un puesto con historial se desactiva).
- **Personal:** casillas de **puestos permitidos** en la ficha (reemplaza «puesto fijo»).
- **Dotación:** pestaña principal con las dos cifras, el desglose, el botón «Verificar con el generador» y el diagnóstico.
- **Parámetros → Cobertura y reglas:** se retiran los números de cobertura.

## 9. Migración (base versión 4)

- Se crean los puestos actuales (Lavado, Autoclave, Sterrad y esto, Cuarto estéril, Ropa) más «Guardia noche».
- La cobertura vieja se convierte en demanda obligatoria conservando los totales: por cada tipo de día y franja M/T, las primeras personas se reparten en el orden de prioridad actual (Autoclave, Lavado, Sterrad, Cuarto estéril, con 1 persona cada uno, y el excedente sumado al primero); la noche pasa a «Guardia noche». Ropa se crea como **deseable** de lunes a sábado.
- `puesto_fijo` de cada persona se convierte en una lista de un puesto en `persona_puesto`.
- La tabla `cobertura` queda sin uso y se elimina en una versión posterior.
- `puesto_dia` guarda ahora tramos o rangos por puesto; los meses ya guardados conservan su reparto anterior.

## 10. Errores y casos límite

Ventana con inicio igual a fin; personas < 1; reglas duplicadas (se suman, con aviso); puesto sin reglas (no exige nada, se avisa); catálogo sin turnos que cubran la ventana; borrar un puesto en uso (se desactiva); persona sin ningún puesto permitido (error al guardar); demanda mayor que el personal (la validación la marca y la calculadora la cuantifica).

## 11. Pruebas

Unitarias: demanda por tramo (incluido cruce de medianoche y `tipo_dia`), derivación de `cubre`, cobertura con un turno parcial (M7), premio de deseables sin romper reglas, migración v3→v4, reparto por tramo con puestos permitidos, estimación por horas con un ejemplo a mano, y bisección con un resolutor simulado. De interfaz: CRUD de puestos y reglas, puestos permitidos en la ficha, pestaña Dotación. Se mantiene `test_turnos.py` y `test_gui.py` como suites de aceptación.

## 12. Fases (cada una se usa sola)

1. **Puestos y demanda:** datos, migración, CRUD en Parámetros, puestos permitidos y estimación por horas. La cobertura que ve el generador se **deriva** de las reglas (máximo por franja), así el solver actual sigue funcionando.
2. **Cobertura por tramos:** solver, validación y grilla pasan a tramos; deseables; `Turno.cubre` pasa a calcularse y se quita de la pantalla de turnos.
3. **Reparto por tramo** con puestos permitidos y cambios dentro del turno.
4. **Verificación con el generador** en la calculadora.

## 13. Riesgos

- **Rendimiento del solver** con 48 tramos por día: se mide en la fase 2 y, si hace falta, se agrupan tramos iguales consecutivos.
- **Turnos que no calzan con los puestos:** el catálogo de turnos debe tener horarios que cubran las ventanas; se avisa, pero no se inventan turnos.
- **Complejidad para quien configura:** muchas reglas de demanda pueden confundir; se mitiga con la vista previa del total por franja y la estimación en vivo.
