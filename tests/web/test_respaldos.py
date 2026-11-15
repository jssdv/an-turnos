import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""«Respaldar ahora» (solo el administrador y solo con la app instalada): copia an.db y los archivos de área. Imprime OK."""
import sqlite3
import tempfile
from pathlib import Path

from fixtura_api import ORIGEN, entorno
from test_edicion import sesion

H = {"Origin": ORIGEN}


def test_respaldar_ahora():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "admin@a.co")
        assert cli.get("/api/respaldos").json() == {"carpeta": None, "respaldos": []}  # sin app instalada: nada que ofrecer
        assert cli.post("/api/respaldos", headers=H).status_code == 404
        destino = Path(tempfile.mkdtemp()) / "An-respaldos"
        e.app.state.respaldo = (Path(e.su._con.ruta), destino)
        assert sesion(e, "editor@a.co").post("/api/respaldos", headers=H).status_code == 403
        r = cli.post("/api/respaldos", headers=H)
        assert r.status_code == 201, r.text
        hecho = r.json()
        assert hecho["archivos"] == 2 and hecho["bytes"] > 0  # an.db y area_<id>.db
        copia = sqlite3.connect(destino / hecho["nombre"] / f"area_{e.ar['A']}.db")
        assert copia.execute("SELECT nombre FROM colaborador").fetchall() == [("P-A",)]
        copia.close()
        lista = cli.get("/api/respaldos").json()
        assert lista["carpeta"] == str(destino) and [x["nombre"] for x in lista["respaldos"]] == [hecho["nombre"]]


if __name__ == "__main__":
    test_respaldar_ahora()
    print("OK")
