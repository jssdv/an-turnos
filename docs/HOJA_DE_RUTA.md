# Hoja de ruta

La dirección general, los principios y las preguntas abiertas están en la [visión](VISION.md).

[← Volver al inicio](../README.md) · [Visión](VISION.md) · [Reglas](REGLAS.md) · [Arquitectura](ARQUITECTURA.md)

Estado a oct-2026. v1 está construida; falta validarla con la coordinación. La app de escritorio se retiró el 26/10/2026 (etiqueta `qt-final`): la versión vigente es la web.

## Antes de seguir creciendo

1. Abrir la web en el navegador del PC de la clínica.
2. Cargar el personal real y generar un mes completo con novedades reales; revisar con la coordinadora.
3. Resolver los puntos **[confirmar]** de [REGLAS.md](REGLAS.md): horarios de turno, pausas, puesto de la restringida, tope de noches seguidas, régimen legal con jurídico.
4. Comparar los totales del reporte de horas con una liquidación manual.

## Siguientes etapas (candidatas)

| Etapa | Idea | Notas |
|---|---|---|
| Excel del banco | Exportar saldos y movimientos para RR. HH. | Hoy se ve en pantalla |
| Interfaz más ágil | Aviso anticipado de subcobertura, rehacer (Ctrl+Y), mover un turno a una celda libre sin intercambiar, vista por semana | Arrastrar, lote, deshacer y estudio ya están; ver [inspiración](ARQUITECTURA.md#interfaz-y-tecnología) |
| Importar el Excel actual | Cargar personal y ciclos desde `TURNOS ESTERILIZACION*.xlsx` | Evita digitar a mano la primera vez |
| Solicitudes | Que la coordinación registre «quiero este turno» y el solver lo tome como deseo | Los cambios y permutas ya se registran; falta esta pieza |
| Pausas en cobertura | Que el solver reserve relevos de almuerzo por puesto | Hoy solo se asignan grupos de pausa |
| Refuerzo y practicantes | Modelar su horario fijo y que cubran ropa | Hoy quedan fuera del solver |
| Ventana entre periodos | Que la ventana del art. 165 continúe de un periodo al siguiente | Hoy se reinicia en cada periodo |
| Día de inicio por servicio | Esquemas que arranquen en otro día distinto del lunes | Hoy: mes calendario o semanas desde un lunes |
| Salario y costo | Ingresar salario para ver el costo de recargos en pesos | Opcional; el dato es sensible |
| Agendas y PDF | Calendario `.ics` por persona y versión imprimible | Existen en la app de Radiología |
| Otros servicios | Reutilizar el modelo para áreas con la misma estructura | Ya hay dos áreas (Radiología, Esterilización) sobre un núcleo común; falta que un área nueva sea configurable sin código |
| Servidor y accesos | Cada colaborador consulta su horario | Implica base compartida y autenticación; fuera de alcance por ahora |

## Hecho recientemente

Cambios de turno registrados: permutas con límite por persona y periodo, cambios por necesidad del servicio y ajustes, con auditoría y anulación (diseño: [spec](superpowers/specs/2026-10-25-cambios-turno-design.md), plan: [plan](superpowers/plans/2026-10-25-cambios-turno.md)).

Puestos editables con demanda por tramos, cobertura derivada, reparto por tramo con puestos permitidos y calculadora de dotación (diseño: [spec](superpowers/specs/2026-10-21-puestos-dotacion-design.md), plan: [plan](superpowers/plans/2026-10-21-puestos-dotacion.md)).

## Siguientes (en orden de valor)

1. **Probar la web en el navegador del PC de la clínica.**
2. **Copia de seguridad y restauración** de `turnos.db`.
3. **Registro de cambios** (quién, cuándo y por qué) en ediciones y cierres.
4. **Excel del banco de horas** para RR. HH.
5. **Sugerir turnos** para ventanas que ningún turno del catálogo cubre.
6. Solicitudes y permutas con aprobación; importar el Excel actual.

## Convenciones del proyecto

- Interfaz y mensajes en español; no cambiar nombres de hojas ni etiquetas de los Excel sin avisar.
- Reglas, tarifas y turnos son datos editables; evitar constantes de negocio en el código.
- Cada cambio de comportamiento deja una prueba en `test_turnos.py`.
- Nunca subir `turnos.db` ni datos del personal.
