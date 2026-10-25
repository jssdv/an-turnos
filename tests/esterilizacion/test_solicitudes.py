import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de las solicitudes personales (datos, solver como deseo blando, evaluación). Imprime OK."""
import tempfile
from datetime import date

from an.esterilizacion import db
from an.esterilizacion.dominio import Colaborador, Solicitud


def test_esquema_v7():
    bd = db.BD()
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 7
    cols = [r["name"] for r in bd.c.execute("PRAGMA table_info(solicitud)")]
    assert cols == ["id", "servicio", "colab_id", "tipo", "desde", "hasta", "turno", "prioridad", "nota", "registrado_en", "usuario"]


def test_migra_v6_a_v7():
    ruta = tempfile.mkdtemp() + "/t.db"
    bd = db.BD(ruta)
    bd.c.execute("DROP TABLE solicitud")
    bd.c.execute("PRAGMA user_version = 6")
    bd.c.commit()
    bd.c.close()
    bd = db.BD(ruta)
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 7
    assert bd.c.execute("SELECT count(*) FROM solicitud").fetchone()[0] == 0


def test_crud():
    bd = db.BD()
    pid = bd.guardar_colaborador(Colaborador(0, "Ana"))
    s = Solicitud(pid, "quiero", date(2026, 10, 14), date(2026, 10, 16), "T", "alta", "cita")
    bd.guardar_solicitud(s, "coord")
    assert s.id and bd.solicitudes() == [s]
    assert bd.contexto(2026).solicitudes == [s]
    assert bd.borrar_colaborador(pid) == "desactivado"
    bd.borrar_solicitud(s.id)
    assert bd.solicitudes() == []


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
