import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del alcance RLS (an/web/conexion.py) y de checks/rls.py (necesitan AN_PG_URL). Imprime OK."""
import contextlib
import io
import uuid

import psycopg

from an.web import conexion, esquema
from checks import rls

URL = os.environ.get("AN_PG_URL")


@contextlib.contextmanager
def dos_clinicas():
    """Esquema desechable con dos clínicas (una área y datos cada una); pool conectado como el rol an_app."""
    if not URL:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            yield None
            return
    nombre = "t_" + uuid.uuid4().hex[:10]
    su = psycopg.connect(URL)
    su.execute(f'CREATE SCHEMA "{nombre}"')
    su.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(su)
    ids = []
    for n in ("A", "B"):
        c = su.execute("INSERT INTO clinica (nombre) VALUES (%s) RETURNING id", (n,)).fetchone()[0]
        a = su.execute("INSERT INTO area (nombre, clinica_id) VALUES ('Servicio', %s) RETURNING id", (c,)).fetchone()[0]
        su.execute("INSERT INTO turno VALUES ('M', 'Mañana', 360, 720, 'FFF1C2', '[]', '[]', 0, 1, 1, %s, %s)", (c, a))
        su.execute("INSERT INTO colaborador (nombre, clinica_id, area_id) VALUES (%s, %s, %s)", (f"P-{n}", c, a))
        ids.append((c, a))
    su.commit()
    pool = conexion.abrir_pool(URL + ("&" if "?" in URL else "?") + f"options=-csearch_path%3D{nombre}", rol="an_app")
    try:
        yield su, pool, ids, nombre
    finally:
        pool.close()
        su.rollback()
        su.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        su.commit()
        su.close()


def test_sin_alcance_falla():
    with dos_clinicas() as d:
        if d is None:
            return
        _, pool, _, _ = d
        with pool.connection() as c:
            try:
                c.execute("select * from turno")
            except psycopg.Error:
                return
        raise AssertionError("una consulta sin alcance no debe devolver filas")


def test_clinica_a_no_ve_filas_de_b():
    with dos_clinicas() as d:
        if d is None:
            return
        su, pool, ((ca, aa), (cb, ab)), nombre = d
        tablas = [r[0] for r in su.execute(
            "select c.relname from pg_class c join pg_namespace n on n.oid=c.relnamespace where n.nspname=%s and c.relkind='r' and exists "
            "(select 1 from pg_attribute a where a.attrelid=c.oid and a.attname='clinica_id' and not a.attisdropped)", (nombre,))]
        assert "turno" in tablas and "colaborador" in tablas and len(tablas) >= 20
        with conexion.transaccion(pool, ca, aa) as c:
            for t in tablas:
                assert c.execute(f"select count(*) from {t} where clinica_id = ?", (cb,)).fetchone()[0] == 0, t
            assert c.execute("select count(*) from turno").fetchone()[0] == 1
            assert c.execute("select nombre from colaborador").fetchone()[0] == "P-A"
        # misma clínica, otra área: tampoco se ve
        with conexion.transaccion(pool, ca, ab) as c:
            assert c.execute("select count(*) from turno").fetchone()[0] == 0


def test_escribir_en_otra_clinica_se_rechaza():
    with dos_clinicas() as d:
        if d is None:
            return
        _, pool, ((ca, aa), (cb, ab)), _ = d
        try:
            with conexion.transaccion(pool, ca, aa) as c:
                c.execute("INSERT INTO colaborador (nombre, clinica_id, area_id) VALUES ('X', ?, ?)", (cb, ab))
        except psycopg.Error:
            return
        raise AssertionError("insertó en otra clínica")


def test_checks_rls():
    with dos_clinicas() as d:
        if d is None:
            return
        su, _, _, nombre = d
        assert rls.main(["--esquema", nombre]) == 0
        su.execute("CREATE TABLE sin_rls (x int, clinica_id bigint)")
        su.commit()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert rls.main(["--esquema", nombre]) == 1
        assert "sin_rls" in err.getvalue()


def test_el_pool_se_niega_a_abrir_con_un_rol_que_se_salta_rls():
    if not URL:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            return
    try:
        conexion.abrir_pool(URL)  # AN_PG_URL entra como superusuario y no se pidió rol: FORCE RLS no aplicaría
    except RuntimeError as e:
        assert "RLS" in str(e)
        return
    raise AssertionError("abrió un pool que se salta RLS")


def test_el_pool_limpia_el_alcance_al_devolver_la_conexion():
    with dos_clinicas() as d:
        if d is None:
            return
        _, pool, _, _ = d
        with pool.connection() as c:
            c.execute("select set_config('app.clinica', '1', false)")  # alcance de sesión: solo un error de programación lo dejaría
        with pool.connection() as c1, pool.connection() as c2:
            for c in (c1, c2):
                assert c.execute("select current_setting('app.clinica', true)").fetchone()[0] in (None, "")


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
