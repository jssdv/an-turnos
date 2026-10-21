"""Orquestación de un periodo (mes calendario o N semanas desde un lunes): prepara los datos del solver, guarda el
resultado y recalcula puestos y capacitación. Cada periodo se identifica por su clave «AAAA-MM-DD/AAAA-MM-DD»."""
import calendar
from collections import defaultdict
from datetime import date, timedelta

import capacitacion
import puestos
import reglas
import solver

MESES = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre",
         "Noviembre", "Diciembre"]


def periodo_mes(año, mes):
    return date(año, mes, 1), date(año, mes, calendar.monthrange(año, mes)[1])


def periodo_semanas(inicio, n):
    """`n` semanas completas desde `inicio` (se espera un lunes)."""
    return inicio, inicio + timedelta(days=7 * n - 1)


def clave(inicio, fin):
    return f"{inicio:%Y-%m-%d}/{fin:%Y-%m-%d}"


def desde_clave(k):
    a, b = k.split("/")
    return date.fromisoformat(a), date.fromisoformat(b)


def fechas(inicio, fin):
    return [inicio + timedelta(days=i) for i in range((fin - inicio).days + 1)]


def etiqueta(inicio, fin):
    """«Octubre 2026» si es un mes completo; si no, «05-10 AL 01-11 2026»."""
    if (inicio, fin) == periodo_mes(inicio.year, inicio.month):
        return f"{MESES[inicio.month - 1]} {inicio.year}"
    return f"{inicio:%d-%m} AL {fin:%d-%m} {fin.year}"


def acumulado(bd, ctx, inicio):
    """Turnos y domingos/festivos de los periodos anteriores, para que la equidad no empiece de cero."""
    total = defaultdict(lambda: defaultdict(int))
    for k in bd.periodos():
        if desde_clave(k)[1] < inicio:
            cuadro = bd.asignaciones(k)
            for cid, v in solver.carga(ctx, cuadro, {f for _, f in cuadro}).items():
                for c, n in v.items():
                    total[cid][c] += n
    return {cid: dict(v) for cid, v in total.items()}


def preparar(bd, inicio, fin, modo="cero", lunes=None, tiempo=20):
    """Argumentos para solver.generar. modo: «cero» (descarta ediciones), «respetar» (celdas manuales fijas) o
    «semana» (solo se rehace la semana de `lunes`; el resto del periodo queda como está)."""
    k, dias = clave(inicio, fin), fechas(inicio, fin)
    ctx = bd.contexto(inicio.year)
    fijos = {} if modo == "cero" else bd.fijos(k)
    if modo == "semana":
        sem = {lunes + timedelta(days=i) for i in range(7)}
        actual = bd.asignaciones(k)
        fijos = {**{(p.id, d): actual.get((p.id, d), "L") for p in ctx.colabs if p.en_solver for d in dias
                    if d not in sem}, **{c: t for c, t in fijos.items() if c[1] in sem}}
    previo = bd.asignaciones_rango(inicio - timedelta(days=3), inicio - timedelta(days=1))  # descanso entre periodos
    return ctx, dias, dict(fijos=fijos, previo=previo, acum=acumulado(bd, ctx, inicio),
                           ventana_sem=int(bd.param("ventana_semanas", 3)), tiempo=tiempo)


def terminar(bd, inicio, fin, ctx, dias, cuadro, modo="cero"):
    """Guarda el cuadro (en «cero» también como original) y recalcula puestos y capacitación sobre `cambios`."""
    k = clave(inicio, fin)
    if modo == "cero":
        bd.guardar_cuadro(k, cuadro, reiniciar=True)
    else:
        bd.guardar_cuadro(k, cuadro, versiones=("cambios",))
    recalcular(bd, inicio, fin, ctx)


def recalcular(bd, inicio, fin, ctx=None):
    k, dias = clave(inicio, fin), fechas(inicio, fin)
    ctx = ctx or bd.contexto(inicio.year)
    cuadro = bd.asignaciones(k)
    bd.guardar_puestos(k, puestos.asignar(ctx, cuadro, dias))
    sesiones, _ = capacitacion.programar(ctx, cuadro, dias)
    bd.guardar_capacitacion(k, sesiones)
    return reglas.validar(ctx, cuadro, dias, bd.fijos(k))


def generar(bd, inicio, fin, modo="cero", lunes=None, tiempo=20):
    """Todo en uno (sin hilos): lo usan las pruebas y la línea de comandos."""
    ctx, dias, kw = preparar(bd, inicio, fin, modo, lunes, tiempo)
    cuadro, info = solver.generar(ctx, dias, **kw)
    terminar(bd, inicio, fin, ctx, dias, cuadro, modo)
    return info
