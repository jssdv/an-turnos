"""Rutas de la cola del solver: encolar la generación de un periodo, consultar un trabajo y cancelarlo. El cálculo lo hace an/web/trabajador.py."""
from datetime import date
from typing import Literal

import psycopg
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from psycopg.types.json import Jsonb
from pydantic import BaseModel, Field

from an.turnos import flujo
from an.turnos.pg import Conexion

from . import conexion
from .deps import Contexto, contexto_area, usuario_actual

router = APIRouter(prefix="/api")
YA_HAY = "Ya hay un cuadro generándose en tu clínica."
CAMPOS = ("id", "area_id", "periodo_id", "tipo", "estado", "progreso", "resultado", "error", "cancelar", "creado", "terminado")


class Pedido(BaseModel):
    modo: Literal["cero", "respetar", "semana"] = "cero"
    lunes: date | None = None
    tiempo: int = Field(20, ge=1, le=300)
    semilla: int = 0


def _revision(if_match):
    if if_match is None:
        raise HTTPException(428, "Falta If-Match con la revisión del periodo")
    try:
        return int(if_match.strip().removeprefix("W/").strip('"'))
    except ValueError:
        raise HTTPException(422, "If-Match debe ser la revisión del periodo (un entero)")


@router.post("/areas/{area}/periodos/{id}/generar", status_code=202)
def generar(id: int, datos: Pedido = Pedido(), if_match: str | None = Header(None), ctx: Contexto = Depends(contexto_area, scope="function")):
    revision = _revision(if_match)
    f = ctx.conn.execute("SELECT clave, revision FROM periodo WHERE id = ?", (id,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    if f["revision"] != revision:
        raise HTTPException(409, {"mensaje": "El periodo cambió; recárgalo antes de generar.", "revision": f["revision"]})
    inicio, fin = flujo.desde_clave(f["clave"])
    if datos.modo == "semana" and not (datos.lunes and datos.lunes.weekday() == 0 and inicio <= datos.lunes <= fin):
        raise HTTPException(422, "Para regenerar una semana indica un lunes dentro del periodo")
    if ctx.conn.execute("SELECT 1 FROM trabajo WHERE estado IN ('en_cola', 'corriendo')").fetchone():
        raise HTTPException(409, YA_HAY)
    params = {"modo": datos.modo, "lunes": datos.lunes.isoformat() if datos.lunes else None, "tiempo": datos.tiempo, "semilla": datos.semilla}
    try:
        return {"id": ctx.conn.execute(
            "INSERT INTO trabajo (periodo_id, tipo, params, revision_base, creado_por) VALUES (?, 'generar', ?, ?, ?) RETURNING id",
            (id, Jsonb(params), revision, ctx.usuario.id)).fetchone()[0]}
    except psycopg.errors.UniqueViolation:  # otra petición de la clínica se coló entre la comprobación y el INSERT
        raise HTTPException(409, YA_HAY)


def _con_trabajo(request, u, id, escribir, accion=None):
    """Busca el trabajo en la clínica del usuario, exige permiso (`ver`, o `editar` si `escribir`) en su área, aplica `accion(conexion, fila)` y lo devuelve."""
    with request.app.state.pool.connection() as conn:
        c = Conexion(conn, confirmar=False)
        conexion.alcance(conn, u.clinica_id)
        f = c.execute("SELECT * FROM trabajo WHERE id = ?", (id,)).fetchone()
        fila = f and c.execute("SELECT permiso FROM usuario_area WHERE usuario_id = ? AND area_id = ?", (u.id, f["area_id"])).fetchone()
        permiso = (fila[0] if fila else "ver" if u.es_admin else None) if f else None
        if permiso is None:
            raise HTTPException(404, "Trabajo no encontrado")
        if escribir and permiso != "editar":
            raise HTTPException(403, "Solo lectura en esta área")
        if accion:
            conexion.alcance(conn, u.clinica_id, f["area_id"])
            accion(c, f)
            f = c.execute("SELECT * FROM trabajo WHERE id = ?", (id,)).fetchone()
        return {k: f[k] for k in CAMPOS}


@router.get("/trabajos/{id}")
def trabajo(id: int, request: Request, u=Depends(usuario_actual)):
    return _con_trabajo(request, u, id, False)


@router.post("/trabajos/{id}/cancelar")
def cancelar(id: int, request: Request, u=Depends(usuario_actual)):
    def accion(c, f):
        if f["estado"] not in ("en_cola", "corriendo"):
            raise HTTPException(409, "El trabajo ya terminó")
        # dos UPDATE en orden: si el trabajador lo toma entre la lectura y aquí, el segundo deja la marca para su monitor
        c.execute("UPDATE trabajo SET estado = 'cancelado', cancelar = true, terminado = now() WHERE id = ? AND estado = 'en_cola'", (id,))
        c.execute("UPDATE trabajo SET cancelar = true WHERE id = ? AND estado = 'corriendo'", (id,))
    return _con_trabajo(request, u, id, True, accion)
