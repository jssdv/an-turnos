"""Reparto diario de personas en los puestos, por tramos horarios, y textos para mostrarlo."""
from collections import defaultdict
from datetime import timedelta

from ortools.sat.python import cp_model

import demanda as dem
from dominio import AsignacionPuesto
from reglas import Alerta, texto_tramos

def por_persona(filas, numeros):
    """{(colab_id, fecha): número del puesto principal} (donde pasa más tiempo; 0 = solo apoyo). `numeros` mapea el id
    de puesto a su número."""
    tiempo = defaultdict(lambda: defaultdict(int))
    for f in filas:
        tiempo[f.colab_id, f.fecha][f.puesto_id] += f.hasta - f.desde
    out = {}
    for k, por_puesto in tiempo.items():
        reales = {q: m for q, m in por_puesto.items() if q}
        out[k] = numeros[max(reales, key=reales.get)] if reales else 0
    return out


def etiqueta(cod, puesto):
    """Texto de celda con el puesto: «M·2» (número 2), «T·A» (apoyo); sin puesto, solo el código."""
    return cod if puesto is None else f"{cod}·{puesto or 'A'}"


def leyenda(puestos):
    """«Puestos: 1 Lavado · 2 Autoclave · … · A apoyo (sin puesto ese día)» con los puestos activos."""
    activos = sorted((p for p in puestos.values() if p.activo), key=lambda p: p.numero)
    return "Puestos: " + " · ".join(f"{p.numero} {p.nombre}" for p in activos) + " · A apoyo (sin puesto ese día)"


# --- reparto por tramos horarios ----------------------------------------------------------------------------------------
W_FALTA_P, W_DES_P, W_CAMBIO_P, W_PRIORIDAD_P = 1000, 10, 60, 500  # por persona y tramo; cambiar de puesto dentro del turno; rotación abajo


def asignar_tramos(ctx, cuadro, fechas, tiempo=3):
    """[AsignacionPuesto] de cada día: en qué puesto está cada persona presente, tramo a tramo. Por día, un CP-SAT
    por bloques de tramos con la misma presencia y demanda: cada persona ocupa un puesto a la vez (solo los que puede),
    los puestos reciben la demanda obligatoria, los deseables se buscan, y se penaliza cambiar de puesto dentro del
    turno, repetir el puesto de ayer y el desequilibrio de veces por puesto. Quien sobra queda en apoyo (puesto 0)."""
    por_id = {p.id: p for p in ctx.colabs if p.en_solver}
    primero = min(fechas)
    hist = defaultdict(lambda: defaultdict(int))
    ayer_p = {}
    out = []
    for d in sorted(fechas):
        d1 = d - timedelta(days=1)
        presentes = defaultdict(set)  # colab_id -> tramos en que está presente hoy
        for (cid, f), cod in cuadro.items():
            if cid in por_id and cod in ctx.turnos and f in (d, d1):
                for off, t in dem.turno_tramos(ctx.turnos[cod]):
                    if off == (0 if f == d else 1):
                        presentes[cid].add(t)
        necesidad = {q: (o, w) for q, (o, w) in dem.demanda_por_puesto(ctx, d, con_ayer=d != primero).items() if any(o) or any(w)}
        # bloques de tramos consecutivos con la misma presencia y la misma demanda
        bloques, firma_ant = [], None
        for t in range(dem.TRAMOS_DIA):
            pres = tuple(sorted(c for c, ts in presentes.items() if t in ts))
            nec = tuple(sorted((q, o[t], w[t]) for q, (o, w) in necesidad.items() if o[t] or w[t]))
            firma = (pres, nec)
            if not pres:
                firma_ant = None
                continue
            if firma == firma_ant and bloques and bloques[-1][1] == t:
                bloques[-1][1] = t + 1
            else:
                bloques.append([t, t + 1, pres, {q: (o, w) for q, o, w in nec}])
            firma_ant = firma
        m = cp_model.CpModel()
        y, obj = {}, []
        permitido = lambda c, q: por_id[c].puestos_permitidos is None or q in por_id[c].puestos_permitidos
        for bi, (t0, t1, pres, nec) in enumerate(bloques):
            largo = t1 - t0
            for c in pres:
                cand = [q for q in nec if permitido(c, q)]
                for q in cand:
                    y[bi, c, q] = m.NewBoolVar("")
                if cand:
                    m.Add(sum(y[bi, c, q] for q in cand) <= 1)
            for q, (o, w) in nec.items():
                suma = sum(y[bi, c, q] for c in pres if (bi, c, q) in y)
                if o:
                    falta = m.NewIntVar(0, o, "")
                    m.Add(suma + falta >= o)
                    numero = ctx.puestos[q].numero if q in ctx.puestos else 99
                    obj.append((W_FALTA_P + (99 - numero) * W_PRIORIDAD_P) * largo * falta)  # si falta gente, queda vacío el de mayor número
                if w and any((bi, c, q) in y for c in pres):
                    ok = m.NewBoolVar("")
                    m.Add(suma >= o + w).OnlyEnforceIf(ok)
                    obj.append(-W_DES_P * largo * w * ok)
        for bi in range(len(bloques) - 1):  # cambiar de puesto dentro del turno
            a, b = bloques[bi], bloques[bi + 1]
            if a[1] != b[0]:
                continue
            for c in set(a[2]) & set(b[2]):
                for q in {k[2] for k in y if k[0] == bi and k[1] == c}:
                    sale = m.NewBoolVar("")
                    m.Add(sale >= y[bi, c, q] - (y[bi + 1, c, q] if (bi + 1, c, q) in y else 0))
                    obj.append(W_CAMBIO_P * sale)
        usa = {}
        for (bi, c, q), v in y.items():  # rotación: no repetir el de ayer y repartir las veces por puesto
            if (c, q) not in usa:
                usa[c, q] = m.NewBoolVar("")
                obj.append((10 * hist[c][q] + (100 if ayer_p.get(c) == q else 0)) * usa[c, q])
            m.Add(usa[c, q] >= v)
        m.Minimize(sum(obj))
        sol = cp_model.CpSolver()
        sol.parameters.max_time_in_seconds = tiempo
        sol.parameters.num_workers = 1
        sol.parameters.random_seed = 0
        if bloques:
            sol.Solve(m)
        puesto_en = {}  # (colab_id, tramo) -> puesto_id
        for bi, (t0, t1, pres, nec) in enumerate(bloques):
            for c in pres:
                elegido = next((q for q in nec if (bi, c, q) in y and sol.Value(y[bi, c, q])), 0)
                for t in range(t0, t1):
                    puesto_en[c, t] = elegido
        cuenta = defaultdict(lambda: defaultdict(int))
        for rank, c in enumerate(sorted(presentes)):
            pausa = (rank + d.toordinal()) % 2 + 1
            ts = sorted(presentes[c])
            i = 0
            while i < len(ts):
                j = i
                while j + 1 < len(ts) and ts[j + 1] == ts[j] + 1 and puesto_en.get((c, ts[j + 1])) == puesto_en.get((c, ts[i])):
                    j += 1
                q = puesto_en.get((c, ts[i]), 0)
                out.append(AsignacionPuesto(d, c, q, ts[i] * dem.TRAMO_MIN, (ts[j] + 1) * dem.TRAMO_MIN, pausa))
                cuenta[c][q] += ts[j] - ts[i] + 1
                i = j + 1
        for c, qs in cuenta.items():
            principal = max((q for q in qs if q), key=lambda q: qs[q], default=0)
            hist[c][principal] += 1 if principal else 0
            ayer_p[c] = principal
    return out


