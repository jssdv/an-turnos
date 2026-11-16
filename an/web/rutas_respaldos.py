"""Respaldos desde la app (solo el administrador): ver los últimos, «Respaldar ahora» y «Restaurar». Solo en la app instalada, que fija
`app.state.respaldo = (ruta de an.db, carpeta de respaldos)`; sin eso la lista llega con `carpeta: null`."""
import re
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


@router.post("/{nombre}/restaurar")
def restaurar(nombre: str, request: Request, u=Depends(usuario_actual)):
    """Reemplaza an.db y los archivos de área por los de la copia `nombre`, tras guardar una copia de lo actual (devuelve su nombre).
    Las áreas que no están en la copia quedan en su archivo; no se borra nada."""
    cfg = _config(request, u)
    elegida = cfg and cfg[1] / nombre
    if not elegida or not re.fullmatch(r"\d{8}_\d{6}", nombre) or not (elegida / "an.db").is_file():
        raise HTTPException(404, "Copia de respaldo no encontrada")
    from . import entregable  # aquí: entregable importa la app
    from .esquema import BaseNoUsable
    try:
        entregable.revisar_base(elegida / "an.db", cfg[1])  # antes de tocar nada: la copia está sana y no es de una versión más nueva
    except BaseNoUsable as e:
        raise HTTPException(409, f"Esa copia no se puede restaurar. {e}")
    with request.app.state.pool.connection() as conn:
        if conn.execute("SELECT 1 FROM trabajo WHERE estado IN ('en_cola', 'corriendo')").fetchone():
            raise HTTPException(409, "Hay un cuadro generándose; espera a que termine para restaurar")
    datos = cfg[0].parent
    try:
        seguridad = entregable.respaldar(*cfg, podar=False)  # sin poda: la elegida puede ser la más vieja
    except (OSError, sqlite3.Error) as e:
        raise HTTPException(409, f"No se pudo guardar la copia de lo actual en {cfg[1]}; no se restauró nada: {getattr(e, 'strerror', None) or e}")
    # ponytail: sin candado entre archivos; una escritura de otra petición durante la copia puede mezclar estados (app de un solo usuario).
    try:
        for archivo in sorted(elegida.glob("*.db")):
            copia, destino = sqlite3.connect(archivo), sqlite3.connect(datos / archivo.name)
            try:
                copia.backup(destino)
            finally:
                destino.close()
                copia.close()
        entregable.preparar_base(cfg[0], cfg[1], copiar=False)  # como al abrir: revisa y migra una copia de una versión anterior
        ids = [int(f.stem[5:]) for f in datos.glob("area_*.db") if f.stem[5:].isdigit()]
        con = sqlite3.connect(cfg[0])
        try:  # un área nueva no debe recibir el id (y el archivo viejo) de una que no estaba en la copia
            con.execute("UPDATE sqlite_sequence SET seq = max(seq, ?) WHERE name = 'area'", (max(ids, default=0),))
            con.commit()
        finally:
            con.close()
    except (OSError, sqlite3.Error, BaseNoUsable) as e:
        raise HTTPException(409, f"La restauración quedó a medias: {getattr(e, 'strerror', None) or e}. "
                                 f"Lo que había antes está en la copia {seguridad.name}.")
    request.state.evento = "respaldo_restaurado"
    return {"nombre": seguridad.name}
