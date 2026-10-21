# Reglas del servicio y marco legal

[← Volver al inicio](../README.md) · [Arquitectura](ARQUITECTURA.md) · [Hoja de ruta](HOJA_DE_RUTA.md)

Estado: v1. Todo lo marcado **[confirmar]** lo debe validar la coordinación, RR. HH. o jurídico.

## Del servicio

- Turnos: **M** y **T** de 6 h; **C** (corrido) de 12 h, cubre mañana y tarde; **NC** de 12 h de noche; **L** libre. Horarios iniciales M 06–12, T 12–18, C 06–18, NC 18–06 **[confirmar]**, editables en la app.
- Cobertura lunes a sábado: 4 M + 4 T + 2 NC. Domingo: 2 M + 2 T + 2 NC. Domingos y festivos solo medios turnos de día (M o T); el corrido no se usa. Un C cuenta para mañana y tarde.
- Mínimo **12 h** entre el fin de un turno y el inicio del siguiente.
- **Después de una noche, el día siguiente es libre** por defecto (configurable de 0 a 3 días). Como la noche termina a las 6:00, cualquier turno de día al día siguiente rompería además las 12 h de descanso; solo cabe otra noche. Quien coordina puede dejarlo sin libre editando la celda a mano: el generador respeta esa decisión y no la reclama como alerta.
- Al menos **1 día libre por semana** completa (configurable de 1 a 3). Los días de novedad y el libre posterior a la noche cuentan como libres.
- Al menos **1 fin de semana completo libre al mes** por persona (sábado y domingo; configurable de 0 a 4). El libre posterior a una noche del viernes cuenta como parte del fin de semana. Si una edición manual ya fijó esos días, no se exige.
- Tope de noches seguidas configurable (3 por defecto); con «libre tras noche» activo no puede haber noches consecutivas salvo edición manual **[confirmar]**.
- 13 personas en cuadro: 12 con rotación completa y 1 con restricciones (sin noches, solo M/T, siempre en el puesto 3). Hay 2 estudiantes con bloques de estudio y 1 estudiante de refuerzo (7–5 de lunes a jueves y 7–1 el viernes) que queda fuera del solver.
- Puestos del día: 1 lavado, 2 autoclave, 3 sterrad y esto, 4 cuarto estéril, 5 ropa (solo si sobra gente). La hoja original decía «siempre autoclave» para la restringida; se usa el 3 **[confirmar]**.
- Capacitación mensual, una vez por semana como máximo, preferiblemente el lunes (festivo → siguiente día hábil), con todos pudiendo asistir.
- Pausa de almuerzo: por turno, con minutos, hora y si es pagada. Por defecto no hay pausa definida **[definir]**.

## Marco legal (fuentes de divulgación, no texto oficial)

- Jornada máxima **42 h/semana** desde el 15-jul-2026 (art. 161 CST; Ley 2101/2021 y Ley 2466/2025).
- Trabajo nocturno de **7 p. m. a 6 a. m.** desde el 25-dic-2025 (art. 160), recargo **35 %**.
- Recargo dominical/festivo: 80 % hasta el 30-jun-2026, **90 %** desde el 1-jul-2026, **100 %** desde el 1-jul-2027. Se acumula con el nocturno.
- Horas extra: diurna +25 %, nocturna +75 %, acumulables con los demás recargos.
- El turno sucesivo del art. 161 (lit. d) limita a 6 h/día y 36/semana. Los turnos de 12 h dependen del **art. 165** (promedio en hasta 3 semanas) o del 166 (56 h/semana, con autorización). El concepto Mintrabajo 115750/2026 no da método de cálculo **[confirmar]**.
- Descanso dentro de la jornada (art. 167): no se computa salvo acuerdo expreso. Las fuentes no tratan turnos de 12 h **[confirmar]**.
- Trabajo en día de descanso: ocasional hasta 2 al mes, habitual desde 3 (afecta el compensatorio). La app reporta el conteo.
- Datos personales (Ley 1581 de 2012): la base `turnos.db` es local y no se versiona.

## Cómo se aplica en la app

- Horas contratadas del mes = horas semanales × (días ÷ 7) × % de jornada, descontando novedades.
- Ventana de N semanas (3 por defecto) contada desde el primer día del mes; no cruza meses. El exceso son horas extra tomadas de las últimas horas de la ventana.
- Tarifas y hora de inicio de la noche son filas con fecha de vigencia (Parámetros → Tarifas): un cambio de ley no requiere código.
