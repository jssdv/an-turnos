import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de los exportes en Excel (necesitan AN_PG_URL). Imprime OK."""
import psycopg
from fixtura_api import entorno

from an.web import conexion


def test_tabla_exporte_rls():
    with entorno() as e:
        if e is None:
            return
        pid = e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0]
        e.su.execute("INSERT INTO exporte (clinica_id, area_id, periodo_id, tipo, numero, nombre_archivo, contenido) VALUES (%s, %s, %s, 'cuadro', 1, 'x.xlsx', %s)",
                     (e.cl["A"], e.ar["A"], pid, b"abc"))
        e.su.commit()

        def contar(n, sql="SELECT count(*) FROM exporte"):
            with e.pool.connection() as conn:
                conexion.alcance(conn, e.cl[n], e.ar[n])
                f = conn.execute(sql).fetchone()
                return f[0] if f else None
        assert contar("A") == 1 and contar("B") == 0
        for sql in ("UPDATE exporte SET numero = 2", "DELETE FROM exporte"):
            try:
                contar("A", sql)
                assert False, sql
            except psycopg.errors.InsufficientPrivilege:
                pass


if __name__ == "__main__":
    import inspect
    for n, f in list(globals().items()):
        if n.startswith("test_") and inspect.isfunction(f):
            f()
    print("OK")
