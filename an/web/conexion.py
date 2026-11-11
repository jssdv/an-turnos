"""Conexiones de la versión portable (`an.db` + un archivo por área) y el alcance por petición: adjuntar el archivo del área."""
import contextlib
import os

from an.turnos.puente import Conexion

from . import sqlite_pg


def abrir_pool(ruta=None):
    """Pool sobre el archivo SQLite `ruta` (por defecto AN_BASE; se admite el prefijo `sqlite:`)."""
    return sqlite_pg.Pool(str(ruta or os.environ["AN_BASE"]).removeprefix("sqlite:"))


def alcance(conn, clinica_id, area_id=None):
    """Fija el área de la transacción adjuntando su archivo (una clínica por base: `clinica_id` no filtra nada)."""
    if area_id is not None:
        conn.adjuntar_area(area_id)


@contextlib.contextmanager
def transaccion(pool, clinica_id, area_id=None):
    """Una transacción con alcance. Devuelve un `Conexion` cuyo commit() no hace nada: confirma este gestor al salir."""
    with pool.connection() as conn:
        alcance(conn, clinica_id, area_id)
        yield Conexion(conn, confirmar=False)
