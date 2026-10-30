"""Estado de las solicitudes personales frente a un cuadro. Puro: sin Qt ni base de datos."""
from collections import namedtuple
from datetime import timedelta

from . import demanda as dem

Resultado = namedtuple("Resultado", "solicitud estado motivo dias_fallidos")
# Peso por día en el objetivo del solver; por debajo de W_FALTA, así la cobertura siempre manda.
W_SOL = {"normal": 400, "alta": 4000}
BANDA_SEMANA_H = 6  # una semana se considera pareja si queda a ±6 h de las horas semanales de la persona; más allá el solver la penaliza


def malo(s, turno):
    """¿`turno` («L» = libre) incumple la solicitud `s`?"""
    if s.tipo == "libre":
        return turno != "L"
    if s.tipo == "quiero":
        return turno not in ("L", s.turno)
    return turno == s.turno


def _motivo(ctx, s, d, cuadro, fijos):
    if ctx.novedad(s.colab_id, d):
        return "tiene novedad"
    colab = next((p for p in ctx.colabs if p.id == s.colab_id), None)
    if s.tipo == "quiero" and colab and s.turno in ctx.turnos and ctx.bloqueo(colab, ctx.turnos[s.turno], d):
        return "turno no permitido"
    if (s.colab_id, d) in fijos:
        return "edición manual"
    for k in range(1, ctx.libre_tras_noche + 1):
        t = ctx.turnos.get(cuadro.get((s.colab_id, d - timedelta(days=k)), "L"))
        if t and dem.es_noche(t):
            return "libre obligatorio tras noche"
    h = _desequilibrio(ctx, colab, s, d, cuadro)
    if h is not None:
        return f"equilibrio de horas: la semana quedaría en {h:g} h"
    return "cobertura o reglas"


def _desequilibrio(ctx, colab, s, d, cuadro):
    """Horas de la semana de `d` si se cumpliera la solicitud, si con eso la semana sale de la banda de equilibrio (y hoy está dentro); si no, None."""
    if colab is None:
        return None
    lunes = d - timedelta(days=d.weekday())
    sem = [lunes + timedelta(days=i) for i in range(7)]
    if any((s.colab_id, x) not in cuadro for x in sem if not ctx.novedad(s.colab_id, x)):
        return None  # semana incompleta (borde del periodo): no se juzga
    horas = lambda cod: ctx.turnos[cod].horas if cod in ctx.turnos else 0
    hoy = sum(horas(cuadro.get((s.colab_id, x), "L")) for x in sem)
    pedido = horas(s.turno) if s.tipo == "quiero" else 0
    nuevo = hoy - horas(cuadro.get((s.colab_id, d), "L")) + pedido
    meta = colab.horas_sem * colab.pct * sum(not ctx.novedad(s.colab_id, x) for x in sem) / 7
    dentro = lambda h: abs(h - meta) <= BANDA_SEMANA_H
    return nuevo if dentro(hoy) and not dentro(nuevo) else None


def evaluar(ctx, cuadro, fechas, fijos=()):
    """Un `Resultado` por solicitud: estado cumplida / parcial / no cumplida / fuera (sin días en `fechas`)."""
    dias, out = set(fechas), []
    for s in ctx.solicitudes:
        rango = sorted(d for d in dias if s.desde <= d <= s.hasta)
        if not rango:
            out.append(Resultado(s, "fuera", "", []))
            continue
        malos = [d for d in rango if malo(s, cuadro.get((s.colab_id, d), "L"))]
        estado = "cumplida" if not malos else "no cumplida" if len(malos) == len(rango) else "parcial"
        out.append(Resultado(s, estado, _motivo(ctx, s, malos[0], cuadro, fijos) if malos else "", malos))
    return out
