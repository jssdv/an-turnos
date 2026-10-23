# Núcleo común de An

**Decisión (22/10/2026):** Radiología y Esterilización dejan de ser dos aplicaciones. Son **áreas** de una sola app (`an`)
que comparten un núcleo (tema, widgets, ventana base, usuarios). El área que se abre la define el **usuario local**.
La estética es la de Radiología; Esterilización se adaptó a ella.

## Qué es núcleo y qué es área

| Núcleo (`an/nucleo/`) | Área (`an/radiologia/`, `an/esterilizacion/`) |
|---|---|
| `tema.py`: tokens de color `C`, `ESTILO`, ícono, arranque de Qt (Fusion, tema claro, fuentes Inter y Sora empaquetadas en `fuentes/`) | Reglas de negocio, datos y archivos de su servicio |
| `widgets.py`: `Tarjeta`, `tabla`/`llenar`, `con_vacio`, `ocupado`, `poner_nivel`, `titulo_pagina`, `abrir` | Sus páginas (`paginas.py`) y su cabecera (selector de semana/periodo, acciones) |
| `shell.py`: `Ventana` (menú lateral oscuro con marca, secciones con insignias y usuario; barra del área, banner, toast, atajos Ctrl+1..N, geometría, `errores.log`) | Sus atajos propios y su estado (`QSettings` con prefijo del área) |
| `usuarios.py`: usuario → área | — |

## Contrato de un área
Clase con `NOMBRE`, `CLAVE` y `__init__(self, ventana)`. Expone:

- `secciones`: lista de `(título, QWidget)`; cada una es una entrada del menú lateral. **Obligatorio.**
- Opcionales: `cabecera` (barra sobre las secciones), `vacia` (reemplaza barra y secciones mientras no hay datos y apaga el menú; se activa con `ventana.mostrar_vacia(True)`), `TAMANO`, `iniciar()` (ventana ya armada: cargar último estado), `seccion_activa(i)`, `dragEnterEvent/dragLeaveEvent/dropEvent`, `cerrar()`.
- Hacia el shell: `ventana.avisar(texto, nivel)`, `notificar(texto)`, `ir_a(i)`, `contar(i, n, nivel)` (insignia; `"warn"` en amarillo), `mostrar_vacia(si)`, `atajo(tecla, función)`, `cfg` (QSettings), `findChildren`/diálogos con `ventana` como padre.

Registrar un área nueva = escribir su clase y añadirla a `AREAS` en `an/__main__.py` y a `usuarios.json`.

## Usuarios locales (v1)
`usuarios.json` (junto al paquete, ignorado por git) mapea `{"nombre": "clave de área"}`. Se crea en el primer arranque con un
usuario por área. Al iniciar se pide el usuario (sin contraseña; se recuerda el último) y el menú lateral tiene «Cambiar usuario».
Un usuario ve una sola área. **No es seguridad**: cualquiera con acceso al PC puede elegir otro usuario o editar el archivo.

Pasos previstos (Etapas 5–6 de `PROYECTO.md`): contraseña/inicio de sesión corporativo, roles (administrador general,
coordinador de área, profesional), un usuario con varias áreas, auditoría de quién cambió qué.

## Datos y ajustes
- Radiología sigue trabajando sobre los Excel del coordinador (sin base de datos). Esterilización usa `turnos.db` (SQLite) junto al paquete.
- `QSettings` ("An"/"An"): claves con prefijo de área (`radiologia/ultimo_archivo`, `esterilizacion/carpeta`) y `usuario`.
  Al unificarse, Radiología perdió sus ajustes anteriores (`Radiologia/PlanillaSemanal`): se vuelve a elegir el último cuadro una vez.
- Los tests redirigen `QSettings` a un ini temporal (`QSettings.setDefaultFormat` + `setPath`) **antes** de crear ventanas.

## Cambios visuales al adaptar Esterilización
Se aplicó el estilo de Radiología: menú lateral en vez de pestañas superiores (las sub-pestañas internas de Parámetros e
Historial se conservan), cabecera blanca con marca, botones y campos de Radiología. Diferencias respecto al diseño anterior
de Esterilización (`ARQUITECTURA.md`): sin filas alternas ni números alineados a la derecha en las tablas, y el foco de teclado
se marca con borde del color de acento (antes anillo de 2 px). Si se quieren recuperar, se hace una vez en `ESTILO`/`llenar`
para ambas áreas.

## Diseño (octubre 2026)
El aspecto sale de `docs/diseno/An_UI.figcraft` (FigCraft; capturas PNG al lado): dirección «clínico oscuro» con menú lateral
azul noche, acento verde azulado, Sora para títulos y cifras e Inter para el resto. Los nombres de `tema.C` son los de las
variables «Color» del archivo. En el cuadro de Esterilización cada turno es una ficha redondeada (`Chip`) y lo cambiado
respecto al original lleva una esquina oscura (antes fondo amarillo; el Excel exportado sigue en amarillo).

La ventana se encaja en la pantalla al abrirse (o al restaurar una geometría guardada en otro monitor) y queda centrada.
Cada sección y la pantalla vacía van dentro de un área desplazable, así que su contenido no agranda la ventana; el ancho
mínimo lo fija la barra del área (~1300 px en Radiología con un archivo cargado; el nombre del archivo se recorta con «…»).

## Pendiente
- Unificar el tratamiento de tablas con números (alineación, orden) en ambas áreas.
- Extraer a `nucleo/` más patrones repetidos (panel con título, barra de acciones) cuando haya una tercera área.
- Probar `dist/An.zip` en el PC corporativo (bloqueo 0.6/0.7 de `PROYECTO.md`).
