"""Validación pura de un cuadro {(colab_id, fecha): código}. Sin GUI ni base de datos."""
from collections import namedtuple
from datetime import timedelta

from dominio import DESCANSO_MIN, intervalo

Alerta = namedtuple("Alerta", "nivel fecha colab_id texto")


def validar_catalogo(turnos):
    return [Alerta("aviso", None, None, f"El turno {t.codigo} dura {t.duracion / 60:g} h y no tiene pausa de almuerzo.")
            for t in turnos.values() if t.duracion > 360 and not t.pausas]


def cobertura_dia(ctx, cuadro, f):
    """{franja: personas} del día `f` (un turno suma a cada franja que cubre)."""
    cuenta = {"M": 0, "T": 0, "N": 0}
    solver = {p.id for p in ctx.colabs if p.en_solver}
    for (cid, d), cod in cuadro.items():
        if d == f and cid in solver and cod in ctx.turnos:
            for fr in ctx.turnos[cod].cubre:
                cuenta[fr] += 1
    return cuenta


def validar(ctx, cuadro, fechas):
    out = []
    fechas = sorted(fechas)
    nombres = {p.id: p.nombre for p in ctx.colabs}
    en = [p for p in ctx.colabs if p.en_solver]
    for p in en:
        for f in fechas:
            cod = cuadro.get((p.id, f), "L")
            if cod in ctx.turnos:
                motivo = ctx.bloqueo(p, ctx.turnos[cod], f)
                if motivo:
                    out.append(Alerta("error", f, p.id, f"{nombres[p.id]}: {cod} no permitido ({motivo})"))
            elif cod != "L":
                out.append(Alerta("error", f, p.id, f"{nombres[p.id]}: código desconocido {cod}"))
        for a, b in zip(fechas, fechas[1:]):
            ta, tb = cuadro.get((p.id, a), "L"), cuadro.get((p.id, b), "L")
            if ta in ctx.turnos and tb in ctx.turnos and b - a == timedelta(days=1):
                fin = intervalo(ctx.turnos[ta], a)[1]
                ini = intervalo(ctx.turnos[tb], b)[0]
                if (ini - fin).total_seconds() / 60 < DESCANSO_MIN:
                    out.append(Alerta("error", b, p.id, f"{nombres[p.id]}: menos de 12 h entre {ta} ({a:%d/%m}) y {tb} ({b:%d/%m})"))
        for lunes in (f for f in fechas if f.weekday() == 0):
            sem = [lunes + timedelta(days=i) for i in range(7)]
            if sem[-1] in fechas and all(cuadro.get((p.id, d), "L") in ctx.turnos for d in sem):
                out.append(Alerta("error", lunes, p.id, f"{nombres[p.id]}: sin día libre en la semana del {lunes:%d/%m}"))
    for f in fechas:
        req, hay = ctx.cobertura[ctx.tipo_dia(f)], cobertura_dia(ctx, cuadro, f)
        for fr, n in req.items():
            if hay[fr] < n:
                out.append(Alerta("error", f, None, f"{f:%d/%m}: faltan {n - hay[fr]} en {fr} (hay {hay[fr]}, se requieren {n})"))
    return out
