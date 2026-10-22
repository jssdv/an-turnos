# Programación de turnos de Radiología — Proyecto por etapas

> Documento vivo. Estado: **borrador de diseño** (19/10/2026). Cada etapa tendrá su propio diseño detallado antes de programarla; aquí se fija el rumbo, el alcance de cada etapa y las preguntas que hay que responder antes de empezarla.

## 1. Visión

Hoy el cuadro mensual de turnos se arma a mano en Excel y de ahí sale, también a mano, la planilla semanal. La meta es llegar a una herramienta en la línea de QGenda o Lightning Bolt, adaptada a las reglas de esta clínica y que funcione en el PC corporativo sin permisos de administrador. Con ella se debe poder:

1. registrar una sola vez los datos maestros: médicos, competencias, jornadas, turnos y reglas;
2. armar el cuadro mensual dentro de la app, validándolo mientras se escribe;
3. recibir una **propuesta automática** del mes, justa y que cumpla las reglas, que la coordinación ajusta;
4. publicar la planilla semanal, las agendas y los avisos de cambios (esto ya existe);
5. más adelante, si el hospital lo decide, crecer a varios servicios con un servidor y acceso para cada médico.

## 2. Dónde estamos (Etapa 0 — terminada)

| Pieza | Archivo | Qué hace |
|---|---|---|
| Núcleo | `app/generar_semana.py` | Lee la hoja `Cambios …` del cuadro mensual, interpreta los códigos y arma la planilla semanal con el formato de `plantilla_semana.xlsx`. |
| Análisis | `app/analisis.py` | Reglas de descanso, revisión del cuadro (cruces, nombres, códigos), equidad del mes y de varios meses, agendas `.ics` y texto, comparación entre versiones, versión imprimible. |
| App | `app/app.py` | Ventana PySide6 con panel de resumen (indicadores y cobertura de la semana), vista previa con los colores del Excel, alertas, equidad, agendas y cambios. Recarga sola al guardar el Excel; arrastrar y soltar; atajos de teclado. Guarda `SEMANA … .xlsx` sin sobrescribir. |
| Distribución | `empaquetar.sh` | Carpeta portátil para Windows (Python embeddable + librerías), sin instalar nada. En Mac: `Planilla Semanal.command`. |

**Limitaciones que condicionan lo que sigue:**
- Las reglas del negocio están **escritas dentro del código**: `CODIGOS`, `FILAS_ECO`, `SLOTS` e `IGNORAR`. Para editar el cuadro o extender la herramienta a otros servicios, deben pasar a ser **datos**.
- El cuadro mensual debe tener fechas completas en la fila 3 y haber sido guardado desde Excel, porque se leen los valores ya calculados.
- No se ha probado aún en el PC corporativo (`dist/PruebaPC.zip`). **Es un bloqueo para todo lo demás.**

## 3. Principios de diseño

1. **Excel sigue siendo el formato de intercambio** mientras dure la transición. La app importa el cuadro actual y exporta exactamente al mismo formato (hoja `Cambios …`), para que nadie dependa de la app desde el primer día.
2. **Núcleo sin interfaz.** Las reglas, el modelo y el motor de propuestas viven en módulos de Python puros. La interfaz (hoy Qt, mañana quizá web) solo los llama. Así, pasar a un servidor no obliga a reescribir la lógica.
3. **Datos antes que código.** Agregar un turno, un servicio o una regla debe hacerse desde la app o editando datos, no programando.
4. **Portátil y sin permisos.** Todo debe correr en la carpeta portátil; solo se agregan dependencias que existan como librerías ya compiladas para Windows.
5. **La persona decide.** El motor propone y quien coordina aprueba. Cada cambio queda registrado con quién, cuándo y por qué.
6. **Etapas pequeñas que sirven solas.** Cada etapa termina en algo que se usa en la práctica, aunque no se hagan las siguientes.

## 4. Arquitectura objetivo

