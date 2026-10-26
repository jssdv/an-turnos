"""Crea o actualiza el rol de la aplicación (`an_app`: LOGIN, sin superusuario ni BYPASSRLS) con la clave de AN_APP_CLAVE.
Uso: python -m an.web.roles, conectado (AN_PG_URL) como el rol dueño. Idempotente. Los permisos sobre las tablas los dan las migraciones."""
import os
import sys

import psycopg
from psycopg import sql


def crear_rol_app(conn, clave, rol="an_app"):
    if not clave:
        raise ValueError("falta la clave del rol de la aplicación (AN_APP_CLAVE)")
    ident = sql.Identifier(rol)
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (rol,)).fetchone():
        conn.execute(sql.SQL("CREATE ROLE {}").format(ident))
    conn.execute(sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {}").format(ident, sql.Literal(clave)))
    conn.commit()


if __name__ == "__main__":
    try:
        with psycopg.connect(os.environ["AN_PG_URL"]) as c:
            crear_rol_app(c, os.environ.get("AN_APP_CLAVE", ""))
    except ValueError as e:
        sys.exit(f"Error: {e}")
    print("rol an_app listo")
