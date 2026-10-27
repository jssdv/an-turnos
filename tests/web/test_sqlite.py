"""Versión portable: la capa web sobre SQLite (login, áreas, periodo, positional INSERT con defaults). Corre como script: imprime OK."""
import os
import tempfile

from fastapi.testclient import TestClient

from an.web import admin, conexion, entregable, sqlite_pg
from an.web.app import crear_app

O = "https://testserver"


def test_flujo_basico():
    ruta = os.path.join(tempfile.mkdtemp(), "an.db")
    primer = entregable.preparar_base(ruta)
    assert "Clave temporal" in primer and entregable.preparar_base(ruta) is None  # la segunda vez no recrea nada
    clave = primer.split("Clave temporal: ")[1].split("\n")[0]
    con = sqlite_pg.abrir(ruta)
    con.execute("UPDATE usuario SET debe_cambiar = 0")
    con.commit()
    con.close()
    cli = TestClient(crear_app(conexion.abrir_pool("sqlite:" + ruta)), base_url=O)
    H = {"Origin": O}
    assert cli.get("/api/areas").status_code == 401
    assert cli.post("/api/auth/entrar", json={"correo": entregable.CORREO, "clave": clave}, headers=H).status_code == 200
    assert cli.get("/api/areas").json()[0]["nombre"] == "Esterilización"
    assert len(cli.get("/api/areas/1/turnos").json()) > 3  # sembrado con INSERT … VALUES posicional
    assert cli.post("/api/areas/1/colaboradores", json={"nombre": "Ana"}, headers=H).status_code == 201
    p = cli.post("/api/areas/1/periodos", json={"inicio": "2026-11-01", "fin": "2026-11-30"}, headers=H)
    assert p.status_code == 201, p.text


if __name__ == "__main__":
    test_flujo_basico()
    print("OK")
