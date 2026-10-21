# Hoja de ruta

La dirección general, los principios y las preguntas abiertas están en la [visión](VISION.md).

[← Volver al inicio](../README.md) · [Visión](VISION.md) · [Reglas](REGLAS.md) · [Arquitectura](ARQUITECTURA.md)

Estado a oct-2026. v1 está construida; falta validarla con la coordinación y en el PC corporativo.

## Antes de seguir creciendo

1. Probar `PruebaPC.zip` en el PC corporativo (Qt + OR-Tools, sin permisos de administrador).
2. Cargar el personal real y generar un mes completo con novedades reales; revisar con la coordinadora.
3. Resolver los puntos **[confirmar]** de [REGLAS.md](REGLAS.md): horarios de turno, pausas, puesto de la restringida, tope de noches seguidas, régimen legal con jurídico.
4. Comparar los totales del reporte de horas con una liquidación manual.

## Siguientes etapas (candidatas)

| Etapa | Idea | Notas |
|---|---|---|
| Interfaz más ágil | Arrastrar y soltar turnos, asignar varios días a la vez, mostrar bloques de estudio en la grilla, deshacer | Ver [inspiración](ARQUITECTURA.md#interfaz-y-tecnología) |
| Importar el Excel actual | Cargar personal y ciclos desde `TURNOS ESTERILIZACION*.xlsx` | Evita digitar a mano la primera vez |
| Cambios y solicitudes | Permutas entre colaboradores con aprobación y registro (quién, cuándo, por qué) | Hoy solo hay edición manual |
| Pausas en cobertura | Que el solver reserve relevos de almuerzo por puesto | Hoy solo se asignan grupos de pausa |
| Refuerzo y practicantes | Modelar su horario fijo y que cubran ropa | Hoy quedan fuera del solver |
| Ventana entre meses | Que la ventana del art. 165 continúe de un mes al siguiente | Hoy se reinicia cada mes |
| Salario y costo | Ingresar salario para ver el costo de recargos en pesos | Opcional; el dato es sensible |
| Agendas y PDF | Calendario `.ics` por persona y versión imprimible | Existen en la app de Radiología |
| Otros servicios | Reutilizar el modelo para áreas con la misma estructura | Hoy el proyecto es solo Esterilización; requeriría servicios configurables |
| Servidor y accesos | Cada colaborador consulta su horario | Implica base compartida y autenticación; fuera de alcance por ahora |

## Convenciones del proyecto

- Interfaz y mensajes en español; no cambiar nombres de hojas ni etiquetas de los Excel sin avisar.
- Reglas, tarifas y turnos son datos editables; evitar constantes de negocio en el código.
- Cada cambio de comportamiento deja una prueba en `test_turnos.py`.
- Nunca subir `turnos.db` ni datos del personal.
