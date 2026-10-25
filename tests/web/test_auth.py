import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de an/web/auth.py: contraseñas, sesiones y bloqueo (necesitan AN_PG_URL). Imprime OK."""
import contextlib
import hashlib
import uuid
from datetime import datetime, timedelta, timezone

import psycopg

from an.turnos.pg import FILAS, Conexion
from an.web import auth, esquema

URL = os.environ.get("AN_PG_URL")
CLAVE = "clave-larga-1"


@contextlib.contextmanager
def con_usuario():
    """Esquema desechable con un usuario a@x.co; la conexión de la prueba actúa como el rol an_app (sin saltarse nada)."""
    if not URL:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            yield None
            return
    nombre = "t_" + uuid.uuid4().hex[:10]
    raw = psycopg.connect(URL, row_factory=FILAS)
    raw.execute(f'CREATE SCHEMA "{nombre}"')
    raw.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(raw)
    cl = raw.execute("INSERT INTO clinica (nombre) VALUES ('A') RETURNING id").fetchone()[0]
    raw.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, clinica_id) VALUES ('a@x.co', 'Ana', %s, false, %s)",
                (auth.hash_clave(CLAVE), cl))
    raw.commit()
    raw.execute("SET ROLE an_app")
    raw.commit()
    try:
        yield Conexion(raw)
    finally:
        raw.rollback()
        raw.execute("RESET ROLE")
        raw.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        raw.commit()
        raw.close()


def test_hash_distinto_por_sal_y_verifica():
    h1, h2 = auth.hash_clave(CLAVE), auth.hash_clave(CLAVE)
    assert h1 != h2 and h1.startswith("scrypt$") and auth.verificar_clave(CLAVE, h1) and not auth.verificar_clave("otra", h1)


def test_login_guarda_solo_el_hash_del_token():
    with con_usuario() as c:
        if c is None:
            return
        token, u = auth.iniciar_sesion(c, "A@x.co ", CLAVE, "1.1.1.1")
        assert auth.usuario_de_token(c, token).id == u.id and u.correo == "a@x.co"
        c.conn.execute("RESET ROLE")
        guardado = c.execute("SELECT hash_token FROM sesion").fetchone()[0]
        c.conn.execute("SET ROLE an_app")
        assert guardado == hashlib.sha256(token.encode()).hexdigest() != token
        try:
            c.execute("SELECT * FROM sesion")
        except psycopg.errors.InsufficientPrivilege:
            return
        raise AssertionError("an_app no debe leer sesion directamente")


def test_bloqueo_tras_5_fallos_incluso_con_clave_correcta():
    with con_usuario() as c:
        if c is None:
            return
        for _ in range(5):
            try:
                auth.iniciar_sesion(c, "a@x.co", "mala", "9.9.9.9")
            except auth.ErrorAuth as e:
                assert "credenciales" in str(e)
        try:
            auth.iniciar_sesion(c, "a@x.co", CLAVE, "9.9.9.9")
            raise AssertionError("debía estar bloqueado")
        except auth.ErrorAuth as e:
            assert "bloqueado" in str(e)
        token, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "8.8.8.8")  # otra IP no está bloqueada
        assert token


def test_token_vencido_cerrado_o_inexistente_da_none():
    with con_usuario() as c:
        if c is None:
            return
        ahora = datetime.now(timezone.utc)
        t1, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        assert auth.usuario_de_token(c, t1, ahora + timedelta(minutes=36)) is None  # 35 min sin uso
        t2, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        for i in range(1, 24):  # uso cada 30 min: sigue viva casi hasta las 12 h
            assert auth.usuario_de_token(c, t2, ahora + timedelta(minutes=30 * i)) is not None, i
        assert auth.usuario_de_token(c, t2, ahora + timedelta(hours=12, minutes=1)) is None  # tope absoluto
        t3, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        auth.cerrar_sesion(c, t3)
        assert auth.usuario_de_token(c, t3) is None and auth.usuario_de_token(c, "inventado") is None


def test_cambiar_clave_quita_debe_cambiar():
    with con_usuario() as c:
        if c is None:
            return
        _, u = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        try:
            auth.cambiar_clave(c, u.id, "equivocada", "otra-clave-larga")
            raise AssertionError("aceptó la clave actual equivocada")
        except auth.ErrorAuth:
            pass
        try:
            auth.cambiar_clave(c, u.id, CLAVE, "corta")
            raise AssertionError("aceptó una clave corta")
        except auth.ErrorAuth as e:
            assert "10" in str(e)
        auth.cambiar_clave(c, u.id, CLAVE, "otra-clave-larga")
        assert auth.iniciar_sesion(c, "a@x.co", "otra-clave-larga", "1.1.1.1")[1].debe_cambiar is False


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
