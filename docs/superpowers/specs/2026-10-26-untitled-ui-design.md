# Migración de la web a Untitled UI

**Fecha:** 26/10/2026 · **Estado:** aprobado en conversación, pendiente de revisión escrita.
**Depende de:** PR #20 (rediseño) fusionado y [retiro de Qt](2026-10-26-retiro-qt-design.md) terminado.
**Cambia una decisión:** `docs/PLAN_WEB.md` decía «Sin Tailwind». Se reemplaza por Tailwind v4 + React Aria con componentes de Untitled UI (MIT, https://github.com/untitleduico/react).

## Objetivo

La web adopta el aspecto de Untitled UI casi tal cual (neutros, tipografía, sombras, componentes), con nuestra marca verde azulada y los colores de turno. El código propio de interfaz se reduce a lo que Untitled no tiene (la grilla de turnos y los pasos del Cuadro). Lo que deja de usarse se borra.

Criterio de éxito: todas las pantallas (Esterilización y Radiología, los cuatro tipos de usuario de la demo) funcionan igual que hoy, con componentes Untitled; no queda ningún `.module.css`, `@base-ui/react` ni token viejo; los checks y las pruebas pasan.

## Decisiones

| Tema | Decisión |
|---|---|
| Identidad | Look Untitled completo; solo cambia la escala de marca (nuestro verde azulado como `brand-600`). Sin modo oscuro: se quita el bloque `.dark-mode` del tema. |
| Cómo se integran | Enfoque A: se copian los componentes de Untitled a `web/src/components/` con su estructura (`base/`, `application/`, `foundations/`, `utils/cx.ts`, `hooks/`), solo los que se usan. Las pantallas los usan directamente; no hay envoltorios propios. |
| Componentes propios que se borran | `Boton`, `Campo`, `Tabla`, `Tarjeta`, `Aviso`, `Dialogo`, `Lateral`, `Progreso`, `Ayuda`, `Ficha`/`Planilla` en su forma actual y todos los `*.module.css`. |
| Propios que siguen (reescritos con Tailwind) | `Planilla`/`Ficha` (grilla de turnos: Untitled no tiene equivalente), `Pasos` del Cuadro, recuadro de ayuda (hecho con piezas Untitled). |
| Tipografía | Inter (la que ya trae el proyecto); Sora se borra. |
| Iconos | `@untitledui/icons`. |
| Rama | `untitled-ui` desde `main` tras los dos PR previos. `prueba-tailwind` se cierra sin fusionar (borra la paleta que Untitled necesita). |

## Colores y FigCraft

- La colección «Color» de `An_UI.figcraft` queda con `brand_25 … brand_950` (escala generada a partir de `#0B7A75` como 600, verificada en contraste) y `turno_M`, `turno_T`, `turno_C`, `turno_NC`. Las 42 variables actuales se borran.
- `checks/tokens.py` escribe `web/src/tokens.css` con `--color-brand-*` y `--turno-*`. En `web/src/styles/theme.css` las líneas de la escala de marca apuntan a esas variables.
- `checks/diseno.py`: colores literales solo en `tokens.css` y `styles/theme.css` (copiado de Untitled, con su origen y versión en la cabecera); texto ≥ 11 px también en clases (`text-[Npx]`); contraste ≥ 4,5:1 en pares de marca y de turnos (texto oscuro sobre cada `turno_*`, blanco sobre `brand-600`/`brand-700`) y en pares `text-*`/`bg-*` de una misma cadena cuando ambos sean tokens con valor conocido.

## Dependencias

`tailwindcss`, `@tailwindcss/vite`, `react-aria-components`, `react-aria`, `tailwind-merge`, `tailwindcss-react-aria-components`, `tailwindcss-animate`, `@untitledui/icons`, en versiones exactas publicadas hace al menos dos semanas (se fijan en el plan). Se desinstala `@base-ui/react`.

## Comportamiento que se conserva

Sesión y cambio de clave obligatorio; permisos por área (editar / solo consulta) y el aviso de modo consulta; estados cargando, vacío y error en cada lista; impresión apaisada del Cuadro (`@media print`); arrastrar para intercambiar celdas, selección por lote y diálogo de registrar cambio; ir a la celda desde una alerta; exportes; textos en español (solo se ajusta la forma cuando un componente lo pida).

## Fases (cada una deja la web funcionando y es un commit)

1. **Base:** dependencias, Vite, `styles/` de Untitled, tokens de marca desde FigCraft, check de diseño adaptado.
2. **Componentes base:** botones, input, select, checkbox, toggle, textarea, badges, tooltip, dropdown, modal, empty state, indicador de carga.
3. **Estructura:** navegación lateral, encabezado de página, contenedores; `Disposicion`, `Ingresar`, `CambiarClave`.
4. **Pantallas de catálogo:** Personal, Ausencias, Puestos, Solicitudes, Reglas y turnos, Usuarios (tabla de Untitled).
5. **Analíticas y Radiología.**
6. **Cuadro:** `Planilla`/`Ficha` con Tailwind, pasos, alertas, exportar, generar (progreso), registrar cambio (modal), acciones del periodo, cambios del periodo.
7. **Limpieza y docs:** borrar CSS Modules, `estilos.css` (lo que sobreviva pasa a `styles/globals.css`), `@base-ui/react`, Sora, tokens viejos; `PLAN_WEB.md` §7 y la tabla de tecnologías, `CLAUDE.md`.

## Verificación por fase

`npm run build` (con `tsc`); `checks/diseno.py`, `checks/tokens.py --verificar`; `tests/web` con Postgres; recorrido en el navegador con `editor`, `lector`, `admin` y `nuevo` de `web/demo.sh`, con capturas a 1280 px y 375 px. En la fase 6, la marca `cuadro:maquetado-ms` sigue por debajo del umbral de 1 s de `PLAN_WEB.md` §8.

## Fuera de alcance

Modo oscuro; nuevas funciones; cambios en la API o el núcleo; componentes PRO de pago.
