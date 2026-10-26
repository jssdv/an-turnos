"""Usuarios y permisos por área de una clínica, solo para su administrador (`es_admin`). Reutiliza an/web/admin.py (la misma lógica de la línea de comandos)."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import admin, auth, conexion
from .deps import usuario_actual

router = APIRouter(prefix="/api/usuarios")


class NuevoUsuario(BaseModel):
    correo: str = Field(pattern=r"^[^@\s]+@[^@\s]+\.[^@\s]+$", max_length=200)
    nombre: str = Field(min_length=1, max_length=120)
    es_admin: bool = False


class Permiso(BaseModel):
    permiso: str | None = Field(None, pattern="^(ver|editar)$")


def _con_clinica(request, u, hacer):
    """Abre una transacción con el alcance de la clínica del administrador y llama `hacer(conn)`; ErrorAdmin → 409."""
    if not u.es_admin:
        raise HTTPException(403, "Solo el administrador de la clínica puede gestionar usuarios")
    with request.app.state.pool.connection() as conn:
        conexion.alcance(conn, u.clinica_id)
        try:
            return hacer(conn)
        except admin.ErrorAdmin as x:
            raise HTTPException(409, str(x))


def _existe(conn, id_):
    if not conn.execute("SELECT 1 FROM usuario WHERE id = %s", (id_,)).fetchone():
        raise HTTPException(404, "Usuario no encontrado")


@router.get("")
def listar(request: Request, u=Depends(usuario_actual)):
    def hacer(conn):
        permisos = {}
        for f in conn.execute("SELECT usuario_id, area_id, permiso FROM usuario_area ORDER BY area_id"):
            permisos.setdefault(f["usuario_id"], []).append(dict(area_id=f["area_id"], permiso=f["permiso"]))
        return [dict(id=f["id"], correo=f["correo"], nombre=f["nombre"], es_admin=f["es_admin"], activo=f["activo"], debe_cambiar=f["debe_cambiar"],
                     permisos=permisos.get(f["id"], []))
                for f in conn.execute("SELECT id, correo, nombre, es_admin, activo, debe_cambiar FROM usuario ORDER BY nombre, id")]
    return _con_clinica(request, u, hacer)


@router.post("", status_code=201)
def crear(datos: NuevoUsuario, request: Request, u=Depends(usuario_actual)):
    id_, clave = _con_clinica(request, u, lambda conn: admin.crear_usuario(conn, u.clinica_id, datos.correo, datos.nombre.strip(), datos.es_admin))
    request.state.evento = "usuario_creado"
    return {"id": id_, "clave_temporal": clave}  # se muestra una sola vez; la auditoría no guarda cuerpos


@router.put("/{id}/areas/{area}")
def permiso(id: int, area: int, datos: Permiso, request: Request, reemplazar: bool = False, u=Depends(usuario_actual)):
    def hacer(conn):
        _existe(conn, id)
        if not conn.execute("SELECT 1 FROM area WHERE id = %s", (area,)).fetchone():
            raise HTTPException(404, "Área no encontrada")
        if datos.permiso is None:
            admin.quitar_permiso(conn, id, area)
            return
        if datos.permiso == "editar" and reemplazar:  # pasa al editor actual a «ver» en la misma transacción
            conn.execute("UPDATE usuario_area SET permiso = 'ver' WHERE area_id = %s AND permiso = 'editar' AND usuario_id <> %s", (area, id))
        admin.dar_permiso(conn, id, area, datos.permiso)
    _con_clinica(request, u, hacer)
    request.state.evento = "permiso_cambiado"
    return {"ok": True}


@router.post("/{id}/desactivar")
def desactivar(id: int, request: Request, u=Depends(usuario_actual)):
    if id == u.id:
        raise HTTPException(409, "No puedes desactivar tu propio usuario")
    def hacer(conn):
        _existe(conn, id)
        conn.execute("UPDATE usuario SET activo = false WHERE id = %s", (id,))
        conn.execute("SELECT app_cerrar_sesiones(%s)", (id,))
    _con_clinica(request, u, hacer)
    request.state.evento = "usuario_desactivado"
    return {"ok": True}


@router.post("/{id}/clave")
def restablecer(id: int, request: Request, u=Depends(usuario_actual)):
    def hacer(conn):
        _existe(conn, id)
        clave = secrets.token_urlsafe(12)
        conn.execute("UPDATE usuario SET hash_clave = %s, debe_cambiar = true WHERE id = %s", (auth.hash_clave(clave), id))
        conn.execute("SELECT app_cerrar_sesiones(%s)", (id,))
        return clave
    clave = _con_clinica(request, u, hacer)
    request.state.evento = "clave_restablecida"
    return {"clave_temporal": clave}
