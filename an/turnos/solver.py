"""Generador del cuadro mensual con OR-Tools CP-SAT. Cobertura, descanso y horas salen del catálogo de turnos."""
import os
import threading
from collections import defaultdict
from datetime import timedelta

from ortools.sat.python import cp_model

from . import demanda as dem
from .solicitudes import BANDA_SEMANA_H, W_SOL, malo

from .dominio import DESCANSO_MIN
from .recargos import horas_df

# Pesos del objetivo (minutos de desviación = 1 punto). La cobertura faltante domina todo lo demás.
W_FALTA, W_DEFICIT, W_EXCESO, W_DESEABLE = 10_000, 1, 2, 10  # W_FALTA es por persona y tramo de 30 min
W_CAMBIO, W_NOCHE_SEG, W_DF_SEG, W_ESTUDIO, W_EQUIDAD = 15, 200, 100, 300, 200
W_C_PAR, W_LIBRE_FDS, W_IGUAL = 250, 120, 60
W_SOBRA, W_SOBRA2, X_NOCHE = 4, 12, 3  # por persona y tramo de 30 min por encima de lo pedido; la segunda sobrante cuesta más; en la noche × X_NOCHE
W_SEMANA = 3  # por minuto de una semana completa fuera de la banda de ±BANDA_SEMANA_H h de sus horas semanales (más que una solicitud normal, menos que una alta)
W_DF_EQ = 150  # por media hora de diferencia entre la persona con más y la de menos horas en domingo/festivo  # dos corridos seguidos; semana sin ningún libre en sábado o domingo


class ErrorSolver(Exception):
    pass


def incompatibles(turnos):
    """Pares (a, b) que no pueden ir en días consecutivos por el descanso mínimo de 12 h."""
    return {(a, b) for a, ta in turnos.items() for b, tb in turnos.items()
            if 1440 + tb.inicio - (ta.inicio + ta.duracion) < DESCANSO_MIN}


def carga(ctx, cuadro, fechas):
    """{colab_id: {código de turno: veces, "DF": medias horas de calendario en domingo/festivo}}; sirve de acumulado para meses futuros."""
    out = defaultdict(lambda: defaultdict(int))
    for (cid, f), cod in cuadro.items():
        if cod in ctx.turnos and f in fechas:
            out[cid][cod] += 1
            out[cid]["DF"] += round(horas_df(ctx.turnos[cod], f, ctx) * 2)
    return {k: dict(v) for k, v in out.items()}


def workers_por_defecto():
    """Hilos de CP-SAT: `AN_SOLVER_WORKERS` si es un entero ≥ 1; si no, los núcleos de la máquina con tope de 8 (más hilos que núcleos no ayudan)."""
    try:
        return max(1, int(os.environ["AN_SOLVER_WORKERS"]))
    except (KeyError, ValueError):
        return min(8, os.cpu_count() or 1)


def generar(ctx, fechas, fijos=None, previo=None, acum=None, ventana_sem=3, tiempo=20, semilla=0, ajuste=None, estricto=False,
            al_avance=None, detener=None, workers=None):
    """Devuelve (cuadro {(colab_id, fecha): código}, info). Los días libres no aparecen en el cuadro.
    `ajuste`: {colab_id: horas} que se suman a la meta de horas del periodo (negativo: se le deben horas, trabaja menos).
    `estricto`: la demanda obligatoria es restricción dura (sin faltantes); si no cabe se lanza ErrorSolver.
    `al_avance(dict)`: se llama en cada solución nueva con soluciones, objetivo, cota, segundos y limite.
    `detener`: `threading.Event`; si se activa se corta la búsqueda y se lanza ErrorSolver («Generación cancelada.»), sin segundo intento.
    `workers`: hilos de CP-SAT (por defecto `AN_SOLVER_WORKERS` o min(8, núcleos)).
    `info["faltan"]` = [(fecha, tramo 0–47, personas que faltan)]."""
    fechas, fijos, previo, acum = sorted(fechas), fijos or {}, previo or {}, acum or {}
    extra = dict(al_avance=al_avance, detener=detener, workers=workers or workers_por_defecto())
    try:
        return _resolver(ctx, fechas, fijos, previo, acum, ventana_sem, tiempo, semilla, ajuste or {}, estricto, **extra)
    except ErrorSolver:
        if not fijos or (detener and detener.is_set()):
            raise
        _resolver(ctx, fechas, {}, previo, acum, ventana_sem, min(tiempo, 10), semilla, ajuste or {}, estricto, **extra)  # sin fijos tampoco → sale ese error
        raise ErrorSolver("Las celdas fijas (ediciones manuales) hacen imposible cumplir el descanso de 12 h "
                          "o el día libre semanal. Quita algunas con «Restaurar» y vuelve a generar.")


