# Cuatro funciones nuevas (diseño corto)

Aprobado el 13/11/2026. Orden de construcción: 1 → 2 → 3 → 4, una rama por función.

## Por qué

Lo que más piden las herramientas de turnos (autoservicio, cambios, avisos) adaptado a An, que corre sin servidor: menos trabajo manual para la coordinación y RR. HH., y que cada persona tenga su horario.

## 1. Excel del banco de horas

- Nuevo tipo de exporte `banco`: hoja «Saldos» (persona, anterior, periodo, total, cerrado) desde `flujo.estado_banco` y hoja «Movimientos» con los movimientos manuales (`bd.movimientos()`).
- Entra por el mismo flujo de exportes (`rutas_exportes`, `exportar.py`) y aparece en Reportes.
- No-objetivo: valores en pesos.

## 2. Agenda .ics y vista imprimible por persona

- `.ics` por persona del periodo, versión `cambios`, reutilizando `radiologia.analisis.ics`. ZIP con todos.
- PDF: vista de impresión del cuadro filtrada a una persona (`?imprimir=1&persona=<id>`); se guarda como PDF desde el navegador. Sin librería de PDF.

## 3. ¿Quién cubre?

- Caso: una celda con turno queda sin cubrir (ausencia, cambio).
- Enfoques: **A (elegido)**: para cada candidato libre ese día, asignar el turno en una copia del cuadro, correr `reglas.validar` y ordenar; instantáneo y reutiliza reglas. B: resolver de nuevo con el resto fijo; más lento y puede mover otras celdas. C: lista manual sin chequeo; no evita errores.
- Orden: sin errores primero; luego menos avisos, menos horas en la ventana, menos veces ese turno en el periodo (equidad).
- Elegir uno registra un cambio `servicio` con motivo (auditado y anulable).
- Interfaz: botón «¿Quién cubre?» en el cuadro; panel con los 5 mejores y su razón.

## 4. Importar el Excel actual

- Carga personal y ciclos desde `BASE`, `CICLOS`, `CICLOS - ESTUDIAN`.
- Bloqueado hasta tener una copia real (anonimizada sirve), fuera del repo y sin subirla.

## Lo que queda al constructor

Nombres de campos y textos de la interfaz, siguiendo las convenciones del proyecto (español, reglas como datos, una prueba por cambio de comportamiento).
