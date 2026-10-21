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


def validar(ctx, cuadro, fechas, fijos=()):
    """`fijos`: celdas (colab_id, fecha) editadas a mano; romper allí «libre tras noche» es decisión de quien coordina."""
    out = []
    fechas = sorted(fechas)
    dias = set(fechas)
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
        for a in fechas:  # libre después de una noche
            t = ctx.turnos.get(cuadro.get((p.id, a), "L"))
            if t and "N" in t.cubre:
                for k in range(1, ctx.libre_tras_noche + 1):
                    b = a + timedelta(days=k)
                    if b in dias and cuadro.get((p.id, b), "L") in ctx.turnos and (p.id, b) not in fijos:
                        out.append(Alerta("aviso", b, p.id, f"{nombres[p.id]}: sin día libre después de la noche del {a:%d/%m}"))
                        break
        noche = lambda d: (t := ctx.turnos.get(cuadro.get((p.id, d), "L"))) is not None and "N" in t.cubre
        corrido = lambda d: (t := ctx.turnos.get(cuadro.get((p.id, d), "L"))) is not None and len(t.cubre) > 1
        paso = ctx.libre_tras_noche + 1
        for a in fechas:  # rachas demasiado largas (si alguna celda es edición manual, es decisión de quien coordina)
            if ctx.max_noches and noche(a) and not noche(a - timedelta(days=paso)):
                n = 0
                while noche(a + timedelta(days=paso * n)):
                    n += 1
                if n > ctx.max_noches and not any((p.id, a + timedelta(days=paso * k)) in fijos for k in range(n)):
                    out.append(Alerta("aviso", a, p.id, f"{nombres[p.id]}: {n} noches seguidas desde el {a:%d/%m} (máximo {ctx.max_noches})"))
            if ctx.max_igual:
                cod = cuadro.get((p.id, a), "L")
                t = ctx.turnos.get(cod)
                if t and "N" not in t.cubre and len(t.cubre) == 1 and cuadro.get((p.id, a - timedelta(days=1)), "L") != cod:
                    n = 0
                    while cuadro.get((p.id, a + timedelta(days=n)), "L") == cod:
                        n += 1
                    if n > ctx.max_igual and not any((p.id, a + timedelta(days=k)) in fijos for k in range(n)):
                        out.append(Alerta("aviso", a, p.id, f"{nombres[p.id]}: {n} {cod} seguidos desde el {a:%d/%m} (máximo {ctx.max_igual})"))
            if ctx.max_c and corrido(a) and not corrido(a - timedelta(days=1)):
                n = 0
                while corrido(a + timedelta(days=n)):
                    n += 1
                if n > ctx.max_c and not any((p.id, a + timedelta(days=k)) in fijos for k in range(n)):
                    out.append(Alerta("aviso", a, p.id, f"{nombres[p.id]}: {n} corridos seguidos desde el {a:%d/%m} (máximo {ctx.max_c})"))
        for lunes in (f for f in fechas if f.weekday() == 0):
            sem = [lunes + timedelta(days=i) for i in range(7)]
            if sem[-1] in dias and sum(cuadro.get((p.id, d), "L") not in ctx.turnos for d in sem) < ctx.libres_semana:
                out.append(Alerta("error", lunes, p.id, f"{nombres[p.id]}: menos de {ctx.libres_semana} día(s) libre(s) en la semana del {lunes:%d/%m}"))
        fines = [(f, f + timedelta(days=1)) for f in fechas if f.weekday() == 5 and f + timedelta(days=1) in dias]
        if ctx.fines_libres and fines:
            libre = lambda x: cuadro.get((p.id, x), "L") not in ctx.turnos
            hay = sum(libre(s) and libre(d) for s, d in fines)
            manual = sum(not (libre(s) and libre(d)) and ((p.id, s) in fijos or (p.id, d) in fijos) for s, d in fines)
            if hay + manual < min(ctx.fines_libres, len(fines)):
                out.append(Alerta("aviso", None, p.id, f"{nombres[p.id]}: sin fin de semana libre (sábado y domingo) en este periodo"))
    for f in fechas:
        req, hay = ctx.cobertura[ctx.tipo_dia(f)], cobertura_dia(ctx, cuadro, f)
        for fr, n in req.items():
            if hay[fr] < n:
                out.append(Alerta("error", f, None, f"{f:%d/%m}: faltan {n - hay[fr]} en {fr} (hay {hay[fr]}, se requieren {n})"))
    return out
