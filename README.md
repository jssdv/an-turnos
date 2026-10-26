<div align="center">

# An~

**Una app web para programar turnos y los procesos que giran alrededor**<br>
Un núcleo común y un área por servicio: **Radiología** (cuadro mensual → planilla semanal) y **Esterilización** (cuadro de turnos con solver, puestos, horas y recargos).

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![React](https://img.shields.io/badge/Interfaz-React%2019-61DAFB?logo=react&logoColor=black)
![FastAPI](https://img.shields.io/badge/API-FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/Datos-PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![OR-Tools](https://img.shields.io/badge/Solver-OR--Tools%20CP--SAT-4285F4?logo=google&logoColor=white)

[Radiología](docs/RADIOLOGIA.md) · [Visión](docs/VISION.md) · [Reglas](docs/REGLAS.md) · [Arquitectura](docs/ARQUITECTURA.md) · [Plan web](docs/PLAN_WEB.md) · [Operación](docs/operacion.md)

<br>

<img src="docs/diseno/web_rediseno_cuadro.png" alt="Cuadro mensual de Esterilización" width="900">

<sub>Cuadro de octubre de 2026 de Esterilización con datos de ejemplo.</sub>

</div>

---

## Áreas

Cada clínica tiene sus áreas; cada usuario ve las áreas en las que tiene permiso (editar o solo consultar).

| Área | Qué hace | Datos | Documentación |
|---|---|---|---|
| **Radiología** | Lee el cuadro mensual de radiólogos (Excel, hoja `Cambios …`) y genera el libro semanal `SEMANA dd AL dd DE MES.xlsx`: resumen, vista previa, alertas de descanso, equidad, agendas `.ics` y comparación entre versiones. También por línea de comandos. | Los Excel del coordinador | [RADIOLOGIA.md](docs/RADIOLOGIA.md), [PROYECTO.md](docs/PROYECTO.md) |
| **Esterilización** | Genera el cuadro mensual con OR-Tools, reparte puestos por tramo, calcula horas (art. 165 CST) y recargos, lleva banco de horas y exporta a Excel. | PostgreSQL | [Reglas](docs/REGLAS.md), [Arquitectura](docs/ARQUITECTURA.md) |

Pensada para coordinadoras no técnicas: solo hace falta un navegador.

## Hacia dónde va

Reglas y turnos son *datos* editables, no código; así se suman servicios sin reprogramar. Siguen más áreas, procesos administrativos vinculados (novedades, permutas, cierre para nómina) y más usuarios con roles y trazabilidad. Plan y preguntas abiertas: [VISION.md](docs/VISION.md), [HOJA_DE_RUTA.md](docs/HOJA_DE_RUTA.md).

## Esterilización: qué hace

| | |
|---|---|
| 🧮 **Cuadro con solver** | OR-Tools genera el esquema completo (un mes, o N semanas desde un lunes): la cobertura que piden los puestos, tramo a tramo, 12 h de descanso, día libre después de cada noche, al menos un día libre por semana y un fin de semana completo libre por esquema. |
| ⚖️ **Rotación y equidad** | Reparte parejo M, T, C y NC y los domingos/festivos, limita rachas de noches y de corridos, prefiere los libres en fin de semana y arrastra lo acumulado de meses anteriores. |
| ✋ **Edición ágil** | Arrastra celdas para intercambiarlas, asigna turnos a varias celdas con clic derecho y deshaz con Ctrl+Z. Los días de estudio se ven en la grilla. |
| 🗂️ **Original y cambios** | Dos versiones por mes. Lo que se edita queda en amarillo, con lista de diferencias, y se puede publicar o restaurar. |
| 👥 **Personal y novedades** | Crear, editar y eliminar colaboradores con casillas para turnos permitidos y bloques de estudio; vacaciones, incapacidades, licencias y días libres. |
| 🕘 **Turnos editables** | Crea, edita y elimina turnos: horarios, franjas que cubren, color y pausa de almuerzo (pagada o no). Todo se recalcula. |
| 🧩 **Puestos con demanda** | Crea y edita puestos con reglas de demanda: personas requeridas, horario por tramos de 30 min (también a mitad de franja o de noche), obligatorio o deseable. La cobertura sale de ahí. |
| 📍 **Reparto por puesto** | Quién ocupa cada puesto en cada tramo, respetando los puestos permitidos de cada persona, con rotación y grupos de relevo. |
| 👥 **Dotación** | Calcula cuántas personas piden los puestos: estimación por horas y verificación con el generador del mínimo que cumple todas las reglas. |
| 🎓 **Capacitación** | Una sesión por semana como máximo, el lunes o el siguiente día hábil, para que asistan todos. |
| 🏦 **Banco de horas e historial** | Cierra cada periodo y lleva el saldo por persona (a quién se le deben horas y quién las debe), con movimientos manuales y un historial de esquemas. El generador usa el saldo para compensar en el siguiente periodo, con topes. |
| 💰 **Horas y recargos** | Ventana del art. 165 CST, pendientes y adicionales, nocturno, dominical/festivo y extras con tarifas por fecha. |
| 📤 **Excel** | Cuadro mensual, planilla de puestos y reporte de horas. Nunca sobrescribe: guarda `v2`, `v3`… |

## Esterilización: cómo funciona

```mermaid
flowchart LR
    A[Personal<br/>y novedades] --> S{{Solver<br/>OR-Tools CP-SAT}}
    T[Catálogo de turnos<br/>y cobertura] --> S
    S --> C[(Cuadro<br/>original · cambios)]
    C --> P[Puestos y<br/>capacitación]
    C --> H[Horas y<br/>recargos]
    C --> X[Excel]
    P --> X
    H --> X
    E[Ediciones<br/>manuales] --> C
```

El solver cumple las reglas duras y optimiza el resto (horas de la ventana, rotación, equidad). Si algo no cabe, lo dice: «el 14-oct faltan 2 en la mañana» en vez de fallar en silencio. Detalle en [Arquitectura](docs/ARQUITECTURA.md).

## Estructura

```
an/
  nucleo/xlsx.py       escritura de celdas compartida por los exportes
  radiologia/          generar_semana, analisis, plantilla_semana.xlsx
  turnos/              núcleo de Esterilización: dominio, db, reglas, solver, puestos, recargos, exportar…
  web/                 API FastAPI, trabajador del solver, migraciones, administración
web/                   front React (Vite + TypeScript)
tests/                 pytest; cada archivo también corre como script e imprime OK
docs/                  reglas, arquitectura, plan web, diseño por etapa
ejemplos/radiologia/   cuadros de prueba
```

## Empezar

```bash
git clone https://github.com/jssdv/an-turnos.git
cd an-turnos
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt -r requirements-web.txt
web/demo.sh            # Postgres, API, trabajador y front con datos de demo: http://localhost:5173
```

Usuarios de la demo: `editor@demo.co`, `lector@demo.co`, `admin@demo.co`, `nuevo@demo.co` (clave `clave-larga-1`). Producción: [docs/operacion.md](docs/operacion.md).

**Radiología por línea de comandos** (la fecha es un lunes)

```bash
.venv/bin/python -m an.radiologia.generar_semana "Asignación Radiólogos Octubre 2026.xlsx" 2026-10-19 [salida.xlsx]
```

**Pruebas**

```bash
.venv/bin/python -m pytest tests --ignore=tests/esterilizacion/test_turnos.py
.venv/bin/python tests/esterilizacion/test_turnos.py   # ≈ 2 min: resuelve meses completos
.venv/bin/python tests/radiologia/test_generar_semana.py
```

## Documentación

| Documento | Para quién | Contenido |
|---|---|---|
| [Plan web](docs/PLAN_WEB.md) | Desarrollo | Fases, decisiones y pendientes de la versión web |
| [Radiología](docs/RADIOLOGIA.md) | Desarrollo, coordinación | Arquitectura del área y requisitos del cuadro mensual |
| [Proyecto Radiología](docs/PROYECTO.md) | Todos | Etapas hacia un sistema completo de programación |
| [Visión](docs/VISION.md) | Todos | Hacia dónde crece An~: más servicios y procesos vinculados |
| [Diseño de puestos y dotación](docs/superpowers/specs/2026-10-21-puestos-dotacion-design.md) | Desarrollo | Diseño y [plan de implementación](docs/superpowers/plans/2026-10-21-puestos-dotacion.md) de puestos con demanda y dotación |
| [Reglas y marco legal](docs/REGLAS.md) | Coordinación, RR. HH., jurídico | Reglas del servicio, normativa aplicada y puntos por confirmar |
| [Arquitectura](docs/ARQUITECTURA.md) | Desarrollo | Módulos, datos y modelo del solver |
| [Hoja de ruta](docs/HOJA_DE_RUTA.md) | Todos | Qué falta validar y hacia dónde crece |
| [Diseño v1](docs/DISENO_V1.md) | Desarrollo | El diseño aprobado con el que se construyó la primera versión |
| [CLAUDE.md](CLAUDE.md) | Asistentes de código | Comandos y convenciones del repositorio |

## Estado

Ambas áreas están construidas y probadas con datos sintéticos o de ejemplo. La app de escritorio (PySide6) se retiró el 26/10/2026; queda en la etiqueta `qt-final`.

> **Aviso.** Las cifras de horas y recargos son de apoyo. Los porcentajes y la interpretación del art. 165 para turnos de 12 h deben confirmarse con Recursos Humanos o el área jurídica antes de usarlos en nómina. El repositorio no contiene datos del personal.
