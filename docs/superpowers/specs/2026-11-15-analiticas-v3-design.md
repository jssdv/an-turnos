# Analíticas v3: cobertura por tramo, equidad y planificación (diseño corto)

15/11/2026. El usuario pidió seguir sin pausas, con métricas y gráficos útiles sacados de investigación web. Investigación: `docs/investigacion/reports/Métricas útiles para analíticas de turnos.md` y sus notas.

## Por qué

v2 cuenta días con déficit, pero no dice **cuántas horas** faltan ni **a qué hora** del día; la equidad solo muestra máx−mín; las solicitudes no tienen historial por persona; y no hay mirada al proceso de planificación ni al costo que viene con el recargo dominical al 100 % (1/7/2027).

## Qué se construye (3 PR, en orden)

### 1. Cobertura por tramo de 30 min
`analitica.cobertura_tramos(bd, ini, fin)`. Para cada día de cada periodo con cuadro, por tramo: `hay` (presentes), `obl`, `des` (de `demanda_fecha`, misma regla `con_ayer` que `cobertura`). El hueco se calcula **por tramo** antes de sumar (un tramo sobrado no tapa otro corto).
- `horas_requeridas` = Σobl/2 · `horas_faltantes` = Σmax(0, obl−hay)/2 · `horas_sobrantes` = Σmax(0, hay−(obl+des))/2.
- `cobertura_pct` = 1 − faltantes/requeridas (Infor) · `eficiencia_pct` = 1 − (faltantes+sobrantes)/requeridas.
- `mapa`: 7 × 48, promedio de `hay − obl` por día de la semana y tramo (solo tramos con demanda o con gente).
- UI: indicadores, mapa de calor día × hora (rojo falta, azul sobra, neutro justo) con tabla de horas por periodo.

### 2. Equidad y solicitudes
- `equidad` suma por categoría: media, desviación media absoluta (MAD), CV y desviación de cada persona respecto de la media (lo recomendado para equipos chicos: Martin et al., MinDev). UI: barras divergentes de desviación (noches; domingos+festivos).
- `concentracion_extra(bd, ini, fin)`: horas extra por persona y % que hizo el 20 % con más horas.
- `solicitudes_resumen(bd, ini, fin)`: por persona, pedidas / cumplidas / parciales / no cumplidas (de `solicitudes.evaluar` por periodo) y tasa del equipo; dispersión de la tasa entre personas.

### 3. Planificación y lo que viene
- `pronostico_ausencias(bd, hasta)`: días de ausencia por mes (12 meses) y estimado del mes siguiente = promedio de «mismo mes del año pasado» y «media de los últimos 3 meses» (benchmark ingenuo estacional; equipo chico).
- `corridas(filas)` desde la tabla `trabajo` (la lee la ruta): corridas por periodo, % que terminaron bien, mediana de duración, faltantes de la última.
- `proximo_recargo(bd, hoy, festivo_h)`: siguiente cambio de tarifa dominical después de hoy y cuántas horas equivalentes más costaría al mes con el volumen dominical/festivo actual.

## Fuera
Pronósticos con modelos, costo en pesos (sin salarios), registro de cuándo se creó una ausencia (requiere migración; anotado en la hoja de ruta).

## Cómo se prueba
Una prueba con assert por métrica en `tests/turnos/test_analitica.py`, la API en `tests/web`, el mapa en `web/pruebas`; demo local en escritorio y a 375 px.
