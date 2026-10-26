# Retiro de la app de escritorio (Qt)

**Fecha:** 26/10/2026 · **Estado:** aprobado en conversación, pendiente de revisión escrita.
**Contexto:** la web reemplaza a la app Qt (`PLAN_WEB.md`, pregunta 3). Antes de migrar la web a Untitled UI ([migración a Untitled UI](2026-10-26-untitled-ui-design.md)) se borra todo lo que solo sirve al escritorio: no se conservan archivos que nadie usa.

## Objetivo

El repositorio queda con el núcleo puro (`an/turnos`, `an/radiologia` sin interfaz), la web (`an/web`, `web/`) y sus pruebas. Nada importa PySide6.

## Respaldo

Antes de borrar, etiqueta git `qt-final` en el commit vigente (`git tag qt-final && git push origin qt-final`). Cualquier archivo se recupera desde ahí.

## Qué se borra

| Grupo | Archivos |
|---|---|
| Arranque | `an/__main__.py`, `An.command`, `empaquetar.sh` (y `dist/`, ignorado) |
| Núcleo Qt | `an/nucleo/shell.py`, `tema.py`, `widgets.py`, `graficos.py`, `usuarios.py`, `fuentes/` |
| Pantallas Qt | `an/turnos/paginas.py`, `an/turnos/ui_puestos.py`, `an/radiologia/paginas.py` |
| Pruebas Qt | `tests/nucleo/` completo, `tests/esterilizacion/test_gui.py`, `tests/radiologia/test_gui.py` |
| Dependencias | `PySide6-Essentials` de `requirements.txt`; `QT_QPA_PLATFORM` y pasos Qt de `.github/workflows/ci.yml` |
| Diseño | páginas «Direcciones» y «Pantallas» de `docs/diseno/An_UI.figcraft` (pantallas Qt) y los PNG Qt de `docs/diseno/` (`esterilizacion_cuadro.png`, `radiologia_*.png`, `sistema.png`) |
| Docs | `docs/NUCLEO.md` (contrato de áreas Qt) |

## Qué se queda

- `an/nucleo/xlsx.py` (`poner_texto`: lo usan `exportar.py`, `generar_semana.py`, `analisis.py` y pruebas) y `an/nucleo/__init__.py` si algo usa `RAIZ`.
- El núcleo puro de `an/turnos` y `an/radiologia`, la `BD` con SQLite (pruebas rápidas y `an.web.migrar`), `ejemplos/`.

## Qué se ajusta

- `checks/tokens.py --verificar`: deja de comparar con `tema.C`; solo FigCraft ↔ `web/src/tokens.css`. `tests/checks/test_tokens.py` en consecuencia.
- `pytest.ini`: sin los `--ignore` de pruebas Qt que ya no existen.
- `CLAUDE.md`, `README.md`, `docs/PLAN_WEB.md`, `docs/RADIOLOGIA.md`, `docs/ARQUITECTURA.md`, `docs/PROYECTO.md`, `docs/DISENO_V1.md`: sin comandos ni instrucciones de escritorio; donde la historia importe, una línea «retirado el 26/10/2026, ver etiqueta `qt-final`».
- Si una prueba de lógica pura importa Qt de paso, se corrige el import, no la prueba.

## Verificación

1. `grep -rn "PySide6\|an.nucleo\.\(shell\|tema\|widgets\|graficos\|usuarios\)"` fuera de `.venv` y de la historia: sin resultados.
2. `pytest tests` (SQLite) y `AN_BD=postgres pytest` sin `test_turnos.py`; `test_turnos.py` aparte; `tests/web` con `AN_PG_URL`.
3. `cd web && npm run build`; `checks/diseno.py`, `checks/tokens.py --verificar`, `checks/rls.py`, `checks/reglas.py`.
4. `web/demo.sh` arranca (API, trabajador, front) y se ingresa con `editor@demo.co`.
5. Entorno nuevo: `pip install -r requirements.txt` sin PySide6 y las pruebas pasan.

## Fuera de alcance

La migración de la web a Untitled UI (spec propio). Cambiar la lógica del núcleo.
