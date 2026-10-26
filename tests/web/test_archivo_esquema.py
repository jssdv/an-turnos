import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Tabla `archivo` (cuadro mensual de Radiología): RLS por clínica y área, grants mínimos y área `radiologia` sin semilla (necesitan AN_PG_URL). Imprime OK."""
import psycopg

from an.web import admin, conexion
from test_rls import dos_clinicas


def _alcance(pool, clinica, area):
    c = pool.connection()
    conn = c.__enter__()
    conexion.alcance(conn, clinica, area)
    return c, conn


def test_archivo_aislado_por_clinica_y_area():
    with dos_clinicas() as d:
        if d is None:
            return
        su, pool, ids, _ = d
        (ca, aa), (cb, ab) = ids
        otra = su.execute("INSERT INTO area (nombre, tipo, clinica_id) VALUES ('Rad', 'radiologia', %s) RETURNING id", (ca,)).fetchone()[0]
        su.commit()
        with pool.connection() as conn:
            conexion.alcance(conn, ca, aa)
            conn.execute("INSERT INTO archivo (nombre, contenido) VALUES ('c.xlsx', %s)", (b"x",))
            assert conn.execute("SELECT count(*) AS n FROM archivo").fetchone()["n"] == 1
        for clinica, area in ((cb, ab), (ca, otra)):
            with pool.connection() as conn:
                conexion.alcance(conn, clinica, area)
                assert conn.execute("SELECT count(*) AS n FROM archivo").fetchone()["n"] == 0
        with pool.connection() as conn:
            conexion.alcance(conn, ca, aa)
            for sentencia in ("UPDATE archivo SET nombre = 'z'", "TRUNCATE archivo"):
                try:
                    conn.execute(sentencia)
                except psycopg.errors.InsufficientPrivilege:
                    conn.rollback()
                    continue
                raise AssertionError(sentencia)


def test_crear_area_radiologia_sin_semilla():
    with dos_clinicas() as d:
        if d is None:
            return
        su, _, ids, _ = d
        area = admin.crear_area(su, ids[0][0], "Radiología", "radiologia")
        for tabla in ("turno", "puesto", "parametro", "tarifa"):
            assert su.execute(f"SELECT count(*) FROM {tabla} WHERE area_id = %s", (area,)).fetchone()[0] == 0, tabla  # sql-ok: nombres fijos de la prueba
