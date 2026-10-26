import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de checks/tokens.py: tokens de FigCraft a CSS y su verificación. Imprime OK."""
import contextlib
import io
import tempfile
from pathlib import Path

from checks import tokens

RAIZ = Path(__file__).resolve().parents[2]
FIGCRAFT = RAIZ / "docs" / "diseno" / "An_UI.figcraft"


def test_a_hex():
    assert tokens.a_hex(0.9607843, 0.96862745, 0.98039216, 1.0) == "#F5F7FA"
    assert tokens.a_hex(0, 0, 0, 0.5) == "#00000080"


def test_css_formato():
    assert tokens.css({"brand_600": "#0B7A75"}) == ":root {\n  --an-brand-600: #0B7A75;\n}\n"
    assert tokens.css({"turno_M": "#FFE9A8"}) == ":root {\n  --turno-M: #FFE9A8;\n}\n"


def test_figcraft_solo_marca_y_turnos():
    marca = {f"brand_{n}" for n in (25, 50, 100, 200, 300, 400, 500, 600, 700, 800, 900, 950)}
    assert set(tokens.leer_variables(FIGCRAFT)) == marca | {"turno_M", "turno_T", "turno_C", "turno_NC"}


def test_verificar_falla_si_tokens_css_cambia():
    with tempfile.TemporaryDirectory() as d:
        css = Path(d) / "tokens.css"
        assert tokens.main(["--css", str(css)]) == 0
        assert tokens.main(["--verificar", "--css", str(css)]) == 0
        marca = tokens.leer_variables(FIGCRAFT)["brand_600"]  # el valor vigente, no uno fijo: la paleta cambia en FigCraft
        css.write_text(css.read_text().replace(marca, "#000000"))
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert tokens.main(["--verificar", "--css", str(css)]) == 1
        assert "brand_600" in err.getvalue()
        css.unlink()
        with contextlib.redirect_stderr(io.StringIO()):
            assert tokens.main(["--verificar", "--css", str(css)]) == 1


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