class _Avance(cp_model.CpSolverSolutionCallback):
    def __init__(self, al_avance, limite):
        super().__init__()
        self.al_avance, self.limite, self.n = al_avance, limite, 0

    def on_solution_callback(self):
        self.n += 1
        self.al_avance({"soluciones": self.n, "objetivo": self.ObjectiveValue(), "cota": self.BestObjectiveBound(),
                        "segundos": self.WallTime(), "limite": self.limite})


def _resolver(ctx, fechas, fijos, previo, acum, ventana_sem, tiempo, semilla, ajuste, estricto, al_avance=None, detener=None, workers=8):
    if detener and detener.is_set():
        raise ErrorSolver("Generación cancelada.")
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
    es_noche = lambda s: s in ctx.turnos and dem.es_noche(ctx.turnos[s])
    es_c = lambda s: s in ctx.turnos and dem.es_corrido(ctx.turnos[s])
    libre_ok = lambda p, dias: all(fijos.get((p.id, d), "L") == "L" for d in dias)  # una edición manual en la ventana manda
    paso = ctx.libre_tras_noche + 1  # separación entre noches de una racha NC-L-NC-L…
    for p in P:
        if ctx.max_noches:  # a lo sumo `max_noches` noches en racha
            for i in range(len(fechas)):
                racha = [fechas[i + k * paso] for k in range(ctx.max_noches + 1) if i + k * paso < len(fechas)]
                if len(racha) > ctx.max_noches and libre_ok(p, racha):
                    m.Add(sum(v for d in racha for s, v in por_pd[p.id, d] if es_noche(s)) <= ctx.max_noches)
        if ctx.max_igual:  # el mismo turno de 6 h (M, T…) no se repite más de `max_igual` días seguidos
            for cod in S:
                if es_noche(cod) or es_c(cod):
                    continue
                for i in range(len(fechas) - ctx.max_igual):
                    ventana = fechas[i:i + ctx.max_igual + 1]
                    if libre_ok(p, ventana):
                        m.Add(sum(x[p.id, d, cod] for d in ventana if (p.id, d, cod) in x) <= ctx.max_igual)
        if ctx.max_c:  # a lo sumo `max_c` corridos en días consecutivos
            for i in range(len(fechas) - ctx.max_c):
                ventana = fechas[i:i + ctx.max_c + 1]
                if libre_ok(p, ventana):
                    m.Add(sum(v for d in ventana for s, v in por_pd[p.id, d] if es_c(s)) <= ctx.max_c)
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
                if any(fijos.get((p.id, dia), "L") != "L" for dia in (sab, dom)):
                    continue  # una edición manual ya decidió ese fin de semana
                z = m.NewBoolVar("")
                for dia in (sab, dom):
                    for s, v in por_pd[p.id, dia]:
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

    if ctx.max_horas_semana:  # tope duro de horas por semana completa (ponytail: las semanas parciales del borde no se topan)
        tope = ctx.max_horas_semana * 60
        for p in P:
            for lunes, dias in semanas.items():
                fijas = sum(ctx.turnos[fijos[p.id, d]].horas * 60 for d in dias if fijos.get((p.id, d)) in ctx.turnos)
                if len(dias) == 7 and fijas <= tope:
                    m.Add(sum(round(ctx.turnos[s].horas * 60) * v for d in dias for s, v in por_pd[p.id, d] if s in ctx.turnos) <= tope)

    if ctx.max_c_semana:  # tope duro de corridos por semana completa (ponytail: las semanas parciales del borde no se topan)
        for p in P:
            for lunes, dias in semanas.items():
                fijos_c = sum(es_c(fijos.get((p.id, d))) for d in dias)
                if len(dias) == 7 and fijos_c <= ctx.max_c_semana:
                    m.Add(sum(v for d in dias for s, v in por_pd[p.id, d] if es_c(s)) <= ctx.max_c_semana)

    for p in P:  # equilibrio: ninguna semana completa muy por debajo o por encima de las horas semanales de la persona
        for lunes, dias in semanas.items():
            if len(dias) == 7:
                meta = round(p.horas_sem * p.pct * 60 * sum(1 for d in dias if not ctx.novedad(p.id, d)) / 7)
                hechas = sum(round(ctx.turnos[s].horas * 60) * v for d in dias for s, v in por_pd[p.id, d] if s in ctx.turnos)
                fuera = m.NewIntVar(0, 100_000, "")
                m.Add(fuera >= meta - hechas - BANDA_SEMANA_H * 60)
                m.Add(fuera >= hechas - meta - BANDA_SEMANA_H * 60)
                obj.append(W_SEMANA * fuera)

    # cobertura por tramos de 30 min: la demanda obligatoria de los puestos, tramo a tramo; los deseables dan un premio
    tr = {c: ([t for o, t in dem.turno_tramos(tu) if o == 0], [t for o, t in dem.turno_tramos(tu) if o == 1])
          for c, tu in ctx.turnos.items()}
    dias_set = set(fechas)
    noche_t = set(dem.FRANJAS["N"])
    previo_ayer = {k: c for k, c in previo.items() if k[1] == fechas[0] - timedelta(days=1)}
    for d in fechas:
        ayer = d - timedelta(days=1)
        con_ayer = d != fechas[0] or bool(previo_ayer)  # sin datos de ayer no se exige su madrugada
        obl, des = dem.demanda_fecha(ctx, d, con_ayer)
        # ponytail: quien solo puede ocupar ciertos puestos cuenta en un tramo solo si alguno de ellos pide gente ahí (aproximación; el reparto fino lo hace puestos.asignar_tramos)
        pide = {q: [a or b for a, b in zip(o, w)] for q, (o, w) in dem.demanda_por_puesto(ctx, d, con_ayer).items()} if ctx.usa_puestos else {}
        sirve = lambda p, t: p.puestos_permitidos is None or not pide or any(pide.get(q, [0] * dem.TRAMOS_DIA)[t] for q in p.puestos_permitidos)
        for p in P:  # quien solo ocupa ciertos puestos no trabaja un turno cuyos tramos ninguno de ellos pide (salvo edición manual)
            if p.puestos_permitidos is not None and pide:
                for s, v in por_pd[p.id, d]:
                    if s in tr and tr[s][0] and not any(sirve(p, t) for t in tr[s][0]) and fijos.get((p.id, d)) != s:
                        m.Add(v == 0)
        for t in range(dem.TRAMOS_DIA):
            if not (obl[t] or des[t]):
                continue
            terms = [v for p in P if sirve(p, t) for s, v in por_pd[p.id, d] if s in tr and t in tr[s][0]]
            const = 0
            if ayer in dias_set:
                terms += [v for p in P if sirve(p, t) for s, v in por_pd[p.id, ayer] if s in tr and t in tr[s][1]]
            else:
                const = sum(1 for p in P if sirve(p, t) and (c := previo.get((p.id, ayer))) in tr and t in tr[c][1])
            presente = sum(terms) + const
            if obl[t]:
                if estricto:
                    if not terms and const < obl[t]:
                        raise ErrorSolver("La demanda obligatoria no se puede cubrir con los turnos disponibles.")
                    if terms:
                        m.Add(presente >= obl[t])
                else:
                    falta = m.NewIntVar(0, obl[t], "")
                    m.Add(presente + falta >= obl[t])
                    obj.append(W_FALTA * falta)
                    faltas[d, t] = falta
            if terms:  # reparto parejo: lo que sobra de la demanda (obligatoria + deseable) se reparte y no se apila, y menos de noche
                peso = X_NOCHE if t in noche_t else 1
                sob, sob2 = m.NewIntVar(0, len(P), ""), m.NewIntVar(0, len(P), "")
                m.Add(sob >= presente - obl[t] - des[t])
                m.Add(sob2 >= presente - obl[t] - des[t] - 1)
                obj += [W_SOBRA * peso * sob, W_SOBRA2 * peso * sob2]
            if des[t] and terms:
                ok = m.NewBoolVar("")
                m.Add(presente >= obl[t] + des[t]).OnlyEnforceIf(ok)
                obj.append(-W_DESEABLE * des[t] * ok)

    dias_vent = 7 * ventana_sem  # horas: objetivo suave por ventana (art. 165)
    for p in P:
        for i in range((len(fechas) + dias_vent - 1) // dias_vent):
            dias = fechas[i * dias_vent:(i + 1) * dias_vent]
            meta = round(p.horas_sem * p.pct * 60 * sum(1 for d in dias if not ctx.novedad(p.id, d)) / 7)
            meta = max(0, meta + round(ajuste.get(p.id, 0) * 60 * len(dias) / len(fechas)))  # banco de horas, repartido por ventana
            hechas = sum(round(ctx.turnos[s].horas * 60) * v for d in dias for s, v in por_pd[p.id, d] if s in ctx.turnos)
            de, ex = m.NewIntVar(0, 100_000, ""), m.NewIntVar(0, 100_000, "")
            m.Add(de >= meta - hechas)
            m.Add(ex >= hechas - meta)
            if estricto:  # calculadora de dotación: nadie pasa de sus horas contratadas en la ventana
                m.Add(hechas <= meta)
            obj += [W_DEFICIT * de, W_EXCESO * ex]

    for p in P:  # estabilidad: no cambiar de turno cada día
        for a, b in zip(fechas, fechas[1:]):
            cambio = m.NewBoolVar("")
            for s1, v1 in por_pd[p.id, a]:
                for s2, v2 in por_pd[p.id, b]:
                    if s1 != s2 and s1 != "L" and s2 != "L":
                        m.Add(cambio >= v1 + v2 - 1)
            obj.append(W_CAMBIO * cambio)
        for a, b in zip(fechas, fechas[1:]):  # evitar dos corridos seguidos
            va, vb = [v for s, v in por_pd[p.id, a] if es_c(s)], [v for s, v in por_pd[p.id, b] if es_c(s)]
            if va and vb:
                par = m.NewBoolVar("")
                m.Add(par >= sum(va) + sum(vb) - 1)
                obj.append(W_C_PAR * par)
        if ctx.max_igual >= 3:  # y se evita incluso llegar a tres iguales seguidos
            for cod in S:
                if es_noche(cod) or es_c(cod):
                    continue
                for i in range(len(fechas) - 2):
                    vs = [x[p.id, d, cod] for d in fechas[i:i + 3] if (p.id, d, cod) in x]
                    if len(vs) == 3:
                        tres = m.NewBoolVar("")
                        m.Add(tres >= sum(vs) - 2)
                        obj.append(W_IGUAL * tres)
        for lunes, dias in semanas.items():  # los libres, de preferencia en sábado o domingo
            fds = [v for d in dias if d.weekday() >= 5 for s, v in por_pd[p.id, d] if s == "L"]
            if fds:
                t = m.NewBoolVar("")
                m.Add(t <= sum(fds))
                obj.append(W_LIBRE_FDS * (1 - t))
        for d in fechas:  # evitar noche justo antes de un bloque de estudio de mañana
            if any(dia == (d + timedelta(days=1)).weekday() and fr == "M" for dia, fr in p.estudio):
                obj += [W_ESTUDIO * v for s, v in por_pd[p.id, d] if es_noche(s)]

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
        seguidas(W_NOCHE_SEG, p, lambda d, s: es_noche(s))
        seguidas(W_DF_SEG, p, lambda d, s: s in ctx.turnos and ctx.tipo_dia(d) == "DF")

    # equidad: M, T, C, NC (y cada turno nuevo) y domingos/festivos parejos entre quienes pueden hacerlos,
    # contando lo acumulado de meses anteriores
    # (clave, cuenta, quién puede, tolerancia): turnos por código, con 1 turno de tolerancia; domingos/festivos en medias horas
    # de calendario (lo mismo que se paga), aparte de las noches y sin tolerancia: se busca la menor diferencia posible
    cargas = [(cod, lambda d, s, cod=cod: s == cod, lambda p, cod=cod: p.permitidos is None or cod in p.permitidos, 1) for cod in S]
    mh_df = {(s, d): round(horas_df(ctx.turnos[s], d, ctx) * 2) for s in S if s in ctx.turnos for d in fechas}
    cargas.append(("DF", lambda d, s: mh_df.get((s, d), 0), lambda p: any(mh_df.get((s, d)) for d in fechas for s, _ in por_pd[p.id, d]), 0))
    for clave, cond, puede, tol in cargas:
        grupos = defaultdict(list)  # se compara entre quienes tienen las mismas restricciones (la restringida va aparte)
        for p in P:
            if puede(p):
                grupos[p.permitidos if clave != "DF" else p.pct].append(p)  # DF: solo entre la misma jornada contratada
        for elegibles in grupos.values():
            if len(elegibles) < 2:
                continue
            tot = {p.id: acum.get(p.id, {}).get(clave, 0) + sum(v * int(cond(d, s)) for d in fechas for s, v in por_pd[p.id, d])
                   for p in elegibles}
            mx, mn = m.NewIntVar(0, 100000, ""), m.NewIntVar(0, 100000, "")
            for p in elegibles:
                m.Add(mx >= tot[p.id])
                m.Add(mn <= tot[p.id])
            if clave == "DF":
                obj.append(W_DF_EQ * (mx - mn))  # por media hora; 6 h de diferencia pesan más que cualquier regla blanda de rotación
                continue
            exceso = m.NewIntVar(0, 100000, "")  # la diferencia hasta `tol` turnos pesa normal; lo que pase pesa el triple
            m.Add(exceso >= mx - mn - 2 * tol)
            obj += [W_EQUIDAD * (mx - mn), 3 * W_EQUIDAD * exceso]

    for s in ctx.solicitudes:  # deseos blandos: cuestan, nunca prohíben
        for d in fechas:
            if s.desde <= d <= s.hasta:
                obj += [W_SOL[s.prioridad] * v for t, v in por_pd.get((s.colab_id, d), ()) if malo(s, t)]

    m.Minimize(sum(obj))
    sol = cp_model.CpSolver()
    sol.parameters.max_time_in_seconds = tiempo
    sol.parameters.num_workers = workers
    sol.parameters.random_seed = semilla
    terminado = threading.Event()
    if detener:
        def vigia():  # stop_search antes de que arranque la búsqueda se pierde: se repite hasta que Solve termine
            while not terminado.is_set():
                if detener.wait(0.1):
                    sol.stop_search()
                    terminado.wait(0.1)
        threading.Thread(target=vigia, daemon=True).start()
    try:
        estado = sol.Solve(m, _Avance(al_avance, tiempo)) if al_avance else sol.Solve(m)
    finally:
        terminado.set()
    if detener and detener.is_set():
        raise ErrorSolver("Generación cancelada.")  # una búsqueda cortada se descarta
    if estado not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        raise ErrorSolver("No existe un cuadro que cumpla el descanso de 12 h y el día libre semanal con estos datos.")
    cuadro = {(p.id, d): s for p in P for d in fechas for s, v in por_pd[p.id, d] if s != "L" and sol.Value(v)}
    faltan = [(d, t, sol.Value(v)) for (d, t), v in faltas.items() if sol.Value(v)]
    return cuadro, {"estado": sol.StatusName(estado), "objetivo": sol.ObjectiveValue(), "faltan": sorted(faltan),
                    "ajuste": {c: h for c, h in ajuste.items() if h}}
