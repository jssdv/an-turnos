# Diseño v1 (aprobado)

> Documento histórico: diseño de la v1 de Esterilización, previo a unirla con Radiología en una sola app (luego retirada: la versión vigente es la web, ver [PLAN_WEB.md](PLAN_WEB.md)). Para el estado actual, ver el [README](../README.md), la [arquitectura](ARQUITECTURA.md) y las [reglas](REGLAS.md).

## Contexto

Esterilización arma hoy sus turnos a mano en Excel (`TURNOS ESTERILIZACION TEST.xlsx`: hojas `BASE`, `CICLOS`, `CICLOS - ESTUDIAN`). La coordinadora necesita una app de escritorio, **independiente** de la de Radiología (`ASIGSEMRADIO`), que:

1. gestione personal y novedades desde la GUI,
2. **genere** el cuadro mensual con OR-Tools (porque llegarán más novedades y días libres),
3. asigne los puestos del día y programe la capacitación mensual,
4. cuente horas (semana / ventana / mes vs contratadas) y recargos según el CST vigente,
5. exporte tres Excel: cuadro mensual, planilla de puestos, reporte de horas y recargos.

Corre en un PC corporativo sin permisos de administrador (mismo empaquetado portátil que Radiología).

## Decisiones tomadas con el usuario

| Tema | Decisión |
|---|---|
| Estructura | App nueva, **solo Esterilización** (sin capa multiservicio) |
| Motor | **OR-Tools CP-SAT** |
| Régimen de horas | **Art. 165 CST**: promedio en ventana de N semanas (N configurable, 3 por defecto) contra 42 h/sem; exceso = suplementario, déficit = pendiente |
| Alcance v1 | Personal y novedades · generar y editar cuadro · puestos y capacitación · horas y recargos |
| Salidas v1 | Excel cuadro mensual · planilla diaria/semanal de puestos · reporte de horas y recargos |
| Turnos | **Catálogo editable**: ajustar horarios de M/T/C/NC y crear turnos nuevos desde la GUI |
| Almuerzo | Cada turno define su **pausa** (minutos, hora, pagada o no); por defecto no pagada y no computa (art. 167 CST) |
| Versiones | **Plantilla original** (cuadro tal como se generó/publicó) y **plantilla de cambios** (la vigente con ediciones, novedades sobrevenidas) |
| Fuera de v1 | Agendas `.ics`, PDF imprimible, solicitudes/cambios entre colegas, multiusuario |

## Reglas del servicio (del usuario)

- Turnos: **M** y **T** = 6 h; **C** (corrido) = 12 h cubre M y T; **NC** = 12 h noche; **L** = libre.
- Cobertura lun–sáb: 4 M + 4 T + 2 NC. Domingo: 2 M + 2 T + 2 NC. Domingos y festivos: solo medios turnos (M o T) de día.
- Descanso mínimo de **12 h** entre fin de un turno e inicio del siguiente.
- 13 personas en cuadro: 12 con rotación completa + 1 con restricciones (sin noches, siempre en el puesto 3, solo M/T).
- 2 estudiantes con bloques fijos de estudio (no disponibles): A = lun, jue, vie en la mañana + mar en la tarde (sáb y dom no estudia); B = jue en la mañana + vie todo el día.
- 1 estudiante de refuerzo: 7–5 lun–jue, 7–1 viernes.
- Puestos del día: 1 lavado, 2 autoclave, 3 sterrad y esto, 4 cuarto estéril, 5 ropa (si sobra gente).
- Capacitación mensual: todos deben poder asistir, repartida en varias semanas, **máx. 1 por semana**, preferencia lunes (festivo → siguiente día hábil).
- Rotación semanal de turnos justa; conteo de horas semana/mes; recargos.
- Cuenta de capacidad: 12 × 42 = 504 h/sem disponibles vs 480 h/sem requeridas (6 × 72 + 48), así que sobran ~24 h para ropa/capacitación/novedades. Por eso el solver debe tratar horas como **objetivo suave** y cobertura como **regla dura**.

## Normativa verificada (fuentes de divulgación; confirmar con jurídico/RR. HH.)

