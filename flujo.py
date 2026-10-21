"""Orquestación de un mes: prepara los datos del solver, guarda el resultado y recalcula puestos y capacitación."""
from collections import defaultdict
from datetime import date, timedelta

import capacitacion
import puestos
import reglas
import solver


def clave(año, mes):
    return f"{año}-{mes:02d}"


def fechas_mes(año, mes):
    d = date(año, mes, 1)
    out = []
    while d.month == mes:
        out.append(d)
        d += timedelta(days=1)
    return out


def acumulado(bd, ctx, mes):
    """Noches, domingos/festivos y corridos de los meses anteriores, para que la equidad no empiece de cero."""
    total = defaultdict(lambda: (0, 0, 0))
    for m in (m for m in bd.meses() if m < mes):
        cuadro = bd.asignaciones(m)
        for cid, v in solver.carga(ctx, cuadro, {f for _, f in cuadro}).items():
            total[cid] = tuple(a + b for a, b in zip(total[cid], v))
    return dict(total)


def preparar(bd, año, mes, modo="cero", lunes=None, tiempo=20):
    """Argumentos para solver.generar. modo: «cero» (descarta ediciones), «respetar» (celdas manuales fijas) o
    «semana» (solo se rehace la semana de `lunes`; el resto del mes queda como está)."""
    k, fechas = clave(año, mes), fechas_mes(año, mes)
    ctx = bd.contexto(año)
    ant = date(año, mes, 1) - timedelta(days=1)
    fijos = {} if modo == "cero" else bd.fijos(k)
    if modo == "semana":
        sem = {lunes + timedelta(days=i) for i in range(7)}
        actual = bd.asignaciones(k)
        fijos = {**{(p.id, d): actual.get((p.id, d), "L") for p in ctx.colabs if p.en_solver for d in fechas
                    if d not in sem}, **{c: t for c, t in fijos.items() if c[1] in sem}}
    return ctx, fechas, dict(fijos=fijos, previo=bd.asignaciones(clave(ant.year, ant.month)),
                             acum=acumulado(bd, ctx, k), ventana_sem=int(bd.param("ventana_semanas", 3)), tiempo=tiempo,
                             max_noches=int(bd.param("max_noches_seguidas", 3)))


def terminar(bd, año, mes, ctx, fechas, cuadro, modo="cero"):
    """Guarda el cuadro (en «cero» también como original) y recalcula puestos y capacitación sobre `cambios`."""
    k = clave(año, mes)
    if modo == "cero":
        bd.guardar_cuadro(k, cuadro, reiniciar=True)
    else:
        bd.guardar_cuadro(k, cuadro, versiones=("cambios",))
    recalcular(bd, año, mes, ctx)


def recalcular(bd, año, mes, ctx=None):
    k, fechas = clave(año, mes), fechas_mes(año, mes)
    ctx = ctx or bd.contexto(año)
    cuadro = bd.asignaciones(k)
    bd.guardar_puestos(k, puestos.asignar(ctx, cuadro, fechas))
    sesiones, _ = capacitacion.programar(ctx, cuadro, fechas)
    bd.guardar_capacitacion(k, sesiones)
    return reglas.validar(ctx, cuadro, fechas, bd.fijos(k))


def generar(bd, año, mes, modo="cero", lunes=None, tiempo=20):
    """Todo en uno (sin hilos): lo usan las pruebas y la línea de comandos."""
    ctx, fechas, kw = preparar(bd, año, mes, modo, lunes, tiempo)
    cuadro, info = solver.generar(ctx, fechas, **kw)
    terminar(bd, año, mes, ctx, fechas, cuadro, modo)
    return info
