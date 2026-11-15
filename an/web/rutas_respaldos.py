"""Respaldos desde la app (solo el administrador): ver los últimos y «Respaldar ahora». Solo en la app instalada, que fija
`app.state.respaldo = (ruta de an.db, carpeta de respaldos)`; sin eso la lista llega con `carpeta: null`."""
import sqlite3
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from .deps import usuario_actual

router = APIRouter(prefix="/api/respaldos")


def _config(request, u):
    if not u.es_admin:
        raise HTTPException(403, "Solo el administrador de la clínica puede hacer esto")
    return getattr(request.app.state, "respaldo", None)


def _fila(d):
    archivos = [f for f in d.iterdir() if f.is_file()]
    return {"nombre": d.name, "fecha": datetime.strptime(d.name, "%Y%m%d_%H%M%S").isoformat(),
            "archivos": len(archivos), "bytes": sum(f.stat().st_size for f in archivos)}


@router.get("")
def listar(request: Request, u=Depends(usuario_actual)):
    cfg = _config(request, u)
    if not cfg:
        return {"carpeta": None, "respaldos": []}
    destino = cfg[1]
    hechos = sorted((d for d in destino.glob("[0-9]*_*") if d.is_dir()), reverse=True) if destino.exists() else []
    return {"carpeta": str(destino), "respaldos": [_fila(d) for d in hechos]}


@router.post("", status_code=201)
def respaldar(request: Request, u=Depends(usuario_actual)):
    cfg = _config(request, u)
    if not cfg:
        raise HTTPException(404, "Los respaldos solo están en la app instalada")
    from .entregable import respaldar as copiar  # aquí: entregable importa la app
    try:
        carpeta = copiar(*cfg)
    except (OSError, sqlite3.Error) as e:
        raise HTTPException(409, f"No se pudo guardar el respaldo en {cfg[1]}: {getattr(e, 'strerror', None) or e}")
    request.state.evento = "respaldo_manual"
    return _fila(carpeta)
