"""Pool de conexiones PostgreSQL y alcance RLS por petición (app.clinica / app.area)."""
import contextlib
import os

import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool

from an.turnos.pg import FILAS, Conexion


def abrir_pool(url=None, rol=None):
    """Pool sobre AN_PG_URL. En producción la URL ya entra como `an_app`; con `rol` (desarrollo y pruebas) se hace SET ROLE al abrir."""
    rol = rol or os.environ.get("AN_ROL")

    def configurar(conn):
        if rol:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(rol)))
        conn.commit()

    return ConnectionPool(url or os.environ["AN_PG_URL"], kwargs={"row_factory": FILAS}, configure=configurar, min_size=2, max_size=10, timeout=10, open=True)


def alcance(conn, clinica_id, area_id=None):
    """Fija la clínica (y el área) de la transacción actual; sin esto las tablas con RLS fallan en vez de devolver filas."""
    conn.execute("SELECT set_config('app.clinica', %s, true)", (str(clinica_id),))
    if area_id is not None:
        conn.execute("SELECT set_config('app.area', %s, true)", (str(area_id),))


@contextlib.contextmanager
def transaccion(pool, clinica_id, area_id=None):
    """Una transacción con alcance. Devuelve un `Conexion` cuyo commit() no hace nada: confirma este gestor al salir."""
    with pool.connection() as conn:
        alcance(conn, clinica_id, area_id)
        yield Conexion(conn, confirmar=False)
