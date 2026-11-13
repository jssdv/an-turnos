"""Exportes en Excel de un periodo. Llaman a `exportar.*` del núcleo (los mismos argumentos que `Turnos.exportar` de Qt) en una carpeta
temporal y guardan el libro en `exporte`. Un exporte nuevo borra el anterior del mismo tipo y cada descarga borra el archivo descargado: no queda basura guardada."""
import tempfile
import zipfile
from io import BytesIO
from typing import Literal
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel

from an.radiologia import analisis
from an.turnos import exportar, flujo

from .deps import Contexto, contexto_area_lectura

router = APIRouter(prefix="/api")
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
                                        bd.asignacion_puesto(clave), bd.catalogo_puestos(), flujo.detalle_horas(bd, inicio, fin))
    if tipo == "puestos":
        return exportar.exportar_puestos(carpeta, txt, ctx, cuadro, fechas, bd.asignacion_puesto(clave), bd.capacitacion(clave), bd.catalogo_puestos())
    return exportar.exportar_horas(carpeta, txt, ctx, bd.tarifas(), cuadro, fechas, int(bd.param("ventana_semanas", 3)))


@router.post("/areas/{area}/periodos/{id}/exportes", status_code=201)
def crear(id: int, datos: NuevoExporte, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ? FOR UPDATE", (id,)).fetchone()  # serializa `numero` por periodo
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    cuadro = ctx.bd.asignaciones(f["clave"])
    if not cuadro:
        raise HTTPException(409, "No hay cuadro para exportar.")
    ctx.conn.execute("DELETE FROM exporte WHERE periodo_id = ? AND tipo = ?", (id, datos.tipo))  # el anterior del mismo tipo es un cuadro viejo
    with tempfile.TemporaryDirectory() as tmp:
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
    ctx.conn.execute("DELETE FROM exporte WHERE id = ?", (exporte,))  # se entrega una vez y no queda guardado
    return Response(bytes(f["contenido"]), media_type=XLSX, headers=_adjunto(nombre))


def _adjunto(nombre):
    return {"Content-Disposition": f"attachment; filename=\"{nombre}\"; filename*=UTF-8''{quote(nombre)}"}


def _periodo(ctx, id):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ?", (id,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    return flujo.desde_clave(f["clave"])


@router.get("/areas/{area}/periodos/{id}/banco.xlsx")
def banco_xlsx(id: int, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    inicio, fin = _periodo(ctx, id)
    nombres = {p.id: p.nombre for p in ctx.bd.colaboradores(solo_activos=False)}
    with tempfile.TemporaryDirectory() as tmp:
        ruta = exportar.exportar_banco(tmp, flujo.etiqueta(inicio, fin), flujo.estado_banco(ctx.bd, inicio, fin), ctx.bd.movimientos(), nombres)
        contenido = ruta.read_bytes()
    request.state.evento = "exportacion"
    return Response(contenido, media_type=XLSX, headers=_adjunto(ruta.name))



def _agendas(ctx, id):
    """(etiqueta del periodo, {colab_id: (nombre, texto .ics)}) del cuadro vigente (`cambios`)."""
    inicio, fin = _periodo(ctx, id)
    c, fechas = ctx.bd.contexto(inicio.year), flujo.fechas(inicio, fin)
    cuadro = ctx.bd.asignaciones(flujo.clave(inicio, fin))
    return flujo.etiqueta(inicio, fin), {p.id: (p.nombre, analisis.ics(p.nombre, exportar.eventos_persona(c, cuadro, p.id, fechas)))
                                         for p in c.colabs if p.en_solver}


@router.get("/areas/{area}/periodos/{id}/agendas/{colab}.ics")
def agenda_ics(id: int, colab: int, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    nombre, texto = _agendas(ctx, id)[1].get(colab) or (None, None)
    if nombre is None:
        raise HTTPException(404, "Esa persona no está en el cuadro")
    request.state.evento = "exportacion"
    return Response(texto.encode("utf-8"), media_type="text/calendar; charset=utf-8", headers=_adjunto(analisis.nombre_archivo(nombre) + ".ics"))


@router.get("/areas/{area}/periodos/{id}/agendas.zip")
def agendas_zip(id: int, request: Request, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    txt, agendas = _agendas(ctx, id)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        vistos = set()
        for cid, (nombre, texto) in agendas.items():
            archivo = analisis.nombre_archivo(nombre) or str(cid)
            archivo = f"{archivo} {cid}" if archivo in vistos else archivo  # dos personas con el mismo nombre
            vistos.add(archivo)
            z.writestr(archivo + ".ics", texto)
    request.state.evento = "exportacion"
    return Response(buf.getvalue(), media_type="application/zip", headers=_adjunto(f"AGENDAS {txt.upper()}.zip"))
