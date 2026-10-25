import logging
from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from an.turnos.pg import Conexion

from . import auth
from .deps import COOKIE, usuario_permitido_cambiar

router = APIRouter(prefix="/api/auth")
log = logging.getLogger("an.web")


class Entrada(BaseModel):
    correo: str
    clave: str


class CambioClave(BaseModel):
    actual: str
    nueva: str


@router.post("/entrar")
def entrar(datos: Entrada, request: Request, response: Response):
    ip = request.client.host if request.client else "?"
    try:
        with request.app.state.pool.connection() as conn:
            token, u = auth.iniciar_sesion(Conexion(conn), datos.correo, datos.clave, ip)
    except auth.ErrorAuth as e:
        bloqueado = "bloqueado" in str(e)
        try:
            with request.app.state.pool.connection() as conn:
                conn.execute("SELECT app_auditar_ingreso(%s, %s, %s, %s)", (datos.correo.strip(), ip, "bloqueado" if bloqueado else "ingreso_fallido", 429 if bloqueado else 401))
        except Exception:
            log.exception("no se pudo auditar el ingreso fallido")  # no debe tapar el 401/429
        raise HTTPException(429 if bloqueado else 401, str(e))
    response.set_cookie(COOKIE, token, httponly=True, secure=True, samesite="lax", max_age=12 * 3600, path="/")
    request.state.usuario, request.state.evento = u, "ingreso"
    return {"usuario": asdict(u)}


@router.post("/salir")
def salir(request: Request, response: Response, u=Depends(usuario_permitido_cambiar)):
    with request.app.state.pool.connection() as conn:
        auth.cerrar_sesion(Conexion(conn), request.cookies[COOKIE])
    response.delete_cookie(COOKIE, path="/")
    request.state.evento = "salida"
    return {"ok": True}


@router.post("/cambiar-clave")
def cambiar_clave(datos: CambioClave, request: Request, u=Depends(usuario_permitido_cambiar)):
    try:
        with request.app.state.pool.connection() as conn:
            auth.cambiar_clave(Conexion(conn), u, datos.actual, datos.nueva, request.cookies.get(COOKIE), request.client.host if request.client else "?")
    except auth.ErrorAuth as e:
        raise HTTPException(429 if "bloqueado" in str(e) else 400, str(e))
    request.state.evento = "cambio_clave"
    return {"ok": True}


@router.get("/yo")
def yo(u=Depends(usuario_permitido_cambiar)):
    return asdict(u)
