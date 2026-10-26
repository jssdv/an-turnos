import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de usuarios y permisos para el administrador de la clínica, y de las analíticas completas (necesitan AN_PG_URL). Imprime OK."""
from fixtura_api import CLAVE, ORIGEN, entorno
from test_edicion import sesion

H = {"Origin": ORIGEN}


def test_solo_el_admin_gestiona_usuarios():
    with entorno() as e:
        if e is None:
            return
        for correo in ("editor@a.co", "lector@a.co"):
            cli = sesion(e, correo)
            assert cli.get("/api/usuarios").status_code == 403
            assert cli.post("/api/usuarios", headers=H, json=dict(correo="x@a.co", nombre="X")).status_code == 403
        assert e.cliente().get("/api/usuarios").status_code == 401
        admin = sesion(e, "admin@a.co")
        r = admin.get("/api/usuarios").json()
        assert sorted(u["correo"] for u in r) == ["admin@a.co", "editor@a.co", "lector@a.co", "nuevo@a.co"]  # nada de la clínica B
        editor = [u for u in r if u["correo"] == "editor@a.co"][0]
        assert editor["permisos"] == [dict(area_id=e.ar["A"], permiso="editar")]


def test_crear_usuario_y_primer_ingreso():
    with entorno() as e:
        if e is None:
            return
        admin = sesion(e, "admin@a.co")
        assert admin.post("/api/usuarios", headers=H, json=dict(correo="mal", nombre="X")).status_code == 422
        r = admin.post("/api/usuarios", headers=H, json=dict(correo="Nuevo2@A.co", nombre="Nuevo Dos"))
        assert r.status_code == 201
        temporal = r.json()["clave_temporal"]
        assert admin.post("/api/usuarios", headers=H, json=dict(correo="nuevo2@a.co", nombre="Otra vez")).status_code == 409
        cli = e.cliente()
        r = cli.post("/api/auth/entrar", json={"correo": "nuevo2@a.co", "clave": temporal}, headers=H)
        assert r.status_code == 200 and r.json()["usuario"]["debe_cambiar"] is True
        aud = e.su.execute("SELECT count(*) FROM auditoria WHERE evento = 'usuario_creado'").fetchone()[0]
        assert aud == 1
        assert not e.su.execute("SELECT 1 FROM auditoria WHERE ruta LIKE %s", (f"%{temporal}%",)).fetchone()


def test_permisos_un_solo_editor_y_reemplazo():
    with entorno() as e:
        if e is None:
            return
        admin = sesion(e, "admin@a.co")
        ruta = f"/api/usuarios/{e.us['lector@a.co']}/areas/{e.ar['A']}"
        r = admin.put(ruta, headers=H, json={"permiso": "editar"})
        assert r.status_code == 409 and "ya tiene un usuario que edita" in r.json()["detalle"]
        assert e.su.execute("SELECT permiso FROM usuario_area WHERE usuario_id = %s", (e.us["editor@a.co"],)).fetchone()[0] == "editar"
        assert admin.put(ruta + "?reemplazar=true", headers=H, json={"permiso": "editar"}).status_code == 200
        permisos = dict(e.su.execute("SELECT usuario_id, permiso FROM usuario_area WHERE area_id = %s", (e.ar["A"],)).fetchall())
        assert permisos == {e.us["lector@a.co"]: "editar", e.us["editor@a.co"]: "ver", e.us["nuevo@a.co"]: "ver"}
        assert admin.put(ruta, headers=H, json={"permiso": None}).status_code == 200
        assert admin.put(ruta, headers=H, json={"permiso": None}).status_code == 409  # ya no tenía
        assert admin.put(ruta, headers=H, json={"permiso": "dueño"}).status_code == 422
        assert admin.put(f"/api/usuarios/{e.us['editor@b.co']}/areas/{e.ar['A']}", headers=H, json={"permiso": "ver"}).status_code == 404  # otra clínica
        assert admin.put(f"/api/usuarios/{e.us['lector@a.co']}/areas/{e.ar['B']}", headers=H, json={"permiso": "ver"}).status_code == 404


def test_desactivar_y_restablecer_cierran_sesiones():
    with entorno() as e:
        if e is None:
            return
        admin, lector = sesion(e, "admin@a.co"), sesion(e, "lector@a.co")
        assert lector.get("/api/areas").status_code == 200
        assert admin.post(f"/api/usuarios/{e.us['admin@a.co']}/desactivar", headers=H).status_code == 409  # a sí mismo no
        r = admin.post(f"/api/usuarios/{e.us['lector@a.co']}/clave", headers=H)
        assert r.status_code == 200
        assert lector.get("/api/areas").status_code == 401  # sesión cerrada
        assert e.cliente().post("/api/auth/entrar", json={"correo": "lector@a.co", "clave": CLAVE}, headers=H).status_code == 401  # la clave vieja ya no sirve
        nueva = e.cliente().post("/api/auth/entrar", json={"correo": "lector@a.co", "clave": r.json()["clave_temporal"]}, headers=H)
        assert nueva.status_code == 200 and nueva.json()["usuario"]["debe_cambiar"] is True
        assert admin.post(f"/api/usuarios/{e.us['lector@a.co']}/desactivar", headers=H).status_code == 200
        assert e.cliente().post("/api/auth/entrar", json={"correo": "lector@a.co", "clave": r.json()["clave_temporal"]}, headers=H).status_code == 401
        assert admin.post(f"/api/usuarios/{e.us['editor@b.co']}/desactivar", headers=H).status_code == 404
        assert admin.post("/api/usuarios/99999/clave", headers=H).status_code == 404


def test_analiticas_completas():
    with entorno() as e:
        if e is None:
            return
        r = sesion(e, "lector@a.co").get(f"/api/areas/{e.ar['A']}/analiticas?desde=2026-10-01&hasta=2026-10-31")
        assert r.status_code == 200, r.text
        assert set(r.json()) == {"ausentismo", "cobertura", "recargos", "simultaneos", "cambios", "horas_extra", "equidad", "banco"}
        assert r.json()["equidad"]["dispersion"] == {"noches": 0, "domingos": 0, "festivos": 0}


if __name__ == "__main__":
    import inspect
    for n, f in list(globals().items()):
        if n.startswith("test_") and inspect.isfunction(f):
            f()
    print("OK")
