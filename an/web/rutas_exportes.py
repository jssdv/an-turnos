"""Exportes en Excel de un periodo. Llaman a `exportar.*` del núcleo (los mismos argumentos que `Turnos.exportar` de Qt) en una carpeta
temporal y guardan el libro en `exporte`. Nunca sobrescriben: `exportar.ruta_libre` da `v2`, `v3`… sobre los nombres ya guardados."""
import tempfile
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from an.turnos import exportar, flujo

from .deps import Contexto, contexto_area_lectura

router = APIRouter(prefix="/api")
MAX_EXPORTES_DIA = 20  # por periodo y por día: un `ver` puede exportar, pero `exporte` es de solo inserción
XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
COLUMNAS = ("e.id, e.tipo, e.numero, e.nombre_archivo, octet_length(e.contenido) AS bytes, e.creado, u.nombre AS creado_por "
            "FROM exporte e LEFT JOIN usuario u ON u.id = e.creado_por")


class NuevoExporte(BaseModel):
    tipo: Literal["cuadro", "puestos", "horas"]


def _plano(f):
    return {k: f[k] for k in f.keys()}


def _libro(bd, tipo, carpeta, clave, cuadro):
    inicio, fin = flujo.desde_clave(clave)
    ctx, fechas, txt = bd.contexto(inicio.year), flujo.fechas(inicio, fin), flujo.etiqueta(inicio, fin)
    if tipo == "cuadro":
        return exportar.exportar_cuadro(carpeta, txt, ctx, cuadro, bd.asignaciones(clave, "original"), fechas, bd.diferencias(clave),
                                        bd.asignacion_puesto(clave), bd.catalogo_puestos())
    if tipo == "puestos":
        return exportar.exportar_puestos(carpeta, txt, ctx, cuadro, fechas, bd.asignacion_puesto(clave), bd.capacitacion(clave), bd.catalogo_puestos())
    return exportar.exportar_horas(carpeta, txt, ctx, bd.tarifas(), cuadro, fechas, int(bd.param("ventana_semanas", 3)))


@router.post("/areas/{area}/periodos/{id}/exportes", status_code=201)
def crear(id: int, datos: NuevoExporte, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ? FOR UPDATE", (id,)).fetchone()  # serializa `numero` por periodo
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    hoy = ctx.conn.execute("SELECT count(*) FROM exporte WHERE periodo_id = ? AND creado > now() - interval '1 day'", (id,)).fetchone()[0]
    if hoy >= MAX_EXPORTES_DIA:
        raise HTTPException(429, f"Ya hay {MAX_EXPORTES_DIA} exportes de este periodo en las últimas 24 horas. Descarga uno de los existentes o inténtalo mañana.")
    cuadro = ctx.bd.asignaciones(f["clave"])
    if not cuadro:
        raise HTTPException(409, "No hay cuadro para exportar.")
    previos = [r[0] for r in ctx.conn.execute("SELECT nombre_archivo FROM exporte WHERE periodo_id = ? AND tipo = ?", (id, datos.tipo))]
    with tempfile.TemporaryDirectory() as tmp:
        for n in previos:
            (Path(tmp) / n).touch()
        ruta = _libro(ctx.bd, datos.tipo, tmp, f["clave"], cuadro)
        contenido = ruta.read_bytes()
    nuevo = ctx.conn.execute(
        "INSERT INTO exporte (periodo_id, tipo, numero, nombre_archivo, contenido, creado_por) "
        "SELECT ?, ?, COALESCE(MAX(numero), 0) + 1, ?, ?, ? FROM exporte WHERE periodo_id = ? AND tipo = ? RETURNING id",
        (id, datos.tipo, ruta.name, contenido, ctx.usuario.id, id, datos.tipo)).fetchone()[0]
    request.state.evento = "exportacion"
    return _plano(ctx.conn.execute(f"SELECT {COLUMNAS} WHERE e.id = ?", (nuevo,)).fetchone())  # sql-ok: columnas constantes


@router.get("/areas/{area}/periodos/{id}/exportes")
def listar(id: int, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    if not ctx.conn.execute("SELECT 1 FROM periodo WHERE id = ?", (id,)).fetchone():
        raise HTTPException(404, "Periodo no encontrado")
    return [_plano(f) for f in ctx.conn.execute(f"SELECT {COLUMNAS} WHERE e.periodo_id = ? ORDER BY e.creado DESC, e.id DESC", (id,)).fetchall()]  # sql-ok: columnas constantes


@router.get("/areas/{area}/periodos/{id}/exportes/{exporte}/descargar")
def descargar(id: int, exporte: int, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    f = ctx.conn.execute("SELECT nombre_archivo, contenido FROM exporte WHERE id = ? AND periodo_id = ?", (exporte, id)).fetchone()
    if not f:
        raise HTTPException(404, "Exporte no encontrado")
    request.state.evento = "exportacion"
    nombre = f["nombre_archivo"]
    return Response(bytes(f["contenido"]), media_type=XLSX,
                    headers={"Content-Disposition": f"attachment; filename=\"{nombre}\"; filename*=UTF-8''{quote(nombre)}"})
