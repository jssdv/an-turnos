"""App FastAPI de An: cadena de seguridad por petición y rutas. Arranque: uvicorn an.web.app:crear_app --factory"""
import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool

from . import conexion
from .deps import ESCRITURA
from .rutas_areas import router as rutas_areas
from .rutas_auth import router as rutas_auth

LIMITE_CUERPO = 1_000_000
CABECERAS = {"Content-Security-Policy": "default-src 'self'; frame-ancestors 'none'", "X-Content-Type-Options": "nosniff",
             "Referrer-Policy": "no-referrer", "Cache-Control": "no-store"}
log = logging.getLogger("an.web")


def _origen_esperado(request):
    """El origen propio. Detrás de un proxy (Caddy) se fija con AN_ORIGEN=https://dominio; si no, se deduce de la petición."""
    return os.environ.get("AN_ORIGEN") or f"{request.url.scheme}://{request.url.netloc}"


def _auditar(pool, request, codigo):
    u = request.state.usuario
    ip = request.client.host if request.client else None
    with pool.connection() as conn:
        conexion.alcance(conn, u.clinica_id)
        conn.execute("INSERT INTO auditoria (usuario_id, correo, metodo, ruta, codigo, ip, evento) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                     (u.id, u.correo, request.method, request.url.path, codigo, ip, getattr(request.state, "evento", None)))


def crear_app(pool=None):
    app = FastAPI(title="An", docs_url=None, redoc_url=None)
    app.state.pool = pool or conexion.abrir_pool()

    @app.middleware("http")
    async def cadena(request: Request, call_next):
        id_ = uuid.uuid4().hex[:12]
        request.state.usuario = None
        if int(request.headers.get("content-length") or 0) > LIMITE_CUERPO:
            respuesta = JSONResponse({"detalle": "Cuerpo demasiado grande"}, 413)
        elif request.method in ESCRITURA and request.headers.get("origin") != _origen_esperado(request):
            respuesta = JSONResponse({"detalle": "Origen no permitido"}, 403)
        else:
            try:
                respuesta = await call_next(request)
            except Exception:
                log.exception("error interno (petición %s)", id_)
                respuesta = JSONResponse({"detalle": "Error interno", "id": id_}, 500)
        for k, v in CABECERAS.items():
            respuesta.headers[k] = v
        respuesta.headers["X-Request-Id"] = id_
        if request.state.usuario is not None:
            try:
                await run_in_threadpool(_auditar, app.state.pool, request, respuesta.status_code)
            except Exception:
                log.exception("no se pudo auditar (petición %s)", id_)
        return respuesta

    app.include_router(rutas_auth)
    app.include_router(rutas_areas)
    return app
