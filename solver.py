"""Generador del cuadro mensual con OR-Tools CP-SAT. Cobertura, descanso y horas salen del catálogo de turnos."""
from collections import defaultdict
from datetime import timedelta

from ortools.sat.python import cp_model

from dominio import DESCANSO_MIN

# Pesos del objetivo (minutos de desviación = 1 punto). La cobertura faltante domina todo lo demás.
W_FALTA, W_SOBRA, W_DEFICIT, W_EXCESO = 100_000, 20, 1, 2
W_CAMBIO, W_NOCHE_SEG, W_DF_SEG, W_ESTUDIO, W_EQUIDAD = 15, 200, 100, 300, 100


class ErrorSolver(Exception):
    pass


def incompatibles(turnos):
    """Pares (a, b) que no pueden ir en días consecutivos por el descanso mínimo de 12 h."""
    return {(a, b) for a, ta in turnos.items() for b, tb in turnos.items()
            if 1440 + tb.inicio - (ta.inicio + ta.duracion) < DESCANSO_MIN}


def carga(ctx, cuadro, fechas):
    """{colab_id: (noches, domingos/festivos trabajados, corridos)} de un cuadro; sirve de acumulado para meses futuros."""
    out = defaultdict(lambda: [0, 0, 0])
    for (cid, f), cod in cuadro.items():
        t = ctx.turnos.get(cod)
        if t and f in fechas:
            out[cid][0] += "N" in t.cubre
            out[cid][1] += ctx.tipo_dia(f) == "DF"
            out[cid][2] += len(t.cubre) > 1
    return {k: tuple(v) for k, v in out.items()}


def generar(ctx, fechas, fijos=None, previo=None, acum=None, ventana_sem=3, tiempo=20, semilla=0, max_noches=3):
    """Devuelve (cuadro {(colab_id, fecha): código}, info). Los días libres no aparecen en el cuadro."""
    fechas, fijos, previo, acum = sorted(fechas), fijos or {}, previo or {}, acum or {}
    try:
        return _resolver(ctx, fechas, fijos, previo, acum, ventana_sem, tiempo, semilla, max_noches)
    except ErrorSolver:
        if not fijos:
            raise
        _resolver(ctx, fechas, {}, previo, acum, ventana_sem, min(tiempo, 10), semilla, max_noches)  # sin fijos tampoco → sale ese error
        raise ErrorSolver("Las celdas fijas (ediciones manuales) hacen imposible cumplir el descanso de 12 h "
                          "o el día libre semanal. Quita algunas con «Restaurar» y vuelve a generar.")


