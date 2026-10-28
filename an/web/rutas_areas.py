"""Rutas de lectura de un área. Cada una llama una función del núcleo; la API no reimplementa reglas."""
from dataclasses import asdict, is_dataclass
from datetime import date
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request

from an.turnos import analitica, cambios, flujo, reglas

from . import deps
from .deps import Contexto, contexto_area, usuario_actual

router = APIRouter(prefix="/api")
MAX_DIAS_ANALITICAS = 3660


@router.get("/areas")
def areas(request: Request, u=Depends(usuario_actual)):
    from . import conexion
    from an.turnos.pg import Conexion
    with request.app.state.pool.connection() as conn:
        conexion.alcance(conn, u.clinica_id)
        c = Conexion(conn, confirmar=False)
        return [dict(id=f["id"], nombre=f["nombre"], tipo=f["tipo"], permiso=f["permiso"]) for f in c.execute(
            "SELECT a.id, a.nombre, a.tipo, CASE WHEN ua.permiso IS NOT NULL THEN ua.permiso WHEN ? = 1 THEN 'ver' END AS permiso "
            "FROM area a LEFT JOIN usuario_area ua ON ua.area_id = a.id AND ua.usuario_id = ? ORDER BY a.id", (int(u.es_admin), u.id))
            if f["permiso"]]


def _plano(x):
    return asdict(x) if is_dataclass(x) else x._asdict() if hasattr(x, "_asdict") else x


def _lista(nombre, leer):
    @router.get(f"/areas/{{area}}/{nombre}")
    def ruta(ctx: Contexto = Depends(contexto_area, scope="function")):
        return [_plano(x) for x in leer(ctx.bd)]
    ruta.__name__ = f"leer_{nombre}"


_lista("turnos", lambda bd: bd.turnos(False).values())
_lista("puestos", lambda bd: bd.catalogo_puestos().values())
_lista("colaboradores", lambda bd: bd.colaboradores(False))
_lista("novedades", lambda bd: bd.novedades())
_lista("solicitudes", lambda bd: bd.solicitudes())
_lista("tarifas", lambda bd: bd.tarifas())


# Valores que usa el núcleo cuando el área no guardó el parámetro (`bd.param(clave, defecto)` en db.py, cambios.py, flujo.py,
# analitica.py), para que la web muestre lo vigente y no un campo vacío.
# ponytail: copia de los defectos del núcleo; si alguno cambia allí, cámbialo aquí (o súbelos a una constante común).
PARAMETROS_POR_DEFECTO = {
    "periodo_modo": "mes", "periodo_semanas": "4", "ventana_semanas": "3", "limite_permutas": "2", "max_noches_seguidas": "2",
    "max_c_seguidos": "2", "max_igual_seguidos": "3", "libre_tras_noche": "1", "libres_por_semana": "1", "fines_semana_libres": "1",
    "banco_tope_favor_h": "12", "banco_tope_deuda_h": "12", "usa_puestos": "1",
}


@router.get("/areas/{area}/parametros")
def parametros(ctx: Contexto = Depends(contexto_area, scope="function")):
    return PARAMETROS_POR_DEFECTO | {f["clave"]: f["valor"] for f in ctx.conn.execute("SELECT clave, valor FROM parametro")}


@router.get("/areas/{area}/periodos")
def periodos(ctx: Contexto = Depends(contexto_area, scope="function")):
    filas = ctx.conn.execute("SELECT id, clave, revision, publicado_en, cerrado_en FROM periodo ORDER BY clave").fetchall()
    rangos = {f["id"]: flujo.desde_clave(f["clave"]) for f in filas}
    return [dict(id=f["id"], clave=f["clave"], revision=f["revision"], publicado_en=f["publicado_en"], cerrado_en=f["cerrado_en"],
                 solapa_con=[o["id"] for o in filas if o["id"] != f["id"] and rangos[o["id"]][0] <= rangos[f["id"]][1] and rangos[f["id"]][0] <= rangos[o["id"]][1]])
            for f in filas]


def _periodo(ctx, id_):
    f = ctx.conn.execute("SELECT clave FROM periodo WHERE id = ?", (id_,)).fetchone()
    if not f:
        raise HTTPException(404, "Periodo no encontrado")
    inicio, fin = flujo.desde_clave(f["clave"])
    return f["clave"], inicio, fin


@router.get("/areas/{area}/periodos/{id}/cuadro")
def cuadro(id: int, version: Literal["original", "cambios"] = "cambios", ctx: Contexto = Depends(contexto_area, scope="function")):
    clave, _, _ = _periodo(ctx, id)
    revision = ctx.conn.execute("SELECT revision FROM periodo WHERE id = ?", (id,)).fetchone()[0]  # antes que las celdas: una revisión vieja solo da un 409 inofensivo
    vigente = version == "cambios"  # el original es la copia publicada: sin ediciones a mano ni puestos (no se guardan por versión)
    fijos, fijos_q = (ctx.bd.fijos(clave), ctx.bd.puestos_fijos(clave)) if vigente else (set(), {})
    usa = ctx.bd.usa_puestos() and vigente
    return {"clave": clave, "version": version, "revision": revision, "usa_puestos": usa,
            "celdas": [dict(colab_id=c, fecha=f, turno=t, fijo=(c, f) in fijos, **({"puesto": cambios.puesto_de(ctx.bd, clave, c, f),
                                                                                   "puesto_fijo": (c, f) in fijos_q} if usa else {}))
                       for (c, f), t in sorted(ctx.bd.asignaciones(clave, version).items())]}


@router.get("/areas/{area}/periodos/{id}/alertas")
def alertas(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    clave, inicio, fin = _periodo(ctx, id)
    fijos = ctx.bd.fijos(clave)
    return [_plano(a) if not isinstance(a, str) else a
            for a in reglas.validar(ctx.bd.contexto(inicio.year), ctx.bd.asignaciones(clave), flujo.fechas(inicio, fin), fijos)]


@router.get("/areas/{area}/periodos/{id}/puestos")
def puestos_periodo(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    clave, _, _ = _periodo(ctx, id)
    return [_plano(x) for x in ctx.bd.asignacion_puesto(clave)]


@router.get("/areas/{area}/periodos/{id}/horas")
def horas(id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    _, inicio, fin = _periodo(ctx, id)
    return [dict(colab_id=c, contratadas=a, trabajadas=b) for c, a, b in flujo.resumen_horas(ctx.bd, inicio, fin)]


@router.get("/areas/{area}/analiticas")
def analiticas(desde: date, hasta: date, ctx: Contexto = Depends(contexto_area, scope="function")):
    if hasta < desde or (hasta - desde).days > MAX_DIAS_ANALITICAS:
        raise HTTPException(422, f"El rango debe ir de «desde» a «hasta» y no pasar de {MAX_DIAS_ANALITICAS} días")
    return {"ausentismo": analitica.ausentismo(ctx.bd, desde, hasta), "cobertura": analitica.cobertura(ctx.bd, desde, hasta),
            "recargos": analitica.recargos_resumen(ctx.bd, desde, hasta), "simultaneos": analitica.simultaneos(ctx.bd, desde, hasta),
            "cambios": analitica.cambios_resumen(ctx.bd, desde, hasta), "horas_extra": analitica.horas_extra(ctx.bd, desde, hasta),
            "equidad": analitica.equidad(ctx.bd, desde, hasta), "banco": analitica.banco(ctx.bd, desde, hasta)}