```
┌────────────── Interfaz ──────────────┐   Qt (portátil) ── más adelante: web
│ editor del cuadro · planilla semanal │
│ alertas · equidad · agendas · config │
└───────────────┬──────────────────────┘
                │ llama
┌───────────────▼──────────────────────┐
│ Dominio (Python puro)                │
│  modelo: médicos, turnos, servicios, │
│          asignaciones, ausencias     │
│  reglas: validaciones (ya existen)   │
│  motor:  propuesta automática (E3)   │
└───────┬──────────────────┬───────────┘
        │                  │
┌───────▼───────┐  ┌───────▼──────────────┐
│ Persistencia  │  │ Adaptadores Excel    │
│ SQLite local  │  │ importar cuadro      │
│ (luego: BD de │  │ exportar `Cambios …` │
│  servidor)    │  │ planilla semanal     │
└───────────────┘  └──────────────────────┘
```

- **Persistencia propuesta:** un archivo **SQLite**. Viene con Python (`_sqlite3.pyd` ya está en el paquete), es un único archivo fácil de respaldar y permite migrar más adelante a una base de datos de servidor (PostgreSQL) sin cambiar el modelo.
- **Motor de propuestas:** **OR-Tools CP-SAT** de Google (licencia Apache 2.0). Tiene librería compilada para Windows, así que entra en la carpeta portátil.

## 5. Etapas

### Etapa 1 — Datos maestros y modelo
**Objetivo:** que todo lo que hoy está repartido entre el Excel, el código y la cabeza de quien coordina quede registrado como datos.

- **Médicos:** nombre completo, categoría (I a IV), especialidades (ESP1/ESP2), servicios y ecógrafos que puede cubrir, jornada semanal y si está activo.
- **Catálogo de turnos:** reemplaza `CODIGOS` y la hoja `Nom-Hrs`. Para cada código: nombre, servicio, tramos horarios, si es remoto, horas que cuenta, si se publica, y si es combinable con `/`.
- **Servicios y franjas:** reemplaza `SLOTS` y `FILAS_ECO`. Para cada servicio, sus franjas estándar por tipo de día (hábil, fin de semana, festivo), la cobertura mínima y la fila que le toca en la planilla semanal.
- **Ausencias:** vacaciones, incapacidades, licencias y día de la familia, con fechas.
- **Festivos de Colombia:** una tabla anual que se puede revisar.
- **Importador:** carga todo lo anterior desde el cuadro actual y las hojas `Horarios` y `Nom-Hrs`.
- **Pantalla de configuración** en la app.
- **Entregable:** `generar_semana.py` deja de tener constantes de negocio y lee el catálogo. La planilla semanal sigue saliendo idéntica, y la comparación con la semana del 12 al 18 de octubre no muestra diferencias nuevas.
- **Fuera de alcance:** editar el cuadro mensual (eso es la Etapa 2).

### Etapa 2 — Editor del cuadro mensual
**Objetivo:** armar y corregir el mes dentro de la app en vez de hacerlo en Excel.

- Grilla de médicos por días, parecida a la hoja actual, con agrupación por especialidad y filas de disponibilidad.
- Se escribe el código o se elige de una lista filtrada por lo que ese médico puede cubrir. Se puede copiar y pegar, rellenar, y deshacer o rehacer.
- **Validación en vivo** con las reglas que ya existen: cruces, descanso (TURG, NURG/LP, 36 horas, tarde larga), horas contra jornada, cobertura mínima por franja y ausencias. Se ve como colores en la grilla y en un panel lateral.
- Totales por médico (horas, noches, domingos, festivos) y por día (cobertura), siempre visibles.
- **Versiones del mes:** "Plan" (lo que hoy es la hoja `Octubre 2026`) y "Vigente" (lo que hoy es `Cambios Octubre 2026`), con historial de cambios.
- **Exportar** al Excel con el formato actual. **Importar** un cuadro hecho en Excel.
- **Entregable:** el mes de noviembre armado de punta a punta en la app y exportado a Excel; la planilla semanal sale de los datos sin pasar por Excel.

### Etapa 3 — Propuesta automática del mes
**Objetivo:** que la app proponga un mes completo que cumpla las reglas y reparta la carga por igual.

- **Reglas obligatorias:**
  - cobertura mínima de cada franja;
  - urgencias 24/7 con la rotación TURG → NURG → LP;
  - competencias de cada médico;
  - ausencias;
  - reglas de descanso;
  - horas máximas.
- **Lo que se optimiza:**
  - reparto equitativo de noches, fines de semana, festivos y disponibilidades (incluye lo acumulado de meses anteriores, aprovechando la equidad de varios meses);
  - cercanía a la jornada de cada uno;
  - preferencias.
