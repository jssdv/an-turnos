import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Rutas generar / trabajos / cancelar (necesitan AN_PG_URL). Imprime OK al correr como script con pytest."""
import subprocess

from fixtura_api import ORIGEN, entorno

H = {"Origin": ORIGEN}


def ruta_generar(e, n="A"):
    pid = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (e.ar[n],)).fetchone()[0]
    return f"/api/areas/{e.ar[n]}/periodos/{pid}/generar"


def sesion(e, correo):
    cli = e.cliente()
    e.entrar(cli, correo)
    return cli


def test_generar_encola_y_responde_202():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        r = cli.post(ruta_generar(e), headers={**H, "If-Match": "0"})
        assert r.status_code == 202, r.text
        tid = r.json()["id"]
        g = cli.get(f"/api/trabajos/{tid}")
        assert g.status_code == 200 and g.json()["estado"] == "en_cola" and g.json()["tipo"] == "generar"
        f = e.su.execute("SELECT params, revision_base, creado_por FROM trabajo WHERE id = %s", (tid,)).fetchone()
        assert f["params"] == {"modo": "cero", "lunes": None, "tiempo": 20, "semilla": 0}
        assert f["revision_base"] == 0 and f["creado_por"] == e.us["editor@a.co"]


def test_if_match_ausente_da_428_vencido_409_y_con_comillas_vale():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        assert cli.post(ruta_generar(e), headers=H).status_code == 428
        assert cli.post(ruta_generar(e), headers={**H, "If-Match": "abc"}).status_code == 422
        r = cli.post(ruta_generar(e), headers={**H, "If-Match": "7"})
        assert r.status_code == 409 and r.json()["detalle"]["revision"] == 0
        assert cli.post(ruta_generar(e), headers={**H, "If-Match": '"0"'}).status_code == 202


def test_segundo_generar_de_la_clinica_da_409():
    with entorno() as e:
        if e is None:
            return
        cli, otro = sesion(e, "editor@a.co"), sesion(e, "editor@b.co")
        h = {**H, "If-Match": "0"}
        tid = cli.post(ruta_generar(e), headers=h).json()["id"]
        r = cli.post(ruta_generar(e), headers=h)
        assert r.status_code == 409 and "generándose" in r.json()["detalle"]
        assert otro.post(ruta_generar(e, "B"), headers=h).status_code == 202  # otra clínica
        assert cli.post(f"/api/trabajos/{tid}/cancelar", headers=H).json()["estado"] == "cancelado"
        assert cli.post(ruta_generar(e), headers=h).status_code == 202


def test_semana_exige_lunes_del_periodo():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        h = {**H, "If-Match": "0"}
        assert cli.post(ruta_generar(e), headers=h, json={"modo": "semana"}).status_code == 422
        assert cli.post(ruta_generar(e), headers=h, json={"modo": "semana", "lunes": "2026-10-07"}).status_code == 422
        assert cli.post(ruta_generar(e), headers=h, json={"modo": "semana", "lunes": "2026-11-02"}).status_code == 422
        assert cli.post(ruta_generar(e), headers=h, json={"modo": "semana", "lunes": "2026-10-05", "tiempo": 5, "semilla": 3}).status_code == 202
        assert cli.post(ruta_generar(e), headers=h, json={"tiempo": 0}).status_code == 422


def test_permisos_de_trabajos():
    with entorno() as e:
        if e is None:
            return
        editor, lector, ajeno = sesion(e, "editor@a.co"), sesion(e, "lector@a.co"), sesion(e, "editor@b.co")
        assert lector.post(ruta_generar(e), headers={**H, "If-Match": "0"}).status_code == 403
        tid = editor.post(ruta_generar(e), headers={**H, "If-Match": "0"}).json()["id"]
        assert e.cliente().get(f"/api/trabajos/{tid}").status_code == 401
        assert lector.get(f"/api/trabajos/{tid}").status_code == 200
        assert lector.post(f"/api/trabajos/{tid}/cancelar", headers=H).status_code == 403
        assert ajeno.get(f"/api/trabajos/{tid}").status_code == 404
        assert ajeno.post(f"/api/trabajos/{tid}/cancelar", headers=H).status_code == 404
        e.su.execute("UPDATE trabajo SET estado = 'corriendo' WHERE id = %s", (tid,))
        e.su.commit()
        r = editor.post(f"/api/trabajos/{tid}/cancelar", headers=H)
        assert r.status_code == 200 and r.json()["cancelar"] is True and r.json()["estado"] == "corriendo"
        e.su.execute("UPDATE trabajo SET estado = 'listo' WHERE id = %s", (tid,))
        e.su.commit()
        assert editor.post(f"/api/trabajos/{tid}/cancelar", headers=H).status_code == 409
        assert editor.get("/api/trabajos/999999").status_code == 404


def test_de_punta_a_punta_la_api_ve_el_trabajo_terminado():
    from an.web.trabajador import Trabajador
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        tid = cli.post(ruta_generar(e), headers={**H, "If-Match": "0"}, json={"tiempo": 5}).json()["id"]
        assert Trabajador(e.pool).correr_uno()
        t = cli.get(f"/api/trabajos/{tid}").json()
        assert t["estado"] == "listo" and t["terminado"] and "faltan" in t["resultado"], t
        pid = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0]
        assert [p["revision"] for p in cli.get(f"/api/areas/{e.ar['A']}/periodos").json()] == [1]
        assert cli.post(ruta_generar(e), headers={**H, "If-Match": "0"}).status_code == 409  # la revisión ya es 1
        assert cli.post(ruta_generar(e), headers={**H, "If-Match": "1"}).status_code == 202


def test_checks_reglas_acepta_las_rutas():
    raiz = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
    r = subprocess.run([sys.executable, "checks/reglas.py"], cwd=raiz, capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


if __name__ == "__main__":
    print("OK: correr con pytest")
