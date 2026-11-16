import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""«Respaldar ahora» y «Restaurar» (solo el administrador y solo con la app instalada): copian an.db y los archivos de área. Imprime OK."""
import sqlite3
import tempfile
from pathlib import Path

from fixtura_api import ORIGEN, entorno, segunda_area
from test_edicion import periodo, sesion

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


def test_restaurar():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "admin@a.co")
        assert cli.post("/api/respaldos/20261115_120000/restaurar", headers=H).status_code == 404  # sin app instalada
        destino = Path(tempfile.mkdtemp()) / "An-respaldos"
        e.app.state.respaldo = (Path(e.su._con.ruta), destino)
        elegida = cli.post("/api/respaldos", headers=H).json()["nombre"]
        e.su.execute("UPDATE colaborador SET nombre = 'Cambiado'")
        b = segunda_area(e, "B")  # creada después de la copia: su archivo queda donde está
        url = f"/api/respaldos/{elegida}/restaurar"
        assert sesion(e, "editor@a.co").post(url, headers=H).status_code == 403
        for malo in ("20261115_12000", "20991231_235959", "..", "x" + elegida):
            assert cli.post(f"/api/respaldos/{malo}/restaurar", headers=H).status_code == 404, malo
        tid = e.su.execute("INSERT INTO trabajo (periodo_id, tipo, revision_base, estado) VALUES (%s, 'generar', 0, 'corriendo') RETURNING id",
                           (periodo(e),)).fetchone()[0]
        assert cli.post(url, headers=H).status_code == 409
        e.su.execute("DELETE FROM trabajo WHERE id = %s", (tid,))
        r = cli.post(url, headers=H)
        assert r.status_code == 200, r.text
        seguridad = destino / r.json()["nombre"]
        assert seguridad.name != elegida and (destino / elegida).is_dir()
        assert e.su.execute("SELECT nombre FROM colaborador").fetchall() == [("P-A",)]  # volvió el dato de la copia
        copia = sqlite3.connect(seguridad / f"area_{e.ar['A']}.db")
        assert copia.execute("SELECT nombre FROM colaborador").fetchall() == [("Cambiado",)]  # lo de antes quedó en la copia de seguridad
        copia.close()
        assert (seguridad / f"area_{b}.db").exists() and (Path(e.su._con.ruta).with_name(f"area_{b}.db")).exists()
        assert e.su.execute("SELECT 1 FROM auditoria WHERE evento = 'respaldo_restaurado'").fetchone()
        nueva = cli.post("/api/areas", json={"nombre": "C", "tipo": "turnos"}, headers=H)
        assert nueva.status_code == 201 and nueva.json()["id"] > b, nueva.text  # no reusa el id (ni el archivo) del área que no estaba en la copia


if __name__ == "__main__":
    test_respaldar_ahora()
    test_restaurar()
    print("OK")
