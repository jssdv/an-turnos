import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""El SQL de an/turnos debe valer en SQLite y PostgreSQL: sin construcciones exclusivas de SQLite fuera de las migraciones. Imprime OK."""
import re
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]


def test_sin_construcciones_exclusivas_de_sqlite():
    fuente = "".join(p.read_text(encoding="utf-8") for p in (RAIZ / "an" / "turnos").glob("*.py") if p.name != "paginas.py")
    sin_migraciones = re.sub(r"    def _migrar_a_\d+\(.*?(?=\n    def |\nclass |\Z)", "", fuente, flags=re.S)
    for malo in ("lastrowid", "INSERT OR REPLACE", "INSERT OR IGNORE", "datetime('now')"):
        assert malo not in sin_migraciones, malo


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
