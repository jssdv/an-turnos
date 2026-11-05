# Estado del proyecto

Foto a 04/11/2026 (`main` en `271170d`, PR 37). Para el detalle de cada pieza: [ARQUITECTURA](ARQUITECTURA.md), [PLAN_WEB](PLAN_WEB.md), [HOJA_DE_RUTA](HOJA_DE_RUTA.md) y `README.md`.

## Qué es hoy

- **Un solo modo:** app portable. API FastAPI + trabajador del solver en un proceso (`an/web/entregable.py`), una base SQLite (`an.db`), front React servido desde `web/dist`.
  - Mac: `deploy/An-mac.command` (doble clic). Windows: exe de PyInstaller armado por `.github/workflows/entregable.yml` al empujar a `main`.
  - Datos en `~/Library/Application Support/AnTurnos/an.db` (Mac) o `%LOCALAPPDATA%/AnTurnos/an.db` (Windows); respaldos al abrir y cerrar.
  - Una clínica y un área por base. Esquema versión 12; migraciones nuevas, numeradas desde 013, en `an/web/migraciones_sqlite/`.
- **Retirado:** el modo servidor (Postgres, Docker, Caddy, RLS) está en la etiqueta `servidor-postgres-final`; la app Qt en `qt-final`.
- **Áreas:** Radiología (cuadro mensual → libro semanal) y Turnos (cuadrícula con OR-Tools CP-SAT, puestos, horas y recargos).

## Pruebas

- Suite completa con `AN_TIEMPO_ESCALA=3`: 250 pasan (≈13 min; `tests/turnos/test_turnos.py` resuelve meses enteros).
- Sin `test_turnos.py`: unos 220 en ≈2 min.
- `web/dist` no va en git: recompilar con `cd web && npm run build` después de traer cambios.

## Cambios recientes (04/11/2026)

- **Sobreasignación de puestos:** `puestos.asignar_tramos` castiga (`W_EXCESO_P` = 500 por persona y tramo) tener más gente que obligatoria + deseable en un puesto; quien sobra queda en apoyo. Es suave: un puesto fijado a mano puede pasarse.
- **Reasignar puestos:** cada ejecución usa una semilla distinta (`semilla` en `asignar_tramos` y `flujo.recalcular`), así que explora otro reparto igual de bueno. Con semilla se suma ruido de desempate (0–9 por variable, menor que el peso real mínimo de 10) porque la semilla del solver sola apenas movía filas (~5 %). Generar sigue reproducible (semilla 0).
- **Partir corridos:** funciona con `partir_corridos=1` (turnos de 10 h o más, que no son de noche): un puesto en la mañana y otro en la tarde. Las áreas nuevas nacen con 1; las existentes se cambian en Parámetros.
- **Celda partida en el cuadro:** con «Ver puestos», una C partida muestra sus dos puestos en orden horario (`C³·⁵`: mañana en el 3, tarde en el 5) y el texto accesible dice «partido: A y luego B». La API del cuadro envía `puestos: [ids]` por celda (vacío si el puesto está fijado a mano); `puesto` sigue siendo el principal. Diseño elegido entre superíndice doble, chip de dos bandas y solo tooltip: el superíndice doble es el que cabe en la celda de 22 px.
- **Verificado con la BD real (04/11):** Reasignar en 30 nov–27 dic y 2–29 nov: 0 tramos con exceso o falta, en puestos y en turnos.
- **Puesto por mitad en una C partida:** el diálogo de doble clic muestra «Puesto de la mañana» y «Puesto de la tarde» (preseleccionados con los actuales; al cambiar uno se fijan los dos, «Automático» suelta una mitad). Tabla nueva `puesto_fijo_mitad` (migración web 013, núcleo v9), excluyente con `puesto_fijo` de la misma celda; `asignar_tramos(..., fijos_mitad=)` lo impone por bloque; `cambio_turno.celdas` guarda el fijo como id o `[mañana, tarde]` (las filas viejas se leen igual) y anular compara y restaura por mitad. La permuta con C partida lleva las dos mitades. API: `CeldaIn.puesto_tarde` (solo en turnos corridos, 422 si no).
- **Interfaz del cuadro:** acciones del periodo en su propia fila (Generar primero, luego Reasignar, Publicar, Cerrar, Nuevo; Restaurar y Eliminar en rojo); confirmaciones con el verbo en el botón y una frase; ayuda en viñetas con «doble clic»; textos de diálogo, guardado y parámetros acortados.
- **Pulido de interfaz (04/11):** los pasos 1-2-3 del cuadro llevan botón (Generar, Ver alertas, Publicar); el foco de celda es un borde punteado distinto de la selección; con puntero táctil las celdas miden 44 px y la columna de nombres se angosta en móvil; el resultado de un cambio se anuncia (`role="status"`) y lista las alertas nuevas; leyenda con muestras reales y «Domingo o festivo»; Parámetros agrupado en Horas, Descansos, Corridos y Permutas/banco; tarifas con nombres legibles. Reglas tomadas de las skills de Appllama (toque ≥ 44 px, una etiqueta por intención) sin instalarlas: son para apps nativas y `npx skills` ejecuta código de terceros.

## Límites conocidos

- Sobrecobertura en el cuadro de turnos (no en puestos): `W_SOBRA` del solver es bajo frente al peso de las horas contratadas. Subirlo exige medir con datos reales.
- Partir corridos es un castigo (`W_PARTIR_P` = 150), no una obligación; quien queda en apoyo todo el día ve una sola fila.
- Fijar puesto por mitad con varias celdas seleccionadas aplica lo mismo a todas, sin mirar cada una.
- Sin verificar con lector de pantalla real ni en un teléfono físico; solo con el panel del navegador.
- `cambios.puesto_de` relee el reparto por cada celda; el cuadro ya no lo necesita para la lista de puestos, pero sigue usándolo para el principal.
- Reasignar con `desde`: los días anteriores se conservan, pero el historial de rotación se recalcula sobre el cuadro actual.

## Pendiente

- **Con la coordinación** (ver [HOJA_DE_RUTA](HOJA_DE_RUTA.md)): probar en el PC de la clínica, cargar personal real, confirmar los puntos `[confirmar]` de [REGLAS](REGLAS.md) y comparar horas contra una liquidación manual.
- **Fase 4:** aceptación con la base migrada y el PC de la clínica.
- **Fase 7b:** el libro del 19 al 25 de octubre igual al de Qt, celda a celda.
- **Fase 7c:** Radiología automática; plan sin escribir.
- **Fase 8:** quedó sin efecto en su parte de servidor (VPS, dominio, Postgres, cron en servidor). Sigue vigente el acuerdo de tratamiento de datos y la capacitación.
- Los documentos `docs/seguridad.md`, `docs/operacion.md` y `docs/seguridad-hallazgos.md` salieron con el modo servidor; se citan aún en PLAN_WEB y en los planes de las fases 2 y 8.
