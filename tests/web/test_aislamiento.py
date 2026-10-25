import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Aislamiento entre clínicas y entre áreas a través de la API (necesitan AN_PG_URL). Imprime OK."""
from an.turnos.db import BD
from an.web import conexion
from fixtura_api import entorno

LECTURAS_AREA = ["turnos", "puestos", "colaboradores", "novedades", "solicitudes", "parametros", "tarifas", "periodos"]
LECTURAS_PERIODO = ["cuadro", "alertas", "puestos", "horas"]


def test_cada_ruta_con_ids_de_otra_clinica_da_404():
    with entorno() as e:
        if e is None:
            return
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        area_b = e.ar["B"]
        periodo_a = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0]
        periodo_b = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (area_b,)).fetchone()[0]
        for r in LECTURAS_AREA:
            assert cli.get(f"/api/areas/{area_b}/{r}").status_code == 404, r
        assert cli.get(f"/api/areas/{area_b}/analiticas?desde=2026-10-01&hasta=2026-10-31").status_code == 404
        for r in LECTURAS_PERIODO:
            assert cli.get(f"/api/areas/{area_b}/periodos/{periodo_b}/{r}").status_code == 404, r
            # el periodo de B pedido bajo el área de A: RLS lo oculta
            assert cli.get(f"/api/areas/{e.ar['A']}/periodos/{periodo_b}/{r}").status_code == 404, r
            assert cli.get(f"/api/areas/{e.ar['A']}/periodos/{periodo_a}/{r}").status_code == 200, r
        assert [a["id"] for a in cli.get("/api/areas").json()] == [e.ar["A"]]


def test_otra_area_de_la_misma_clinica_sin_permiso_da_404():
    with entorno() as e:
        if e is None:
            return
        otra = e.su.execute("INSERT INTO area (nombre, clinica_id) VALUES ('Otra', %s) RETURNING id", (e.cl["A"],)).fetchone()[0]
        e.su.commit()
        cli = e.cliente()
        e.entrar(cli, "lector@a.co")
        assert cli.get(f"/api/areas/{otra}/turnos").status_code == 404
        assert [a["id"] for a in cli.get("/api/areas").json()] == [e.ar["A"]]
        admin = e.cliente()
        e.entrar(admin, "admin@a.co")
        assert {a["id"] for a in admin.get("/api/areas").json()} == {e.ar["A"], otra}
        assert admin.get(f"/api/areas/{otra}/turnos").status_code == 200


def test_bd_con_alcance_de_a_no_lee_filas_de_b():
    with entorno() as e:
        if e is None:
            return
        with conexion.transaccion(e.pool, e.cl["A"], e.ar["A"]) as c:
            bd = BD.postgres(c)
            assert [p.nombre for p in bd.colaboradores(False)] == ["P-A"]
            assert set(bd.periodos()) == {"2026-10-01/2026-10-31"} and len(bd.turnos(False)) == 4
            assert all(c.execute(f"select count(*) from {t} where clinica_id = ?", (e.cl["B"],)).fetchone()[0] == 0  # sql-ok: nombres de tabla fijos
                       for t in ("turno", "colaborador", "asignacion", "puesto", "demanda", "parametro", "periodo"))


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
