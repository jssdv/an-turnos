import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))
"""La app de escritorio se retiró (etiqueta qt-final): el núcleo y la web no cargan Qt. Imprime OK."""
from pathlib import Path


def test_nucleo_y_web_no_cargan_qt():
    import an.turnos.db, an.turnos.solver, an.turnos.exportar, an.turnos.cambios  # noqa: F401
    import an.radiologia.generar_semana, an.radiologia.analisis  # noqa: F401
    import an.web.app, an.web.trabajador  # noqa: F401
    assert not any(m.startswith("PySide6") for m in sys.modules)


def test_no_queda_la_app_qt():
    raiz = Path(__file__).resolve().parents[1]
    assert not (raiz / "an" / "__main__.py").exists()
    assert sorted(p.name for p in (raiz / "an" / "nucleo").glob("*.py")) == ["__init__.py", "xlsx.py"]


if __name__ == "__main__":
    test_nucleo_y_web_no_cargan_qt()
    test_no_queda_la_app_qt()
    print("OK")
