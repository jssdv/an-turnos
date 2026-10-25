import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de an/web/auth.py: contraseñas, sesiones y bloqueo (necesitan AN_PG_URL). Imprime OK."""
import contextlib
import hashlib
import uuid

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


def test_funciones_de_ingreso_no_son_ejecutables_por_cualquier_rol():
    with con_usuario() as c:
        if c is None:
            return
        esq = c.execute("SELECT current_schema()").fetchone()[0]
        c.conn.execute("RESET ROLE")
        c.conn.execute("DROP ROLE IF EXISTS an_otro")
        c.conn.execute("CREATE ROLE an_otro NOLOGIN")
        c.conn.execute(f'GRANT USAGE ON SCHEMA "{esq}" TO an_otro')
        c.conn.commit()
        try:
            c.conn.execute("SET ROLE an_otro")
            try:
                c.execute("SELECT app_hash_clave(1)")
                raise AssertionError("un rol cualquiera ejecutó app_hash_clave")
            except psycopg.errors.InsufficientPrivilege:
                c.conn.rollback()
        finally:
            c.conn.execute("RESET ROLE")
            c.conn.execute(f'REVOKE USAGE ON SCHEMA "{esq}" FROM an_otro')
            c.conn.execute("DROP ROLE an_otro")
            c.conn.commit()
            c.conn.execute("SET ROLE an_app")


def test_cambiar_clave_solo_dentro_de_la_clinica_del_usuario():
    with con_usuario() as c:
        if c is None:
            return
        _, u = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        c.execute("SELECT set_config('app.clinica', '99999', true)")
        c.execute("SELECT app_poner_clave(?, ?)", (u.id, auth.hash_clave("intrusa-larga-1")))
        c.commit()
        assert auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.2")  # la clave no cambió: otra clínica en el alcance


def test_una_sesion_no_se_renueva_con_una_hora_elegida_por_quien_llama():
    with con_usuario() as c:
        if c is None:
            return
        token, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        c.conn.execute("RESET ROLE")
        c.execute("UPDATE sesion SET ultima = ultima - interval '36 minutes'")
        c.conn.commit()
        c.conn.execute("SET ROLE an_app")
        assert auth.usuario_de_token(c, token) is None
        t2, _ = auth.iniciar_sesion(c, "a@x.co", CLAVE, "1.1.1.1")
        c.conn.execute("RESET ROLE")
        c.execute("UPDATE sesion SET creada = creada - interval '12 hours 1 minute' WHERE hash_token = ?", (hashlib.sha256(t2.encode()).hexdigest(),))
        c.conn.commit()
        c.conn.execute("SET ROLE an_app")
        assert auth.usuario_de_token(c, t2) is None
        try:
            c.execute("SELECT * FROM app_sesion(?, now())", (hashlib.sha256(t2.encode()).hexdigest(),))
            raise AssertionError("app_sesion aún acepta una hora externa")
        except psycopg.errors.UndefinedFunction:
            c.conn.rollback()


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


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