- Jornada máxima **42 h/sem** desde el 15-jul-2026 (art. 161 CST, Ley 2101/2021 + Ley 2466/2025).
- Franja nocturna **7 p. m.–6 a. m.** desde el 25-dic-2025 (art. 160), recargo **35 %**.
- Recargo dominical/festivo: **80 %** hasta 30-jun-2026, **90 %** desde 1-jul-2026, **100 %** desde 1-jul-2027. Se acumula con el nocturno (90 + 35 = 125 %).
- Extras: diurna **+25 %**, nocturna **+75 %**; se suman a los otros recargos.
- Turno sucesivo (art. 161 lit. d) limita a 6 h/día y 36/sem, así que los turnos de 12 h dependen del **art. 165** (promedio ≤ 3 semanas) o del 166 (56 h/sem, autorización). Mintrabajo concepto 115750/2026 no da método de cálculo → la ventana y tarifas son **datos editables**, no constantes.
- Trabajo en día de descanso: ocasional ≤ 2 al mes, habitual ≥ 3 (afecta compensatorio). La app reporta el conteo.
- Descanso semanal: al menos 1 día libre por semana (regla dura del solver).

## Arquitectura

Proyecto nuevo, carpeta propia (propuesta: la raíz del repositorio, git propio). Python 3.13, `PySide6-Essentials`, `openpyxl`, `ortools`, `sqlite3` (stdlib). Núcleo sin GUI; Qt solo lo llama. Pocos archivos planos, como la app de Radiología.

```
dominio.py     dataclasses + catálogo de turnos (horas, hora inicio/fin, cuenta M/T), cobertura por tipo de día,
               festivos de Colombia (ley Emiliani, stdlib), tipos de novedad
db.py          SQLite: esquema, migraciones (PRAGMA user_version), CRUD
reglas.py      validación pura sobre un cuadro (intervalos): cobertura, descanso 12 h, estudio, novedades, día libre
solver.py      modelo CP-SAT del mes; devuelve cuadro + explicación si es infactible
puestos.py     asignación diaria de puestos 1–5 con rotación (CP-SAT pequeño)
capacitacion.py  reparto de sesiones del mes (lunes, ≤1/sem, todos asisten)
recargos.py    corta cada turno en horas → nocturna/diurna × ordinaria/dominical-festiva × extra; ventana art. 165; tarifas por vigencia
exportar.py    3 Excel (openpyxl), nombres sin sobrescribir (v2, v3…)
app.py         ventana PySide6
test_turnos.py asserts, imprime OK
empaquetar.sh  zip portátil Windows (copia adaptada del de Radiología)
```

### Catálogo de turnos editable

Cada turno es una fila de datos, no una constante: código, nombre, hora inicio, hora fin (puede cruzar medianoche), horas (calculadas), color, `cubre` (subconjunto de {mañana, tarde, noche} para la cobertura; C = mañana+tarde), `pausas` (lista de {minutos, hora de inicio sugerida, pagada}; p. ej. C: almuerzo 60 min; NC: cena 60 min; M/T: ninguna o 30 min), `permitido_domingo_festivo`, `usar_en_solver`, activo. Pestaña **Turnos** en Parámetros: cambiar horarios de M/T/C/NC y crear turnos nuevos (p. ej. "M7" 07–13, "T5" 13–19). Todo lo demás se deriva del catálogo, así que cambiar un horario actualiza solo: transiciones prohibidas por el descanso de 12 h, horas semanales, cortes nocturnos/dominicales de los recargos y la cobertura. Reglas: un turno en uso no se borra (se desactiva); al editar horarios el cuadro existente se revalida y se avisa qué choca. La cobertura requerida por tipo de día (lun–sáb, domingo/festivo, por franja) también es editable.

### Pausas de almuerzo

