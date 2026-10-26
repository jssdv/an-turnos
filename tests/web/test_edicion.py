import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de la API de edición del cuadro (necesitan AN_PG_URL). Imprime OK."""
from fixtura_api import ORIGEN, entorno

H = {"Origin": ORIGEN}


def sesion(e, correo):
    cli = e.cliente()
    e.entrar(cli, correo)
    return cli


def periodo(e, n="A"):
    return e.su.execute("SELECT id FROM periodo WHERE area_id = %s ORDER BY id", (e.ar[n],)).fetchone()[0]


def test_cuadro_trae_revision_y_fijo():
    with entorno() as e:
        if e is None:
            return
        e.su.execute("UPDATE asignacion SET fijo = 1 WHERE fecha = '2026-10-06' AND area_id = %s", (e.ar["A"],))
        e.su.commit()
        cli = sesion(e, "lector@a.co")
        r = cli.get(f"/api/areas/{e.ar['A']}/periodos/{periodo(e)}/cuadro").json()
        assert r["revision"] == 0
        assert [(c["fecha"], c["fijo"]) for c in r["celdas"]] == [("2026-10-05", False), ("2026-10-06", True), ("2026-10-07", False)]
