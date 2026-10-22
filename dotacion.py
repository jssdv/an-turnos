"""Calculadora de dotación: cuántas personas piden los puestos y con qué margen."""
import demanda


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
