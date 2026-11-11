import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Varias áreas por clínica: un archivo por área (aislamiento), gestión de áreas por el administrador y la migración 014. Imprime OK."""
import sqlite3
import tempfile
from pathlib import Path

from an.web import admin, esquema, sqlite_pg
from an.web.trabajador import Trabajador
from fixtura_api import ORIGEN, entorno, segunda_area
from test_edicion import sesion

H = {"Origin": ORIGEN}


def _archivo(e, area):
    return Path(e.su._con.ruta).with_name(f"area_{area}.db")


def test_crear_areas_sembradas_y_aisladas():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "admin@a.co")
        assert sesion(e, "editor@a.co").post("/api/areas", json={"nombre": "X"}, headers=H).status_code == 403
        r = cli.post("/api/areas", json={"nombre": "Esterilización 2"}, headers=H)
        assert r.status_code == 201, r.text
        b = r.json()["id"]
        assert _archivo(e, b).exists()
        assert cli.post("/api/areas", json={"nombre": "Esterilización 2"}, headers=H).status_code == 409
        for a in (e.ar["A"], b):  # las dos sembradas de cero
            assert len(cli.get(f"/api/areas/{a}/turnos").json()) > 3 and len(cli.get(f"/api/areas/{a}/puestos").json()) == 6
        assert cli.put(f"/api/areas/{b}/parametros", json={"limite_permutas": 7}, headers=H).status_code == 200
        assert cli.post(f"/api/areas/{b}/colaboradores", json={"nombre": "Solo en B"}, headers=H).status_code == 201
        assert cli.post(f"/api/areas/{b}/periodos", json={"inicio": "2026-11-01", "fin": "2026-11-30"}, headers=H).status_code == 201
        assert cli.get(f"/api/areas/{b}/parametros").json()["limite_permutas"] == "7"
        assert cli.get(f"/api/areas/{e.ar['A']}/parametros").json()["limite_permutas"] == "2"
        assert [c["nombre"] for c in cli.get(f"/api/areas/{e.ar['A']}/colaboradores").json()] == ["P-A"]
        assert [p["clave"] for p in cli.get(f"/api/areas/{b}/periodos").json()] == ["2026-11-01/2026-11-30"]
        assert [p["clave"] for p in cli.get(f"/api/areas/{e.ar['A']}/periodos").json()] == ["2026-10-01/2026-10-31"]
        # el periodo de B tiene id 1 en su archivo, igual que el de A: los trabajos se distinguen por área
        pb = cli.get(f"/api/areas/{b}/periodos").json()[0]["id"]
        t = cli.post(f"/api/areas/{b}/periodos/{pb}/generar", json={"modo": "cero", "tiempo": 1}, headers={**H, "If-Match": "0"})
        assert t.status_code == 202, t.text
        assert e.su.execute("SELECT area_id FROM trabajo WHERE id = %s", (t.json()["id"],)).fetchone()[0] == b
        assert cli.get(f"/api/areas/{e.ar['A']}/trabajos").json() == []
        assert [x["id"] for x in cli.get(f"/api/areas/{b}/trabajos").json()] == [t.json()["id"]]
        assert Trabajador(e.pool).correr_uno() is True
        e.en_area(b)
        assert e.su.execute("SELECT count(*) FROM asignacion").fetchone()[0] > 0
        e.en_area(e.ar["A"])
        assert e.su.execute("SELECT count(*) FROM asignacion").fetchone()[0] == 3  # el cuadro de A no se tocó


def test_renombrar_y_borrar_area():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "admin@a.co")
        b = segunda_area(e, "B")
        assert cli.put(f"/api/areas/{b}", json={"nombre": "Turnos"}, headers=H).status_code == 409  # ya existe
        assert cli.put(f"/api/areas/{b}", json={"nombre": "B2"}, headers=H).status_code == 200
        assert cli.put("/api/areas/999", json={"nombre": "Z"}, headers=H).status_code == 404
        assert cli.put(f"/api/usuarios/{e.us['editor@a.co']}/areas/{b}", json={"permiso": "ver"}, headers=H).status_code == 200
        pb = cli.post(f"/api/areas/{b}/periodos", json={"inicio": "2026-11-01", "fin": "2026-11-30"}, headers=H).json()["id"]
        tid = cli.post(f"/api/areas/{b}/periodos/{pb}/generar", json={"modo": "cero", "tiempo": 1}, headers={**H, "If-Match": "0"}).json()["id"]
        assert cli.request("DELETE", f"/api/areas/{b}", json={"nombre": "B2"}, headers=H).status_code == 409  # generándose
        e.su.execute("UPDATE trabajo SET estado = 'cancelado' WHERE id = %s", (tid,))
        assert cli.request("DELETE", f"/api/areas/{b}", json={"nombre": "otro"}, headers=H).status_code == 409  # nombre errado
        assert cli.request("DELETE", f"/api/areas/{b}", json={"nombre": "B2"}, headers=H).status_code == 204
        assert not _archivo(e, b).exists()
        assert cli.get("/api/areas").json() == [dict(id=e.ar["A"], nombre="Turnos", tipo="turnos", permiso="editar")]
        assert e.su.execute("SELECT count(*) FROM usuario_area WHERE area_id = %s", (b,)).fetchone()[0] == 0
        assert e.su.execute("SELECT count(*) FROM trabajo WHERE area_id = %s", (b,)).fetchone()[0] == 0
        assert cli.get(f"/api/areas/{b}/turnos").status_code == 404


def test_admin_edita_sin_fila_de_permiso():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "admin@a.co")
        assert cli.get("/api/areas").json()[0]["permiso"] == "editar"
        assert cli.post(f"/api/areas/{e.ar['A']}/colaboradores", json={"nombre": "Nueva"}, headers=H).status_code == 201
        assert cli.put(f"/api/usuarios/{e.us['admin@a.co']}/areas/{e.ar['A']}", json={"permiso": "editar"}, headers=H).status_code == 409
        assert sesion(e, "lector@a.co").post(f"/api/areas/{e.ar['A']}/colaboradores", json={"nombre": "No"}, headers=H).status_code == 403


def test_migracion_014_separa_las_areas():
    d = Path(tempfile.mkdtemp())
    ruta = d / "an.db"
    raw = sqlite3.connect(ruta)
    raw.executescript(esquema.BASE_SQLITE.read_text(encoding="utf-8") + (esquema.MIGRACIONES_SQLITE / "013_puesto_fijo_mitad.sql").read_text(encoding="utf-8")
                      + "PRAGMA user_version = 13;")
    raw.executescript("""
        INSERT INTO clinica (nombre) VALUES ('C');
        INSERT INTO area (nombre) VALUES ('Turnos');
        INSERT INTO usuario (id, correo, nombre, hash_clave, es_admin) VALUES (1, 'a@a.co', 'A', 'h', 1), (2, 'e@a.co', 'E', 'h', 0);
        INSERT INTO usuario_area (usuario_id, area_id, permiso) VALUES (1, 1, 'editar'), (2, 1, 'ver');
        INSERT INTO periodo (id, clave) VALUES (7, '2026-10-01/2026-10-31');
        INSERT INTO colaborador (nombre, tipo, horas_sem, pct, permitidos, puesto_fijo, estudio, activo) VALUES ('P', 'colab', 42, 1, '', NULL, NULL, 1);
        INSERT INTO asignacion VALUES ('2026-10-01/2026-10-31', 'cambios', 1, '2026-10-05', 'M', 'solver', 0, 1, 1);
        INSERT INTO parametro (clave, valor) VALUES ('limite_permutas', '5');
        INSERT INTO trabajo (periodo_id, tipo, revision_base, estado) VALUES (7, 'generar', 0, 'listo');
    """)
    raw.commit()
    raw.close()
    con = sqlite_pg.abrir(str(ruta))
    assert esquema.aplicar_sqlite(con) == 14
    con.close()
    raw = sqlite3.connect(ruta)
    tablas = {r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    assert "periodo" not in tablas and "trabajo" in tablas and "usuario" in tablas
    assert raw.execute("SELECT periodo_id, estado, area_id FROM trabajo").fetchall() == [(7, "listo", 1)]
    assert raw.execute("SELECT usuario_id FROM usuario_area").fetchall() == [(2,)]  # el administrador ya no necesita fila
    assert "REFERENCES periodo" not in raw.execute("SELECT sql FROM sqlite_master WHERE name = 'trabajo'").fetchone()[0]
    raw.close()
    a = sqlite3.connect(d / "area_1.db")
    assert a.execute("PRAGMA user_version").fetchone()[0] == 1
    assert a.execute("SELECT id, clave FROM periodo").fetchall() == [(7, "2026-10-01/2026-10-31")]
    assert a.execute("SELECT valor FROM parametro WHERE clave = 'limite_permutas'").fetchone() == ("5",)
    assert a.execute("SELECT count(*) FROM asignacion").fetchone()[0] == 1 and a.execute("SELECT nombre FROM colaborador").fetchone() == ("P",)
    a.close()
    con = sqlite_pg.abrir(str(ruta))  # abrir de nuevo no migra nada más y el área sigue en pie
    assert esquema.aplicar_sqlite(con) == 14
    con.close()


if __name__ == "__main__":
    for prueba in [test_crear_areas_sembradas_y_aisladas, test_renombrar_y_borrar_area, test_admin_edita_sin_fila_de_permiso, test_migracion_014_separa_las_areas]:
        prueba()
    print("OK")
