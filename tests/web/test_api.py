import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de la API FastAPI (necesitan AN_PG_URL). Imprime OK."""
from fixtura_api import CLAVE_PERIODO, ORIGEN, entorno


def test_sin_cookie_da_401():
    with entorno() as e:
        if e is None:
            return
        assert e.cliente().get("/api/areas").status_code == 401


def test_entrar_pone_cookie_httponly_secure_lax():
    with entorno() as e:
        if e is None:
            return
        r = e.entrar(e.cliente(), "lector@a.co")
        cookie = r.headers["set-cookie"].lower()
        assert r.status_code == 200 and "an_sid=" in cookie and "httponly" in cookie and "secure" in cookie and "samesite=lax" in cookie
        assert e.entrar(e.cliente(), "lector@a.co").status_code == 200
        assert e.cliente().post("/api/auth/entrar", json={"correo": "lector@a.co", "clave": "mala"}, headers={"Origin": ORIGEN}).status_code == 401


def test_cuadro_igual_a_bd_asignaciones():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        pid = cli.get(f"/api/areas/{e.ar['A']}/periodos").json()[0]["id"]
        celdas = cli.get(f"/api/areas/{e.ar['A']}/periodos/{pid}/cuadro").json()["celdas"]
        assert [(c["colab_id"], c["fecha"], c["turno"]) for c in celdas] == [
            (e.colab["A"], "2026-10-05", "M"), (e.colab["A"], "2026-10-06", "T"), (e.colab["A"], "2026-10-07", "L")]
        for ruta in ("alertas", "puestos", "horas"):
            assert cli.get(f"/api/areas/{e.ar['A']}/periodos/{pid}/{ruta}").status_code == 200, ruta
        assert cli.get(f"/api/areas/{e.ar['A']}/analiticas?desde=2026-10-01&hasta=2026-10-31").status_code == 200
        for ruta in ("turnos", "puestos", "colaboradores", "novedades", "solicitudes", "parametros", "tarifas"):
            assert cli.get(f"/api/areas/{e.ar['A']}/{ruta}").status_code == 200, ruta


def test_ver_no_escribe_y_editar_si():
    with entorno() as e:
        if e is None:
            return
        lector, editor = e.cliente(), e.cliente()
        e.entrar(lector, "lector@a.co")
        e.entrar(editor, "editor@a.co")
        ruta = f"/api/areas/{e.ar['A']}/ping"
        assert lector.post(ruta, headers={"Origin": ORIGEN}).status_code == 403
        assert editor.post(ruta, headers={"Origin": ORIGEN}).json() == {"ok": 1}
        assert editor.post(f"/api/areas/{e.ar['B']}/ping", headers={"Origin": ORIGEN}).status_code == 404  # área de otra clínica


def test_escritura_con_origin_ajeno_da_403():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        ruta = f"/api/areas/{e.ar['A']}/ping"
        assert cli.post(ruta, headers={"Origin": "https://malo.example"}).status_code == 403
        assert cli.post(ruta).status_code == 403  # sin Origin tampoco


def test_debe_cambiar_bloquea_todo_salvo_cambiar_clave():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "nuevo@a.co")
        assert cli.get("/api/areas").status_code == 403
        assert cli.get("/api/auth/yo").json()["debe_cambiar"] is True
        assert cli.post("/api/auth/cambiar-clave", json={"actual": "clave-larga-1", "nueva": "otra-clave-larga"}, headers={"Origin": ORIGEN}).status_code == 200
        assert cli.get("/api/areas").status_code == 200


def test_cabeceras_de_seguridad_y_error_generico():
    with entorno() as e:
        if e is None:
            return
        r = e.cliente().get("/api/boom")
        assert r.status_code == 500 and "secreto" not in r.text and r.json()["id"] == r.headers["x-request-id"]
        h = e.cliente().get("/api/areas").headers
        assert "frame-ancestors 'none'" in h["content-security-policy"] and h["x-content-type-options"] == "nosniff"
        grande = e.cliente().post("/api/auth/entrar", content=b"x" * 1_100_000, headers={"Origin": ORIGEN, "content-type": "application/json"})
        assert grande.status_code == 413


def test_cada_peticion_autenticada_deja_fila_en_auditoria():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        cli.get(f"/api/areas/{e.ar['A']}/periodos?x=secreto")
        filas = e.su.execute("SELECT metodo, ruta, codigo, evento FROM auditoria ORDER BY id").fetchall()
        assert ("GET", f"/api/areas/{e.ar['A']}/periodos", 200, None) in [tuple(f) for f in filas]
        assert not any("secreto" in f[1] for f in filas) and any(f[3] == "ingreso" for f in filas)


def test_cerrar_sesion_invalida_la_cookie():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        galleta = cli.cookies.get("an_sid")
        assert cli.post("/api/auth/salir", headers={"Origin": ORIGEN}).status_code == 200
        otro = e.cliente()
        otro.cookies.set("an_sid", galleta, domain="testserver.local")
        assert otro.get("/api/areas").status_code == 401


def test_la_conexion_de_la_peticion_se_libera_antes_de_auditar():
    import time
    with entorno(pool_max=1) as e:  # con una sola conexión, si la petición la retiene la auditoría espera y se pierde
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        t = time.time()
        assert cli.get(f"/api/areas/{e.ar['A']}/periodos").status_code == 200
        assert time.time() - t < 5
        filas = e.su.execute("SELECT ruta FROM auditoria WHERE metodo = 'GET'").fetchall()
        assert [f[0] for f in filas] == [f"/api/areas/{e.ar['A']}/periodos"]


def test_origen_configurado_detras_de_un_proxy():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        ruta = f"/api/areas/{e.ar['A']}/ping"
        os.environ["AN_ORIGEN"] = "https://app.clinica.co"
        try:
            assert cli.post(ruta, headers={"Origin": "https://app.clinica.co"}).status_code == 200
            assert cli.post(ruta, headers={"Origin": ORIGEN}).status_code == 403
        finally:
            del os.environ["AN_ORIGEN"]


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
