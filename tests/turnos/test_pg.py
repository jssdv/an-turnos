import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del adaptador psycopg (an/turnos/pg.py). Las que usan base piden AN_PG_URL. Imprime OK."""
from an.turnos import pg


def _sin_pg():
    if os.environ.get("AN_PG_URL"):
        return False
    try:
        import pytest
        pytest.skip("sin AN_PG_URL")
    except ImportError:
        return True


def test_traducir():
    assert pg.traducir("SELECT * FROM t WHERE a=? AND b LIKE '50%' AND c='¿?'") == "SELECT * FROM t WHERE a=%s AND b LIKE '50%%' AND c='¿?'"


def test_traducir_construcciones_con_comillas():
    t = pg.traducir
    assert t("SELECT ? -- no es d'él ?\nFROM t WHERE a=?") == "SELECT %s -- no es d'él ?\nFROM t WHERE a=%s"  # comentario de línea
    assert t("SELECT /* d'? */ ?") == "SELECT /* d'? */ %s"
    assert t("SELECT E'it\\'s ?', ?") == "SELECT E'it\\'s ?', %s"  # E'' con \'
    assert t("SELECT 'it''s ?', ?") == "SELECT 'it''s ?', %s"
    assert t("SELECT $$a'?%$$, ?") == "SELECT $$a'?%%$$, %s"
    assert t("SELECT $f$ x ? $$ ' $f$, ?") == "SELECT $f$ x ? $$ ' $f$, %s"
    assert t('SELECT "col?", "o\'x", ?') == 'SELECT "col?", "o\'x", %s'
    assert t('SELECT "a""?", ?') == 'SELECT "a""?", %s'
    assert t("SELECT $1, a % 2, '5%', -- 100%\n?") == "SELECT $1, a %% 2, '5%%', -- 100%%\n%s"


def test_fila_por_indice_y_nombre():
    f = pg.Fila(("a", 2), ("nombre", "n"))
    assert f[0] == "a" and f["n"] == 2 and f["nombre"] == "a" and f.keys() == ["nombre", "n"]


def test_conexion_con_base():
    if _sin_pg():
        return
    c = pg.Conexion.abrir(os.environ["AN_PG_URL"])
    c.execute("CREATE TEMP TABLE t (id int, nombre text)")
    c.executemany("INSERT INTO t VALUES (?,?)", [(1, "a"), (2, "b")])
    r = c.execute("SELECT * FROM t WHERE id=?", (2,)).fetchone()
    assert r["nombre"] == "b" and r[0] == 2
    assert [x["id"] for x in c.execute("SELECT * FROM t ORDER BY id")] == [1, 2]
    assert c.execute("UPDATE t SET nombre='z'").rowcount == 2
    c.rollback()
    assert c.execute("SELECT count(*) FROM pg_tables WHERE tablename='t' AND schemaname LIKE 'pg_temp%'").fetchone()[0] == 0
    c.close()


def test_bd_en_postgres_siembra_y_aisla():
    if _sin_pg():
        return
    os.environ["AN_BD"] = "postgres"
    try:
        from an.turnos import db
        a, b = db.BD(), db.BD()
        try:
            assert a.dialecto == "postgres" and len(a.turnos(False)) == 4 and len(a.catalogo_puestos()) == 6
            a.guardar_colaborador(__import__("an.turnos.dominio", fromlist=["x"]).Colaborador(0, "Ana"))
            assert [c.id for c in a.colaboradores()] == [1] and b.colaboradores() == []
        finally:
            a.cerrar()
            b.cerrar()
    finally:
        del os.environ["AN_BD"]


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
