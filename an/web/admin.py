"""Administración por línea de comandos: clínicas, áreas, usuarios y permisos. Uso: python -m an.web.admin <comando> …
Se conecta con AN_PG_URL como el rol dueño de las tablas (el que aplica las migraciones)."""
import argparse
import os
import secrets
import sys

import psycopg

from an.turnos.db import BD
from an.turnos.pg import FILAS, Conexion

from . import auth, conexion


class ErrorAdmin(Exception):
    pass


def crear_clinica(conn, nombre):
    return conn.execute("INSERT INTO clinica (nombre) VALUES (%s) RETURNING id", (nombre,)).fetchone()[0]


def crear_area(conn, clinica_id, nombre, tipo="turnos"):
    """Crea el área; las de tipo `turnos` arrancan con los datos base del motor (turnos, puestos, tarifas, parámetros)."""
    try:
        area = conn.execute("INSERT INTO area (nombre, tipo, clinica_id) VALUES (%s, %s, %s) RETURNING id", (nombre, tipo, clinica_id)).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ErrorAdmin("esa clínica ya tiene un área con ese nombre")
    if tipo == "turnos":
        conexion.alcance(conn, clinica_id, area)
        BD.postgres(Conexion(conn, confirmar=False)).sembrar()
    conn.commit()
    return area


def crear_usuario(conn, clinica_id, correo, nombre, es_admin=False):
    """(id, clave temporal). La clave se muestra una sola vez y el usuario debe cambiarla al ingresar."""
    clave = secrets.token_urlsafe(12)
    try:
        uid = conn.execute("INSERT INTO usuario (correo, nombre, hash_clave, es_admin, clinica_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                           (correo.strip().lower(), nombre, auth.hash_clave(clave), es_admin, clinica_id)).fetchone()[0]
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ErrorAdmin("no se pudo crear el usuario con ese correo; usa otro")
    conn.commit()
    return uid, clave


def dar_permiso(conn, usuario_id, area_id, permiso):
    if permiso not in ("ver", "editar"):
        raise ErrorAdmin("el permiso debe ser «ver» o «editar»")
    u, a = (conn.execute("SELECT clinica_id FROM usuario WHERE id = %s", (usuario_id,)).fetchone(),
            conn.execute("SELECT clinica_id FROM area WHERE id = %s", (area_id,)).fetchone())
    if u is None or a is None:
        raise ErrorAdmin("el usuario o el área no existe")
    if u[0] != a[0]:
        raise ErrorAdmin("el usuario y el área son de clínicas distintas")
    try:
        conn.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s) "
                     "ON CONFLICT (usuario_id, area_id) DO UPDATE SET permiso = excluded.permiso", (usuario_id, area_id, permiso, a[0]))
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ErrorAdmin("esta área ya tiene un usuario que edita; cámbialo a «ver» antes")
    conn.commit()


def quitar_permiso(conn, usuario_id, area_id):
    if conn.execute("DELETE FROM usuario_area WHERE usuario_id = %s AND area_id = %s", (usuario_id, area_id)).rowcount == 0:
        raise ErrorAdmin("ese usuario no tiene permiso en esa área")
    conn.commit()


def desactivar_usuario(conn, usuario_id):
    """El usuario ya no puede ingresar y sus sesiones se cierran."""
    if conn.execute("UPDATE usuario SET activo = false WHERE id = %s", (usuario_id,)).rowcount == 0:
        raise ErrorAdmin("el usuario no existe")
    conn.execute("DELETE FROM sesion WHERE usuario_id = %s", (usuario_id,))
    conn.commit()


def restablecer_clave(conn, usuario_id):
    """Clave temporal nueva (se muestra una vez); cierra las sesiones y obliga a cambiarla al ingresar."""
    clave = secrets.token_urlsafe(12)
    if conn.execute("UPDATE usuario SET hash_clave = %s, debe_cambiar = true WHERE id = %s", (auth.hash_clave(clave), usuario_id)).rowcount == 0:
        raise ErrorAdmin("el usuario no existe")
    conn.execute("DELETE FROM sesion WHERE usuario_id = %s", (usuario_id,))
    conn.commit()
    return clave


def main(argv, conn=None):
    p = argparse.ArgumentParser(prog="python -m an.web.admin")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("crear-clinica").add_argument("nombre")
    s = sub.add_parser("crear-area")
    s.add_argument("--clinica", type=int, required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("--tipo", default="turnos", choices=["turnos", "radiologia"])
    s = sub.add_parser("crear-usuario")
    s.add_argument("--clinica", type=int, required=True)
    s.add_argument("--correo", required=True)
    s.add_argument("--nombre", required=True)
    s.add_argument("--admin", action="store_true")
    s = sub.add_parser("dar-permiso")
    s.add_argument("--usuario", type=int, required=True)
    s.add_argument("--area", type=int, required=True)
    s.add_argument("--permiso", required=True)
    s = sub.add_parser("quitar-permiso")
    s.add_argument("--usuario", type=int, required=True)
    s.add_argument("--area", type=int, required=True)
    sub.add_parser("desactivar-usuario").add_argument("usuario", type=int)
    sub.add_parser("restablecer-clave").add_argument("usuario", type=int)
    a = p.parse_args(argv)
    propia = conn is None
    conn = conn or psycopg.connect(os.environ["AN_PG_URL"], row_factory=FILAS)
    try:
        if a.cmd == "crear-clinica":
            print(crear_clinica(conn, a.nombre))
            conn.commit()
        elif a.cmd == "crear-area":
            print(crear_area(conn, a.clinica, a.nombre, a.tipo))
        elif a.cmd == "crear-usuario":
            uid, clave = crear_usuario(conn, a.clinica, a.correo, a.nombre, a.admin)
            print(f"usuario: {uid}\nclave temporal: {clave}\n(se muestra una sola vez)")
        elif a.cmd == "quitar-permiso":
            quitar_permiso(conn, a.usuario, a.area)
            print("listo")
        elif a.cmd == "desactivar-usuario":
            desactivar_usuario(conn, a.usuario)
            print("listo")
        elif a.cmd == "restablecer-clave":
            print(f"clave temporal: {restablecer_clave(conn, a.usuario)}\n(se muestra una sola vez)")
        else:
            dar_permiso(conn, a.usuario, a.area, a.permiso)
            print("listo")
        return 0
    except ErrorAdmin as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        if propia:
            conn.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
