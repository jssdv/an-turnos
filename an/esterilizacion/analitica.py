"""Métricas del dashboard de Analíticas. Solo lectura: nada se escribe en la base. Sin Qt."""
from collections import defaultdict
from datetime import timedelta

from . import demanda as dem
from . import cambios, flujo, puestos, reglas


def _ausencias(bd, ini, fin):
    """({(colab_id, fecha): tipo}, [Colaborador]) del rango; la primera novedad gana si se solapan."""
    gente = [p for p in bd.colaboradores() if p.en_solver]
    ids = {p.id for p in gente}
    out = {}
    for n in bd.novedades():
        if n.colab_id not in ids:
            continue
        d = max(n.desde, ini)
        while d <= min(n.hasta, fin):
            out.setdefault((n.colab_id, d), n.tipo)
            d += timedelta(days=1)
    return out, gente


def ausentismo(bd, ini, fin):
    aus, gente = _ausencias(bd, ini, fin)
    nombre = {p.id: p.nombre for p in gente}
    por_tipo, por_persona, por_mes = defaultdict(int), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    for (cid, f), tipo in aus.items():
        por_tipo[tipo] += 1
        por_persona[nombre[cid]][tipo] += 1
        por_mes[f"{f:%Y-%m}"][tipo] += 1
    dias = (fin - ini).days + 1
    pct = len(aus) / (dias * len(gente)) * 100 if gente else 0
    return {"por_tipo": dict(por_tipo), "por_persona": {k: dict(v) for k, v in por_persona.items()},
            "por_mes": {k: dict(v) for k, v in sorted(por_mes.items())}, "pct": pct}


def simultaneos(bd, ini, fin):
    aus, _ = _ausencias(bd, ini, fin)
    cuenta = defaultdict(int)
    for _, f in aus:
        cuenta[f] += 1
    serie = [(f, cuenta[f]) for f in flujo.fechas(ini, fin)]
    maximo = max((n for _, n in serie), default=0)
    fecha_max = next((f for f, n in serie if n == maximo), None) if maximo else None
    cuadro = bd.asignaciones_rango(ini, fin)
    dias = sorted({f for _, f in cuadro})
    riesgo = []
    if dias:
        falt = reglas.faltantes_periodo(bd.contexto(ini.year), cuadro, dias)
        riesgo = [f for f in dias if cuenta[f] and any(v[0] for v in falt[f].values())]
    return {"serie": serie, "maximo": maximo, "fecha_maximo": fecha_max, "dias_riesgo": riesgo}


def _presentes(ctx, cuadro, fecha, con_ayer):
    """Personas por tramo de 30 min: quienes empiezan hoy y, si `con_ayer`, la madrugada de las noches de ayer."""
    hay = [0] * dem.TRAMOS_DIA
    activos = {p.id for p in ctx.colabs if p.en_solver}
    ayer = fecha - timedelta(days=1)
    for (cid, f), cod in cuadro.items():
        if cid in activos and cod in ctx.turnos and (f == fecha or (f == ayer and con_ayer)):
            for off, t in dem.turno_tramos(ctx.turnos[cod]):
                if off == (0 if f == fecha else 1):
                    hay[t] += 1
    return hay


def _cruza(k, ini, fin):
    a, b = flujo.desde_clave(k)
    return a <= fin and b >= ini


def cobertura(bd, ini, fin):
    """Por periodo con cuadro que toca el rango: días con déficit, días con exceso y puestos obligatorios sin cubrir."""
    ctx, out = bd.contexto(ini.year), []
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        a, b = flujo.desde_clave(k)
        dias, cuadro = flujo.fechas(a, b), bd.asignaciones(k)
        deficit = exceso = 0
        for f in dias:
            con_ayer = f != a
            if any(v[0] for v in reglas.faltantes_dia(ctx, cuadro, f, con_ayer).values()):
                deficit += 1
            obl, des = dem.demanda_fecha(ctx, f, con_ayer)
            if any(h > o + d for h, o, d in zip(_presentes(ctx, cuadro, f, con_ayer), obl, des)):
                exceso += 1
        alertas = puestos.alertas_reparto(ctx, bd.asignacion_puesto(k), dias, bd.catalogo_puestos())
        out.append({"periodo": k, "dias_deficit": deficit, "dias_exceso": exceso, "puestos_sin_cubrir": len(alertas)})
    return out


def cambios_resumen(bd, ini, fin):
    """{periodo: {permuta, servicio, ajuste, excepciones}} de los cambios vigentes (sin anulados)."""
    out = {}
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        filas = [r for r in cambios.listar(bd, k) if not r["anulado_en"]]
        if filas:
            out[k] = {t: sum(r["tipo"] == t for r in filas) for t in ("permuta", "servicio", "ajuste")}
            out[k]["excepciones"] = sum(1 for r in filas if r["excepcion"])
    return out