- **Horas:** horas trabajadas = duración − pausas no pagadas. Ese valor alimenta el conteo semanal, la ventana del art. 165 y los recargos; la pausa no pagada no cuenta como hora ni recibe recargo. Una pausa marcada "pagada" sí cuenta (acuerdo expreso). Cambiar el catálogo recalcula todo.
- **Descanso de 12 h** entre turnos se mide sobre inicio y fin del turno completo (pausas no lo alteran).
- **Cobertura:** el solver no las modela; la planilla de puestos asigna **relevos escalonados** (grupo 1 / grupo 2 por franja) para que lavado y autoclave no queden vacíos, rotando quién almuerza primero. La restringida se escalona con su grupo.
- **Aviso, no bloqueo:** la app avisa si un turno de más de 6 h no tiene pausa. Lo dispuesto por el art. 167 (descanso sin computar, salvo acuerdo) lo confirma RR. HH.; las fuentes no tratan turnos de 12 h.

### Plantilla original y plantilla de cambios

Cada mes tiene dos versiones guardadas en la base: **Original** (se congela al generar o al pulsar "Publicar") y **Cambios** (copia de trabajo donde caen las ediciones manuales, novedades que llegan tarde y regeneraciones parciales). El cuadro siempre se edita sobre Cambios; Original no se modifica salvo volver a publicar. La grilla marca en amarillo las celdas distintas de Original y un panel lista los cambios (persona, fecha, antes → después), reutilizando la idea de `comparar_libros` de Radiología. "Restaurar celda/semana desde Original" deshace cambios. Los tres Excel salen de Cambios, y el cuadro mensual incluye la hoja `Original` y la hoja `Cambios` (lista de diferencias). Horas y recargos se calculan sobre Cambios (lo realmente trabajado) y se puede ver la diferencia contra Original.

### Datos (SQLite)

`turno` (catálogo arriba) · `cobertura` (tipo de día, franja, cantidad) · `colaborador` (nombre, tipo: regular / restringido / estudiante / refuerzo, horas contrato por sem, % jornada, activo, restricciones como JSON: turnos permitidos, puesto fijo, bloques de estudio) · `novedad` (colaborador, tipo: vacaciones / incapacidad / licencia / libre solicitado, desde, hasta, nota) · `mes` · `asignacion` (mes, **version: original|cambios**, colaborador, fecha, turno, origen solver/manual, `fijo`) · `puesto_dia` (fecha, franja, puesto, colaborador) · `capacitacion` (fecha, colaborador) · `tarifa` (concepto, %, vigente_desde) · `parametro` (ventana semanas, divisor mensual, duración capacitación…) · `festivo` (año, fecha, nombre; autogenerado, editable).

### Solver (CP-SAT)

Variables `x[p,d,s]` con `s` = L más los turnos del catálogo con `usar_en_solver`; una por persona/día. Cobertura, descanso y horas se leen del catálogo.

**Duras:** cobertura por día (C cuenta para M y T); sin M/T-C en domingo/festivo salvo medio turno; descanso 12 h = transiciones prohibidas con fin/inicio reales (NC → M/C del día siguiente, etc.); ≥ 1 L por semana; novedades y bloques de estudio → L/no disponible; restricciones de la persona restringida; celdas `fijo` (ediciones manuales) intocables; continuidad con los últimos días del mes anterior.

**Suaves (objetivo ponderado):** horas por ventana del art. 165 cerca de 42 h/sem × N (penaliza déficit y exceso por separado); rotación (no repetir el mismo turno muchas semanas seguidas); equidad de noches, domingos/festivos y turnos C, incluyendo acumulado de meses anteriores; evitar NC justo antes de bloque de estudio.

**Infactible:** se relaja por grupos con supuestos (`assumptions`) y se muestra al usuario qué regla choca ("el 14-oct faltan 2 M: 3 personas con novedad").

Regeneración parcial: congelar todo menos una semana o persona. Se ejecuta en `QThread` con límite de tiempo.

### Puestos

Por día y franja (M, T), asigna 4 puestos (5 si sobra gente) minimizando repetición del mismo puesto por persona y rotando justo; la persona restringida queda siempre en el 3; C ocupa el mismo puesto toda la jornada; noche sin puestos; añade el grupo de almuerzo/pausa de cada persona. La estudiante de refuerzo cubre ropa cuando está disponible.