- **Uso:**
  - se pueden fijar celdas antes de generar y el motor completa el resto;
  - se puede regenerar solo una semana o un servicio;
  - si no hay solución, la app explica qué regla lo impide (por ejemplo, "faltan 2 médicos de MSK el 24/12").
- **Entregable:** comparar una propuesta para un mes real con el mes hecho a mano: cuántas reglas cumple, qué tan pareja queda la equidad y cuánto se tarda.

### Etapa 4 — Solicitudes, preferencias y auditoría (sin servidor)
**Objetivo:** registrar en la app lo que hoy llega por WhatsApp o correo.

- Solicitudes de vacaciones, días libres, preferencias ("no noches los martes") y permutas entre dos médicos. Las carga quien coordina y quedan con estado: pendiente, aprobada o rechazada.
- Las aprobadas pasan solas a ausencias o restricciones del motor.
- Historial de cambios del cuadro: quién, cuándo, qué y por qué. Los avisos de cambios (ya existen) se generan desde ese historial.
- Indicadores del mes: cobertura cumplida, cambios después de publicar y equidad.

### Etapa 5 — Servidor y acceso para los médicos (requiere TI)
**Objetivo:** que cada radiólogo vea su agenda y haga solicitudes por su cuenta.

- La misma lógica de las etapas 1 a 4, publicada como aplicación web interna (con FastAPI u otra opción similar). Base de datos PostgreSQL; se entra con la cuenta corporativa si TI lo permite.
- Vista para el celular: mi agenda, solicitar, aceptar una permuta, y suscripción al calendario `.ics` que se actualiza sola.
- La app de escritorio puede seguir como herramienta de coordinación, o reemplazarse por la versión web.
- **Requisitos previos:** que TI provea un servidor o alojamiento, cumplimiento de la política de datos personales (Ley 1581 de 2012 en Colombia), respaldos y soporte.

### Etapa 6 — Hospital completo (visión)
**Objetivo:** que el mismo sistema sirva a otros servicios (urgencias, UCI, enfermería, otras especialidades).

- El modelo de la Etapa 1 se generaliza a **Hospital, Departamento, Servicio, Franja y Turno**, con reglas configurables por departamento y roles (administración general, coordinación por departamento y profesional).
- Reportes institucionales (horas, costos y cobertura) e integraciones con talento humano o nómina.
- **Condición:** que las etapas 1 a 3 funcionen bien en Radiología. Es el piloto que justifica crecer.

## 6. Cronograma orientativo

| Etapa | Depende de | Tamaño relativo | Valor |
|---|---|---|---|
| Prueba en el PC corporativo | — | muy pequeño | desbloquea todo |
| 1. Datos maestros | Prueba en PC | mediano | base de todo lo demás |
| 2. Editor del cuadro | 1 | grande | deja de usarse Excel para armar el mes |
| 3. Propuesta automática | 1 y 2 | grande | el salto tipo QGenda |
| 4. Solicitudes y auditoría | 2 | mediano | orden y trazabilidad |
| 5. Servidor | 1 a 4 y TI | grande | acceso de los médicos |
| 6. Hospital | 5 y decisión institucional | muy grande | escala |

## 7. Riesgos

| Riesgo | Cómo se mitiga |
|---|---|
| TI bloquea `pythonw.exe` en carpetas del usuario (AppLocker) | Probar `PruebaPC.zip` antes de seguir. Si falla, pedir una excepción a TI o pasar antes a la Etapa 5. |
| Reglas implícitas que nadie ha escrito | Sesiones con quien coordina antes de la Etapa 3. Partir de un cuadro real y explicar por qué cada turno está donde está. |
| La propuesta automática no convence | Fijar celdas, regenerar por partes y explicar por qué no hay solución. La persona siempre decide. |
| Dos personas editan el mismo archivo SQLite a la vez | En las etapas 1 a 4, un solo editor (bloqueo de archivo y aviso). Varios editores llegan con la Etapa 5. |
| Datos personales de médicos (nombres, ausencias, incapacidades) | Guardarlos solo en el equipo o servidor de la institución, sin servicios externos. Revisar la política de datos personales antes de la Etapa 5. |
| Dejar de exportar a Excel demasiado pronto | Exportar al formato actual al menos hasta la Etapa 4. |

