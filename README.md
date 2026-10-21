# Turnos Esterilización

Aplicación de escritorio (interfaz en español) para programar los turnos de la Central de Esterilización: genera el cuadro mensual con un solver, asigna los puestos del día, programa la capacitación y calcula horas y recargos según el Código Sustantivo del Trabajo de Colombia.

Pensada para una coordinadora no técnica en un PC corporativo **sin permisos de administrador**: se entrega como carpeta portátil de Windows (Python embebido, nada que instalar).

## Qué hace hoy (v1)

| Área | Funciones |
|---|---|
| Personal | Alta/edición, tipo (regular, restringida, estudiante, refuerzo), horas contratadas, turnos permitidos, puesto fijo, horario de estudio |
| Novedades | Vacaciones, incapacidades, licencias y días libres solicitados |
| Cuadro mensual | Generación con OR-Tools CP-SAT; edición por celda con validación en vivo; regenerar todo, respetando cambios, o solo una semana |
| Versiones | **Original** (publicada) y **Cambios** (copia de trabajo), con diferencias en amarillo, publicar y restaurar |
| Turnos | Catálogo editable: horarios, pausas de almuerzo (pagadas o no), turnos nuevos, cobertura requerida |
| Puestos | Lavado, autoclave, sterrad, cuarto estéril y ropa, con rotación y grupos de pausa |
| Capacitación | Una sesión por semana como máximo, lunes o siguiente día hábil |
| Horas y recargos | Ventana del art. 165 CST, pendientes y adicionales, recargo nocturno, dominical/festivo y extras con tarifas por fecha de vigencia |
| Excel | Cuadro mensual, planilla de puestos, reporte de horas y recargos (nunca sobrescribe: `v2`, `v3`…) |

## Empezar

```bash
python3 -m venv .venv
.venv/bin/pip install PySide6-Essentials openpyxl ortools
.venv/bin/python app.py
```

En Mac también sirve el doble clic en `Turnos Esterilizacion.command`. Los datos quedan en `turnos.db`, junto a `app.py` (no se sube al repositorio).

Pruebas (≈ 1 min, resuelven meses completos):

```bash
.venv/bin/python test_turnos.py   # imprime OK
```

Paquete para Windows (se arma desde el Mac):

```bash
./empaquetar.sh prueba   # dist/PruebaPC.zip: comprueba Qt + OR-Tools en el PC corporativo
./empaquetar.sh          # dist/TurnosEsterilizacion.zip: la app completa
```

## Estructura

Núcleo en Python puro; Qt solo lo llama. Detalle en [CLAUDE.md](CLAUDE.md) y [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md).

```
dominio.py   turnos, personas, novedades, festivos de Colombia
db.py        SQLite (versiones original / cambios)
reglas.py    validación del cuadro
solver.py    generación mensual (OR-Tools CP-SAT)
puestos.py · capacitacion.py · recargos.py · flujo.py · exportar.py
app.py       ventana PySide6
test_turnos.py
```

## Documentación

- [docs/HOJA_DE_RUTA.md](docs/HOJA_DE_RUTA.md): hacia dónde crece el proyecto y preguntas abiertas.
- [docs/REGLAS.md](docs/REGLAS.md): reglas del servicio y marco legal, con lo que falta confirmar.
- [docs/ARQUITECTURA.md](docs/ARQUITECTURA.md): módulos, datos y modelo del solver.
- [docs/DISENO_V1.md](docs/DISENO_V1.md): diseño con el que se construyó la v1.

## Aviso

Las cifras de horas y recargos son de apoyo. Los porcentajes y la interpretación del art. 165 para turnos de 12 h deben confirmarse con Recursos Humanos o el área jurídica antes de usarlos en nómina. El repositorio no contiene datos de personal.
