# Dashboard de analíticas de Esterilización — diseño

[← Volver al inicio](../../../README.md) · [Visión](../../VISION.md) · [Núcleo](../../NUCLEO.md)

Estado: **entrega 1 en desarrollo** (25/10/2026). Las entregas 2 y 3 están especificadas aquí pero no se construyen todavía.

## 1. Qué se quiere lograr

Una sección **Analíticas** del área Esterilización que responda, en solo lectura y con datos que ya existen, a ocho preguntas de la coordinación. El usuario aprobó las 8 métricas y que se entreguen por partes.

**Criterios de éxito**
- Nada se escribe en la base: sin migraciones (`user_version` sigue en 6; la sesión de solicitudes puede añadir la 7) y sin dependencias nuevas.
- El cálculo vive en un módulo puro sin Qt; la UI solo pinta.
- Gráficos con `QPainter` y los tokens `C` de `an/nucleo/tema.py`; ningún estilo por área.

**Fuera de alcance:** costo en pesos (no hay salario por persona; exigiría migración v7). El «costo estimado» es **horas equivalentes** (`recargos.reporte["equivalentes"]`). Otros servicios (pieza V). Exportar a Excel.

## 2. Entregas

| Entrega | Métricas | Fuente |
|---|---|---|
| **1** (esta) | 1 Ausentismo, 2 Simultáneos, 6 Cobertura, 8 Cambios | `novedad`, `asignacion`, `cambio_turno`, `reglas.faltantes_dia`, `puestos.alertas_reparto` |
| 2 | 3 Horas extra por esquema, 4 Recargos, 5 Equidad | `recargos.reporte`, `flujo.resumen_horas`, `solver.carga` |
| 3 | 7 Banco de horas y tendencia | `banco_mov`, `cierre`, `flujo.estado_banco` |

Las entregas 2 y 3 añaden funciones al mismo módulo y bloques a la misma sección; no cambian lo de la entrega 1.

## 3. Módulo puro `an/esterilizacion/analitica.py`

Todas las funciones reciben `bd` y un rango de fechas `(ini, fin)` y devuelven estructuras simples (dict/list de tipos básicos). Solo cuentan personas `en_solver` (activas y no refuerzo).

- `ausentismo(bd, ini, fin)` → `{"por_tipo": {tipo: dias}, "por_persona": {nombre: {tipo: dias}}, "por_mes": {"AAAA-MM": {tipo: dias}}, "pct": float}`. Cada novedad se recorta al rango; un día con varias novedades cuenta una vez (la primera, igual que `Contexto.novedad`). `pct` = días de ausencia / (días del rango × personas).
- `simultaneos(bd, ini, fin)` → `{"serie": [(fecha, n)], "maximo": n, "fecha_maximo": fecha|None, "dias_riesgo": [fecha]}`. `n` = personas distintas con novedad ese día. `dias_riesgo` = días con cuadro cuyo `reglas.faltantes_dia` tiene algún faltante obligatorio **y** al menos una ausencia.
- `cobertura(bd, ini, fin)` → lista por periodo con cuadro que intersecta el rango: `{"periodo", "dias_deficit", "dias_exceso", "puestos_sin_cubrir"}`. Déficit = día con faltante en alguna franja. **Exceso** = día en que hay al menos un tramo de 30 min con más personas presentes que la demanda total (obligatoria + deseable). `puestos_sin_cubrir` = `len(puestos.alertas_reparto(...))` con `bd.asignacion_puesto`.
- `cambios_resumen(bd, ini, fin)` → `{periodo: {"permuta": n, "servicio": n, "ajuste": n, "excepciones": n}}` vía `cambios.listar`, sin anulados.

Rango por defecto en la UI: últimos 6 meses terminando en el mes de la vista.

## 4. Gráficos `an/nucleo/graficos.py`

Núcleo compartido, para reutilizar en otras áreas:
- `Barras(datos, horizontal=False, apilado=False)` — `datos` = lista de `(etiqueta, {serie: valor})`; colores de serie tomados de `C`.
- `Linea(puntos)` — serie `(etiqueta, valor)` con marcador del máximo.
Ambos son `QWidget` con `paintEvent`, tamaño mínimo razonable, sin datos → texto atenuado. No leen base ni parámetros.

## 5. UI

`_pestana_analiticas` en `paginas.py`, sección **Analíticas** después de «Historial y banco de horas». Arriba: selector de mes inicial y final y 4 tarjetas con cifras (ausentismo %, máx. simultáneos, días en déficit, cambios). Debajo: un panel por métrica (gráfico + tabla corta). Se recalcula al cambiar el rango o al entrar en la sección (`seccion_activa`). Sin datos → `con_vacio`.

## 6. Pruebas (cada una imprime `OK`)

- `tests/esterilizacion/test_analitica.py`: BD en memoria con novedades solapadas y fuera de rango (recorte), un día con déficit conocido, cambios con una anulación y una excepción.
- `tests/nucleo/test_graficos.py`: los widgets pintan (`grab()`) con datos y vacíos, offscreen.
- Ampliar `tests/esterilizacion/test_gui.py`: la sección existe, se llena y `grab()` no falla.
- Regresión: `test_cambios`, `test_puestos`, `test_turnos`, `test_nucleo`.

## 7. Docs

`CLAUDE.md` (layout y comandos de prueba) y `docs/GUIA_USUARIO.md` (qué mide cada gráfico).
