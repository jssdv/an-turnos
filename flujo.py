"""Orquestación de un periodo (mes calendario o N semanas desde un lunes): prepara los datos del solver, guarda el
resultado y recalcula puestos y capacitación. Cada periodo se identifica por su clave «AAAA-MM-DD/AAAA-MM-DD»."""
import calendar
from collections import defaultdict
from datetime import date, timedelta

import capacitacion
import puestos
import recargos
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


# --- cierre de periodos, banco de horas e historial ---------------------------------------------------
CONCEPTOS_BANCO = {  # concepto -> ¿resta del saldo? (el valor se ingresa positivo y se guarda negativo)
    "Saldo inicial": False, "Compensado en descanso": True, "Pagado en nómina": True, "Ajuste": False}


def resumen_horas(bd, inicio, fin):
    """[(colab_id, contratadas, trabajadas)] del cuadro vigente (`cambios`) del periodo."""
    ctx, k, dias = bd.contexto(inicio.year), clave(inicio, fin), fechas(inicio, fin)
    cuadro, tar, vent = bd.asignaciones(k), bd.tarifas(), int(bd.param("ventana_semanas", 3))
    out = []
    for p in (p for p in ctx.colabs if p.en_solver):
        r = recargos.reporte(ctx, tar, p, cuadro, dias, vent)
        out.append((p.id, round(r["contratadas"], 2), round(r["trabajadas"], 2)))
    return out


def cerrar(bd, inicio, fin):
    """Congela las horas del periodo en el banco. El cuadro queda en solo lectura hasta reabrirlo."""
    k = clave(inicio, fin)
    if not bd.asignaciones(k):
        raise ValueError("Este periodo no tiene cuadro: genera uno antes de cerrarlo.")
    bd.cerrar_periodo(k, resumen_horas(bd, inicio, fin))


def estado_banco(bd, inicio, fin):
    """Saldo de horas por persona: [{id, nombre, anterior, periodo, total, cerrado}]. Positivo = se le deben horas.
    `anterior` suma los periodos cerrados (menos el actual) y los movimientos manuales; `periodo` es lo ya cerrado
    o, si sigue abierto, lo proyectado con el cuadro actual."""
    k = clave(inicio, fin)
    cerrados = {}
    por_periodo = defaultdict(float)
    for per, cid, contr, trab in bd.cierres():
        cerrados[cid] = cerrados.get(cid, 0) + (trab - contr if per != k else 0)
        if per == k:
            por_periodo[cid] = trab - contr
    movs = defaultdict(float)
    for _, cid, _, horas, _, _ in bd.movimientos():
        movs[cid] += horas
    abierto = not bd.periodo_cerrado(k)
    if abierto and bd.asignaciones(k):
        for cid, contr, trab in resumen_horas(bd, inicio, fin):
            por_periodo[cid] = trab - contr
    filas = []
    for p in bd.colaboradores(solo_activos=False):
        if not p.en_solver:
            continue
        ant = round(cerrados.get(p.id, 0) + movs.get(p.id, 0), 2)
        per = round(por_periodo.get(p.id, 0), 2)
        if p.activo or ant or per:
            filas.append({"id": p.id, "nombre": p.nombre, "anterior": ant, "periodo": per, "total": round(ant + per, 2),
                          "cerrado": not abierto})
    return filas


def historial(bd):
    """Un registro por periodo con cuadro, del más reciente al más antiguo."""
    horas_cierre = defaultdict(float)
    for per, cid, contr, trab in bd.cierres():
        horas_cierre[per] += trab - contr
    out = []
    for k in bd.periodos():
        ini, fin = desde_clave(k)
        ctx, dias, cuadro = bd.contexto(ini.year), fechas(ini, fin), bd.asignaciones(k)
        gente = {c for c, _ in cuadro}
        trabajadas = sum(ctx.turnos[t].horas for t in cuadro.values() if t in ctx.turnos)
        errores = [a for a in reglas.validar(ctx, cuadro, dias, bd.fijos(k)) if a.nivel == "error"]
        cerrado = bd.periodo_cerrado(k)
        out.append({"clave": k, "inicio": ini, "fin": fin, "dias": len(dias), "cerrado": cerrado, "personas": len(gente),
                    "trabajadas": round(trabajadas, 1), "saldo": round(horas_cierre[k], 1) if cerrado else None,
                    "cambios": len(bd.diferencias(k)), "alertas": len(errores)})
    return sorted(out, key=lambda r: r["inicio"], reverse=True)