def alertas_reparto(ctx, filas, fechas, catalogo):
    """Alertas de los puestos obligatorios que quedan sin cubrir en el reparto aunque haya gente suficiente por cabezas
    (por ejemplo, porque quien está presente no puede ocupar ese puesto). Si falta gente en total, ya lo avisa
    `reglas.faltantes_dia`."""
    por_dia = defaultdict(list)
    for a in filas:
        por_dia[a.fecha].append(a)
    primero, out = min(fechas), []
    for d in sorted(fechas):
        nec = dem.demanda_por_puesto(ctx, d, con_ayer=d != primero)
        presentes, ocupa = [0] * dem.TRAMOS_DIA, defaultdict(lambda: [0] * dem.TRAMOS_DIA)
        for a in por_dia.get(d, []):
            for t in range(a.desde // dem.TRAMO_MIN, a.hasta // dem.TRAMO_MIN):
                presentes[t] += 1
                if a.puesto_id:
                    ocupa[a.puesto_id][t] += 1
        total = [sum(o[t] for o, _ in nec.values()) for t in range(dem.TRAMOS_DIA)]
        for q in sorted(nec, key=lambda q: catalogo[q].numero if q in catalogo else 99):
            obl = nec[q][0]
            faltas = [max(0, obl[t] - ocupa[q][t]) if presentes[t] >= total[t] else 0 for t in range(dem.TRAMOS_DIA)]
            nombre = catalogo[q].nombre if q in catalogo else f"puesto {q}"
            t = 0
            while t < dem.TRAMOS_DIA:
                if not faltas[t]:
                    t += 1
                    continue
                u = t
                while u + 1 < dem.TRAMOS_DIA and faltas[u + 1] == faltas[t]:
                    u += 1
                out.append(Alerta("error", d, None, f"{d:%d/%m}: {nombre} sin cubrir {texto_tramos(t, u + 1)} (falta {faltas[t]})"))
                t = u + 1
    return out
