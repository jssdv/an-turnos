import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Dos áreas de turnos en la misma clínica: permisos por área, generar sin tocar la otra y administración (necesitan AN_PG_URL). Imprime OK."""
import io
import contextlib
from psycopg.types.json import Jsonb

from an.turnos import flujo
from an.turnos.db import BD
from an.turnos.dominio import Colaborador
from an.turnos.pg import Conexion
from an.web import admin, conexion
from an.web.trabajador import Trabajador
from fixtura_api import CLAVE_PERIODO, entorno, segunda_area

SEMANA = "2026-10-05/2026-10-11"


def permisos(cli):
    return {a["id"]: a["permiso"] for a in cli.get("/api/areas").json()}


def ping(cli, area):
    from fixtura_api import ORIGEN
    return cli.post(f"/api/areas/{area}/ping", headers={"Origin": ORIGEN}).status_code


def dar(e, correo, area, permiso):
    admin.dar_permiso(e.su, e.us[correo], area, permiso)


def test_editar_en_una_y_ver_en_otra():
    with entorno() as e:
        if e is None:
            return
        a, a2 = e.ar["A"], segunda_area(e)
        dar(e, "editor@a.co", a2, "ver")
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        assert permisos(cli) == {a: "editar", a2: "ver"}
        assert ping(cli, a2) == 403 and ping(cli, a) == 200
        assert cli.get(f"/api/areas/{a2}/turnos").status_code == 200


def test_editar_en_ambas_y_un_solo_editor_por_area():
    with entorno() as e:
        if e is None:
            return
        a, a2 = e.ar["A"], segunda_area(e)
        dar(e, "editor@a.co", a2, "editar")
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        assert ping(cli, a) == 200 and ping(cli, a2) == 200
        try:
            dar(e, "lector@a.co", a2, "editar")
        except admin.ErrorAdmin as x:
            assert "ya tiene un usuario que edita" in str(x)
        else:
            raise AssertionError("aceptó un segundo editor en la segunda área")
        e.su.rollback()
        assert e.su.execute("SELECT permiso FROM usuario_area WHERE usuario_id = %s AND area_id = %s", (e.us["editor@a.co"], a)).fetchone()[0] == "editar"


def test_sin_permiso_en_la_segunda_no_la_ve():
    with entorno() as e:
        if e is None:
            return
        a, a2 = e.ar["A"], segunda_area(e)
        pid = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (a2,)).fetchone()[0]
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        assert cli.get(f"/api/areas/{a2}/turnos").status_code == 404
        assert cli.get(f"/api/areas/{a2}/periodos/{pid}/cuadro").status_code == 404
        assert ping(cli, a2) == 404
        assert permisos(cli) == {a: "ver"}
        admin_ = e.cliente()
        e.entrar(admin_, "admin@a.co")
        assert permisos(admin_) == {a: "ver", a2: "ver"}
        otra = e.cliente()
        e.entrar(otra, "editor@b.co")  # otra clínica: no ve ni la primera ni la segunda
        assert otra.get(f"/api/areas/{a2}/turnos").status_code == 404 and a2 not in permisos(otra)


def snapshot(e, area):
    q = lambda t: e.su.execute(f"SELECT count(*) FROM {t} WHERE area_id = %s", (area,)).fetchone()[0]  # sql-ok: lista constante en esta prueba
    celdas = e.su.execute("SELECT mes, version, colab_id, fecha, turno FROM asignacion WHERE area_id = %s ORDER BY 1, 2, 3, 4", (area,)).fetchall()
    return [tuple(c) for c in celdas], e.su.execute("SELECT revision FROM periodo WHERE area_id = %s", (area,)).fetchone()[0], \
        {t: q(t) for t in ("colaborador", "turno", "puesto", "asignacion", "novedad")}


def test_generar_en_la_segunda_area_no_toca_la_primera():
    with entorno() as e:
        if e is None:
            return
        a, a2 = e.ar["A"], segunda_area(e)
        e.su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl["A"]), str(a2)))
        bd2 = BD.postgres(Conexion(e.su))
        for i in range(4):
            bd2.guardar_colaborador(Colaborador(0, f"Y{i}"))
        e.su.commit()
        e.su.execute("RESET app.clinica")
        e.su.execute("RESET app.area")
        e.su.commit()
        antes = snapshot(e, a)
        pid = e.su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s) RETURNING id", (SEMANA, e.cl["A"], a2)).fetchone()[0]
        params = {"modo": "cero", "lunes": None, "tiempo": 30, "semilla": 0}
        tid = e.su.execute("INSERT INTO trabajo (periodo_id, tipo, params, revision_base, clinica_id, area_id) VALUES (%s, 'generar', %s, 0, %s, %s) RETURNING id",
                           (pid, Jsonb(params), e.cl["A"], a2)).fetchone()[0]
        e.su.commit()
        previo = os.environ.get("AN_SOLVER_WORKERS")
        os.environ["AN_SOLVER_WORKERS"] = "1"
        try:
            assert Trabajador(e.pool).correr_uno() is True
        finally:
            os.environ.pop("AN_SOLVER_WORKERS", None) if previo is None else os.environ.update(AN_SOLVER_WORKERS=previo)
        e.su.rollback()
        f = e.su.execute("SELECT estado, error FROM trabajo WHERE id = %s", (tid,)).fetchone()
        assert f["estado"] == "listo", f["error"]
        assert e.su.execute("SELECT count(*) FROM asignacion WHERE mes = %s AND area_id = %s", (SEMANA, a2)).fetchone()[0] > 0
        assert e.su.execute("SELECT revision FROM periodo WHERE id = %s", (pid,)).fetchone()[0] == 1
        assert snapshot(e, a) == antes


def test_crear_area_por_cli_y_nombres():
    with entorno() as e:
        if e is None:
            return
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            assert admin.main(["crear-area", "--clinica", str(e.cl["A"]), "--nombre", "Cirugía"], e.su) == 0
        nueva = int(out.getvalue().strip())
        e.su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl["A"]), str(nueva)))
        assert e.su.execute("SELECT count(*) FROM turno WHERE area_id = %s", (nueva,)).fetchone()[0] == 4
        assert e.su.execute("SELECT count(*) FROM puesto WHERE area_id = %s", (nueva,)).fetchone()[0] == 6
        e.su.execute("RESET app.clinica")
        e.su.execute("RESET app.area")
        e.su.commit()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert admin.main(["crear-area", "--clinica", str(e.cl["A"]), "--nombre", "Cirugía"], e.su) == 1
        assert "ya tiene un área con ese nombre" in err.getvalue()
        assert isinstance(admin.crear_area(e.su, e.cl["B"], "Cirugía"), int)  # el mismo nombre en otra clínica sí vale
