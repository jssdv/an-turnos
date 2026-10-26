# Corrección de la revisión de seguridad (I-1, M-1…M-9)

Una prueba que falle primero por hallazgo; un solo PR. M-4 y M-7 quedan fuera (decisión de la persona dueña), anotados en `docs/seguridad-hallazgos.md`.

- [ ] I-1: `cargar_mensual` rechaza hojas con más de 500 filas o 60 columnas (ErrorPlanilla → 422 al subir y al leer archivos ya guardados); `MAX_DESCOMPRIMIDO` a 10 MB; `mem_limit` y `pids_limit` en API y trabajador
- [ ] M-1: helper común `texto_seguro` (`data_type='s'`) en las salidas xlsx de Radiología y Esterilización
- [ ] M-2: exportar en Radiología exige `editar`; en Esterilización tope de 20 exportes por periodo y día (429)
- [ ] M-3: médico por índice en la URL de la agenda, nombre de archivo en cabecera; `--no-access-log`; retención de logs en `docs/operacion.md`
- [ ] M-5: Caddy sin capacidades extra, red pública separada de la `internal: true`; probar la pila local
- [ ] M-6: documentar AAAA / `userland-proxy`
- [ ] M-8: borrador de `sessionStorage` ligado al usuario y borrado al salir
- [ ] M-9: claves `CAMBIAR_` rechazadas; auditoría de subida/borrado de `archivo`; documentar y cifrar `.cifras`
- [ ] Hallazgos M-4 y M-7 pendientes en el registro; checks y pruebas; PR
