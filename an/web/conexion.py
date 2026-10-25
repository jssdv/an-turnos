"""Pool de conexiones PostgreSQL y alcance RLS por petición (app.clinica / app.area)."""
import contextlib
import os

import psycopg
from psycopg import sql
from psycopg_pool import ConnectionPool

from an.turnos.pg import FILAS, Conexion


def abrir_pool(url=None, rol=None, max_size=10):
    """Pool sobre AN_PG_URL. En producción la URL ya entra como `an_app`; con `rol` (desarrollo y pruebas) se hace SET ROLE al abrir.
    Se niega a abrir si el rol efectivo se salta RLS (superusuario o BYPASSRLS): sin aislamiento por clínica no se sirve nada."""
    rol = rol or os.environ.get("AN_ROL")

    def configurar(conn):
        if rol:
            conn.execute(sql.SQL("SET ROLE {}").format(sql.Identifier(rol)))
        conn.commit()

    def limpiar(conn):  # el alcance de una petición no debe pasar a la siguiente aunque alguien lo fije a nivel de sesión
        conn.execute("RESET app.clinica")
        conn.execute("RESET app.area")
        conn.commit()

    pool = ConnectionPool(url or os.environ["AN_PG_URL"], kwargs={"row_factory": FILAS}, configure=configurar, reset=limpiar,
                          min_size=min(2, max_size), max_size=max_size, timeout=10, open=True)
    with pool.connection() as c:
        if c.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user").fetchone()[0]:
            pool.close()
            raise RuntimeError("el rol de la aplicación se salta RLS (superusuario o BYPASSRLS); conecta como an_app")
    return pool


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
