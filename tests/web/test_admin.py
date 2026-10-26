import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de an/web/admin.py (necesitan AN_PG_URL). Imprime OK."""
import contextlib
import io
import uuid

import psycopg

from an.turnos.pg import FILAS, Conexion
from an.web import admin, auth, esquema

URL = os.environ.get("AN_PG_URL")


@contextlib.contextmanager
def conn_nueva():
    if not URL:
        try:
            import pytest
            pytest.skip("sin AN_PG_URL")
        except ImportError:
            yield None
            return
    nombre = "t_" + uuid.uuid4().hex[:10]
    c = psycopg.connect(URL, row_factory=FILAS)
    c.execute(f'CREATE SCHEMA "{nombre}"')
    c.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(c)
    try:
        yield c
    finally:
        c.rollback()
        c.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        c.commit()
        c.close()


def falla(fn, texto):
    try:
        fn()
    except admin.ErrorAdmin as e:
        assert texto in str(e), str(e)
        return
    raise AssertionError(f"debía fallar con «{texto}»")


def test_clinica_area_usuario_permiso():
    with conn_nueva() as c:
        if c is None:
            return
        cl = admin.crear_clinica(c, "Clínica A")
        ar = admin.crear_area(c, cl, "Esterilización")
        c.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(cl), str(ar)))
        assert len(c.execute("SELECT * FROM turno").fetchall()) == 4 and len(c.execute("SELECT * FROM puesto").fetchall()) == 6
        uid, clave = admin.crear_usuario(c, cl, "Coord@A.co", "Coord")
        assert c.execute("SELECT correo, debe_cambiar FROM usuario WHERE id=%s", (uid,)).fetchone()[:] == ("coord@a.co", True)
        admin.dar_permiso(c, uid, ar, "editar")
        token, u = auth.iniciar_sesion(Conexion(c), "coord@a.co", clave, "1.1.1.1")
        assert u.debe_cambiar and token


def test_un_solo_editor_y_correo_unico():
    with conn_nueva() as c:
        if c is None:
            return
        cl = admin.crear_clinica(c, "A")
        ar = admin.crear_area(c, cl, "Uno")
        u1, _ = admin.crear_usuario(c, cl, "u1@a.co", "U1")
        u2, _ = admin.crear_usuario(c, cl, "u2@a.co", "U2")
        admin.dar_permiso(c, u1, ar, "editar")
        admin.dar_permiso(c, u2, ar, "ver")
        falla(lambda: admin.dar_permiso(c, u2, ar, "editar"), "ya tiene un usuario que edita")
        falla(lambda: admin.crear_usuario(c, cl, "U1@a.co", "Otro"), "no se pudo crear el usuario")
        falla(lambda: admin.dar_permiso(c, u1, ar, "dueño"), "permiso")
        otra = admin.crear_clinica(c, "B")
        falla(lambda: admin.dar_permiso(c, u1, admin.crear_area(c, otra, "X"), "ver"), "clínicas distintas")


def test_linea_de_comandos_imprime_ids_y_clave_una_vez():
    with conn_nueva() as c:
        if c is None:
            return
        def correr(*args):
            salida = io.StringIO()
            with contextlib.redirect_stdout(salida):
                assert admin.main(list(args), conn=c) == 0
            return salida.getvalue()
        cl = correr("crear-clinica", "Clínica A").strip()
        ar = correr("crear-area", "--clinica", cl, "--nombre", "Esterilización").strip()
        texto = correr("crear-usuario", "--clinica", cl, "--correo", "c@a.co", "--nombre", "Coord")
        assert "clave temporal:" in texto and ar.isdigit()
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            assert admin.main(["crear-usuario", "--clinica", cl, "--correo", "c@a.co", "--nombre", "Otro"], conn=c) == 1
        assert "no se pudo crear el usuario" in err.getvalue()


def test_quitar_permiso_desactivar_y_restablecer_clave():
    with conn_nueva() as c:
        if c is None:
            return
        cl = admin.crear_clinica(c, "A")
        ar = admin.crear_area(c, cl, "Uno")
        uid, clave = admin.crear_usuario(c, cl, "u@a.co", "U")
        admin.dar_permiso(c, uid, ar, "editar")
        admin.quitar_permiso(c, uid, ar)
        assert c.execute("SELECT count(*) FROM usuario_area").fetchone()[0] == 0
        falla(lambda: admin.quitar_permiso(c, uid, ar), "no tiene permiso")
        token, _ = auth.iniciar_sesion(Conexion(c), "u@a.co", clave, "1.1.1.1")
        nueva = admin.restablecer_clave(c, uid)
        assert nueva != clave and c.execute("SELECT count(*) FROM sesion").fetchone()[0] == 0  # cierra sus sesiones
        assert auth.iniciar_sesion(Conexion(c), "u@a.co", nueva, "1.1.1.1")[1].debe_cambiar
        admin.desactivar_usuario(c, uid)
        try:
            auth.iniciar_sesion(Conexion(c), "u@a.co", nueva, "1.1.1.2")
            raise AssertionError("un usuario desactivado ingresó")
        except auth.ErrorAuth:
            pass
        assert c.execute("SELECT count(*) FROM sesion").fetchone()[0] == 0
        falla(lambda: admin.restablecer_clave(c, 99999), "no existe")


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
