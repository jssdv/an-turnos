"""Estado de las solicitudes personales frente a un cuadro. Puro: sin Qt ni base de datos."""
from collections import namedtuple
from datetime import timedelta

from . import demanda as dem

Resultado = namedtuple("Resultado", "solicitud estado motivo dias_fallidos")
# Peso por día en el objetivo del solver; por debajo de W_FALTA, así la cobertura siempre manda.
W_SOL = {"normal": 400, "alta": 4000}


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
    return "cobertura o reglas"


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
