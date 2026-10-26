import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de checks/diseno.py: el árbol real pasa y cada tipo de falta se detecta. Imprime OK."""
import tempfile
from pathlib import Path

from checks import diseno

TOKENS = (diseno.RAIZ / "web" / "src" / "tokens.css").read_text(encoding="utf-8")


def _arbol(css="", tsx=""):
    d = Path(tempfile.mkdtemp())
    (d / "web" / "src").mkdir(parents=True)
    (d / "web" / "src" / "tokens.css").write_text(TOKENS, encoding="utf-8")
    (d / "web" / "src" / "a.module.css").write_text(css, encoding="utf-8")
    (d / "web" / "src" / "a.tsx").write_text(tsx, encoding="utf-8")
    return d


def test_arbol_real_pasa():
    assert diseno.revisar() == []


def test_contraste():
    assert round(diseno.contraste("#000000", "#FFFFFF"), 1) == 21.0
    assert diseno.contraste("#777777", "#888888") < 1.5


def test_limpio():
    assert diseno.revisar(_arbol(".a { color: var(--turno-M); font-size: 12px; }")) == []


def test_color_literal():
    assert any("color literal" in x for x in diseno.revisar(_arbol(".a { color: #fff; }")))
    assert any("color literal" in x for x in diseno.revisar(_arbol(tsx='const c = "rgb(1,2,3)";')))
    assert diseno.revisar(_arbol(tsx='const c = `#${color}`; // comentario')) == []


def test_texto_menor_al_minimo():
    assert any("font-size" in x for x in diseno.revisar(_arbol(".a { font-size: 10px; }")))
    assert any("font-size" in x for x in diseno.revisar(_arbol(".a { font-size: 0.5rem; }")))


def test_contraste_de_una_regla():
    assert any("contraste" in x for x in diseno.revisar(_arbol(".a { color: var(--an-brand-50); background: var(--an-brand-25); }")))
    assert diseno.revisar(_arbol(".a:disabled { color: var(--an-brand-50); background: var(--an-brand-25); }")) == []


def test_tema_de_untitled_admite_colores():
    d = _arbol()
    (d / "web" / "src" / "styles").mkdir()
    (d / "web" / "src" / "styles" / "theme.css").write_text("@theme { --color-white: #FFFFFF; }", encoding="utf-8")
    assert diseno.revisar(d) == []


def test_clases_tailwind():
    assert any("text-[9px]" in x for x in diseno.revisar(_arbol(tsx='const c = "text-[9px]";')))
    assert diseno.revisar(_arbol(tsx='const c = "text-white bg-brand-600 hover:bg-brand-700 text-[12px]";')) == []


def test_sin_tokens():
    d = Path(tempfile.mkdtemp())
    assert any("no existe" in x for x in diseno.revisar(d))


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f()
    print("OK")
