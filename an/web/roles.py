"""Crea o actualiza el rol de la aplicación (`an_app`: LOGIN, sin superusuario ni BYPASSRLS) con la clave de AN_APP_CLAVE.
Uso: python -m an.web.roles, conectado (AN_PG_URL) como el rol dueño. Idempotente. Los permisos sobre las tablas los dan las migraciones."""
import os
import sys

import psycopg
from psycopg import sql


def crear_rol_app(conn, clave, rol="an_app"):
    if not clave:
        raise ValueError("falta la clave del rol de la aplicación (AN_APP_CLAVE)")
    if clave.startswith("CAMBIAR_"):
        raise ValueError("la clave sigue siendo el valor de ejemplo de .env.example (CAMBIAR_…): genera una con `openssl rand -hex 24`")
    ident = sql.Identifier(rol)
    if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (rol,)).fetchone():
        conn.execute(sql.SQL("CREATE ROLE {}").format(ident))
    conn.execute(sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE PASSWORD {}").format(ident, sql.Literal(clave)))
    conn.commit()


if __name__ == "__main__":
    try:
        with psycopg.connect(os.environ["AN_PG_URL"]) as c:
            if os.environ.get("PGPASSWORD", "").startswith("CAMBIAR_"):  # la clave del rol dueño (AN_ADMIN_CLAVE)
                raise ValueError("AN_ADMIN_CLAVE sigue siendo el valor de ejemplo (CAMBIAR_…)")
            crear_rol_app(c, os.environ.get("AN_APP_CLAVE", ""))
    except ValueError as e:
        sys.exit(f"Error: {e}")
    print("rol an_app listo")
