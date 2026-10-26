"""Reglas de diseño del front (docs/PLAN_WEB.md §7): sin colores literales fuera de web/src/tokens.css, texto no menor al mínimo
y pares de tokens con contraste WCAG ≥ 4,5:1. Uso: python checks/diseno.py [--raiz DIR]. Sale 1 si algo falla."""
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
MIN_PX = 11  # el mínimo que ya usa la app Qt (tema.py); la colección «Tipo» de FigCraft aún no existe
MIN_CONTRASTE = 4.5
# (texto, fondo) que el diseño usa de verdad. Excluidos: --lateral-tenue sobre --lateral (4,42:1; no se usa para texto) y los controles
# deshabilitados (WCAG 1.4.3 los exime). Un par nuevo se añade aquí; los de las reglas CSS se comprueban solos.
PARES = [
    ("texto", "fondo"), ("texto", "superficie"), ("titulo", "superficie"), ("titulo", "superficie-sutil"), ("atenuado", "superficie"),
    ("atenuado", "fondo"), ("atenuado", "superficie-sutil"), ("acento", "superficie"), ("acento", "acento-suave"), ("superficie", "acento"),
    ("superficie", "acento-hover"), ("superficie", "error"), ("lateral-texto", "lateral"), ("lateral-texto", "lateral-sel"),
    ("lateral-texto", "lateral-hover"), ("superficie", "lateral-sel"), ("superficie", "lateral-hover"),
    ("warn-texto", "warn-fondo"), ("warn-texto", "warn-celda"), ("error-texto", "error-fondo"), ("ok-texto", "ok-fondo"),
    ("info-texto", "info-fondo"), ("error", "superficie"), ("error", "error-fondo"), ("ok", "superficie"), ("info", "superficie"),
    ("titulo", "turno-M"), ("titulo", "turno-T"), ("titulo", "turno-C"), ("titulo", "turno-NC"), ("titulo", "marca"),
    ("lateral", "marca"), ("titulo", "warn-insignia"), ("warn-texto", "superficie"),
]
COLOR_LITERAL = re.compile(r"#[0-9a-fA-F]{3,8}\b|\b(?:rgba?|hsla?|oklch|oklab|lab|lch)\(|:\s*(?:white|black)\b", re.I)
IGNORAR = {"tokens.css", "esquema.d.ts"}
# Clases de Tailwind en .ts/.tsx: tamaño arbitrario (`text-[9px]`) y pares sin variante (`text-x bg-y`, no `hover:bg-y`) en una misma cadena.
TW_TAM = re.compile(r"(?<![\w:-])text-\[([\d.]+(?:px|rem|em))\]")
TW_TEXTO = re.compile(r"(?<![\w:\[-])text-([a-z][\w-]*)")
TW_FONDO = re.compile(r"(?<![\w:\[-])bg-([a-z][\w-]*)")
CADENA = re.compile(r'"([^"\n]*)"|`([^`]*)`')


def luminancia(hexa):
    r, g, b = (int(hexa[i:i + 2], 16) / 255 for i in (1, 3, 5))
    f = lambda c: c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b)


def contraste(a, b):
    la, lb = sorted((luminancia(a), luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def leer_tokens(css):
    return {m.group(1): m.group(2) for m in re.finditer(r"--([\w-]+):\s*(#[0-9A-Fa-f]{6})\s*;", css)}


def _fuentes(src):
    return sorted(p for p in src.rglob("*") if p.suffix in (".css", ".ts", ".tsx") and p.name not in IGNORAR and "fuentes" not in p.parts)


def _reglas(css):
    """[(selector, {propiedad: valor})] de un CSS plano (sin anidar, como el de este proyecto)."""
    css = re.sub(r"/\*.*?\*/", "", css, flags=re.S)
    return [(s.strip(), dict(re.findall(r"([\w-]+)\s*:\s*([^;]+?)\s*(?:;|$)", cuerpo))) for s, cuerpo in re.findall(r"([^{}]+)\{([^{}]*)\}", css)]


def _px(valor):
    m = re.fullmatch(r"([\d.]+)(px|rem|em)", valor.strip())
    return float(m.group(1)) * (1 if m.group(2) == "px" else 16) if m else None


def revisar(raiz=RAIZ):
    src = Path(raiz) / "web" / "src"
    tokens_css = src / "tokens.css"
    if not tokens_css.exists():
        return [f"{tokens_css} no existe (python checks/tokens.py lo genera)"]
    tokens = leer_tokens(tokens_css.read_text(encoding="utf-8"))
    out = []
    for a, b in PARES:
        for t in (a, b):
            if t not in tokens:
                out.append(f"par ({a}, {b}): el token --{t} no existe en tokens.css")
        if a in tokens and b in tokens and (c := contraste(tokens[a], tokens[b])) < MIN_CONTRASTE:
            out.append(f"contraste {c:.2f}:1 < {MIN_CONTRASTE}:1 en el par --{a} sobre --{b}")
    for p in _fuentes(src):
        rel = p.relative_to(Path(raiz))
        texto = p.read_text(encoding="utf-8")
        for n, linea in enumerate(texto.splitlines(), 1):
            if COLOR_LITERAL.search(linea) and not linea.lstrip().startswith(("//", "*", "/*")):
                out.append(f"{rel}:{n}: color literal fuera de tokens.css: {linea.strip()[:70]}")
        if p.suffix != ".css":
            for n, linea in enumerate(texto.splitlines(), 1):
                for m in TW_TAM.finditer(linea):
                    if _px(m.group(1)) < MIN_PX:
                        out.append(f"{rel}:{n}: clase {m.group(0)} (mínimo {MIN_PX}px)")
                for a, b in CADENA.findall(linea):
                    cad = a or b
                    col = [t for t in TW_TEXTO.findall(cad) if t in tokens]
                    fon = [t for t in TW_FONDO.findall(cad) if t in tokens]
                    for c_, f_ in ((c_, f_) for c_ in col for f_ in fon):
                        if (c := contraste(tokens[c_], tokens[f_])) < MIN_CONTRASTE:
                            out.append(f"{rel}:{n}: contraste {c:.2f}:1 con text-{c_} sobre bg-{f_}")
            continue
        for sel, props in _reglas(texto):
            tam = _px(props.get("font-size", "")) if "font-size" in props else None
            if tam is not None and tam < MIN_PX:
                out.append(f"{rel}: «{sel}» usa font-size {props['font-size']} (mínimo {MIN_PX}px)")
            if ":disabled" in sel:
                continue
            col = re.fullmatch(r"var\(--([\w-]+)\)", props.get("color", ""))
            fon = re.fullmatch(r"var\(--([\w-]+)\)", props.get("background", props.get("background-color", "")))
            if col and fon and col.group(1) in tokens and fon.group(1) in tokens:
                c = contraste(tokens[col.group(1)], tokens[fon.group(1)])
                if c < MIN_CONTRASTE:
                    out.append(f"{rel}: «{sel}» contraste {c:.2f}:1 con --{col.group(1)} sobre --{fon.group(1)}")
    return out


def main(argv):
    raiz = Path(argv[argv.index("--raiz") + 1]) if "--raiz" in argv else RAIZ
    problemas = revisar(raiz)
    for x in problemas:
        print(x, file=sys.stderr)
    return 1 if problemas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
