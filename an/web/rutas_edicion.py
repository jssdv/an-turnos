"""Rutas de escritura del cuadro de un periodo. Cada una exige `If-Match: <revision>`, bloquea la fila del periodo, llama al núcleo
(`cambios`, `flujo`) y sube la revisión. Si algo falla la excepción HTTP deshace la transacción de `contexto_area`."""
from collections import namedtuple
from datetime import date, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field

from an.turnos import cambios, flujo, puestos, reglas

from .deps import Contexto, contexto_area, leer_revision

router = APIRouter(prefix="/api")
MAX_CELDAS = 400
MAX_DIAS = 366
Periodo = namedtuple("Periodo", "clave inicio fin revision")


class CeldaIn(BaseModel):
    colab_id: int
    fecha: date
    turno: str = "L"


class Cambio(BaseModel):
    tipo: Literal["permuta", "servicio", "ajuste"]
    celdas: list[CeldaIn] = Field(min_length=1, max_length=MAX_CELDAS)
    motivo: str = Field("", max_length=500)
    excepcion: bool = False


class NuevoPeriodo(BaseModel):
    inicio: date
    fin: date


def bloquear(ctx, id, if_match):
    """Valida `If-Match` y bloquea el periodo hasta el final de la transacción. 409 con la revisión actual y quién cambió si no coincide."""
    revision = leer_revision(if_match)
    f = ctx.conn.execute("SELECT clave, revision, modificado_por FROM periodo WHERE id = ? FOR UPDATE", (id,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    if f["revision"] != revision:
        raise HTTPException(409, {"mensaje": "El periodo cambió; recárgalo antes de continuar.", "revision": f["revision"],
                                  "modificado_por": f["modificado_por"] or "Alguien"})
    inicio, fin = flujo.desde_clave(f["clave"])
    return Periodo(f["clave"], inicio, fin, f["revision"])


def subir(ctx, id, request, evento):
    """Sube la revisión, anota quién cambió y deja el evento para la auditoría. Devuelve la revisión nueva."""
    request.state.evento = evento
    return ctx.conn.execute("UPDATE periodo SET revision = revision + 1, modificado_por = ?, modificado_en = now() WHERE id = ? RETURNING revision",
                            (ctx.usuario.nombre, id)).fetchone()[0]


def abierto(ctx, p):
    if ctx.bd.periodo_cerrado(p.clave):
        raise HTTPException(409, "El periodo está cerrado. Reábrelo para cambiarlo.")


def textos_alertas(bd, clave, inicio, fin):
    """Reglas y puestos que quedan sin cubrir en el reparto (lo mismo que el toast de Qt)."""
    dias, c = flujo.fechas(inicio, fin), bd.contexto(inicio.year)
    return ([a.texto for a in reglas.validar(c, bd.asignaciones(clave), dias, bd.fijos(clave))]
            + [a.texto for a in puestos.alertas_reparto(c, bd.asignacion_puesto(clave), dias, bd.catalogo_puestos())])


def _nuevas(antes, despues):
    return [t for t in despues if t not in antes]


def _validar_celdas(bd, p, celdas, con_turno):
    """Misma regla que `_editable` de Qt: persona del cuadro, fecha del periodo, turno conocido y no una libre cubierta por novedad."""
    c = bd.contexto(p.inicio.year)
    gente = {x.id for x in c.colabs if x.en_solver}
    actual = bd.asignaciones(p.clave)
    vistas = set()
    for x in celdas:
        if x.colab_id not in gente:
            raise HTTPException(422, "Esa persona no está en el cuadro")
        if not p.inicio <= x.fecha <= p.fin:
            raise HTTPException(422, f"El {x.fecha:%d/%m} está fuera del periodo")
        if (x.colab_id, x.fecha) in vistas:
            raise HTTPException(422, "Una celda aparece dos veces")
        vistas.add((x.colab_id, x.fecha))
        if con_turno and x.turno != "L" and x.turno not in c.turnos:
            raise HTTPException(422, f"«{x.turno}» no es un turno. Usa L o uno de: {', '.join(c.turnos)}.")
        if c.novedad(x.colab_id, x.fecha) and actual.get((x.colab_id, x.fecha), "L") == "L":
            raise HTTPException(422, f"El {x.fecha:%d/%m} tiene una novedad; esa celda no se puede cambiar")


def _cupos(bd, clave, ids):
    return [dict(colab_id=c, usadas=cambios.cupo(bd, clave, c)[0], limite=cambios.limite(bd)) for c in ids]


@router.post("/areas/{area}/periodos/{id}/cambios")
def registrar(id: int, datos: Cambio, request: Request, if_match: str | None = Header(None), ctx: Contexto = Depends(contexto_area, scope="function")):
    p = bloquear(ctx, id, if_match)
    abierto(ctx, p)
    bd = ctx.bd
    if datos.tipo == "permuta" and len(datos.celdas) != 2:
        raise HTTPException(422, "Una permuta es entre dos celdas")
    _validar_celdas(bd, p, datos.celdas, datos.tipo != "permuta")
    antes = textos_alertas(bd, p.clave, p.inicio, p.fin)
    usuario, nuevas = ctx.usuario.nombre, [(x.colab_id, x.fecha, x.turno) for x in datos.celdas]
    try:
        if datos.tipo == "permuta":
            (a, fa, _), (b, fb, _) = nuevas
            ids = cambios.permuta(bd, p.clave, a, fa, b, fb, datos.motivo, usuario, datos.excepcion)
        elif datos.tipo == "servicio":
            ids = cambios.servicio(bd, p.clave, nuevas, datos.motivo, usuario)
        else:
            ids = cambios.ajuste(bd, p.clave, nuevas, datos.motivo, usuario)
    except cambios.LimiteExcedido as x:
        raise HTTPException(409, {"mensaje": str(x), "ids": x.ids, "cupos": _cupos(bd, p.clave, x.ids)})
    except cambios.ErrorCambio as x:
        raise HTTPException(422, str(x))
    flujo.recalcular(bd, p.inicio, p.fin)
    return {"revision": subir(ctx, id, request, f"cambio_{datos.tipo}"), "ids": ids,
            "alertas_nuevas": _nuevas(antes, textos_alertas(bd, p.clave, p.inicio, p.fin))}


def _periodo_de(ctx, id):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ?", (id,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    return f["clave"]


@router.get("/areas/{area}/periodos/{id}/cambios")
def listar(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    return [{**{k: r[k] for k in ("id", "tipo", "registrado_en", "usuario", "colab_a", "colab_b", "motivo", "excepcion", "anulado_en", "anulado_por")},
             "excepcion": bool(r["excepcion"]),
             "celdas": [dict(colab_id=c, fecha=f.isoformat(), antes=a, despues=d) for c, f, a, d in r["celdas"]]}
            for r in cambios.listar(ctx.bd, _periodo_de(ctx, id))]


@router.get("/areas/{area}/periodos/{id}/cupos")
def cupos(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    clave = _periodo_de(ctx, id)
    return _cupos(ctx.bd, clave, [c.id for c in ctx.bd.contexto(flujo.desde_clave(clave)[0].year).colabs if c.en_solver])


@router.post("/areas/{area}/periodos/{id}/cambios/{cambio}/anular")
def anular(id: int, cambio: int, request: Request, if_match: str | None = Header(None), ctx: Contexto = Depends(contexto_area, scope="function")):
    p = bloquear(ctx, id, if_match)
    f = ctx.conn.execute("SELECT periodo FROM cambio_turno WHERE id = ?", (cambio,)).fetchone()
    if not f or f["periodo"] != p.clave:
        raise HTTPException(404, "Cambio no encontrado")
    abierto(ctx, p)
    bd = ctx.bd
    antes = textos_alertas(bd, p.clave, p.inicio, p.fin)
    try:
        hecho = cambios.anular(bd, cambio, ctx.usuario.nombre)
    except cambios.EditadoDespues as x:
        raise HTTPException(409, {"mensaje": str(x), "celdas": [dict(colab_id=c, fecha=d.isoformat()) for c, d in x.celdas]})
    except cambios.ErrorCambio as x:
        raise HTTPException(422, str(x))
    if not hecho:
        return {"revision": p.revision, "anulado": False, "alertas_nuevas": []}
    flujo.recalcular(bd, p.inicio, p.fin)
    return {"revision": subir(ctx, id, request, "cambio_anulado"), "anulado": True,
            "alertas_nuevas": _nuevas(antes, textos_alertas(bd, p.clave, p.inicio, p.fin))}


def _solapes(ctx, inicio, fin):
    """[(id, clave)] de los periodos del área que comparten alguna fecha con inicio..fin."""
    return [(f["id"], f["clave"]) for f in ctx.conn.execute("SELECT id, clave FROM periodo ORDER BY clave")
            if (o := flujo.desde_clave(f["clave"])) and o[0] <= fin and inicio <= o[1]]


@router.post("/areas/{area}/periodos", status_code=201)
def crear_periodo(datos: NuevoPeriodo, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    if datos.fin < datos.inicio or datos.fin - datos.inicio > timedelta(days=MAX_DIAS - 1):
        raise HTTPException(422, f"El periodo debe ir de «inicio» a «fin» y durar como máximo {MAX_DIAS} días")
    ctx.conn.execute("SELECT pg_advisory_xact_lock(?)", (int(request.path_params["area"]),))  # dos altas simultáneas no se solapan entre sí
    if solapes := _solapes(ctx, datos.inicio, datos.fin):
        raise HTTPException(409, f"Se solapa con el periodo {solapes[0][1].replace('/', ' a ')}. Dos cuadros no pueden compartir fechas.")
    clave = flujo.clave(datos.inicio, datos.fin)
    request.state.evento = "periodo_creado"
    return {"id": ctx.conn.execute("INSERT INTO periodo (clave) VALUES (?) RETURNING id", (clave,)).fetchone()[0], "clave": clave, "revision": 0}


def _accion(nombre, hacer, evento, cerrado_ok=False):
    @router.post(f"/areas/{{area}}/periodos/{{id}}/{nombre}")
    def ruta(id: int, request: Request, if_match: str | None = Header(None), ctx: Contexto = Depends(contexto_area, scope="function")):
        p = bloquear(ctx, id, if_match)
        if not cerrado_ok:
            abierto(ctx, p)
        hacer(ctx, id, p)
        return {"revision": subir(ctx, id, request, evento)}
    ruta.__name__ = nombre


def _publicar(ctx, id, p):
    ctx.bd.publicar(p.clave)
    ctx.conn.execute("UPDATE periodo SET publicado_en = now() WHERE id = ?", (id,))


def _restaurar(ctx, id, p):
    ctx.bd.restaurar(p.clave)
    flujo.recalcular(ctx.bd, p.inicio, p.fin)


def _cerrar(ctx, id, p):
    try:
        flujo.cerrar(ctx.bd, p.inicio, p.fin)
    except ValueError as x:
        raise HTTPException(409, str(x))
    ctx.conn.execute("UPDATE periodo SET cerrado_en = now() WHERE id = ?", (id,))


def _reabrir(ctx, id, p):
    if not ctx.bd.periodo_cerrado(p.clave):
        raise HTTPException(409, "El periodo no está cerrado.")
    ctx.bd.reabrir_periodo(p.clave)
    ctx.conn.execute("UPDATE periodo SET cerrado_en = NULL WHERE id = ?", (id,))


_accion("publicar", _publicar, "periodo_publicado")
_accion("restaurar", _restaurar, "periodo_restaurado")
_accion("cerrar", _cerrar, "periodo_cerrado")
_accion("reabrir", _reabrir, "periodo_reabierto", cerrado_ok=True)
