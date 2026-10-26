"""Rutas de escritura de los catálogos de un área: solicitudes, personal, novedades, turnos, puestos, demandas, parámetros y tarifas.
Cada una valida lo mismo que la pestaña de Qt y llama al núcleo (`BD.guardar_*`, `borrar_*`). No tocan la revisión de ningún periodo."""
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from an.turnos import flujo, solicitudes
from an.turnos.dominio import PRIORIDADES, TIPOS_COLAB, TIPOS_NOVEDAD, TIPOS_SOLICITUD, Colaborador, Novedad, Puesto, Solicitud, Turno

from .deps import Contexto, contexto_area

router = APIRouter(prefix="/api/areas/{area}")
RANGOS_PARAMETROS = {"usa_puestos": (0, 1), "ventana_semanas": (1, 8), "limite_permutas": (0, 20), "banco_tope_favor_h": (0, 48), "banco_tope_deuda_h": (0, 48),
                     "periodo_semanas": (1, 8), "max_noches_seguidas": (0, 7), "max_c_seguidos": (0, 7), "max_igual_seguidos": (0, 7),
                     "libre_tras_noche": (0, 3), "libres_por_semana": (1, 3), "fines_semana_libres": (0, 4)}
CONCEPTOS_TARIFA = ("dominical", "nocturno", "extra_diurna", "extra_nocturna", "noche_inicio")
COLOR = r"^[0-9A-Fa-f]{6}$"


def _evento(request, nombre):
    request.state.evento = nombre


def _rango(desde, hasta):
    if hasta < desde:
        raise HTTPException(422, "La fecha final es anterior a la inicial.")


def _persona(bd, id_):
    if not any(c.id == id_ for c in bd.colaboradores(False)):
        raise HTTPException(422, "Esa persona no existe en esta área")


def _guardar(f, *args):
    try:
        return f(*args)
    except ValueError as x:
        raise HTTPException(422, str(x))


# --- solicitudes --------------------------------------------------------------------------------
class SolicitudIn(BaseModel):
    colab_id: int
    tipo: Literal[*TIPOS_SOLICITUD]
    desde: date
    hasta: date
    turno: str = ""
    prioridad: Literal[*PRIORIDADES] = "normal"
    nota: str = Field("", max_length=300)


