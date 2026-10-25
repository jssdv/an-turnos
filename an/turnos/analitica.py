"""Métricas del dashboard de Analíticas. Solo lectura: nada se escribe en la base. Sin Qt."""
from collections import defaultdict
from datetime import timedelta
from math import ceil

from . import demanda as dem
from . import cambios, flujo, puestos, recargos, reglas


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


# --- entrega 2: horas, recargos y equidad ---------------------------------------------------------
def _reportes(bd, ini, fin, ventana=None):
    """[(periodo, [(Colaborador, reporte)])] de los periodos con cuadro que tocan el rango. `ventana` en semanas
    (por defecto la configurada); `"periodo"` = una sola ventana que abarca todo el periodo."""
    ctx, tar = bd.contexto(ini.year), bd.tarifas()
    conf = int(bd.param("ventana_semanas", 3))
    gente = [p for p in ctx.colabs if p.en_solver]
    out = []
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        dias, cuadro = flujo.fechas(*flujo.desde_clave(k)), bd.asignaciones(k)
        v = ceil(len(dias) / 7) if ventana == "periodo" else conf
        out.append((k, [(p, recargos.reporte(ctx, tar, p, cuadro, dias, v)) for p in gente]))
    return out


def _extras(reportes):
    suma = {"diurna": 0.0, "nocturna": 0.0}
    for _, r in reportes:
        for (tipo, jornada, _), h in r["cat"].items():
            if tipo == "extra":
                suma[jornada] += h
    return {k: round(v, 2) for k, v in suma.items()}


def horas_extra(bd, ini, fin):
    """Por periodo: horas extra diurnas y nocturnas con la ventana de N semanas y con una sola ventana del periodo."""
    conf = int(bd.param("ventana_semanas", 3))
    semanas, mes = _reportes(bd, ini, fin), _reportes(bd, ini, fin, "periodo")
    return [{"periodo": k, "ventana": conf, "mes": _extras(m), "semanas": _extras(s)}
            for (k, s), (_, m) in zip(semanas, mes)]


def recargos_resumen(bd, ini, fin):
    """{nombre: {festivo, nocturna, equivalentes}} en horas, sumando los periodos del rango (festivo = domingos y festivos)."""
    out = {}
    for _, filas in _reportes(bd, ini, fin):
        for p, r in filas:
            o = out.setdefault(p.nombre, {"festivo": 0.0, "nocturna": 0.0, "equivalentes": 0.0})
            o["festivo"] += sum(h for c, h in r["cat"].items() if c[2] == "festivo")
            o["nocturna"] += sum(h for c, h in r["cat"].items() if c[1] == "nocturna")
            o["equivalentes"] += r["equivalentes"]
    return {n: {k: round(v, 2) for k, v in o.items()} for n, o in out.items()}


def equidad(bd, ini, fin):
    """Noches, domingos y festivos trabajados por persona (turnos contados por su fecha de inicio)."""
    ctx = bd.contexto(ini.year)
    gente = {p.id: p.nombre for p in ctx.colabs if p.en_solver}
    por = {n: {"noches": 0, "domingos": 0, "festivos": 0} for n in gente.values()}
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        for (cid, f), cod in bd.asignaciones(k).items():
            t = ctx.turnos.get(cod)
            if cid not in gente or not t or not ini <= f <= fin:
                continue
            o = por[gente[cid]]
            o["noches"] += dem.es_noche(t)
            if f.weekday() == 6:
                o["domingos"] += 1
            elif f in ctx.fest:
                o["festivos"] += 1
    disp = {c: (max(o[c] for o in por.values()) - min(o[c] for o in por.values())) if por else 0
            for c in ("noches", "domingos", "festivos")}
    return {"por_persona": por, "dispersion": disp}


# --- entrega 3: banco de horas --------------------------------------------------------------------
def banco(bd, ini, fin):
    """Saldos al fin del rango y serie mensual (favor, deuda). Solo periodos cerrados y movimientos; sin proyecciones."""
    gente = {p.id: p.nombre for p in bd.colaboradores(solo_activos=False) if p.en_solver}
    cierres = [(flujo.desde_clave(per)[1], cid, trab - contr) for per, cid, contr, trab in bd.cierres()]
    movs = [(f, cid, h) for _, cid, f, h, _, _ in bd.movimientos()]

    def saldos(hasta):
        s = {cid: 0.0 for cid in gente}
        for f, cid, h in cierres + movs:
            if f <= hasta and cid in s:
                s[cid] += h
        return s

    serie, m = [], ini.year * 12 + ini.month - 1
    while m <= fin.year * 12 + fin.month - 1:
        y, mes = divmod(m, 12)
        s = saldos(flujo.periodo_mes(y, mes + 1)[1])
        serie.append((f"{mes + 1:02d}/{y % 100:02d}", round(sum(v for v in s.values() if v > 0), 2),
                      round(-sum(v for v in s.values() if v < 0), 2)))
        m += 1
    return {"saldos": {gente[c]: round(v, 2) for c, v in saldos(fin).items()}, "serie": serie}
