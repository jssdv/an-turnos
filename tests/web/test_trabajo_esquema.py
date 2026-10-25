import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""La tabla trabajo (cola del solver): índice único por clínica, RLS y funciones del trabajador (necesitan AN_PG_URL). Imprime OK."""
import psycopg
import pytest

from fixtura_api import CLAVE_PERIODO, entorno


def periodo(e, n):
    return e.su.execute("SELECT id FROM periodo WHERE area_id = %s", (e.ar[n],)).fetchone()[0]


def encolar(e, n, estado="en_cola", **extra):
    cols = {"periodo_id": periodo(e, n), "tipo": "generar", "revision_base": 0, "estado": estado, "clinica_id": e.cl[n], "area_id": e.ar[n], **extra}
    return e.su.execute(f"INSERT INTO trabajo ({', '.join(cols)}) VALUES ({', '.join(['%s'] * len(cols))}) RETURNING id", tuple(cols.values())).fetchone()[0]  # sql-ok: columnas fijas del test


def como_app(e, n):
    """Conexión como an_app con el alcance de la clínica `n` (o sin alcance si n es None)."""
    c = e.pool.getconn()
    if n:
        c.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl[n]), str(e.ar[n])))
    return c


def test_indice_unico_por_clinica():
    with entorno() as e:
        if e is None:
            return
        a = encolar(e, "A")
        e.su.commit()
        with pytest.raises(psycopg.errors.UniqueViolation):
            encolar(e, "A")
        e.su.rollback()
        encolar(e, "B")  # otra clínica no choca
        e.su.execute("UPDATE trabajo SET estado = 'listo' WHERE id = %s", (a,))
        encolar(e, "A")
        e.su.commit()


def test_rls_de_trabajo():
    with entorno() as e:
        if e is None:
            return
        encolar(e, "A")
        e.su.commit()
        c = como_app(e, "B")
        try:
            assert c.execute("SELECT count(*) FROM trabajo").fetchone()[0] == 0
            c.rollback()
        finally:
            e.pool.putconn(c)
        c = e.pool.getconn()
        try:
            with pytest.raises(psycopg.Error):
                c.execute("SELECT count(*) FROM trabajo")
            c.rollback()
        finally:
            e.pool.putconn(c)


def test_tomar_trabajo():
    with entorno() as e:
        if e is None:
            return
        a = encolar(e, "A", creado="2026-10-01 10:00+00")
        b = encolar(e, "B", creado="2026-10-01 09:00+00")
        e.su.commit()
        c = como_app(e, None)
        try:
            t1 = c.execute("SELECT * FROM app_tomar_trabajo()").fetchone()
            t2 = c.execute("SELECT * FROM app_tomar_trabajo()").fetchone()
            t3 = c.execute("SELECT * FROM app_tomar_trabajo()").fetchone()
            c.commit()
        finally:
            e.pool.putconn(c)
        assert (t1["id"], t1["clinica_id"], t1["area_id"], t1["tipo"], t1["revision_base"]) == (b, e.cl["B"], e.ar["B"], "generar", 0)
        assert t2["id"] == a and t3 is None
        assert [f[0] for f in e.su.execute("SELECT estado FROM trabajo ORDER BY id")] == ["corriendo", "corriendo"]
        assert e.su.execute("SELECT count(*) FROM trabajo WHERE latido IS NOT NULL").fetchone()[0] == 2


def test_marcar_fallidos():
    with entorno() as e:
        if e is None:
            return
        viejo = encolar(e, "A", "corriendo", latido="2000-01-01 00:00+00")
        nuevo = encolar(e, "B", "corriendo")
        e.su.execute("UPDATE trabajo SET latido = now() WHERE id = %s", (nuevo,))
        e.su.commit()
        c = como_app(e, None)
        try:
            assert c.execute("SELECT app_marcar_fallidos(60)").fetchone()[0] == 1
            c.commit()
        finally:
            e.pool.putconn(c)
        f = e.su.execute("SELECT estado, error, terminado FROM trabajo WHERE id = %s", (viejo,)).fetchone()
        assert f["estado"] == "fallido" and "interrumpi" in f["error"] and f["terminado"] is not None
        assert e.su.execute("SELECT estado FROM trabajo WHERE id = %s", (nuevo,)).fetchone()[0] == "corriendo"


def test_estado_invalido():
    with entorno() as e:
        if e is None:
            return
        with pytest.raises(psycopg.errors.CheckViolation):
            encolar(e, "A", "x")
        e.su.rollback()


if __name__ == "__main__":
    print("OK: correr con pytest")