@router.post("/solicitudes", status_code=201)
def crear_solicitud(datos: SolicitudIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _rango(datos.desde, datos.hasta)
    _persona(ctx.bd, datos.colab_id)
    turno = ""
    if datos.tipo != "libre":
        if datos.turno not in ctx.bd.turnos():
            raise HTTPException(422, "Elige un turno para esta solicitud.")
        turno = datos.turno
    s = Solicitud(datos.colab_id, datos.tipo, datos.desde, datos.hasta, turno, datos.prioridad, datos.nota)
    ctx.bd.guardar_solicitud(s, ctx.usuario.nombre)
    _evento(request, "solicitud_creada")
    return {"id": s.id}


@router.delete("/solicitudes/{id}")
def borrar_solicitud(id: int, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    if not any(s.id == id for s in ctx.bd.solicitudes()):
        raise HTTPException(404, "Solicitud no encontrada")
    ctx.bd.borrar_solicitud(id)
    _evento(request, "solicitud_borrada")
    return {"ok": True}


@router.get("/periodos/{id}/solicitudes")
def evaluacion(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ?", (id,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    inicio, fin = flujo.desde_clave(f["clave"])
    c = ctx.bd.contexto(inicio.year)
    return [dict(id=r.solicitud.id, estado=r.estado, motivo=r.motivo)
            for r in solicitudes.evaluar(c, ctx.bd.asignaciones(f["clave"]), flujo.fechas(inicio, fin), ctx.bd.fijos(f["clave"]))]


# --- personal -----------------------------------------------------------------------------------
class ColaboradorIn(BaseModel):
    nombre: str = Field(max_length=120)
    tipo: Literal[*TIPOS_COLAB] = "regular"
    horas_sem: float = Field(42, gt=0, le=84)
    pct: float = Field(1.0, gt=0, le=1)
    permitidos: list[str] | None = None
    puestos_permitidos: list[int] | None = None
    estudio: list[tuple[int, Literal["M", "T"]]] = []
    activo: bool = True


def _colaborador(bd, datos, id_=0):
    nombre = datos.nombre.strip()
    if not nombre:
        raise HTTPException(422, "Escribe el nombre del colaborador.")
    turnos = bd.turnos(False)
    if datos.permitidos is not None and (not datos.permitidos or any(t not in turnos for t in datos.permitidos)):
        raise HTTPException(422, "Marca al menos un turno que pueda hacer (del catálogo).")
    catalogo = bd.catalogo_puestos()
    pp = datos.puestos_permitidos
    if pp is not None and (not pp or any(q not in catalogo for q in pp)):
        raise HTTPException(422, "Marca al menos un puesto que pueda ocupar (del catálogo).")
    if any(not 0 <= d <= 6 for d, _ in datos.estudio):
        raise HTTPException(422, "El día de estudio debe ir de 0 (lunes) a 6 (domingo).")
    fijo = catalogo[pp[0]].numero if pp and len(pp) == 1 else None  # como Qt: un solo puesto permitido = puesto fijo
    return Colaborador(id_, nombre, datos.tipo, datos.horas_sem, datos.pct, None if datos.permitidos is None else tuple(sorted(datos.permitidos)),
                       fijo, tuple(sorted(datos.estudio)), datos.activo, None if pp is None else tuple(sorted(pp)))


@router.post("/colaboradores", status_code=201)
def crear_colaborador(datos: ColaboradorIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _evento(request, "persona_creada")
    return {"id": _guardar(ctx.bd.guardar_colaborador, _colaborador(ctx.bd, datos))}


@router.put("/colaboradores/{id}")
def editar_colaborador(id: int, datos: ColaboradorIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _persona(ctx.bd, id)
    _evento(request, "persona_editada")
    return {"id": _guardar(ctx.bd.guardar_colaborador, _colaborador(ctx.bd, datos, id))}


@router.delete("/colaboradores/{id}")
def borrar_colaborador(id: int, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _persona(ctx.bd, id)
    _evento(request, "persona_borrada")
    return {"resultado": ctx.bd.borrar_colaborador(id)}


# --- novedades ----------------------------------------------------------------------------------
class NovedadIn(BaseModel):
    colab_id: int
    tipo: Literal[*TIPOS_NOVEDAD]
    desde: date
    hasta: date
    nota: str = Field("", max_length=300)


@router.post("/novedades", status_code=201)
def crear_novedad(datos: NovedadIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _rango(datos.desde, datos.hasta)
    _persona(ctx.bd, datos.colab_id)
    n = Novedad(datos.colab_id, datos.tipo, datos.desde, datos.hasta, datos.nota)
    ctx.bd.guardar_novedad(n)
    _evento(request, "novedad_creada")
    return {"id": n.id}


@router.delete("/novedades/{id}")
def borrar_novedad(id: int, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    if not any(n.id == id for n in ctx.bd.novedades()):
        raise HTTPException(404, "Novedad no encontrada")
    ctx.bd.borrar_novedad(id)
    _evento(request, "novedad_borrada")
    return {"ok": True}


# --- turnos -------------------------------------------------------------------------------------
class Pausa(BaseModel):
    ini: int = Field(ge=0, le=1439)
    min: int = Field(gt=0, le=1440)
    pagada: bool = False


class TurnoIn(BaseModel):
    codigo: str = Field(max_length=6)
    nombre: str = Field("", max_length=60)
    inicio: int = Field(ge=0, le=1439)
    fin: int = Field(ge=0, le=1439)
    color: str = Field("FFFFFF", pattern=COLOR)
    pausa: Pausa | None = None
    dom_fest: bool = True
    solver: bool = True
    activo: bool = True


def _turno(datos, codigo=None):
    cod = (codigo or datos.codigo).strip().upper()
    if not cod or cod == "L":
        raise HTTPException(422, "Escribe un código para el turno (distinto de L).")
    if datos.inicio == datos.fin:
        raise HTTPException(422, "El turno no puede empezar y terminar a la misma hora.")
    pausas = ({"ini": datos.pausa.ini, "min": datos.pausa.min, "pagada": datos.pausa.pagada},) if datos.pausa else ()
    t = Turno(cod, datos.nombre.strip() or cod, datos.inicio, datos.fin, datos.color.upper(), (), pausas, datos.dom_fest, datos.solver, datos.activo)
    if pausas and pausas[0]["ini"] + pausas[0]["min"] > t.duracion:
        raise HTTPException(422, "La pausa debe quedar dentro del turno.")
    return t


@router.post("/turnos", status_code=201)
def crear_turno(datos: TurnoIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    t = _turno(datos)
    if t.codigo in ctx.bd.turnos(False):
        raise HTTPException(409, f"Ya existe un turno «{t.codigo}».")
    ctx.bd.guardar_turno(t)
    _evento(request, "turno_creado")
    return {"codigo": t.codigo}


@router.put("/turnos/{codigo}")
def editar_turno(codigo: str, datos: TurnoIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    if codigo not in ctx.bd.turnos(False):
        raise HTTPException(404, "Turno no encontrado")
    ctx.bd.guardar_turno(_turno(datos, codigo))
    _evento(request, "turno_editado")
    return {"codigo": codigo}


@router.delete("/turnos/{codigo}")
def borrar_turno(codigo: str, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    if codigo not in ctx.bd.turnos(False):
        raise HTTPException(404, "Turno no encontrado")
    _evento(request, "turno_borrado")
    return {"resultado": ctx.bd.borrar_turno(codigo)}


# --- puestos y demandas -------------------------------------------------------------------------
class PuestoIn(BaseModel):
    numero: int = Field(ge=1, le=99)
    nombre: str = Field(max_length=60)
    color: str = Field("FFFFFF", pattern=COLOR)
    activo: bool = True


def _puesto_existe(bd, id_):
    if id_ not in bd.catalogo_puestos():
        raise HTTPException(404, "Puesto no encontrado")


@router.get("/demandas")
def leer_demandas(ctx: Contexto = Depends(contexto_area, scope="function")):
    return [dict(id=d.id, puesto_id=d.puesto_id, tipo_dia=d.tipo_dia, inicio=d.inicio, fin=d.fin, personas=d.personas, obligatorio=d.obligatorio)
            for d in ctx.bd.demandas()]


@router.post("/puestos", status_code=201)
def crear_puesto(datos: PuestoIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _evento(request, "puesto_creado")
    return {"id": _guardar(ctx.bd.guardar_puesto, Puesto(0, datos.numero, datos.nombre.strip(), datos.color.upper(), datos.activo))}


@router.put("/puestos/{id}")
def editar_puesto(id: int, datos: PuestoIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _puesto_existe(ctx.bd, id)
    _evento(request, "puesto_editado")
    return {"id": _guardar(ctx.bd.guardar_puesto, Puesto(id, datos.numero, datos.nombre.strip(), datos.color.upper(), datos.activo))}


@router.delete("/puestos/{id}")
def borrar_puesto(id: int, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _puesto_existe(ctx.bd, id)
    _evento(request, "puesto_borrado")
    return {"resultado": ctx.bd.borrar_puesto(id)}


class RequerimientoIn(BaseModel):
    dia: int = Field(ge=0, le=7)  # 0 lunes … 6 domingo, 7 festivo
    inicio: int = Field(ge=0, le=1439)
    fin: int = Field(ge=0, le=1440)
    personas: int = Field(ge=0, le=50)
    obligatorio: bool = True


def _requerimiento(datos, ctx, puesto_id, request):
    if len({(d.dia, d.inicio, d.fin) for d in datos}) != len(datos):
        raise HTTPException(422, "Un horario aparece dos veces el mismo día")
    if any(d.inicio == d.fin or d.inicio % 30 or d.fin % 30 for d in datos):
        raise HTTPException(422, "Las horas deben ser distintas y múltiplos de 30 minutos")
    ctx.bd.guardar_requerimiento([d.model_dump() for d in datos], puesto_id)
    _evento(request, "requerimiento_guardado")
    return {"ok": True}


@router.get("/requerimiento")
def leer_requerimiento(ctx: Contexto = Depends(contexto_area, scope="function")):
    return ctx.bd.requerimiento()


@router.put("/requerimiento")
def guardar_requerimiento(datos: list[RequerimientoIn], request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    """Personas por ventana horaria (la de cada turno) y día de la semana de un área sin puestos."""
    return _requerimiento(datos, ctx, 0, request)


@router.get("/puestos/{id}/requerimiento")
def leer_requerimiento_puesto(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    _puesto_existe(ctx.bd, id)
    return ctx.bd.requerimiento(id)


@router.put("/puestos/{id}/requerimiento")
def guardar_requerimiento_puesto(id: int, datos: list[RequerimientoIn], request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    """Lo mismo que el de un área sin puestos, para un puesto (obligatorio o deseable en todas sus filas)."""
    _puesto_existe(ctx.bd, id)
    return _requerimiento(datos, ctx, id, request)


# --- parámetros y tarifas -----------------------------------------------------------------------
@router.put("/parametros")
def guardar_parametros(datos: dict[str, int | str], request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    for k, v in datos.items():
        if k == "periodo_modo":
            if v not in ("mes", "semanas"):
                raise HTTPException(422, "«periodo_modo» debe ser «mes» o «semanas»")
        elif k not in RANGOS_PARAMETROS:
            raise HTTPException(422, f"Parámetro desconocido: {k}")
        else:
            lo, hi = RANGOS_PARAMETROS[k]
            if isinstance(v, bool) or not isinstance(v, int) or not lo <= v <= hi:
                raise HTTPException(422, f"«{k}» debe ser un entero entre {lo} y {hi}")
    for k, v in datos.items():  # todo validado: se guarda todo o nada
        ctx.bd.set_param(k, v)
    _evento(request, "parametros_guardados")
    return {"ok": True}


class TarifaIn(BaseModel):
    concepto: Literal[*CONCEPTOS_TARIFA]
    valor: float = Field(ge=0, le=5000)
    desde: date


@router.post("/tarifas", status_code=201)
def agregar_tarifa(datos: TarifaIn, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    ctx.bd.agregar_tarifa(datos.concepto, datos.valor, datos.desde)
    _evento(request, "tarifa_agregada")
    return {"ok": True}
