"""Asignación diaria de puestos (1 lavado, 2 autoclave, 3 sterrad y esto, 4 cuarto estéril, 5 ropa) y relevos de pausa."""
from collections import defaultdict
from datetime import timedelta
from itertools import permutations

from ortools.sat.python import cp_model

import demanda as dem
from dominio import AsignacionPuesto

PUESTOS = {0: "Apoyo", 1: "Lavado", 2: "Autoclave", 3: "Sterrad y esto", 4: "Cuarto estéril", 5: "Ropa"}
PRIORIDAD = [2, 1, 3, 4, 5]  # si falta gente, se cubren primero estos puestos


LEYENDA = "Puestos: " + " · ".join(f"{n} {PUESTOS[n]}" for n in (1, 2, 3, 4, 5)) + " · A apoyo (sin puesto fijo ese día)"


def por_persona(filas):
    """{(colab_id, fecha): puesto} a partir de las filas de `asignar`; un corrido tiene el mismo puesto en M y T."""
    out = {}
    for f, fr, p, c, g in sorted(filas, key=lambda x: x[1] != "M"):
        out.setdefault((c, f), p)
    return out


def tiene_puesto(turno):
    """Solo los turnos de día (que cubren mañana o tarde) llevan puesto; la noche no."""
    return bool({"M", "T"} & set(turno.cubre))


def etiqueta(cod, puesto):
    """Texto de celda con el puesto: «M·2» (autoclave), «T·A» (apoyo)."""
    return cod if puesto is None else f"{cod}·{puesto or 'A'}"


def _mejor(personas, opciones, costo):
    """Reparte `opciones` (más ceros de apoyo) entre `personas` con el menor costo total."""
    destino = (list(opciones) + [0] * len(personas))[:len(personas)]
    mejor = min(set(permutations(destino)), key=lambda perm: sum(costo(c, p) for c, p in zip(personas, perm)))
    return dict(zip(personas, mejor))


def asignar(ctx, cuadro, fechas):
    """[(fecha, franja, puesto, colab_id, grupo_pausa)] para las franjas M y T. Orden de reparto cada día: personas con
    puesto fijo, luego corridos (mismo puesto en M y T) y luego medias jornadas. Rota: castiga repetir el puesto del
    día anterior y los que la persona ya ocupó en el mes. Puesto 0 = apoyo (sobra gente)."""
    por_id = {p.id: p for p in ctx.colabs}
    hist = defaultdict(lambda: defaultdict(int))
    ayer = {}
    filas = []
    costo = lambda c, p: 10 * hist[c][p] + (100 if p and ayer.get(c) == p else 0)
    for d in sorted(fechas):
        franjas = {}  # persona -> franjas M/T que cubre su turno
        for (cid, f), cod in cuadro.items():
            if f == d and cod in ctx.turnos and cid in por_id:
                fr = tuple(x for x in ("M", "T") if x in ctx.turnos[cod].cubre)
                if fr:
                    franjas[cid] = fr
        libre = {"M": list(PRIORIDAD), "T": list(PRIORIDAD)}
        asig = {}
        for c, fr in franjas.items():  # 1) puesto fijo
            if por_id[c].puesto_fijo:
                asig[c] = por_id[c].puesto_fijo
                for x in fr:
                    if asig[c] in libre[x]:
                        libre[x].remove(asig[c])
        corridos = sorted(c for c, fr in franjas.items() if len(fr) == 2 and c not in asig)
        comunes = [p for p in PRIORIDAD if p in libre["M"] and p in libre["T"]]  # 2) corridos: un puesto libre en ambas
        asig.update(_mejor(corridos, comunes, costo))
        for c in corridos:
            for x in ("M", "T"):
                if asig[c] in libre[x]:
                    libre[x].remove(asig[c])
        for x in ("M", "T"):  # 3) medias jornadas
            solos = sorted(c for c, fr in franjas.items() if fr == (x,) and c not in asig)
            asig.update(_mejor(solos, libre[x], costo))
        for x in ("M", "T"):
            gente = sorted((c for c, fr in franjas.items() if x in fr), key=lambda c: (asig[c] == 0, asig[c]))
            for i, c in enumerate(gente):
                filas.append((d, x, asig[c], c, (i + d.toordinal()) % 2 + 1))
        for c, p in asig.items():
            hist[c][p] += 1
        ayer = asig
    return filas


# --- reparto por tramos horarios (reemplaza a `asignar` cuando la interfaz lo use) -------------------------------------
W_FALTA_P, W_DES_P, W_CAMBIO_P = 1000, 10, 60  # por persona y tramo; cambiar de puesto dentro del turno; rotación abajo


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
                    obj.append(W_FALTA_P * largo * falta)
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
