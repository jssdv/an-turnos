"""Capacitación mensual: una sesión por semana como máximo (lunes; si es festivo, el siguiente día hábil)."""
from collections import defaultdict
from datetime import timedelta


def dia_sesion(ctx, lunes):
    d = lunes
    while d < lunes + timedelta(days=7) and ctx.tipo_dia(d) == "DF":
        d += timedelta(days=1)
    return d if ctx.tipo_dia(d) == "LS" else None


def programar(ctx, cuadro, fechas):
    """Devuelve ([(fecha, colab_id)], [colab_id sin sesión posible]). Usa las menos sesiones que permitan asistir a todos;
    asiste quien trabaja un turno que cubre la mañana ese día y no tiene novedad."""
    fechas = sorted(fechas)
    lunes = sorted({f - timedelta(days=f.weekday()) for f in fechas})
    sesiones = [d for d in (dia_sesion(ctx, l) for l in lunes) if d and d in fechas]
    gente = [p for p in ctx.colabs if p.en_solver]
    puede = lambda p, d: (cod := cuadro.get((p.id, d))) in ctx.turnos and "M" in ctx.turnos[cod].cubre
    mejor = []
    for k in range(1, len(sesiones) + 1):
        usar, cuenta, asig = sesiones[:k], defaultdict(int), []
        for p in gente:
            opciones = [d for d in usar if puede(p, d)]
            if opciones:
                d = min(opciones, key=lambda d: cuenta[d])
                cuenta[d] += 1
                asig.append((d, p.id))
        mejor = asig
        if len(asig) == len(gente):
            break
    return mejor, [p.id for p in gente if p.id not in {c for _, c in mejor}]
