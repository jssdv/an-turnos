"""Asignación diaria de puestos (1 lavado, 2 autoclave, 3 sterrad y esto, 4 cuarto estéril, 5 ropa) y relevos de pausa."""
from collections import defaultdict
from itertools import permutations

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
