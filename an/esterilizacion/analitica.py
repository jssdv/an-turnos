"""Métricas del dashboard de Analíticas. Solo lectura: nada se escribe en la base. Sin Qt."""
from collections import defaultdict
from datetime import timedelta

from . import demanda as dem
from . import flujo, reglas


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
