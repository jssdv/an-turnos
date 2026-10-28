"""Horas, ventana del art. 165 CST y recargos. Tarifas por fecha de vigencia (datos, no constantes)."""
from collections import defaultdict
from datetime import datetime, timedelta

def tarifa(tarifas, concepto, f):
    """Último valor vigente de `concepto` en la fecha `f`; tarifas = [(concepto, valor, desde)]."""
    return max((t for t in tarifas if t[0] == concepto and t[2] <= f), key=lambda t: t[2])[1]


def segmentos(turno, fecha, ctx, tarifas):
    """Tramos pagados del turno: [(inicio, fin, nocturno, festivo)] cortados en medianoche, 6:00 y el inicio de la noche."""
    noche = tarifa(tarifas, "noche_inicio", fecha)
    for a, b in turno.tramos():
        cur, fin = turno.inicio + a, turno.inicio + b
        while cur < fin:
            dia, m = divmod(cur, 1440)
            f = fecha + timedelta(days=dia)
            nxt = min(x for x in (360, noche, 1440) if x > m) + dia * 1440
            end = min(nxt, fin)
            ini = datetime.combine(fecha, datetime.min.time()) + timedelta(minutes=cur)
            yield ini, ini + timedelta(minutes=end - cur), (m < 360 or m >= noche), (f in ctx.fest or f.weekday() == 6)
            cur = end


def horas_df(turno, fecha, ctx):
    """Horas del turno que `fecha` inicia y que caen en un día domingo o festivo (calendario, igual que `segmentos`)."""
    total = 0
    for a, b in turno.tramos():
        cur, fin = turno.inicio + a, turno.inicio + b
        while cur < fin:
            dia = cur // 1440
            end = min(fin, (dia + 1) * 1440)
            f = fecha + timedelta(days=dia)
            total += (end - cur) * (ctx.tipo_dia(f) == "DF")
            cur = end
    return total / 60


def reporte(ctx, tarifas, colab, cuadro, fechas, ventana_sem=3):
    """Horas del mes de `colab` clasificadas por recargo. Ventanas de `ventana_sem` semanas contadas desde el
    primer día (ponytail: la ventana no cruza periodos; el siguiente arranca una nueva)."""
    fechas = sorted(fechas)
    segs = []
    for f in fechas:
        t = ctx.turnos.get(cuadro.get((colab.id, f), "L"))
        if t:
            segs += [(f, *s) for s in segmentos(t, f, ctx, tarifas)]
    segs.sort(key=lambda s: s[1])
    dias_vent = 7 * ventana_sem
    ventanas = defaultdict(list)
    for s in segs:
        ventanas[(s[0] - fechas[0]).days // dias_vent].append(s)
    out = {"trabajadas": 0.0, "contratadas": 0.0, "pendientes": 0.0, "adicionales": 0.0, "equivalentes": 0.0,
           "cat": defaultdict(float), "festivos_trabajados": 0, "h_nocturnas": 0.0, "h_dominicales": 0.0, "semanas": defaultdict(float)}
    for i in range((len(fechas) + dias_vent - 1) // dias_vent):
        dias = fechas[i * dias_vent:(i + 1) * dias_vent]
        libres = sum(1 for d in dias if not ctx.novedad(colab.id, d))
        contr = colab.horas_sem * colab.pct * libres / 7
        s_v = ventanas.get(i, [])
        trab = sum((s[2] - s[1]).total_seconds() / 3600 for s in s_v)
        exceso = max(0.0, trab - contr)
        out["contratadas"] += contr
        out["pendientes"] += max(0.0, contr - trab)
        out["adicionales"] += exceso
        restante = exceso  # las horas extra son las últimas trabajadas de la ventana
        for f, ini, fin, noct, fest in reversed(s_v):
            h = (fin - ini).total_seconds() / 3600
            extra = min(h, restante)
            restante -= extra
            for hh, es_extra in ((h - extra, False), (extra, True)):
                if hh <= 0:
                    continue
                dom = tarifa(tarifas, "dominical", f) if fest else 0
                if es_extra:
                    rec = tarifa(tarifas, "extra_nocturna" if noct else "extra_diurna", f) + dom
                    out["equivalentes"] += hh * (1 + rec / 100)
                else:
                    rec = (tarifa(tarifas, "nocturno", f) if noct else 0) + dom
                    out["equivalentes"] += hh * rec / 100
                out["cat"][("extra" if es_extra else "ordinaria", "nocturna" if noct else "diurna",
                            "festivo" if fest else "hábil")] += hh
    for f, ini, fin, noct, fest in segs:
        h = (fin - ini).total_seconds() / 3600
        out["trabajadas"] += h
        out["semanas"][f - timedelta(days=f.weekday())] += h
    for (_, jornada, dia), h in out["cat"].items():  # nocturnas y dominicales/festivas por separado: no se suman entre sí
        out["h_nocturnas"] += h * (jornada == "nocturna")
        out["h_dominicales"] += h * (dia == "festivo")
    out["festivos_trabajados"] = len({s[1].date() for s in segs if s[4]})
    out["habitual"] = out["festivos_trabajados"] >= 3
    return out