### Recargos y horas

Cada turno se corta por hora real y se clasifica según `franja nocturna (19–06)`, `domingo/festivo` y si cae sobre el exceso de la ventana. Salida por colaborador/mes: horas ordinarias diurnas, nocturnas, dominical/festiva diurna y nocturna, extras por tipo, horas contratadas vs trabajadas (pendientes/adicionales), días de descanso trabajados (ocasional/habitual) y **horas equivalentes ponderadas** (horas × factor), útil sin salario. Valor en pesos solo si se ingresa el salario (opcional). Las tarifas se leen por fecha de vigencia, así el cambio de 80→90→100 % no requiere código.

### GUI (pestañas)

Cuadro (grilla editable por celda con validación en vivo, selector Original/Cambios, celdas cambiadas en amarillo, Generar, Publicar, restaurar desde Original, estado y explicación) · Personal · Novedades (calendario/lista) · Puestos · Capacitación · Horas y recargos · Parámetros (catálogo de turnos con horarios y turnos nuevos, cobertura, tarifas, festivos, ventana). Se copian de `app.py` de Radiología: `ESTILO`, `tabla`, `llenar`, `ocupado`, `error_inesperado`, patrón de `QSettings` (con otro nombre de organización/app) y `ruta_libre`. Siempre modo claro y textos en español.

## Supuestos a confirmar al implementar

1. Horarios iniciales: M 06–12, T 12–18, C 06–18, NC 18–06 (editables desde la GUI).
2. C cuenta como cobertura de M y T a la vez; festivo = cobertura de domingo.
3. Las 13 personas incluyen a las 2 estudiantes y a la restringida; el refuerzo queda fuera del solver (horario fijo, aprendiz).
4. Persona restringida: tu mensaje dice puesto 3 (sterrad); la hoja `BASE` dice "siempre asignación autoclave" (2). Se usa 3 hasta que lo confirmes.
5. Capacitación: duración por defecto 2 h dentro de un turno de día de cada persona; si no calza, se programa otro lunes.
6. Horas contratadas del mes = 42 h × (días del mes / 7) × % jornada, descontando novedades.

## Orden de construcción (cada paso sirve solo)

1. `dominio` (catálogo de turnos editable), `db` (con versiones original/cambios), `reglas`, `recargos`, festivos + tests.
2. `solver` con tests de factibilidad (cuadro del mes con 13 personas y novedades).
3. `puestos` y `capacitacion`.
4. `exportar` (3 Excel).
5. `app.py` (Personal → Novedades → Cuadro → resto).
6. `empaquetar.sh` con wheels `ortools` win_amd64 y prueba en el PC corporativo (`prueba`).

## Riesgos

- **Wheel de OR-Tools** para Python 3.13 en Windows (y el venv de desarrollo usa 3.14): verificar antes de empezar; si no hay para 3.14, crear venv con 3.13. Paquete ~100 MB.
- Antivirus/política del PC corporativo con `.pyd`/DLL de OR-Tools: probar con el modo `prueba` antes de invertir en la GUI.
- Interpretación legal del art. 165 con 12 h: dejar ventana y tarifas editables y marcar en el reporte el régimen aplicado.

## Verificación

- `.venv/bin/python test_turnos.py` imprime `OK`: festivos 2026 (p. ej. lun 12-oct), cálculo de recargos con ejemplos a mano (NC dominical 18:00–06:00 = 12 h con 11 nocturnas), descanso 12 h, y un mes generado con cobertura 4/4/2 y 2/2/2 sin violar reglas; cambiar el horario de un turno y crear uno nuevo cambia descanso/recargos/cobertura; una pausa no pagada de 60 min en C baja sus horas trabajadas de 12 a 11 y quita esa hora de los recargos; editar una celda de Cambios deja Original intacto y aparece en la lista de diferencias.
- Smoke GUI con `QT_QPA_PLATFORM=offscreen`.
- Generar un mes real con novedades de prueba, abrir los 3 Excel y revisar totales contra el cálculo manual.
- `./empaquetar.sh prueba` en el PC corporativo.
