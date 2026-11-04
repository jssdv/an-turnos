import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de an/web/auth.py: contraseñas, sesiones y bloqueo. Imprime OK."""
import contextlib
import hashlib
import shutil
import tempfile
from pathlib import Path

import psycopg

from an.turnos.pg import FILAS, Conexion
from an.web import auth, esquema, sqlite_pg

URL = os.environ.get("AN_PG_URL")
CLAVE = "clave-larga-1"


@contextlib.contextmanager
def con_usuario():
    """Base SQLite desechable con un usuario a@x.co."""
    carpeta = Path(tempfile.mkdtemp())
    raw = sqlite_pg.abrir(str(carpeta / "an.db"))
    esquema.aplicar_sqlite(raw)
    cl = raw.execute("INSERT INTO clinica (nombre) VALUES ('A') RETURNING id").fetchone()[0]
    raw.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, clinica_id) VALUES ('a@x.co', 'Ana', %s, 0, %s)",
                (auth.hash_clave(CLAVE), cl))
    raw.commit()
    try:
        yield Conexion(raw)
    finally:
        raw.close()
        shutil.rmtree(carpeta, ignore_errors=True)


def test_hash_distinto_por_sal_y_verifica():
    h1, h2 = auth.hash_clave(CLAVE), auth.hash_clave(CLAVE)
    assert h1 != h2 and h1.startswith("scrypt$") and auth.verificar_clave(CLAVE, h1) and not auth.verificar_clave("otra", h1)


def test_login_guarda_solo_el_hash_del_token():
    with con_usuario() as c:
        if c is None:
            return
        token, u = auth.iniciar_sesion(c, "A@x.co ", CLAVE, "1.1.1.1")
        assert auth.usuario_de_token(c, token).id == u.id and u.correo == "a@x.co"
        guardado = c.execute("SELECT hash_token FROM sesion").fetchone()[0]
        assert guardado == hashlib.sha256(token.encode()).hexdigest() != token


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


def test_token_cerrado_o_inexistente_da_none():
    with con_usuario() as c:
        if c is None:
            return
        t3, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        auth.cerrar_sesion(c, t3)
        assert auth.usuario_de_token(c, t3) is None and auth.usuario_de_token(c, "inventado") is None


def test_cambiar_clave_quita_debe_cambiar():
    with con_usuario() as c:
        if c is None:
            return
        _, u = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        try:
            auth.cambiar_clave(c, u, "equivocada", "otra-clave-larga")
            raise AssertionError("aceptó la clave actual equivocada")
        except auth.ErrorAuth:
            pass
        try:
            auth.cambiar_clave(c, u, CLAVE, "corta")
            raise AssertionError("aceptó una clave corta")
        except auth.ErrorAuth as e:
            assert "10" in str(e)
        auth.cambiar_clave(c, u, CLAVE, "otra-clave-larga")
        assert auth.iniciar_sesion(c, "a@x.co", "otra-clave-larga", "1.1.1.1")[1].debe_cambiar is False


def test_una_sesion_no_se_renueva_con_una_hora_elegida_por_quien_llama():
    with con_usuario() as c:
        if c is None:
            return
        token, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        c.execute("UPDATE sesion SET ultima = datetime(ultima, '-36 minutes')")
        c.conn.commit()
        assert auth.usuario_de_token(c, token) is None
        t2, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        c.execute("UPDATE sesion SET creada = datetime(creada, '-12 hours', '-1 minute') WHERE hash_token = ?", (hashlib.sha256(t2.encode()).hexdigest(),))
        c.conn.commit()
        assert auth.usuario_de_token(c, t2) is None


def test_el_intento_se_registra_antes_de_verificar_la_clave():
    with con_usuario() as c:
        if c is None:
            return
        vistos = []
        original = auth.verificar_clave

        def espia(clave, guardado):
            vistos.append(c.execute("SELECT app_intentos(?, ?)", ("a@x.co", "7.7.7.7")).fetchone()[0])
            return original(clave, guardado)

        auth.verificar_clave = espia
        try:
            auth.iniciar_sesion(c, "a@x.co", CLAVE, "7.7.7.7")
        finally:
            auth.verificar_clave = original
        assert vistos == [1]  # ya contaba cuando se verificó (si no, 200 peticiones en paralelo pasarían antes del bloqueo)
        assert c.execute("SELECT app_intentos(?, ?)", ("a@x.co", "7.7.7.7")).fetchone()[0] == 0  # y un ingreso correcto lo borra


def test_cambiar_clave_cierra_las_otras_sesiones_y_limita_intentos():
    with con_usuario() as c:
        if c is None:
            return
        t1, u = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        t2, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        auth.cambiar_clave(c, u, CLAVE, "otra-clave-larga", token=t2, ip="1.1.1.1")
        assert auth.usuario_de_token(c, t1) is None and auth.usuario_de_token(c, t2) is not None
        for _ in range(5):
            try:
                auth.cambiar_clave(c, u, "equivocada", "nueva-clave-larga", ip="2.2.2.2")
            except auth.ErrorAuth as e:
                assert "no coincide" in str(e)
        try:
            auth.cambiar_clave(c, u, "otra-clave-larga", "nueva-clave-larga", ip="2.2.2.2")
            raise AssertionError("debía estar bloqueado")
        except auth.ErrorAuth as e:
            assert "bloqueado" in str(e)


def test_ingresar_purga_sesiones_vencidas_e_intentos_viejos():
    with con_usuario() as c:
        if c is None:
            return
        uid = c.execute("SELECT id FROM usuario").fetchone()[0]
        c.execute("INSERT INTO sesion (hash_token, usuario_id, creada, ultima) VALUES ('vieja', ?, now() - interval '2 days', now() - interval '2 days')", (uid,))
        c.execute("INSERT INTO intento_login (correo, ip, fecha) VALUES ('x@y.co', '1.1.1.1', now() - interval '2 days')")
        c.conn.commit()
        auth.iniciar_sesion(c, "a@x.co", CLAVE, "3.3.3.3")
        assert c.execute("SELECT count(*) FROM sesion WHERE hash_token = 'vieja'").fetchone()[0] == 0
        assert c.execute("SELECT count(*) FROM intento_login WHERE correo = 'x@y.co'").fetchone()[0] == 0


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
