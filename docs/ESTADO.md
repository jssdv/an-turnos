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
- **Reasignar puestos:** cada ejecución usa una semilla distinta (`semilla` en `asignar_tramos` y `flujo.recalcular`), así que explora otro reparto igual de bueno. Generar sigue reproducible (semilla 0).
- **Partir corridos:** funciona con `partir_corridos=1` (turnos de 10 h o más, que no son de noche): un puesto en la mañana y otro en la tarde. Las áreas nuevas nacen con 1; las existentes se cambian en Parámetros.

## Límites conocidos

- Sobrecobertura en el cuadro de turnos (no en puestos): `W_SOBRA` del solver es bajo frente al peso de las horas contratadas. Subirlo exige medir con datos reales.
- Partir corridos es un castigo (`W_PARTIR_P` = 150), no una obligación; quien queda en apoyo todo el día ve una sola fila.
- Reasignar con `desde`: los días anteriores se conservan, pero el historial de rotación se recalcula sobre el cuadro actual.

## Pendiente

- **Con la coordinación** (ver [HOJA_DE_RUTA](HOJA_DE_RUTA.md)): probar en el PC de la clínica, cargar personal real, confirmar los puntos `[confirmar]` de [REGLAS](REGLAS.md) y comparar horas contra una liquidación manual.
- **Fase 4:** aceptación con la base migrada y el PC de la clínica.
- **Fase 7b:** el libro del 19 al 25 de octubre igual al de Qt, celda a celda.
- **Fase 7c:** Radiología automática; plan sin escribir.
- **Fase 8:** quedó sin efecto en su parte de servidor (VPS, dominio, Postgres, cron en servidor). Sigue vigente el acuerdo de tratamiento de datos y la capacitación.
- Los documentos `docs/seguridad.md`, `docs/operacion.md` y `docs/seguridad-hallazgos.md` salieron con el modo servidor; se citan aún en PLAN_WEB y en los planes de las fases 2 y 8.
