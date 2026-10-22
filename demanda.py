"""Modelo puro de la demanda de puestos por tramos de 30 minutos (sin base de datos ni interfaz)."""
import math
from collections import defaultdict
from datetime import timedelta

TRAMO_MIN = 30
TRAMOS_DIA = 48
FRANJAS = {"M": range(12, 24), "T": range(24, 36), "N": [*range(36, 48), *range(0, 12)]}
_MIN_FRANJA = {"M": (360, 720), "T": (720, 1080), "N": (1080, 1800)}  # N sigue de 18:00 a 06:00 del día siguiente


def tramos_ventana(inicio, fin):
    """[(dia_offset, tramo)] de la ventana [inicio, fin); offset 1 = día siguiente. Cuenta solo tramos completos."""
    dur = (fin - inicio) % 1440 or 1440
    primero = -(-inicio // TRAMO_MIN)
    ultimo = (inicio + dur) // TRAMO_MIN
    return [divmod(i, TRAMOS_DIA) for i in range(primero, ultimo)]


def franjas_de(turno):
    """Franjas (M, T, N) en que un turno cuenta: se solapa con ellas al menos 3 h."""
    ini, dur = turno.inicio, turno.duracion
    out = []
    for fr, (a, b) in _MIN_FRANJA.items():
        solape = 0
        for desp in (-1440, 0, 1440):
            solape += max(0, min(ini + dur, b + desp) - max(ini, a + desp))
        if solape >= 180:
            out.append(fr)
    return tuple(out)


def turno_tramos(turno):
    """[(dia_offset, tramo)] que cubre un turno que empieza el día de referencia."""
    return tramos_ventana(turno.inicio, turno.fin)


def demanda_fecha(ctx, fecha):
    """(obligatoria, deseable): 48 enteros cada una con las personas pedidas en cada tramo de `fecha`. Incluye la
    parte que cae hoy de las ventanas que empezaron ayer, con el tipo de día de ayer."""
    obl, des = [0] * TRAMOS_DIA, [0] * TRAMOS_DIA
    ayer = fecha - timedelta(days=1)
    for d in ctx.demandas:
        for dia, tipo in ((0, ctx.tipo_dia(fecha)), (1, ctx.tipo_dia(ayer))):
            if d.tipo_dia != tipo:
                continue
            for off, t in tramos_ventana(d.inicio, d.fin):
                if off == dia:
                    (obl if d.obligatorio else des)[t] += d.personas
    return obl, des


def _plano(demandas, tipo_dia, obligatorio=True):
    """Demanda de un tipo de día plegada a 48 tramos (la madrugada de una ventana nocturna suma a los tramos 0–11)."""
    out = [0] * TRAMOS_DIA
    for d in demandas:
        if d.tipo_dia == tipo_dia and d.obligatorio == obligatorio:
            for _, t in tramos_ventana(d.inicio, d.fin):
                out[t] += d.personas
    return out


def cobertura_derivada(demandas):
    """{"LS": {"M": n, "T": n, "N": n}, "DF": {...}}: la mayor demanda obligatoria simultánea de cada franja."""
    return {td: {fr: max((plano[t] for t in tr), default=0) for fr, tr in FRANJAS.items()}
            for td in ("LS", "DF") for plano in [_plano(demandas, td)]}


def huecos_sin_turno(demandas, turnos):
    """Rangos (inicio, fin) en minutos de las ventanas que ningún turno activo cubre."""
    huecos = []
    for d in demandas:
        cubierto = set()
        for t in turnos.values():
            if not (t.activo and t.solver) or (d.tipo_dia == "DF" and not t.dom_fest):
                continue
            for base in (0, TRAMOS_DIA):
                cubierto |= {base + o * TRAMOS_DIA + x for o, x in turno_tramos(t)}
        libres = sorted(o * TRAMOS_DIA + x for o, x in tramos_ventana(d.inicio, d.fin) if o * TRAMOS_DIA + x not in cubierto)
        i = 0
        while i < len(libres):
            j = i
            while j + 1 < len(libres) and libres[j + 1] == libres[j] + 1:
                j += 1
            huecos.append((libres[i] * TRAMO_MIN, (libres[j] + 1) * TRAMO_MIN))
            i = j + 1
    return huecos


def horas_persona_semana(demandas, incluir_deseables=False):
    """Horas-persona de una semana tipo (6 días LS + 1 DF)."""
    total = 0.0
    for d in demandas:
        if d.obligatorio or incluir_deseables:
            total += len(tramos_ventana(d.inicio, d.fin)) * 0.5 * d.personas * (6 if d.tipo_dia == "LS" else 1)
    return total


def estimar_personas(demandas, jornada_media, margen, incluir_deseables=False):
    por_puesto, por_franja = defaultdict(float), {"M": 0.0, "T": 0.0, "N": 0.0}
    for d in demandas:
        if not (d.obligatorio or incluir_deseables):
            continue
        veces = 6 if d.tipo_dia == "LS" else 1
        for _, t in tramos_ventana(d.inicio, d.fin):
            h = 0.5 * d.personas * veces
            por_puesto[d.puesto_id] += h
            por_franja[next(fr for fr, tr in FRANJAS.items() if t in tr)] += h
    horas = sum(por_puesto.values())
    personas = math.ceil(round(horas / (jornada_media * (1 - margen)), 6)) if horas else 0
    return {"horas_semana": horas, "personas": personas, "por_puesto": dict(por_puesto), "por_franja": por_franja}
