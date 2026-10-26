"""App FastAPI de An: cadena de seguridad por petición y rutas. Arranque: uvicorn an.web.app:crear_app --factory"""
import logging
import os
import uuid

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from an.turnos.pg import Conexion

from . import auth, conexion
from .deps import COOKIE, ESCRITURA
from .rutas_areas import router as rutas_areas
from .rutas_auth import router as rutas_auth
from .rutas_catalogos import router as rutas_catalogos
from .rutas_radiologia import MAX_ARCHIVO, RUTA_ARCHIVOS
from .rutas_radiologia import router as rutas_radiologia
from .rutas_edicion import router as rutas_edicion
from .rutas_exportes import router as rutas_exportes
from .rutas_trabajos import router as rutas_trabajos
from .rutas_usuarios import router as rutas_usuarios

LIMITE_CUERPO = 1_000_000
LIMITE_ARCHIVO = MAX_ARCHIVO + 1024  # holgura: la ruta mide el tamaño exacto y da el mensaje
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


def _usuario_del_rechazo(pool, request):
    """Si el 403 por Origin llega con una sesión válida, deja al usuario en el estado de la petición para que se audite como `origen_rechazado`."""
    token = request.cookies.get(COOKIE)
    try:
        if token:
            with pool.connection() as conn:
                request.state.usuario = auth.usuario_de_token(Conexion(conn), token)
            request.state.evento = "origen_rechazado"
    except Exception:
        log.exception("no se pudo resolver la sesión del origen rechazado")


def crear_app(pool=None):
    app = FastAPI(title="An", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.pool = pool or conexion.abrir_pool()

    @app.middleware("http")
    async def cadena(request: Request, call_next):
        id_ = uuid.uuid4().hex[:12]
        request.state.usuario = None
        largo = request.headers.get("content-length")
        subida = request.method == "POST" and RUTA_ARCHIVOS.match(request.url.path) is not None
        if largo is not None and not largo.isdigit():
            respuesta = JSONResponse({"detalle": "Content-Length inválido"}, 400)
        elif largo is None and request.method in ESCRITURA and "chunked" in request.headers.get("transfer-encoding", "").lower():
            respuesta = JSONResponse({"detalle": "Se requiere Content-Length"}, 411)
        elif int(largo or 0) > (LIMITE_ARCHIVO if subida else LIMITE_CUERPO):
            respuesta = JSONResponse({"detalle": "El archivo pasa de 10 MB." if subida else "Cuerpo demasiado grande"}, 413)
        elif request.method in ESCRITURA and request.headers.get("origin") != _origen_esperado(request):
            respuesta = JSONResponse({"detalle": "Origen no permitido"}, 403)
            await run_in_threadpool(_usuario_del_rechazo, app.state.pool, request)
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

    @app.exception_handler(StarletteHTTPException)
    async def _http(request, exc):  # un solo formato de error: {"detalle": …}
        return JSONResponse({"detalle": exc.detail}, exc.status_code, headers=getattr(exc, "headers", None))

    @app.exception_handler(RequestValidationError)
    async def _validacion(request, exc):  # sin devolver el cuerpo enviado (puede traer contraseñas)
        return JSONResponse({"detalle": "Datos inválidos", "campos": [".".join(str(x) for x in e["loc"]) for e in exc.errors()]}, 422)

    app.include_router(rutas_auth)
    app.include_router(rutas_areas)
    app.include_router(rutas_catalogos)
    app.include_router(rutas_edicion)
    app.include_router(rutas_radiologia)
    app.include_router(rutas_exportes)
    app.include_router(rutas_trabajos)
    app.include_router(rutas_usuarios)
    return app
