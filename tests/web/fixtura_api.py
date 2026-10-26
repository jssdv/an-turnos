"""Fixture compartida de las pruebas de la API: esquema desechable con dos clínicas, usuarios, un periodo con cuadro y la app lista."""
import contextlib
import os
import uuid
from datetime import date

import psycopg
from fastapi import Depends
from fastapi.testclient import TestClient

from an.turnos.db import BD
from an.turnos.dominio import Colaborador
from an.turnos.pg import FILAS, Conexion
from an.web import auth, conexion, esquema
from an.web.app import crear_app
from an.web.deps import contexto_area

URL = os.environ.get("AN_PG_URL")
ORIGEN = "https://testserver"
CLAVE = "clave-larga-1"
CLAVE_PERIODO = "2026-10-01/2026-10-31"


@contextlib.contextmanager
def entorno(pool_max=10):
    """Rinde un objeto con: cliente (TestClient https), ids (clinicas/areas/usuarios) y su.conn (superusuario, sin RLS) para sembrar."""
    if not URL:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            yield None
            return
    nombre = "t_" + uuid.uuid4().hex[:10]
    su = psycopg.connect(URL, row_factory=FILAS)
    su.execute(f'CREATE SCHEMA "{nombre}"')
    su.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(su)
    e = type("Entorno", (), {})()
    e.su, e.cl, e.ar, e.us = su, {}, {}, {}
    for n in ("A", "B"):
        e.cl[n] = su.execute("INSERT INTO clinica (nombre) VALUES (%s) RETURNING id", (n,)).fetchone()[0]
        e.ar[n] = su.execute("INSERT INTO area (nombre, clinica_id) VALUES ('Servicio', %s) RETURNING id", (e.cl[n],)).fetchone()[0]
        su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl[n]), str(e.ar[n])))
        bd = BD.postgres(Conexion(su))
        bd.sembrar()
        p = Colaborador(0, f"P-{n}")
        bd.guardar_colaborador(p)
        cid = p.id
        su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s)", (CLAVE_PERIODO, e.cl[n], e.ar[n]))
        for d, t in ((5, "M"), (6, "T"), (7, "L")):
            su.execute("INSERT INTO asignacion VALUES (%s, 'cambios', %s, %s, %s, 'solver', 0, %s, %s)",
                       (CLAVE_PERIODO, cid, date(2026, 10, d).isoformat(), t, e.cl[n], e.ar[n]))
    e.colab = {n: su.execute("SELECT id FROM colaborador WHERE clinica_id=%s", (e.cl[n],)).fetchone()[0] for n in e.cl}
    su.execute("RESET app.clinica")
    su.execute("RESET app.area")
    for correo, perm, debe in (("editor@a.co", "editar", False), ("lector@a.co", "ver", False), ("nuevo@a.co", "ver", True), ("admin@a.co", None, False),
                               ("editor@b.co", "editar", False)):
        n = "B" if correo.endswith("b.co") else "A"
        uid = su.execute("INSERT INTO usuario (correo, nombre, hash_clave, es_admin, debe_cambiar, clinica_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                         (correo, correo, auth.hash_clave(CLAVE), correo.startswith("admin"), debe, e.cl[n])).fetchone()[0]
        e.us[correo] = uid
        if perm:
            su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s)", (uid, e.ar[n], perm, e.cl[n]))
    su.commit()
    sep = "&" if "?" in URL else "?"
    pool = conexion.abrir_pool(f"{URL}{sep}options=-csearch_path%3D{nombre}", rol="an_app", max_size=pool_max)
    app = crear_app(pool)

    @app.post("/api/areas/{area}/ping")
    def ping(ctx=Depends(contexto_area, scope="function")):
        return {"ok": 1}

    @app.get("/api/boom")
    def boom():
        raise RuntimeError("secreto interno")

    e.app, e.pool = app, pool
    e.cliente = lambda: TestClient(app, base_url=ORIGEN, raise_server_exceptions=False)
    e.entrar = lambda cli, correo: cli.post("/api/auth/entrar", json={"correo": correo, "clave": CLAVE}, headers={"Origin": ORIGEN})
    try:
        yield e
    finally:
        pool.close()
        su.rollback()
        su.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        su.commit()
        su.close()


def segunda_area(e, nombre="Cirugía"):
    """Crea con `admin.crear_area` un segundo servicio de turnos en la clínica A (catálogo sembrado) con una persona y un periodo de 3 celdas.
    Deja el id en `e.ar["A2"]` y el de su colaboradora en `e.colab["A2"]`."""
    from an.web import admin
    a2 = admin.crear_area(e.su, e.cl["A"], nombre)
    e.ar["A2"] = a2
    e.su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl["A"]), str(a2)))
    p = Colaborador(0, "P-A2")
    BD.postgres(Conexion(e.su)).guardar_colaborador(p)
    e.colab["A2"] = p.id
    e.su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s)", (CLAVE_PERIODO, e.cl["A"], a2))
    for d, t in ((5, "M"), (6, "T"), (7, "L")):
        e.su.execute("INSERT INTO asignacion VALUES (%s, 'cambios', %s, %s, %s, 'solver', 0, %s, %s)",
                     (CLAVE_PERIODO, p.id, date(2026, 10, d).isoformat(), t, e.cl["A"], a2))
    e.su.commit()
    e.su.execute("RESET app.clinica")
    e.su.execute("RESET app.area")
    e.su.commit()
    return a2
