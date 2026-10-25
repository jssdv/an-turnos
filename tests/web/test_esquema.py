import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del esquema PostgreSQL y su aplicador (necesitan AN_PG_URL). Imprime OK."""
import contextlib
import uuid

import psycopg

from an.web import esquema


@contextlib.contextmanager
def conn_nueva():
    url = os.environ.get("AN_PG_URL")
    if not url:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            yield None
            return
    c = psycopg.connect(url)
    nombre = "t_" + uuid.uuid4().hex[:10]
    c.execute(f'CREATE SCHEMA "{nombre}"')
    c.execute(f'SET search_path TO "{nombre}"')
    c.commit()
    try:
        yield c
    finally:
        c.rollback()
        c.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        c.commit()
        c.close()


def sembrar(c):
    c.execute("INSERT INTO clinica (nombre) VALUES ('A')")
    c.execute("INSERT INTO area (nombre, clinica_id) SELECT 'Uno', id FROM clinica")
    c.execute("INSERT INTO area (nombre, clinica_id) SELECT 'Dos', id FROM clinica")
    return [r[0] for r in c.execute("SELECT id FROM area ORDER BY id")], c.execute("SELECT id FROM clinica").fetchone()[0]


def test_aplicar_es_idempotente():
    with conn_nueva() as c:
        if c is None:
            return
        assert esquema.aplicar(c) == sorted(p.name for p in esquema.MIGRACIONES.glob("[0-9][0-9][0-9]_*.sql"))
        assert esquema.aplicar(c) == []


def test_toda_tabla_con_clinica_id_tiene_rls_forzado():
    with conn_nueva() as c:
        if c is None:
            return
        esquema.aplicar(c)
        filas = c.execute("select c.relname, c.relrowsecurity, c.relforcerowsecurity from pg_class c join pg_namespace n on n.oid=c.relnamespace "
                          "where n.nspname=current_schema() and c.relkind='r' and exists "
                          "(select 1 from pg_attribute a where a.attrelid=c.oid and a.attname='clinica_id' and not a.attisdropped)").fetchall()
        assert len(filas) >= 20 and all(r[1] and r[2] for r in filas), filas


def test_dos_areas_comparten_codigo_de_turno():
    with conn_nueva() as c:
        if c is None:
            return
        esquema.aplicar(c)
        (a1, a2), clin = sembrar(c)
        for a in (a1, a2):
            c.execute("SELECT set_config('app.clinica', %s, true), set_config('app.area', %s, true)", (str(clin), str(a)))
            c.execute("INSERT INTO turno VALUES ('M', 'Mañana', 360, 720, 'FFF1C2', '[]', '[]', 0, 1, 1)")
        assert c.execute("select count(*) from turno where codigo='M'").fetchone()[0] == 2


def test_un_solo_editor_por_area():
    with conn_nueva() as c:
        if c is None:
            return
        esquema.aplicar(c)
        (a1, _), clin = sembrar(c)
        c.execute("SELECT set_config('app.clinica', %s, true)", (str(clin),))
        for i in range(3):
            c.execute("INSERT INTO usuario (correo, nombre, hash_clave) VALUES (%s, 'n', 'h')", (f"u{i}@x.co",))
        uids = [r[0] for r in c.execute("SELECT id FROM usuario ORDER BY id")]
        c.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso) VALUES (%s, %s, 'editar')", (uids[0], a1))
        c.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso) VALUES (%s, %s, 'ver')", (uids[1], a1))
        try:
            c.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso) VALUES (%s, %s, 'editar')", (uids[2], a1))
        except psycopg.errors.UniqueViolation:
            return
        raise AssertionError("permitió dos editores en la misma área")


def test_la_aplicacion_no_toca_esquema_version():
    with conn_nueva() as c:
        if c is None:
            return
        esquema.aplicar(c)
        c.execute("SET ROLE an_app")
        try:
            c.execute("SELECT * FROM esquema_version")
        except psycopg.errors.InsufficientPrivilege:
            c.rollback()
            return
        finally:
            c.execute("RESET ROLE")
        raise AssertionError("an_app lee esquema_version")


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
