# Radiología: notas de arquitectura

Área **Radiología** de An (`an/radiologia/`): convierte el cuadro mensual de radiólogos (`Asignación Radiólogos <Mes> 2026.xlsx`,
hoja `Cambios …`) en el libro semanal (`SEMANA dd AL dd DE MES.xlsx`). Hoja de ruta hacia un sistema completo: `PROYECTO.md`.
Comandos, tests y empaquetado: `CLAUDE.md` en la raíz. Ejemplos de prueba: `ejemplos/radiologia/`.

## Arquitectura
- `generar_semana.py` — núcleo del área, sin interfaz. `cargar_mensual` → `lunes_disponibles` → `construir(ws, lunes)` devuelve `(workbook, resumen, datos)`; `ruta_libre` elige `SEMANA … .xlsx`, luego `v2`, `v3`… (nunca sobrescribe). Los problemas que el usuario puede corregir lanzan `ErrorPlanilla` (el mensaje se muestra tal cual).
  - Mapeo código de turno → servicio/franja: `CODIGOS`, `FILAS_ECO`/`FILAS_CJ` (filas de la cuadrícula ECO), `SLOTS` (franjas estándar entre semana de los servicios de lectura), `IGNORAR`. Los códigos desconocidos se reportan, no se publican.
  - Las hojas de lectura se reconstruyen copiando estilos de `plantilla_semana.xlsx`; ECO es una cuadrícula fija que se llena en el sitio. Regla de disponibilidad (`linea_tiempo`): las horas sin cubrir van al médico `disp` — antes de las 7 am el del día anterior, después el del mismo día.
- `analisis.py` — funciones puras sobre el cuadro y el libro: `alertas` (reglas de descanso que replican las filas «prueba turg/nurg/CCC»; horas de la hoja `Nom-Hrs`), `equidad` (horas de la semana y totales del mes leídos de las columnas `JORNADA`, `TOTAL`, `HORAS A`, `PNTE`, `NC`, `FDS`, `D`, `Fes`), `agenda_por_medico`/`ics`/`exportar_agendas`, `comparar_libros` (diferencias con la última versión guardada de la misma semana; celdas cambiadas en amarillo + hoja `Cambios`), `revisar_cuadro` (turnos que se cruzan, nombres incompletos, códigos desconocidos con ubicación), `equidad_meses` y `html_planilla` (HTML imprimible; comparte `texto_celda`/`color_hex` con la vista previa).
- `paginas.py` — clase `Planilla` (área): secciones Resumen (tarjetas + cobertura semanal), Vista previa, Alertas, Equidad y horas, Agendas, Cambios. La vista previa pinta el libro en memoria que se va a guardar (sin modelo aparte), de forma perezosa al mostrar la sección, con los colores del tema del libro (`analisis.paleta_tema`). `QFileSystemWatcher` recarga el cuadro cuando Excel lo guarda; arrastrar y soltar; atajos Ctrl+O/G/P, Alt+←/→, F5 (Ctrl+1..6 los pone el shell).

## Requisitos del cuadro mensual / reglas acordadas
- La fila 3 de `Cambios …` debe tener fechas completas (formato `d`); las semanas se emparejan por fecha exacta, nunca por número de día. Los valores se leen con `data_only=True`: el cuadro debe haberlo guardado Excel (los archivos guardados por openpyxl no traen valores de fórmulas).
- Contingencia, vacaciones, asignación de estudios y notas libres quedan en blanco (manual); nombres completos en todas partes; densitometría incluye domingo; `Z` y hemodinamia no se publican.
- Conservar nombres de hojas, encabezados y etiquetas en español tal como están escritos. `~$…xlsx` son archivos de bloqueo de Excel: se ignoran.
