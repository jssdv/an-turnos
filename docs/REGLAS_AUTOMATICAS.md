# Reglas automáticas

Lo que el repo comprueba solo, sin depender de que alguien lo recuerde. Origen: [PLAN_WEB.md](PLAN_WEB.md) §5 y §8. Cada herramienta usa solo la biblioteca estándar y sale con código ≠ 0 si la regla falla.

| Regla | Qué comprueba | Herramienta | Estado |
|---|---|---|---|
| Tokens de diseño | `web/src/tokens.css` y `tema.C` coinciden con las variables «Color» de `An_UI.figcraft` | `checks/tokens.py --verificar` | Fase 0 (ver nota) |
| Aislamiento por clínica | Toda tabla con `clinica_id` tiene RLS activado y forzado | `checks/rls.py` | Pendiente (Fase 1) |
| Reglas de API | Toda ruta declara permiso de área; sin SQL con f-strings; `subprocess` solo en el trabajador | `checks/reglas.py` | Pendiente (Fase 1) |
| Diseño | Sin colores literales fuera de `tokens.css`; texto no menor al mínimo de «Tipo»; pares de tokens con contraste 4,5:1 | `checks/diseno.py` | Pendiente (Fase 4) |
| Núcleo | Los tests de `tests/` pasan (pytest y scripts de Qt) | `.github/workflows/ci.yml` | Fase 0 |

Nota: los tokens de turno (`turno_M`, `turno_T`, `turno_NC`, `turno_C`) y nueve tokens de estado de `tema.C` no están en ambos lados todavía; ver el avance de la Fase 0.