## 8. Decisiones ya tomadas

- Interfaz en Qt (PySide6), distribuida como carpeta portátil sin `.exe` (Python embeddable). En Mac se usa `Planilla Semanal.command`.
- La fila 3 del cuadro mensual lleva fechas completas; las semanas se ubican por fecha exacta.
- En la planilla semanal:
  - contingencia, vacaciones, asignación de estudios y notas libres se llenan a mano;
  - nombres completos;
  - densitometría incluye el domingo;
  - `Z` y hemodinamia no se publican.
- La app siempre usa modo claro.
- Al guardar nunca se sobrescribe: se crean versiones `v2`, `v3`… y los cambios quedan marcados en amarillo.

## 9. Preguntas abiertas (responder antes de la Etapa 1)

1. ¿Quién arma hoy el cuadro mensual y cuántas personas lo editan? ¿Una sola, o varias por especialidad?
2. ¿Qué reglas usa quien coordina que **no** están en el Excel? Por ejemplo: mínimos por franja, quién no puede hacer noches, rotaciones fijas o preferencias.
3. ¿Qué tan estables son los códigos de `Nom-Hrs`? Hay combinaciones (`M3/TN`, `MTA2/TC`…) que podrían calcularse en vez de listarse una por una.
4. ¿Cómo se paga y cuenta lo que hoy está en las columnas `PAGO$`, `SALDO H` y `PTE ANT.`? ¿Debe calcularlo la app?
5. ¿El cuadro de Angio (hemodinamia) entra al sistema o sigue aparte?
6. ¿Dónde se guardarían los datos? ¿En el PC de quien coordina, o en una carpeta compartida de la red con respaldo?
7. ¿Existe alguna conversación con TI sobre alojar una aplicación interna? Esto define cuándo es viable la Etapa 5.

## 10. Plan de trabajo paso a paso

Marca `[x]` al terminar cada paso. Cada etapa empieza con su diseño (`docs/etapa-N-….md`) y termina con su verificación. No se pasa a la siguiente etapa sin cerrar la anterior.

### Etapa 0 — Base actual
- [x] 0.1 Generador de la planilla semanal desde el cuadro mensual (`generar_semana.py`)
- [x] 0.2 Fechas completas en la fila 3; las semanas se ubican por fecha exacta
- [x] 0.3 App de escritorio: vista previa, alertas, equidad, agendas y cambios (`app.py`)
- [x] 0.4 Revisión del cuadro, equidad de varios meses y versión para imprimir
- [x] 0.5 Paquete portátil para Windows (`empaquetar.sh`) y lanzador para Mac
- [x] 0.5b Interfaz renovada, carpeta ordenada (`app/`, `tests/`, `ejemplos/`) y recarga automática
- [ ] 0.6 Probar `dist/PruebaPC.zip` en el PC corporativo (abrir la ventana y el diálogo de archivos) — **bloqueante**
- [ ] 0.7 Probar `dist/PlanillaSemanal.zip` en el PC corporativo con un cuadro real
- [ ] 0.8 Poner fechas completas en la fila 3 del cuadro mensual real y adoptarlo como plantilla para los meses siguientes
- [ ] 0.9 Usar la app en paralelo al proceso manual durante 2 a 4 semanas y anotar las diferencias

### Etapa 1 — Datos maestros y modelo
- [ ] 1.1 Responder las preguntas abiertas de la sección 9
- [ ] 1.2 Diseño detallado: modelo, esquema SQLite e importador (`docs/etapa-1-datos-maestros.md`)
- [ ] 1.3 Módulo de dominio y persistencia: médicos, turnos, servicios, franjas, ausencias y festivos
- [ ] 1.4 Importador desde el cuadro actual (`Cambios …`, `Horarios` y `Nom-Hrs`)
- [ ] 1.5 Pasar `CODIGOS`, `SLOTS`, `FILAS_ECO` e `IGNORAR` a datos; el generador lee el catálogo
- [ ] 1.6 Tabla de festivos de Colombia y aviso cuando no coincidan con la marca `LF` del cuadro
- [ ] 1.7 Pantalla de configuración: médicos, turnos, servicios y ausencias
- [ ] 1.8 Verificar: la planilla del 12 al 18 de octubre sale igual que antes; pruebas en verde
- [ ] 1.9 Validar los datos cargados con quien coordina

