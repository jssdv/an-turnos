import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del registro de cambios de turno (permutas, cambios de servicio, ajustes). Imprime OK."""
import tempfile
from datetime import date

from an.esterilizacion import db


def test_esquema_v6():
    bd = db.BD()
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 6
    cols = [r["name"] for r in bd.c.execute("PRAGMA table_info(cambio_turno)")]
    assert cols == ["id", "periodo", "servicio", "tipo", "registrado_en", "usuario", "colab_a", "colab_b",
                    "celdas", "motivo", "excepcion", "anulado_en", "anulado_por"]


def test_migra_v5_a_v6():
    ruta = tempfile.mkdtemp() + "/t.db"
    bd = db.BD(ruta)
    bd.c.execute("DROP TABLE cambio_turno")
    bd.c.execute("PRAGMA user_version = 5")
    bd.guardar_cuadro("2026-10-01/2026-10-31", {(1, date(2026, 10, 5)): "M"})
    bd.c.commit()
    bd.c.close()
    bd = db.BD(ruta)
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 6
    assert bd.asignaciones("2026-10-01/2026-10-31") == {(1, date(2026, 10, 5)): "M"}
    assert bd.c.execute("SELECT count(*) FROM cambio_turno").fetchone()[0] == 0
    assert bd.ruta == ruta


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
