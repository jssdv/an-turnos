import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Superficie pública de la API: sin documentación ni esquema OpenAPI servidos (necesita AN_PG_URL)."""
from fixtura_api import entorno


def test_sin_esquema_openapi_ni_documentacion():
    with entorno() as e:
        cli = e.cliente()
        for ruta in ("/openapi.json", "/api/openapi.json", "/docs", "/redoc"):
            assert cli.get(ruta).status_code in (401, 404), ruta
        assert e.app.openapi_url is None