### Etapa 2 — Editor del cuadro mensual
- [ ] 2.1 Diseño detallado y bocetos del editor (`docs/etapa-2-editor.md`)
- [ ] 2.2 Grilla de médicos por días con agrupación por especialidad y filas de disponibilidad
- [ ] 2.3 Edición: escribir o elegir el código (filtrado por competencias), copiar y pegar, rellenar, deshacer y rehacer
- [ ] 2.4 Validación en vivo en la grilla y en un panel lateral (reglas ya existentes y cobertura mínima)
- [ ] 2.5 Totales por médico y cobertura por día, siempre visibles
- [ ] 2.6 Versiones del mes "Plan" y "Vigente", con historial de cambios
- [ ] 2.7 Importar un cuadro hecho en Excel y exportar al formato `Cambios …` actual
- [ ] 2.8 Planilla semanal generada directamente desde los datos, sin pasar por Excel
- [ ] 2.9 Piloto: armar un mes completo en la app y compararlo con el Excel

### Etapa 3 — Propuesta automática
- [ ] 3.1 Sesiones con quien coordina para escribir todas las reglas, incluidas las implícitas
- [ ] 3.2 Diseño detallado del modelo de optimización (`docs/etapa-3-motor.md`)
- [ ] 3.3 Agregar OR-Tools al paquete portátil y comprobar que corre en el PC corporativo
- [ ] 3.4 Reglas obligatorias: cobertura, rotación de urgencias TURG → NURG → LP, competencias, ausencias, descanso y horas máximas
- [ ] 3.5 Objetivo de equidad: noches, fines de semana, festivos y disponibilidades (con lo acumulado de meses anteriores) y cercanía a la jornada
- [ ] 3.6 Fijar celdas, regenerar por semana o por servicio, y explicar por qué no hay solución cuando no la hay
- [ ] 3.7 Comparar con un mes real hecho a mano: reglas cumplidas, equidad y tiempo invertido
- [ ] 3.8 Piloto: un mes armado desde la propuesta y ajustado a mano

### Etapa 4 — Solicitudes, preferencias y auditoría
- [ ] 4.1 Diseño detallado (`docs/etapa-4-solicitudes.md`)
- [ ] 4.2 Registro de solicitudes (vacaciones, días libres, preferencias y permutas) con estados
- [ ] 4.3 Las solicitudes aprobadas pasan solas a ausencias o restricciones del motor
- [ ] 4.4 Historial de auditoría (quién, cuándo, qué y por qué) y avisos de cambios generados desde él
- [ ] 4.5 Indicadores del mes: cobertura, cambios después de publicar y equidad
- [ ] 4.6 Revisar el uso real con quien coordina y decidir si seguir a la Etapa 5

### Etapa 5 — Servidor y acceso para los médicos
- [ ] 5.1 Reunión con TI: alojamiento, base de datos, inicio de sesión corporativo, respaldos y soporte
- [ ] 5.2 Revisión de datos personales (Ley 1581 de 2012) y aprobación institucional
- [ ] 5.3 Diseño detallado (`docs/etapa-5-servidor.md`)
- [ ] 5.4 Migrar de SQLite a PostgreSQL y exponer el núcleo como servicio web
- [ ] 5.5 Vista web de coordinación (equivalente a la app de escritorio)
- [ ] 5.6 Vista para el celular de cada médico: agenda, solicitudes, permutas y calendario `.ics` suscrito
- [ ] 5.7 Piloto con un grupo de radiólogos y luego con todo el servicio

### Etapa 6 — Hospital completo
- [ ] 6.1 Presentar los resultados del piloto de Radiología (horas ahorradas, cumplimiento de reglas, equidad)
- [ ] 6.2 Generalizar el modelo a Hospital, Departamento, Servicio, Franja y Turno, con roles
- [ ] 6.3 Reglas configurables por departamento
- [ ] 6.4 Incorporar un segundo servicio como piloto
- [ ] 6.5 Reportes institucionales e integración con talento humano y nómina
- [ ] 6.6 Despliegue gradual al resto del hospital
