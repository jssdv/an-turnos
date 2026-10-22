"""Validación pura de un cuadro {(colab_id, fecha): código}. Sin GUI ni base de datos."""
from collections import namedtuple
from datetime import timedelta

from . import demanda as dem
from .dominio import DESCANSO_MIN, intervalo

Alerta = namedtuple("Alerta", "nivel fecha colab_id texto")


def validar_catalogo(turnos):
    return [Alerta("aviso", None, None, f"El turno {t.codigo} dura {t.duracion / 60:g} h y no tiene pausa de almuerzo.")
            for t in turnos.values() if t.duracion > 360 and not t.pausas]


FRANJA_NOMBRE = {"M": "mañana", "T": "tarde", "N": "noche"}


def texto_tramos(ini, fin):
    """«08:00–12:00» a partir de tramos de 30 min (el fin es exclusivo y puede ser el inicio del día siguiente)."""
    hm = lambda t: f"{t * 30 // 60 % 24:02d}:{t * 30 % 60:02d}"
    return f"{hm(ini)}–{hm(fin)}"


def faltantes_dia(ctx, cuadro, fecha, con_ayer=True):
    """{franja: (faltante_máximo, [(tramo_ini, tramo_fin, falta), ...])} del día `fecha` frente a la demanda obligatoria
    de los puestos. Cuenta a quienes empiezan hoy y, si `con_ayer`, la madrugada de las noches de ayer."""
    obl, _ = dem.demanda_fecha(ctx, fecha, con_ayer)
    hay = [0] * dem.TRAMOS_DIA
    activos = {p.id for p in ctx.colabs if p.en_solver}
    ayer = fecha - timedelta(days=1)
    for (cid, f), cod in cuadro.items():
        if cid in activos and cod in ctx.turnos and (f == fecha or (f == ayer and con_ayer)):
            for off, t in dem.turno_tramos(ctx.turnos[cod]):
                if off == (0 if f == fecha else 1):
                    hay[t] += 1
    out = {}
    for fr, tramos in dem.FRANJAS.items():
        tramos = list(tramos)
        faltas = [max(0, obl[t] - hay[t]) for t in tramos]
        rangos, i = [], 0
        while i < len(tramos):
            if not faltas[i]:
                i += 1
                continue
            j = i
            while j + 1 < len(tramos) and faltas[j + 1] == faltas[i] and tramos[j + 1] % dem.TRAMOS_DIA == (tramos[j] + 1) % dem.TRAMOS_DIA:
                j += 1
            rangos.append((tramos[i], (tramos[j] + 1) % dem.TRAMOS_DIA, faltas[i]))
            i = j + 1
        out[fr] = (max(faltas, default=0), rangos)
    return out


def faltantes_periodo(ctx, cuadro, fechas):
    """{fecha: faltantes_dia(...)}; del primer día no se exige la madrugada que viene de la noche anterior (se desconoce)."""
    fechas = sorted(fechas)
    return {f: faltantes_dia(ctx, cuadro, f, con_ayer=f != fechas[0]) for f in fechas}


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
            if t and dem.es_noche(t):
                for k in range(1, ctx.libre_tras_noche + 1):
                    b = a + timedelta(days=k)
                    if b in dias and cuadro.get((p.id, b), "L") in ctx.turnos and (p.id, b) not in fijos:
                        out.append(Alerta("aviso", b, p.id, f"{nombres[p.id]}: sin día libre después de la noche del {a:%d/%m}"))
                        break
        noche = lambda d: (t := ctx.turnos.get(cuadro.get((p.id, d), "L"))) is not None and dem.es_noche(t)
        corrido = lambda d: (t := ctx.turnos.get(cuadro.get((p.id, d), "L"))) is not None and dem.es_corrido(t)
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
                if t and not dem.es_noche(t) and not dem.es_corrido(t) and cuadro.get((p.id, a - timedelta(days=1)), "L") != cod:
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
    for f, por_franja in faltantes_periodo(ctx, cuadro, fechas).items():
        for fr, (peor, rangos) in por_franja.items():
            if peor:
                tramos = ", ".join(texto_tramos(a, b) for a, b, _ in rangos)
                out.append(Alerta("error", f, None, f"{f:%d/%m}: faltan {peor} en {FRANJA_NOMBRE[fr]} ({tramos})"))
    return out
