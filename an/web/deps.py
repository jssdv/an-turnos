"""Dependencias de FastAPI: sesión, bloqueo por `debe_cambiar` y contexto de un área (permiso + alcance RLS + BD)."""
from fastapi import HTTPException, Request

from an.turnos.db import BD
from an.turnos.pg import Conexion

from . import auth, conexion

COOKIE = "an_sid"
ESCRITURA = {"POST", "PUT", "PATCH", "DELETE"}


def usuario_permitido_cambiar(request: Request):
    """El usuario de la sesión (incluso con `debe_cambiar`); 401 si no hay sesión válida."""
    token = request.cookies.get(COOKIE)
    u = None
    if token:
        with request.app.state.pool.connection() as conn:
            u = auth.usuario_de_token(Conexion(conn), token)
    if u is None:
        raise HTTPException(401, "Ingresa de nuevo")
    request.state.usuario = u
    return u


def usuario_actual(request: Request):
    u = usuario_permitido_cambiar(request)
    if u.debe_cambiar:
        raise HTTPException(403, "Debes cambiar tu contraseña antes de continuar")
    return u


def leer_revision(if_match):
    """La revisión de `If-Match` (acepta comillas y `W/`); 428 si falta, 422 si no es un entero."""
    if if_match is None:
        raise HTTPException(428, "Falta If-Match con la revisión del periodo")
    try:
        return int(if_match.strip().removeprefix("W/").strip('"'))
    except ValueError:
        raise HTTPException(422, "If-Match debe ser la revisión del periodo (un entero)")


class Contexto:
    def __init__(self, bd, usuario, permiso, conn):
        self.bd, self.usuario, self.permiso, self.conn = bd, usuario, permiso, conn


def _contexto(area, request, exige_editar):
    u = usuario_actual(request)
    with request.app.state.pool.connection() as conn:
        c = Conexion(conn, confirmar=False)
        conexion.alcance(conn, u.clinica_id)
        if not c.execute("SELECT 1 FROM area WHERE id = ?", (area,)).fetchone():
            raise HTTPException(404, "Área no encontrada")
        fila = c.execute("SELECT permiso FROM usuario_area WHERE usuario_id = ? AND area_id = ?", (u.id, area)).fetchone()
        permiso = fila[0] if fila else ("ver" if u.es_admin else None)
        if permiso is None:
            raise HTTPException(404, "Área no encontrada")
        if exige_editar and request.method in ESCRITURA and permiso != "editar":
            raise HTTPException(403, "Solo lectura en esta área")
        conexion.alcance(conn, u.clinica_id, area)
        yield Contexto(BD.postgres(c), u, permiso, c)


def contexto_area(area: int, request: Request):
    """Dependencia por área: permiso (`ver` para GET, `editar` para escribir), alcance RLS y una BD lista. Una transacción por petición."""
    yield from _contexto(area, request, True)


def contexto_area_lectura(area: int, request: Request):
    """Como `contexto_area`, pero `ver` basta también en POST: para acciones que no cambian el cuadro (exportes)."""
    yield from _contexto(area, request, False)
