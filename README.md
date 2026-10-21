<div align="center">

# An~

**Gestión de turnos y de los procesos que giran alrededor**<br>
Hoy programa la Central de Esterilización: genera el cuadro mensual, asigna puestos y calcula horas y recargos según el Código Sustantivo del Trabajo. Está pensada para crecer a más servicios y a procesos administrativos vinculados.

![Python](https://img.shields.io/badge/Python-3.13-3776AB?logo=python&logoColor=white)
![Qt](https://img.shields.io/badge/Interfaz-PySide6%20(Qt)-41CD52?logo=qt&logoColor=white)
![OR-Tools](https://img.shields.io/badge/Solver-OR--Tools%20CP--SAT-4285F4?logo=google&logoColor=white)
![SQLite](https://img.shields.io/badge/Datos-SQLite-003B57?logo=sqlite&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-portátil%2C%20sin%20instalar-0078D6?logo=windows&logoColor=white)

[Guía de uso](docs/GUIA_USUARIO.md) · [Visión](docs/VISION.md) · [Reglas y marco legal](docs/REGLAS.md) · [Arquitectura](docs/ARQUITECTURA.md) · [Hoja de ruta](docs/HOJA_DE_RUTA.md)

<br>

<img src="docs/img/cuadro.png" alt="Cuadro mensual generado por An~" width="900">

<sub>Cuadro de octubre de 2026 con datos de ejemplo: cobertura completa, descansos de 12 h y novedades (VAC, INC) respetadas.</sub>

</div>

---

## Por qué existe

En muchos servicios de un hospital el cuadro de turnos se arma a mano en Excel: ciclos que rotan, personas con restricciones, estudiantes con horarios fijos, vacaciones, incapacidades… y después hay que contar horas y recargos. **An~** hace ese trabajo en segundos, deja que la coordinadora ajuste lo que quiera y explica cada alerta.

Está pensada para una persona no técnica en un **PC corporativo sin permisos de administrador**: se entrega como una carpeta que se descomprime y se abre con doble clic.

## Hacia dónde va

La v1 resuelve un servicio, la **Central de Esterilización**, y lo hace con reglas y turnos como *datos* editables, no como código. Esa es la base para convertirla en una herramienta general de gestión de turnos:

- **Más servicios** con la misma estructura, cada uno con sus turnos, cobertura y puestos.
- **Procesos administrativos vinculados**: novedades, solicitudes y permutas, capacitaciones, y el cierre de horas y recargos para nómina.
- **Más personas usándola**, con aprobaciones y trazabilidad.

El plan, los principios y las preguntas abiertas están en [docs/VISION.md](docs/VISION.md). Hoy el alcance es solo Esterilización.

## Qué hace

| | |
|---|---|
| 🧮 **Cuadro con solver** | OR-Tools genera el esquema completo (un mes, o N semanas desde un lunes): cobertura 4+4+2 (lunes a sábado) y 2+2+2 (domingo y festivo), 12 h de descanso, día libre después de cada noche, al menos un día libre por semana y un fin de semana completo libre por esquema. |
| ⚖️ **Rotación y equidad** | Reparte parejo M, T, C y NC y los domingos/festivos, limita rachas de noches y de corridos, prefiere los libres en fin de semana y arrastra lo acumulado de meses anteriores. |
| ✋ **Edición ágil** | Arrastra celdas para intercambiarlas, asigna turnos a varias celdas con clic derecho y deshaz con Ctrl+Z. Los días de estudio se ven en la grilla. |
| 🗂️ **Original y cambios** | Dos versiones por mes. Lo que se edita queda en amarillo, con lista de diferencias, y se puede publicar o restaurar. |
| 👥 **Personal y novedades** | Crear, editar y eliminar colaboradores con casillas para turnos permitidos y bloques de estudio; vacaciones, incapacidades, licencias y días libres. |
| 🕘 **Turnos editables** | Crea, edita y elimina turnos: horarios, franjas que cubren, color y pausa de almuerzo (pagada o no). Todo se recalcula. |
| 📍 **Puestos del día** | Lavado, autoclave, sterrad, cuarto estéril y ropa, con rotación y grupos de relevo. |
| 🎓 **Capacitación** | Una sesión por semana como máximo, el lunes o el siguiente día hábil, para que asistan todos. |
| 🏦 **Banco de horas e historial** | Cierra cada periodo y lleva el saldo por persona (a quién se le deben horas y quién las debe), con movimientos manuales y un historial de esquemas. |
| 💰 **Horas y recargos** | Ventana del art. 165 CST, pendientes y adicionales, nocturno, dominical/festivo y extras con tarifas por fecha. |
| 📤 **Excel** | Cuadro mensual, planilla de puestos y reporte de horas. Nunca sobrescribe: guarda `v2`, `v3`… |

## Cómo funciona

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

## Un vistazo

<table>
<tr>
<td width="50%"><img src="docs/img/puestos.png" alt="Puestos y capacitación"><br><sub><b>Puestos y capacitación.</b> Quién va en cada puesto, con el grupo de pausa (P1/P2).</sub></td>
<td width="50%"><img src="docs/img/horas.png" alt="Horas y recargos"><br><sub><b>Horas y recargos.</b> Contratadas, trabajadas, pendientes y adicionales por persona.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/img/banco.png" alt="Banco de horas"><br><sub><b>Banco de horas.</b> Saldo por persona, con cierres y movimientos.</sub></td>
<td width="50%"><img src="docs/img/cuadro_puestos.png" alt="Cuadro con puestos"><br><sub><b>Cuadro con puestos.</b> «Mostrar puesto» pasa <code>M</code> a <code>M·2</code> (autoclave).</sub></td>
<td width="50%"><img src="docs/img/personal.png" alt="Personal"><br><sub><b>Personal.</b> Restricciones, puesto fijo y horario de estudio.</sub></td>
</tr>
<tr>
<td width="50%"><img src="docs/img/turnos.png" alt="Catálogo de turnos"><br><sub><b>Turnos.</b> Horarios, pausas y turnos nuevos desde la propia app.</sub></td>
<td></td>
</tr>
</table>

## Empezar

**Desarrollo (Mac o Linux)**

```bash
git clone https://github.com/jssdv/an-turnos.git
cd an-turnos
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials openpyxl ortools
.venv/bin/python app.py
```

En Mac también sirve el doble clic en `An.command`: prepara el entorno la primera vez y abre la app. Los datos quedan en `turnos.db`, junto a `app.py`.

**Paquete para Windows** (se arma desde el Mac)

```bash
./empaquetar.sh prueba   # dist/PruebaPC.zip: comprueba Qt y OR-Tools en el PC corporativo
./empaquetar.sh          # dist/An.zip: la app completa (≈ 150 MB comprimida)
```

En el PC destino basta descomprimir y abrir `An.bat`. No se instala nada.

**Pruebas**

```bash
.venv/bin/python test_turnos.py   # imprime OK (≈ 1 min: resuelve meses completos)
.venv/bin/python test_gui.py      # imprime OK (ventana sin pantalla)
```

## Documentación

| Documento | Para quién | Contenido |
|---|---|---|
| [Guía de uso](docs/GUIA_USUARIO.md) | Coordinación | El mes paso a paso: personal, novedades, generar, ajustar, exportar |
| [Visión](docs/VISION.md) | Todos | Hacia dónde crece An~: más servicios y procesos vinculados |
| [Reglas y marco legal](docs/REGLAS.md) | Coordinación, RR. HH., jurídico | Reglas del servicio, normativa aplicada y puntos por confirmar |
| [Arquitectura](docs/ARQUITECTURA.md) | Desarrollo | Módulos, datos, modelo del solver, empaquetado |
| [Hoja de ruta](docs/HOJA_DE_RUTA.md) | Todos | Qué falta validar y hacia dónde crece |
| [Diseño v1](docs/DISENO_V1.md) | Desarrollo | El diseño aprobado con el que se construyó la primera versión |
| [CLAUDE.md](CLAUDE.md) | Asistentes de código | Comandos y convenciones del repositorio |

## Estado

La v1 está construida y probada con datos sintéticos. Antes de usarla en producción falta [probarla en el PC corporativo y confirmar las reglas pendientes](docs/HOJA_DE_RUTA.md#antes-de-seguir-creciendo).

> **Aviso.** Las cifras de horas y recargos son de apoyo. Los porcentajes y la interpretación del art. 165 para turnos de 12 h deben confirmarse con Recursos Humanos o el área jurídica antes de usarlos en nómina. El repositorio no contiene datos del personal.
