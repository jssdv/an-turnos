"""Tokens de color: FigCraft (An_UI.figcraft) → web/src/tokens.css, y verificación contra an/nucleo/tema.py (C)."""
import ast
import json
import sys
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
FIGCRAFT = RAIZ / "docs" / "diseno" / "An_UI.figcraft"
TEMA = RAIZ / "an" / "nucleo" / "tema.py"
CSS = RAIZ / "web" / "src" / "tokens.css"


def a_hex(r, g, b, a):
    h = "#" + "".join(f"{round(x * 255):02X}" for x in (r, g, b))
    return h if a >= 1 else h + f"{round(a * 255):02X}"


def leer_variables(ruta):
    with zipfile.ZipFile(ruta) as z:
        v = json.loads(z.read("document.json"))["variables"]
    col = next(c for c in v["collections"] if c["name"] == "Color")
    modo = col["modes"][0]["id"]
    return {x["name"]: a_hex(**{k: x["values"][modo]["value"][k] for k in "rgba"})
            for x in v["variables"] if x["collection"] == col["id"]}


def leer_tema(ruta):
    for n in ast.walk(ast.parse(Path(ruta).read_text(encoding="utf-8"))):
        if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", None) == "C":
            return {k.arg: ast.literal_eval(k.value) for k in n.value.keywords}
    raise ValueError("no se encontró C en tema.py")


def css(tokens):
    return ":root {\n" + "".join(f"  --{k.replace('_', '-')}: {v};\n" for k, v in tokens.items()) + "}\n"


def _diferencias(esperado, real, nombre):
    return [f"{nombre}: {k}: esperado {esperado.get(k)}, real {real.get(k)}"
            for k in sorted(esperado.keys() | real.keys()) if esperado.get(k) != real.get(k)]


def main(argv):
    ruta = Path(argv[argv.index("--css") + 1]) if "--css" in argv else CSS
    tokens = leer_variables(FIGCRAFT)
    if "--verificar" not in argv:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.write_text(css(tokens), encoding="utf-8")
        return 0
    dif = _diferencias(tokens, leer_tema(TEMA), "tema.C")
    if not ruta.exists():
        dif.append(f"{ruta} no existe")
    elif ruta.read_text(encoding="utf-8") != css(tokens):
        actual = {}
        for l in ruta.read_text(encoding="utf-8").splitlines()[1:-1]:
            k, _, v = l.strip().rstrip(";").partition(": ")
            actual[k[2:].replace("-", "_")] = v
        dif += _diferencias(tokens, actual, "tokens.css") or ["tokens.css: formato distinto al generado"]
    for d in dif:
        print(d, file=sys.stderr)
    return 1 if dif else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
