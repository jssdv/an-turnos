"""Fixture compartida de las pruebas de la API: una base SQLite desechable (una clínica, un área «Turnos») con usuarios, un periodo con cuadro y la app lista."""
import contextlib
import shutil
import tempfile
from datetime import date
from pathlib import Path

from fastapi import Depends
from fastapi.testclient import TestClient

from an.turnos.db import BD
from an.turnos.dominio import Colaborador
from an.turnos.puente import Conexion
from an.web import admin, auth, conexion, esquema, sqlite_pg
from an.web.app import crear_app
from an.web.deps import contexto_area

ORIGEN = "https://testserver"
CLAVE = "clave-larga-1"
CLAVE_PERIODO = "2026-10-01/2026-10-31"
USUARIOS = (("editor@a.co", "editar", False), ("lector@a.co", "ver", False), ("nuevo@a.co", "ver", True), ("admin@a.co", None, False))


class Filas:
    """Resultado ya leído de una sentencia: fetchone, fetchall e iteración."""

    def __init__(self, filas):
        self._f = list(filas)

    def fetchone(self):
        return self._f.pop(0) if self._f else None

    def fetchall(self):
        f, self._f = self._f, []
        return f

    def __iter__(self):
        return iter(self.fetchall())


class Directa:
    """Conexión de siembra y lectura: confirma tras cada sentencia, para no retener el candado de escritura que cada cursor de SQLite abre."""

    def __init__(self, con):
        self._con = con

    def execute(self, sql, params=()):
        if sql.lstrip().upper().startswith(("RESET", "SET ", "SELECT SET_CONFIG")):
            return Filas([])  # alcance de RLS: no existe en SQLite
        r = self._con.execute(sql, params)
        try:
            filas = r.fetchall()
        except Exception:
            filas = []
        self._con.commit()
        return Filas(filas)

    def __getattr__(self, nombre):
        return getattr(self._con, nombre)


@contextlib.contextmanager
def entorno(pool_max=10):
    """Rinde un objeto con: cliente (TestClient https), ids (cl/ar/us/colab, solo la clínica y el área «A») y su (conexión directa) para sembrar."""
    carpeta = Path(tempfile.mkdtemp())
    ruta = str(carpeta / "an.db")
    su = sqlite_pg.abrir(ruta)
    esquema.aplicar_sqlite(su)
    su.commit()
    e = type("Entorno", (), {})()
    e.su, e.cl, e.ar, e.us = su, {}, {}, {}
    e.cl["A"] = admin.crear_clinica(su, "A")
    su.commit()
    e.ar["A"] = admin.crear_area(su, e.cl["A"], "Turnos")
    bd = BD.web(Conexion(su))
    p = Colaborador(0, "P-A")
    bd.guardar_colaborador(p)
    su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s)", (CLAVE_PERIODO, e.cl["A"], e.ar["A"]))
    for d, t in ((5, "M"), (6, "T"), (7, "L")):
        su.execute("INSERT INTO asignacion VALUES (%s, 'cambios', %s, %s, %s, 'solver', 0, %s, %s)",
                   (CLAVE_PERIODO, p.id, date(2026, 10, d).isoformat(), t, e.cl["A"], e.ar["A"]))
    e.colab = {"A": p.id}
    for correo, perm, debe in USUARIOS:
        uid = su.execute("INSERT INTO usuario (correo, nombre, hash_clave, es_admin, debe_cambiar, clinica_id) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                         (correo, correo, auth.hash_clave(CLAVE), correo.startswith("admin"), debe, e.cl["A"])).fetchone()[0]
        e.us[correo] = uid
        if perm:
            su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s)", (uid, e.ar["A"], perm, e.cl["A"]))
    su.commit()
    e.su = Directa(su)
    pool = conexion.abrir_pool("sqlite:" + ruta)
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
        su.close()
        shutil.rmtree(carpeta, ignore_errors=True)
