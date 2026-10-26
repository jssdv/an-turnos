import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""IP real detrás de Caddy: uvicorn (--proxy-headers --forwarded-allow-ips) confía en X-Forwarded-For solo si viene del proxy (necesita AN_PG_URL)."""
from fastapi.testclient import TestClient
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from fixtura_api import CLAVE, ORIGEN, entorno

CADDY = "172.29.8.2"  # la IP fija de Caddy en docker-compose.prod.yml


def _fallar_ingreso(e, desde, forwarded):
    app = ProxyHeadersMiddleware(e.app, trusted_hosts=CADDY)
    cli = TestClient(app, base_url=ORIGEN, client=(desde, 50000), raise_server_exceptions=False)
    r = cli.post("/api/auth/entrar", json={"correo": "editor@a.co", "clave": CLAVE + "x"},
                 headers={"Origin": ORIGEN, "X-Forwarded-For": forwarded})
    assert r.status_code == 401, r.text


def test_ip_del_cliente_viene_de_caddy():
    with entorno() as e:
        _fallar_ingreso(e, CADDY, "203.0.113.9")
        assert e.su.execute("SELECT ip FROM intento_login").fetchall()[-1][0] == "203.0.113.9"
        assert e.su.execute("SELECT ip FROM auditoria ORDER BY id DESC").fetchone()[0] == "203.0.113.9"


def test_ip_falsificada_desde_otro_origen_se_ignora():
    with entorno() as e:
        _fallar_ingreso(e, "198.51.100.7", "203.0.113.9")
        assert e.su.execute("SELECT ip FROM intento_login").fetchall()[-1][0] == "198.51.100.7"
        assert e.su.execute("SELECT ip FROM auditoria ORDER BY id DESC").fetchone()[0] == "198.51.100.7"


if __name__ == "__main__":
    test_ip_del_cliente_viene_de_caddy()
    test_ip_falsificada_desde_otro_origen_se_ignora()
    print("OK")
