"""Calculadora de dotación: cuántas personas piden los puestos y con qué margen."""
import math
from dataclasses import replace

from . import demanda
from . import solver
from .dominio import Colaborador

TOPE_PERSONAS = 60


def estimar(bd, incluir_deseables=False):
    """Estimación por horas: horas-persona semanales de los puestos activos ÷ jornada media (con margen de ausentismo).
    `diferencia` = personal activo − personas necesarias (negativo: faltan)."""
    margen = float(bd.param("dotacion_margen_pct", 10)) / 100
    activos = [p for p in bd.colaboradores() if p.en_solver]
    jornada = sum(p.horas_sem * p.pct for p in activos) / len(activos) if activos else 42.0
    puestos = bd.catalogo_puestos(solo_activos=True)
    demandas = [d for d in bd.demandas() if d.puesto_id in puestos]
    e = demanda.estimar_personas(demandas, jornada, margen, incluir_deseables)
    return {**e, "activos": len(activos), "jornada_media": jornada, "margen": margen,
            "diferencia": len(activos) - e["personas"]}


def verificar_minimo(ctx, fechas, margen, activos, tiempo=8, progreso=None, cancelar=None):
    """Busca el mínimo de personas genéricas (jornada completa, sin restricciones) con el que el generador encuentra un
    cuadro de `fechas` que cumple la demanda obligatoria y todas las reglas. Parte de la cota por horas, duplica hasta
    encontrar una cantidad factible y luego bisecta. Supuesto: si N personas alcanzan, N+1 también (más gente no
    estorba). `progreso(n_pruebas, total_estimado)` y `cancelar() -> bool` son opcionales.
    Devuelve minimo, con_margen, activos, diferencia, pruebas [(N, factible)], motivo y cancelado."""
    obligatorias = [d for d in ctx.demandas if d.obligatorio]
    pruebas, estado = [], {"cancelado": False}
    total = math.ceil(math.log2(TOPE_PERSONAS)) + 2

    def factible(n):
        if cancelar and cancelar():
            estado["cancelado"] = True
            return None
        genericas = [Colaborador(-(i + 1), f"Persona {i + 1}") for i in range(n)]
        try:
            solver.generar(replace(ctx, colabs=genericas, novedades=[], _nov={}), fechas, tiempo=tiempo, estricto=True)
            ok = True
        except solver.ErrorSolver:
            ok = False
        pruebas.append((n, ok))
        if progreso:
            progreso(len(pruebas), total)
        return ok

    minimo = None
    lo = max(1, demanda.estimar_personas(obligatorias, 42, 0)["personas"])  # cota inferior por horas
    falla, hi = lo - 1, lo
    while True:  # duplicar hasta una cantidad factible
        r = factible(hi)
        if r is None or r or hi >= TOPE_PERSONAS:
            break
        falla, hi = hi, min(TOPE_PERSONAS, hi * 2)
    if r:
        while falla + 1 < hi:  # bisección entre la última que falla y la primera que alcanza
            medio = (falla + hi) // 2
            r = factible(medio)
            if r is None:
                break
            falla, hi = (falla, medio) if r else (medio, hi)
        else:
            minimo = hi
    resultado = {"minimo": minimo, "con_margen": None, "activos": activos, "diferencia": None, "pruebas": pruebas,
                 "motivo": None, "cancelado": estado["cancelado"]}
    if minimo is not None:
        resultado["con_margen"] = math.ceil(round(minimo / (1 - margen), 6))
        resultado["diferencia"] = activos - resultado["con_margen"]
    elif not estado["cancelado"]:
        resultado["motivo"] = (f"Ninguna cantidad de personas (hasta {TOPE_PERSONAS}) cumple las reglas con la demanda "
                               "obligatoria. Revisa que los turnos del catálogo cubran las ventanas de los puestos y que "
                               "las reglas de descanso (libre tras noche, fines de semana libres, rachas) permitan esa cobertura.")
    return resultado
