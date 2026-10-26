import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""an.web.roles: el rol de la aplicación entra con clave, sin superusuario ni BYPASSRLS, y repetirlo cambia la clave (necesita AN_PG_URL como superusuario)."""
import uuid

import psycopg
import pytest

URL = os.environ.get("AN_PG_URL")


def test_crear_rol_app_idempotente_y_sin_privilegios():
    if not URL:
        pytest.skip("sin AN_PG_URL")
    from an.web.roles import crear_rol_app
    rol = "t_rol_" + uuid.uuid4().hex[:8]
    su = psycopg.connect(URL)
    try:
        crear_rol_app(su, "primera-clave-1", rol)
        crear_rol_app(su, "segunda-clave-2", rol)
        assert su.execute("SELECT rolcanlogin, rolsuper, rolbypassrls FROM pg_roles WHERE rolname = %s", (rol,)).fetchone() == (True, False, False)
        base = psycopg.conninfo.conninfo_to_dict(URL)
        for clave, ok in (("segunda-clave-2", True), ("primera-clave-1", False)):
            try:
                psycopg.connect(**{**base, "user": rol, "password": clave}).close()
                assert ok
            except psycopg.OperationalError:
                assert not ok
        with pytest.raises(ValueError):
            crear_rol_app(su, "", rol)
    finally:
        su.rollback()
        su.execute(f'DROP ROLE IF EXISTS "{rol}"')  # sql-ok: nombre generado aquí
        su.commit()
        su.close()
