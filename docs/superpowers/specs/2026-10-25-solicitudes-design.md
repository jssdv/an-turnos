# Solicitudes personales — diseño

[← Volver al inicio](../../../README.md) · [Visión](../../VISION.md) · [Arquitectura](../../ARQUITECTURA.md) · [Cambios de turno](2026-10-25-cambios-turno-design.md)

Estado: **implementado** (25/10/2026), según el [plan](../plans/2026-10-25-solicitudes.md). Pieza **S** de cuatro (C hecha, D dashboard en paralelo, V varios servicios fuera de este ciclo).

## 1. Qué se quiere lograr

Una persona pide un turno concreto («quiero el 14 libre», «prefiero tarde esa semana», «no puedo noche el 20»). La coordinación (no hay login de colaboradores) lo registra en la app y el generador intenta cumplirlo.

**Criterios de éxito**
- La coordinación registra y borra solicitudes en una pestaña propia.
- El solver las trata como **deseo blando**: cede ante cobertura, puestos y reglas legales (art. 165, descansos).
- Al generar, la app informa cuáles no se cumplieron y por qué; la pestaña muestra siempre el estado frente al cuadro vigente.

**Fuera de alcance:** roles o login de colaboradores, editar una solicitud (se borra y se crea), cola de aprobación, varios servicios (V), dashboard (D).

## 2. Decisiones tomadas

| Tema | Decisión |
|---|---|
| Quién registra | Solo la coordinación, en la app |
| Tipos | `libre`, `quiero` (turno concreto), `evitar` (turno concreto) |
| Prioridad | `normal` o `alta`; ambas ceden ante cobertura y reglas legales |
| Interfaz | Pestaña nueva «Solicitudes» |
| Servicio | Columna `servicio` fija `esterilizacion` (no bloquea V) |

## 3. Datos

Migración **v7** (también en `ESQUEMA` para bases nuevas):

```sql
CREATE TABLE solicitud (
  id INTEGER PRIMARY KEY, servicio TEXT DEFAULT 'esterilizacion', colab_id INT,
  tipo TEXT,        -- 'libre' | 'quiero' | 'evitar'
  desde TEXT, hasta TEXT,
  turno TEXT,       -- código de turno; vacío en 'libre'
  prioridad TEXT,   -- 'normal' | 'alta'
  nota TEXT, registrado_en TEXT, usuario TEXT);
```

`dominio.Solicitud` es un dataclass (como `Novedad`); `Contexto.solicitudes` (lista, vacía por defecto) se llena en `db.contexto`. `BD.guardar_solicitud / borrar_solicitud / solicitudes`. Borrar una persona con solicitudes la desactiva, igual que con novedades.

## 4. Solver

Sin restricciones duras nuevas. Para cada solicitud, cada día de su rango dentro de `fechas` y cada persona en el solver, se suma una penalidad al objetivo sobre las variables existentes `x[p, d, s]`:

- `libre`: penaliza cualquier turno de trabajo ese día.
- `quiero T`: penaliza cualquier turno de trabajo distinto de `T`. Estar libre no se penaliza (se pide «si trabajo, que sea T»).
- `evitar T`: penaliza `T`.

Pesos: `W_SOL = {normal: 400, alta: 4000}` por día. Quedan por debajo de `W_FALTA` (10 000 por persona y tramo de 30 min), así que la cobertura manda; las reglas de descanso, libres semanales, fines de semana y noches son restricciones duras, así que la solicitud siempre cede. Las celdas `fijo` (ediciones manuales) mandan sobre la solicitud. Un turno que no existe o no está disponible para la persona simplemente no tiene variable y no suma.

## 5. Informe: `an/esterilizacion/solicitudes.py` (puro)

`evaluar(ctx, cuadro, fechas, fijos=())` → lista de `Resultado(solicitud, estado, motivo, dias_fallidos)`.

- Por día: cumplida según el tipo (arriba, con el turno de `cuadro`, «L» si falta la celda). Solo cuentan días dentro de `fechas`; sin ningún día en el periodo → estado `fuera`.
- `estado`: `cumplida`, `parcial` (algunos días) o `no cumplida`.
- `motivo` (heurístico, del primer día fallido): `tiene novedad`, `turno no permitido`, `libre obligatorio tras noche` (la noche anterior), `edición manual` (celda en `fijos`) y, si nada de eso, `cobertura o reglas`.

No se guarda estado: se recalcula desde el cuadro vigente, así es válido tras ediciones manuales.

## 6. Interfaz

Pestaña «Solicitudes» (después de «Novedades»): tabla Colaborador · Tipo · Turno · Desde · Hasta · Prioridad · Estado · Nota, y formulario «Nueva solicitud» (el turno solo se habilita en `quiero`/`evitar`). Estado y motivo salen de `evaluar` para el periodo mostrado. Tras generar, el toast agrega «N solicitudes no cumplidas: …» (hasta 3 con motivo) o, si todas se cumplieron, no dice nada extra. Estilos solo en `ESTILO`; textos en español.

## 7. Pruebas

- `tests/esterilizacion/test_solicitudes.py` (imprime `OK`): migración v7 y CRUD; `evaluar` por tipo y motivo; solver: un `libre` y un `evitar` se cumplen en un escenario holgado; una `libre` imposible (la única persona que cubre) cede y se informa; alta gana a normal en conflicto.
- GUI: añadir al test de GUI la pestaña (crear, ver estado, borrar).
- Las existentes siguen en verde.
