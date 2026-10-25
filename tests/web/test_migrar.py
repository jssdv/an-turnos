import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de an.web.migrar: base sintética de 3 meses, negativas y verificación (las de destino piden AN_PG_URL). Imprime OK."""
import contextlib
import io
import tempfile

from an.turnos.db import BD
from an.turnos.dominio import Colaborador
from an.turnos.pg import Conexion
from an.web import admin, migrar

from fixtura_migracion import crear_sintetica

PREFIJO = "Persona"


def _sin_pg():
    if os.environ.get("AN_PG_URL"):
        return False
    try:
        import pytest
        pytest.skip("sin AN_PG_URL")
    except ImportError:
        return True


def origen():
    ruta = tempfile.mkdtemp() + "/turnos.db"
    ids = crear_sintetica(ruta)
    return BD(ruta), ruta, ids


@contextlib.contextmanager
def destino():
    """(conexión psycopg, clínica, área vacía). El área se crea con `crear_area`, o sea con los catálogos base sembrados."""
    from an.web.pruebas import esquema_temporal
    c, limpiar = esquema_temporal()
    clinica = c.conn.execute("SELECT id FROM clinica").fetchone()[0]
    area = admin.crear_area(c.conn, clinica, "Esterilización")
    try:
        yield c.conn, clinica, area
    finally:
        limpiar()


def test_cifras_iguales_y_una_celda_alterada_se_nota():
    bd, ruta, ids = origen()
    a = migrar.cifras(bd)
    assert migrar.diferencias(a, migrar.cifras(bd)) == []
    assert a["filas"]["colaborador"] == 6 and a["filas"]["asignacion"] == 1104 and a["filas"]["periodo"] == 3
    assert a["filas"]["cambio_turno"] == 4 and a["filas"]["solicitud"] == 3 and a["filas"]["novedad"] == 3
    assert a["filas"]["periodo_estado"] == 2 and a["filas"]["banco_mov"] == 2 and a["filas"]["cierre"] == 10
    assert a["ids"]["colaborador"] == [1, 7, 25]  # 1,2,4,5,6,7: el hueco del 3 se conserva
    assert a["cambios"]["2026-10-01/2026-10-31"] == {"permuta": [1, 0], "servicio": [1, 0], "ajuste": [2, 1]}
    bd.set_celda("2026-10-01/2026-10-31", ids[0], __import__("datetime").date(2026, 10, 20), "N")
    dif = migrar.diferencias(a, migrar.cifras(bd))
    assert "celdas/2026-10-01/2026-10-31|cambios" in dif and not any(PREFIJO in d for d in dif), dif


def test_migra_conserva_ids_y_las_cifras_coinciden():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    with destino() as (conn, clinica, area):
        copiadas = migrar.migrar(bd, conn, clinica, area)
        assert copiadas["asignacion"] == 1104 and copiadas["periodo"] == 3 and copiadas["cierre"] == 10
        assert migrar.verificar(bd, conn, clinica, area) == []
        from an.web import conexion
        conexion.alcance(conn, clinica, area)
        assert [r[0] for r in conn.execute("SELECT id FROM colaborador ORDER BY id")] == [1, 2, 4, 5, 6, 7]
        assert [r[0] for r in conn.execute("SELECT clave FROM periodo WHERE cerrado_en IS NOT NULL ORDER BY clave")] == [
            "2026-08-01/2026-08-31", "2026-09-01/2026-09-30"]
        nuevo = BD.postgres(Conexion(conn, confirmar=False)).guardar_colaborador(Colaborador(None, "Nueva"))
        assert nuevo == 8  # la identidad siguió al máximo migrado
        conn.rollback()


def test_se_niega_si_el_area_ya_tiene_datos_y_no_escribe():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    with destino() as (conn, clinica, area):
        migrar.migrar(bd, conn, clinica, area)
        try:
            migrar.migrar(bd, conn, clinica, area)
        except migrar.ErrorMigracion as e:
            assert "ya tiene datos" in str(e)
        else:
            raise AssertionError("debía negarse")
        assert migrar.verificar(bd, conn, clinica, area) == []  # sigue igual que el origen


def test_area_ajena_o_inexistente():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    with destino() as (conn, clinica, area):
        for c, a in ((clinica, 99999), (99999, area)):
            try:
                migrar.migrar(bd, conn, c, a)
            except migrar.ErrorMigracion as e:
                assert "no existe" in str(e)
            else:
                raise AssertionError("debía negarse")


def test_dos_areas_de_la_misma_clinica_no_se_tocan():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    with destino() as (conn, clinica, area):
        otra = admin.crear_area(conn, clinica, "Otra")
        migrar.migrar(bd, conn, clinica, area)
        from an.web import conexion
        conexion.alcance(conn, clinica, otra)
        assert conn.execute("SELECT count(*) FROM asignacion WHERE area_id = %s", (otra,)).fetchone()[0] == 0
        assert conn.execute("SELECT count(*) FROM turno WHERE area_id = %s", (otra,)).fetchone()[0] == 4  # su catálogo sembrado sigue
        conn.rollback()
        try:  # los ids ya están en uso por la otra área: se niega sin escribir nada
            migrar.migrar(bd, conn, clinica, otra)
        except migrar.ErrorMigracion as e:
            assert "otra área" in str(e)
        else:
            raise AssertionError("debía negarse")
        conexion.alcance(conn, clinica, otra)
        assert conn.execute("SELECT count(*) FROM colaborador WHERE area_id = %s", (otra,)).fetchone()[0] == 0
        conn.rollback()
        assert migrar.verificar(bd, conn, clinica, area) == []


def test_clave_de_periodo_invalida():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    bd.c.execute("UPDATE asignacion SET mes='2026-10' WHERE mes='2026-10-01/2026-10-31'")
    with destino() as (conn, clinica, area):
        try:
            migrar.migrar(bd, conn, clinica, area)
        except migrar.ErrorMigracion as e:
            assert "«2026-10»" in str(e)
        else:
            raise AssertionError("debía negarse")


def test_una_diferencia_revierte_y_sale_con_codigo_1():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    with destino() as (conn, clinica, area):
        def alterar(c):
            c.execute("UPDATE asignacion SET turno = 'N' WHERE mes = '2026-10-01/2026-10-31' AND version = 'cambios' "
                      "AND colab_id = 1 AND fecha = '2026-10-20'")
        try:
            migrar.migrar(bd, conn, clinica, area, antes_de_verificar=alterar)
        except migrar.ErrorMigracion as e:
            assert "celdas/2026-10-01/2026-10-31|cambios" in str(e) and PREFIJO not in str(e)
        else:
            raise AssertionError("debía fallar")
        from an.web import conexion
        conexion.alcance(conn, clinica, area)
        assert conn.execute("SELECT count(*) FROM asignacion WHERE area_id = %s", (area,)).fetchone()[0] == 0  # revertido
        conn.rollback()


def test_main_codigos_de_salida():
    if _sin_pg():
        return
    bd, ruta, ids = origen()
    bd.cerrar()
    with destino() as (conn, clinica, area):
        args = [ruta, "--clinica", str(clinica), "--area", str(area)]
        err = io.StringIO()
        with contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(err):
            assert migrar.main(args, conn=conn) == 0
            assert migrar.main(args + ["--solo-verificar"], conn=conn) == 0
            assert migrar.main(args, conn=conn) == 1  # ya tiene datos
        assert "asignacion: 1104" in out.getvalue() and "ya tiene datos" in err.getvalue()
        from an.web import conexion
        conexion.alcance(conn, clinica, area)
        conn.execute("UPDATE asignacion SET turno = 'N' WHERE mes = '2026-10-01/2026-10-31' AND version = 'cambios' AND colab_id = 1 "
                     "AND fecha = '2026-10-20'")
        conn.commit()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert migrar.main(args + ["--solo-verificar"], conn=conn) == 1
        assert "celdas/2026-10-01/2026-10-31|cambios" in err.getvalue() and PREFIJO not in err.getvalue()
        assert migrar.main([ruta + ".no", "--clinica", "1", "--area", "1"], conn=conn) == 1


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
