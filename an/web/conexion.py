"""Conexiones de la versión portable (una base SQLite, una clínica y un área) y el alcance por petición, que aquí no filtra nada."""
import contextlib
import os

from an.turnos.puente import Conexion

from . import sqlite_pg


def abrir_pool(ruta=None):
    """Pool sobre el archivo SQLite `ruta` (por defecto AN_BASE; se admite el prefijo `sqlite:`)."""
    return sqlite_pg.Pool((ruta or os.environ["AN_BASE"]).removeprefix("sqlite:"))


def alcance(conn, clinica_id, area_id=None):
    """Fija la clínica (y el área) de la transacción; `sqlite_pg` lo ignora porque la base tiene una sola de cada una."""
    conn.execute("SELECT set_config('app.clinica', %s, true)", (str(clinica_id),))
    if area_id is not None:
        conn.execute("SELECT set_config('app.area', %s, true)", (str(area_id),))


@contextlib.contextmanager
def transaccion(pool, clinica_id, area_id=None):
    """Una transacción con alcance. Devuelve un `Conexion` cuyo commit() no hace nada: confirma este gestor al salir."""
    with pool.connection() as conn:
        alcance(conn, clinica_id, area_id)
        yield Conexion(conn, confirmar=False)