def _resolver(ctx, fechas, fijos, previo, acum, ventana_sem, tiempo, semilla, max_noches):
    P = [p for p in ctx.colabs if p.en_solver]
    S = [c for c, t in ctx.turnos.items() if t.solver]
    mal = incompatibles(ctx.turnos)
    m = cp_model.CpModel()
    x = {}
    for p in P:
        for d in fechas:
            fx = fijos.get((p.id, d))
            opts = ["L"] + [s for s in S if not ctx.bloqueo(p, ctx.turnos[s], d)]
            if fx is not None and fx not in opts:
                opts.append(fx)
            ant = ctx.turnos.get(previo.get((p.id, d - timedelta(days=1)), "L"))
            for s in opts:
                if ant and s in ctx.turnos and (ant.codigo, s) in mal:
                    continue
                x[p.id, d, s] = m.NewBoolVar(f"x{p.id}_{d}_{s}")
            m.AddExactlyOne([x[p.id, d, s] for s in opts if (p.id, d, s) in x])
            if fx is not None:
                m.Add(x[p.id, d, fx] == 1)
    por_pd = defaultdict(list)
    for (pi, d, s), v in x.items():
        por_pd[pi, d].append((s, v))
    obj, faltas = [], {}

    for p in P:  # descanso de 12 h entre días consecutivos
        for a, b in zip(fechas, fechas[1:]):
            for s1, v1 in por_pd[p.id, a]:
                for s2, v2 in por_pd[p.id, b]:
                    if (s1, s2) in mal:
                        m.Add(v1 + v2 <= 1)
    es_noche = lambda s: s in ctx.turnos and "N" in ctx.turnos[s].cubre
    for p in P:  # tope de noches consecutivas
        for i in range(len(fechas) - max_noches):
            m.Add(sum(v for d in fechas[i:i + max_noches + 1] for s, v in por_pd[p.id, d] if es_noche(s)) <= max_noches)
    n_libres = ctx.libre_tras_noche  # después de una noche, el día siguiente es libre (salvo edición manual)
    for p in P:
        for i, a in enumerate(fechas):
            for k in range(1, n_libres + 1):
                if i + k >= len(fechas):
                    break
                b = fechas[i + k]
                if fijos.get((p.id, b), "L") != "L":
                    continue
                for s1, v1 in por_pd[p.id, a]:
                    if es_noche(s1):
                        for s2, v2 in por_pd[p.id, b]:
                            if s2 != "L":
                                m.Add(v1 + v2 <= 1)
        for j in range(1, n_libres + 1):  # la noche fue en el último día del mes anterior
            if es_noche(previo.get((p.id, fechas[0] - timedelta(days=j)), "L")):
                for k in range(n_libres - j + 1):
                    if fijos.get((p.id, fechas[k]), "L") == "L":
                        m.Add(sum(v for s, v in por_pd[p.id, fechas[k]] if s != "L") == 0)
    fines = [(d, d + timedelta(days=1)) for d in fechas if d.weekday() == 5 and d + timedelta(days=1) in set(fechas)]
    if ctx.fines_libres and fines:  # al menos un fin de semana completo libre al mes (el libre posterior a la noche cuenta)
        for p in P:
            libres = []
            for sab, dom in fines:
                if any(fijos.get((p.id, x), "L") != "L" for x in (sab, dom)):
                    continue  # una edición manual ya decidió ese fin de semana
                z = m.NewBoolVar("")
                for x in (sab, dom):
                    for s, v in por_pd[p.id, x]:
                        if s != "L":
                            m.Add(z + v <= 1)
                libres.append(z)
            if libres:
                m.Add(sum(libres) >= min(ctx.fines_libres, len(libres)))
    semanas = defaultdict(list)
    for d in fechas:
        semanas[d - timedelta(days=d.weekday())].append(d)
    for p in P:  # al menos un día libre en cada semana completa
        for lunes, dias in semanas.items():
            if len(dias) == 7:
                m.Add(sum(v for d in dias for s, v in por_pd[p.id, d] if s == "L") >= ctx.libres_semana)

    for d in fechas:  # cobertura: faltante muy caro, sobrante barato
        for fr, req in ctx.cobertura[ctx.tipo_dia(d)].items():
            n = sum(v for p in P for s, v in por_pd[p.id, d] if s in ctx.turnos and fr in ctx.turnos[s].cubre)
            falta, sobra = m.NewIntVar(0, req, ""), m.NewIntVar(0, len(P), "")
            m.Add(n + falta >= req)
            m.Add(sobra >= n - req)
            obj += [W_FALTA * falta, W_SOBRA * sobra]
            faltas[d, fr] = falta

    dias_vent = 7 * ventana_sem  # horas: objetivo suave por ventana (art. 165)
    for p in P:
        for i in range((len(fechas) + dias_vent - 1) // dias_vent):
            dias = fechas[i * dias_vent:(i + 1) * dias_vent]
            meta = round(p.horas_sem * p.pct * 60 * sum(1 for d in dias if not ctx.novedad(p.id, d)) / 7)
            hechas = sum(round(ctx.turnos[s].horas * 60) * v for d in dias for s, v in por_pd[p.id, d] if s in ctx.turnos)
            de, ex = m.NewIntVar(0, 100_000, ""), m.NewIntVar(0, 100_000, "")
            m.Add(de >= meta - hechas)
            m.Add(ex >= hechas - meta)
            obj += [W_DEFICIT * de, W_EXCESO * ex]

    for p in P:  # estabilidad: no cambiar de turno cada día
        for a, b in zip(fechas, fechas[1:]):
            cambio = m.NewBoolVar("")
            for s1, v1 in por_pd[p.id, a]:
                for s2, v2 in por_pd[p.id, b]:
                    if s1 != s2 and s1 != "L" and s2 != "L":
                        m.Add(cambio >= v1 + v2 - 1)
            obj.append(W_CAMBIO * cambio)
        for d in fechas:  # evitar noche justo antes de un bloque de estudio de mañana
            if any(dia == (d + timedelta(days=1)).weekday() and fr == "M" for dia, fr in p.estudio):
                obj += [W_ESTUDIO * v for s, v in por_pd[p.id, d] if s in ctx.turnos and "N" in ctx.turnos[s].cubre]

    def seguidas(peso, p, cond):  # rotación: no repetir lo pesado en semanas seguidas
        lunes_s = sorted(semanas)
        tiene = {}
        for l in lunes_s:
            t = m.NewBoolVar("")
            for d in semanas[l]:
                for s, v in por_pd[p.id, d]:
                    if cond(d, s):
                        m.Add(t >= v)
            tiene[l] = t
        for a, b in zip(lunes_s, lunes_s[1:]):
            c = m.NewBoolVar("")
            m.Add(c >= tiene[a] + tiene[b] - 1)
            obj.append(peso * c)

    for p in P:
        seguidas(W_NOCHE_SEG, p, lambda d, s: s in ctx.turnos and "N" in ctx.turnos[s].cubre)
        seguidas(W_DF_SEG, p, lambda d, s: s in ctx.turnos and ctx.tipo_dia(d) == "DF")

    metricas = [  # (cuenta el turno s del día d, ¿puede la persona acumular esta carga?)
        (lambda d, s: "N" in ctx.turnos[s].cubre, lambda p: any("N" in ctx.turnos[c].cubre for c in S if p.permitidos is None or c in p.permitidos)),
        (lambda d, s: ctx.tipo_dia(d) == "DF", lambda p: True),
        (lambda d, s: len(ctx.turnos[s].cubre) > 1, lambda p: any(len(ctx.turnos[c].cubre) > 1 for c in S if p.permitidos is None or c in p.permitidos)),
    ]
    for k, (cond, puede) in enumerate(metricas):  # equidad: reducir la diferencia entre mayor y menor carga acumulada
        elegibles = [p for p in P if puede(p)]
        if len(elegibles) < 2:
            continue
        tot = {p.id: acum.get(p.id, (0, 0, 0))[k] + sum(v for d in fechas for s, v in por_pd[p.id, d]
                                                          if s in ctx.turnos and cond(d, s)) for p in elegibles}
        mx, mn = m.NewIntVar(0, 1000, ""), m.NewIntVar(0, 1000, "")
        for p in elegibles:
            m.Add(mx >= tot[p.id])
            m.Add(mn <= tot[p.id])
        obj.append(W_EQUIDAD * (mx - mn))

    m.Minimize(sum(obj))
    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = tiempo
    sol.parameters.num_workers = 8
    sol.parameters.random_seed = semilla
    estado = sol.Solve(m)
    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ErrorSolver("No existe un cuadro que cumpla el descanso de 12 h y el día libre semanal con estos datos.")
    cuadro = {(p.id, d): s for p in P for d in fechas for s, v in por_pd[p.id, d] if s != "L" and sol.Value(v)}
    faltan = [(d, fr, sol.Value(v)) for (d, fr), v in faltas.items() if sol.Value(v)]
    return cuadro, {"estado": sol.StatusName(estado), "objetivo": sol.ObjectiveValue(), "faltan": sorted(faltan)}
