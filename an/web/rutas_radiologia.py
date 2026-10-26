"""Radiología en la web: cuadro mensual subido (`archivo`) y, sobre él, las funciones de `an/radiologia/`. La API no reimplementa reglas."""
import re
import zipfile
from io import BytesIO
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from starlette.concurrency import run_in_threadpool

from an.radiologia import generar_semana as gs

from .deps import Contexto, contexto_area

router = APIRouter(prefix="/api")
MAX_ARCHIVO = 10 * 1024 * 1024
MAX_DESCOMPRIMIDO = 100 * 1024 * 1024
RUTA_ARCHIVOS = re.compile(r"^/api/areas/\d+/archivos$")


def _exigir_radiologia(ctx, area):
    f = ctx.conn.execute("SELECT tipo FROM area WHERE id = ?", (area,)).fetchone()
    if f is None or f["tipo"] != "radiologia":
        raise HTTPException(404, "Área no encontrada")


def _validar_xlsx(nombre, datos):
    """Rechaza con un mensaje en español lo que no sea un cuadro mensual .xlsx usable; devuelve el nombre limpio."""
    limpio = Path(nombre or "").name.strip()[:120]
    if not limpio.lower().endswith(".xlsx"):
        raise HTTPException(422, "Sube un archivo .xlsx.")
    if len(datos) > MAX_ARCHIVO:
        raise HTTPException(413, "El archivo pasa de 10 MB.")
    try:  # un .xlsx es un zip: se mide lo que descomprime antes de que openpyxl lo abra
        with zipfile.ZipFile(BytesIO(datos)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_DESCOMPRIMIDO:
                raise HTTPException(422, "El archivo es demasiado grande al abrirlo.")
    except zipfile.BadZipFile:
        pass  # cargar_mensual da el mensaje
    try:
        if not gs.lunes_disponibles(gs.cargar_mensual(BytesIO(datos))):
            raise gs.ErrorPlanilla("El cuadro no tiene ninguna semana completa (lunes a domingo).")
    except gs.ErrorPlanilla as e:
        raise HTTPException(422, str(e))
    return limpio


def _fila(f):
    return dict(id=f["id"], nombre=f["nombre"], tamano=f["tamano"], subido=f["subido"], subido_por=f["subido_por"])


COLUMNAS = ("SELECT a.id, a.nombre, octet_length(a.contenido) AS tamano, a.subido, u.nombre AS subido_por "
            "FROM archivo a LEFT JOIN usuario u ON u.id = a.subido_por ")


@router.get("/areas/{area}/archivos")
def listar_archivos(area: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    _exigir_radiologia(ctx, area)
    return [_fila(f) for f in ctx.conn.execute(COLUMNAS + "ORDER BY a.subido DESC, a.id DESC")]


def _guardar(ctx, area, nombre, datos):
    _exigir_radiologia(ctx, area)
    limpio = _validar_xlsx(nombre, datos)
    id_ = ctx.conn.execute("INSERT INTO archivo (nombre, contenido, subido_por) VALUES (?, ?, ?) RETURNING id", (limpio, datos, ctx.usuario.id)).fetchone()[0]
    return _fila(ctx.conn.execute(COLUMNAS + "WHERE a.id = ?", (id_,)).fetchone())


@router.post("/areas/{area}/archivos", status_code=201)
async def subir_archivo(area: int, request: Request, nombre: str = "", ctx: Contexto = Depends(contexto_area, scope="function")):
    datos = await request.body()  # crudo (sin multipart): el nombre va en la consulta
    return await run_in_threadpool(_guardar, ctx, area, nombre, datos)


@router.delete("/areas/{area}/archivos/{id}", status_code=204)
def borrar_archivo(area: int, id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    _exigir_radiologia(ctx, area)
    if ctx.conn.execute("DELETE FROM archivo WHERE id = ? RETURNING id", (id,)).fetchone() is None:
        raise HTTPException(404, "Archivo no encontrado")
