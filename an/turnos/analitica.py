"""Métricas del dashboard de Analíticas. Solo lectura: nada se escribe en la base. Sin Qt."""
from collections import defaultdict
from datetime import datetime, timedelta
from math import ceil

from . import demanda as dem
from . import cambios, flujo, puestos, recargos, reglas, solicitudes
from .dominio import DESCANSO_MIN, festivos, intervalo


def _ausencias(bd, ini, fin):
    """({(colab_id, fecha): tipo}, [Colaborador]) del rango; la primera novedad gana si se solapan."""
    gente = [p for p in bd.colaboradores() if p.en_solver]
    ids = {p.id for p in gente}
    out = {}
    for n in bd.novedades():
        if n.colab_id not in ids:
            continue
        d = max(n.desde, ini)
        while d <= min(n.hasta, fin):
            out.setdefault((n.colab_id, d), n.tipo)
            d += timedelta(days=1)
    return out, gente


def ausentismo(bd, ini, fin):
    aus, gente = _ausencias(bd, ini, fin)
    nombre = {p.id: p.nombre for p in gente}
    por_tipo, por_persona, por_mes = defaultdict(int), defaultdict(lambda: defaultdict(int)), defaultdict(lambda: defaultdict(int))
    for (cid, f), tipo in aus.items():
        por_tipo[tipo] += 1
        por_persona[nombre[cid]][tipo] += 1
        por_mes[f"{f:%Y-%m}"][tipo] += 1
    dias = (fin - ini).days + 1
    pct = len(aus) / (dias * len(gente)) * 100 if gente else 0
    return {"por_tipo": dict(por_tipo), "por_persona": {k: dict(v) for k, v in por_persona.items()},
            "por_mes": {k: dict(v) for k, v in sorted(por_mes.items())}, "pct": pct}


def simultaneos(bd, ini, fin):
    aus, _ = _ausencias(bd, ini, fin)
    cuenta = defaultdict(int)
    for _, f in aus:
        cuenta[f] += 1
    serie = [(f, cuenta[f]) for f in flujo.fechas(ini, fin)]
    maximo = max((n for _, n in serie), default=0)
    fecha_max = next((f for f, n in serie if n == maximo), None) if maximo else None
    cuadro = bd.asignaciones_rango(ini, fin)
    dias = sorted({f for _, f in cuadro})
    riesgo = []
    if dias:
        falt = reglas.faltantes_periodo(bd.contexto(ini.year), cuadro, dias)
        riesgo = [f for f in dias if cuenta[f] and any(v[0] for v in falt[f].values())]
    return {"serie": serie, "maximo": maximo, "fecha_maximo": fecha_max, "dias_riesgo": riesgo}


def _presentes(ctx, cuadro, fecha, con_ayer):
    """Personas por tramo de 30 min: quienes empiezan hoy y, si `con_ayer`, la madrugada de las noches de ayer."""
    hay = [0] * dem.TRAMOS_DIA
    activos = {p.id for p in ctx.colabs if p.en_solver}
    ayer = fecha - timedelta(days=1)
    for (cid, f), cod in cuadro.items():
        if cid in activos and cod in ctx.turnos and (f == fecha or (f == ayer and con_ayer)):
            for off, t in dem.turno_tramos(ctx.turnos[cod]):
                if off == (0 if f == fecha else 1):
                    hay[t] += 1
    return hay


def _cruza(k, ini, fin):
    a, b = flujo.desde_clave(k)
    return a <= fin and b >= ini


def cobertura(bd, ini, fin):
    """Por periodo con cuadro que toca el rango: días con déficit, días con exceso y puestos obligatorios sin cubrir."""
    ctx, out = bd.contexto(ini.year), []
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        a, b = flujo.desde_clave(k)
        dias, cuadro = flujo.fechas(a, b), bd.asignaciones(k)
        deficit = exceso = 0
        for f in dias:
            con_ayer = f != a
            if any(v[0] for v in reglas.faltantes_dia(ctx, cuadro, f, con_ayer).values()):
                deficit += 1
            obl, des = dem.demanda_fecha(ctx, f, con_ayer)
            if any(h > o + d for h, o, d in zip(_presentes(ctx, cuadro, f, con_ayer), obl, des)):
                exceso += 1
        alertas = puestos.alertas_reparto(ctx, bd.asignacion_puesto(k), dias, bd.catalogo_puestos())
        out.append({"periodo": k, "dias_deficit": deficit, "dias_exceso": exceso, "puestos_sin_cubrir": len(alertas)})
    return out


def cobertura_tramos(bd, ini, fin):
    """Personas frente a demanda por tramo de 30 min en los periodos con cuadro del rango. El hueco se mide en cada
    tramo antes de sumar (un tramo sobrado no tapa otro corto). Horas = personas-tramo / 2. Cobertura = 1 − faltantes /
    requeridas; eficiencia = 1 − (faltantes + sobrantes) / requeridas (sobra = por encima de obligatoria + deseable).
    `mapa`: 7 × 48 con el promedio de presentes − obligatorias por día de la semana y tramo (None si nunca hubo demanda
    ni gente)."""
    ctx = bd.contexto(ini.year)
    suma, n = [[0] * dem.TRAMOS_DIA for _ in range(7)], [[0] * dem.TRAMOS_DIA for _ in range(7)]
    por_periodo = []
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        a, b = flujo.desde_clave(k)
        cuadro, req, falta, sobra = bd.asignaciones(k), 0, 0, 0
        for f in (f for f in flujo.fechas(a, b) if ini <= f <= fin):
            con_ayer = f != a
            obl, des = dem.demanda_fecha(ctx, f, con_ayer)
            hay = _presentes(ctx, cuadro, f, con_ayer)
            for t in range(dem.TRAMOS_DIA):
                req += obl[t]
                falta += max(0, obl[t] - hay[t])
                sobra += max(0, hay[t] - obl[t] - des[t])
                if obl[t] or hay[t]:
                    suma[f.weekday()][t] += hay[t] - obl[t]
                    n[f.weekday()][t] += 1
        por_periodo.append({"periodo": k, "horas_requeridas": req / 2, "horas_faltantes": falta / 2, "horas_sobrantes": sobra / 2})
    req, falta, sobra = (sum(p[c] for p in por_periodo) for c in ("horas_requeridas", "horas_faltantes", "horas_sobrantes"))
    return {"horas_requeridas": req, "horas_faltantes": falta, "horas_sobrantes": sobra,
            "cobertura_pct": (1 - falta / req) * 100 if req else None,
            "eficiencia_pct": max(0.0, (1 - (falta + sobra) / req) * 100) if req else None,  # con más sobra que demanda, 0 (no negativa)
            "mapa": [[round(suma[w][t] / n[w][t], 2) if n[w][t] else None for t in range(dem.TRAMOS_DIA)] for w in range(7)],
            "por_periodo": por_periodo}


def cambios_resumen(bd, ini, fin):
    """{periodo: {permuta, servicio, ajuste, excepciones}} de los cambios vigentes (sin anulados)."""
    out = {}
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        filas = [r for r in cambios.listar(bd, k) if not r["anulado_en"]]
        if filas:
            out[k] = {t: sum(r["tipo"] == t for r in filas) for t in ("permuta", "servicio", "ajuste")}
            out[k]["excepciones"] = sum(1 for r in filas if r["excepcion"])
    return out


def estabilidad(bd, ini, fin, publicados):
    """Qué tanto se movió el cuadro después de publicarlo. `publicados` = {clave: datetime local de la primera
    publicación}; los periodos sin publicar no cuentan. Por periodo, mirando los cambios vigentes registrados desde esa
    publicación (publicar otra vez no borra la cuenta): celdas distintas que tocaron, cuántas se registraron con menos
    de `aviso_corto_horas` antes del turno (las correcciones de un turno ya empezado no son aviso) y días de
    anticipación de la publicación. `cubre_mas`: turnos que cada persona tomó en un día libre por cambios de servicio."""
    ctx = bd.contexto(ini.year)
    gente = {p.id: p.nombre for p in ctx.colabs if p.en_solver}
    aviso = timedelta(hours=int(bd.param("aviso_corto_horas", 48)))
    periodos, cubre = [], defaultdict(int)
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin) and k in publicados):
        a, b = flujo.desde_clave(k)
        total = len(gente) * ((b - a).days + 1)
        tocadas, corto = set(), 0
        for r in (r for r in cambios.listar(bd, k) if not r["anulado_en"]):
            hecho = datetime.fromisoformat(r["registrado_en"])
            for cid, f, antes, despues, *_ in r["celdas"]:
                if r["tipo"] == "servicio" and antes not in ctx.turnos and despues in ctx.turnos and cid in gente:
                    cubre[gente[cid]] += 1
                if hecho < publicados[k] or cid not in gente:
                    continue
                tocadas.add((cid, f))
                cod = despues if despues in ctx.turnos else antes
                inicio = intervalo(ctx.turnos[cod], f)[0] if cod in ctx.turnos else datetime.combine(f, datetime.min.time())
                corto += timedelta(0) <= inicio - hecho < aviso
        periodos.append({"periodo": k, "celdas_cambiadas": len(tocadas), "celdas_total": total,
                         "pct": len(tocadas) / total * 100 if total else 0, "aviso_corto": corto,
                         "dias_anticipacion": (a - publicados[k].date()).days})
    return {"periodos": periodos, "cubre_mas": dict(cubre)}


def fatiga(bd, ini, fin):
    """Señales de cansancio por persona en el cuadro vigente del rango (los 27 días previos solo siembran rachas y la
    ventana de 4 semanas). No son alertas: `validar` ya avisa lo que rompe reglas dentro de cada periodo.
    `senales` cuenta: racha de días más larga que `max_dias_seguidos`, más noches seguidas que `max_noches_seguidas`
    (noche-libre-noche, como en `validar`), algún descanso menor a `descanso_corto_horas`, y fines de semana trabajados
    por encima de la media del equipo + 1."""
    ctx = bd.contexto(ini.year)
    gente = [p for p in ctx.colabs if p.en_solver]
    if not gente:
        return {}
    antes = ini - timedelta(days=27)
    cuadro, dias = bd.asignaciones_rango(antes, fin), flujo.fechas(antes, fin)
    tope, max_n = int(bd.param("max_dias_seguidos", 6)), int(bd.param("max_noches_seguidas", 2))
    corto = timedelta(hours=int(bd.param("descanso_corto_horas", DESCANSO_MIN // 60)))
    paso = ctx.libre_tras_noche + 1
    out = {}
    for p in gente:
        t = lambda d: ctx.turnos.get(cuadro.get((p.id, d), "L"))
        noche = lambda d: (x := t(d)) is not None and dem.es_noche(x)
        r = {"max_dias_seguidos": 0, "rachas_largas": 0, "max_noches_seguidas": 0, "descansos_cortos": 0,
             "fines_trabajados": 0, "horas_4_sem_max": 0.0}
        racha, fines = 0, set()
        for d in dias:
            racha = racha + 1 if t(d) else 0
            if d < ini:
                continue
            r["max_dias_seguidos"] = max(r["max_dias_seguidos"], racha)
            r["rachas_largas"] += racha == tope + 1 or (d == ini and racha > tope)  # la racha pudo empezar antes del rango
            ayer = d - timedelta(days=1)
            if t(d) and t(ayer) and intervalo(t(d), d)[0] - intervalo(t(ayer), ayer)[1] < corto:
                r["descansos_cortos"] += 1
            if noche(d):
                n = 1
                while noche(d - timedelta(days=paso * n)):
                    n += 1
                r["max_noches_seguidas"] = max(r["max_noches_seguidas"], n)
            if t(d) and d.weekday() >= 5:
                fines.add(d - timedelta(days=d.weekday() - 5))  # el sábado de ese fin de semana
            horas = sum(x.horas for k in range(28) if (x := t(d - timedelta(days=k))))
            r["horas_4_sem_max"] = max(r["horas_4_sem_max"], round(horas, 2))
        r["fines_trabajados"] = len(fines)
        out[p.nombre] = r
    media = sum(r["fines_trabajados"] for r in out.values()) / len(out)
    for r in out.values():
        r["senales"] = ((r["rachas_largas"] > 0) + (bool(max_n) and r["max_noches_seguidas"] > max_n)  # 0 = sin límite + (r["descansos_cortos"] > 0)
                        + (r["fines_trabajados"] > media + 1))
    return out


NO_PLANEADAS = ("Incapacidad", "Licencia")  # vacaciones y libres solicitados se planean: no dicen nada del patrón
TRAMOS_BRADFORD = (("0-49", 0), ("50-199", 50), ("200-499", 200), ("500+", 500))


def _rachas_ausencia(bd, ini, fin):
    """[(colab_id, tipo, desde, hasta)] de ausencias no planeadas: días seguidos de la misma persona y tipo, recortados al rango."""
    aus, _ = _ausencias(bd, ini, fin)
    out = []
    for (cid, f), tipo in sorted(aus.items()):
        if tipo not in NO_PLANEADAS:
            continue
        if out and out[-1][0] == cid and out[-1][1] == tipo and out[-1][3] == f - timedelta(days=1):
            out[-1] = (cid, tipo, out[-1][2], f)
        else:
            out.append((cid, tipo, f, f))
    return out


def patrones_ausencia(bd, ini, fin):
    """Ausencias no planeadas: % de días-persona por día de la semana (lunes primero) en el rango, rachas que empiezan
    el día después de un festivo y factor Bradford (rachas² × días). Bradford mira siempre los 12 meses que terminan en
    `fin` (sus tramos 0-49…500+ suponen un año); sirve para ver patrones, no para sancionar."""
    ctx = bd.contexto(ini.year)
    gente = {p.id: p.nombre for p in ctx.colabs if p.en_solver}
    dias = flujo.fechas(ini, fin)
    ausentes = [0] * 7
    for _, _, a, b in _rachas_ausencia(bd, ini, fin):
        for f in flujo.fechas(a, b):
            ausentes[f.weekday()] += 1
    por_dia = [ausentes[w] / (n * len(gente)) * 100 if (n := sum(f.weekday() == w for f in dias)) and gente else 0 for w in range(7)]
    desde_b = fin - timedelta(days=364)
    por = {}
    for cid, _, a, b in _rachas_ausencia(bd, desde_b, fin):
        o = por.setdefault(gente[cid], {"rachas": 0, "dias": 0})
        o["rachas"] += 1
        o["dias"] += (b - a).days + 1
    for o in por.values():
        o["puntaje"] = o["rachas"] ** 2 * o["dias"]
    equipo = {k: 0 for k, _ in TRAMOS_BRADFORD}
    for nombre in gente.values():
        puntaje = por.get(nombre, {}).get("puntaje", 0)
        equipo[next(k for k, lo in reversed(TRAMOS_BRADFORD) if puntaje >= lo)] += 1
    fest = set().union(*(festivos(y) for y in range(ini.year - 1, fin.year + 1)))
    antes = ini - timedelta(days=1)  # mirar un día antes: una racha recortada en `ini` no empezó allí
    tras = sum(1 for _, _, a, _ in _rachas_ausencia(bd, antes, fin) if a >= ini and a - timedelta(days=1) in fest)
    return {"por_dia_semana": por_dia, "tras_festivo": tras, "bradford": {"desde": desde_b, "equipo": equipo, "por_persona": por}}


MIN_HISTORIAL = 3  # días de ausencia en ese día de la semana para tomarlo en serio: con uno solo todo sería «riesgo»


def riesgo_proximo(bd, hoy, dias=14):
    """Días de los próximos `dias` con cuadro guardado donde alguna franja queda justa o en falta (margen ≤ 0) y que caen
    en un día de la semana con más ausencias no planeadas que la media en los últimos 365 días (y al menos
    `MIN_HISTORIAL` días de ausencia en ese día)."""
    ctx = bd.contexto(hoy.year)
    hasta = hoy + timedelta(days=dias - 1)
    con_cuadro = [k for k in bd.periodos() if _cruza(k, hoy, hasta)]
    if not con_cuadro:
        return []
    desde_h, fin_h = hoy - timedelta(days=365), hoy - timedelta(days=1)
    tasas = patrones_ausencia(bd, desde_h, fin_h)["por_dia_semana"]
    conteo = [0] * 7
    for _, _, a, b in _rachas_ausencia(bd, desde_h, fin_h):
        for f in flujo.fechas(a, b):
            conteo[f.weekday()] += 1
    media = sum(tasas) / 7
    cuadro = bd.asignaciones_rango(hoy - timedelta(days=1), hasta)
    out = []
    for f in flujo.fechas(hoy, hasta):
        w = f.weekday()
        if tasas[w] <= media or conteo[w] < MIN_HISTORIAL or not any(a <= f <= b for a, b in map(flujo.desde_clave, con_cuadro)):
            continue
        justas = [reglas.FRANJA_NOMBRE[fr] for fr, m in reglas.margen_dia(ctx, cuadro, f).items() if m is not None and m <= 0]
        if justas:
            out.append({"fecha": f, "franjas": justas, "tasa": round(tasas[w], 2), "media": round(media, 2)})
    return out


# --- entrega 2: horas, recargos y equidad ---------------------------------------------------------
def _reportes(bd, ini, fin, ventana=None):
    """[(periodo, [(Colaborador, reporte)])] de los periodos con cuadro que tocan el rango. `ventana` en semanas
    (por defecto la configurada); `"periodo"` = una sola ventana que abarca todo el periodo."""
    ctx, tar = bd.contexto(ini.year), bd.tarifas()
    conf = int(bd.param("ventana_semanas", 3))
    gente = [p for p in ctx.colabs if p.en_solver]
    out = []
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        dias, cuadro = flujo.fechas(*flujo.desde_clave(k)), bd.asignaciones(k)
        v = ceil(len(dias) / 7) if ventana == "periodo" else conf
        out.append((k, [(p, recargos.reporte(ctx, tar, p, cuadro, dias, v)) for p in gente]))
    return out


def _extras(reportes):
    suma = {"diurna": 0.0, "nocturna": 0.0}
    for _, r in reportes:
        for (tipo, jornada, _), h in r["cat"].items():
            if tipo == "extra":
                suma[jornada] += h
    return {k: round(v, 2) for k, v in suma.items()}


def horas_extra(bd, ini, fin):
    """Por periodo: horas extra diurnas y nocturnas con la ventana de N semanas y con una sola ventana del periodo."""
    conf = int(bd.param("ventana_semanas", 3))
    semanas, mes = _reportes(bd, ini, fin), _reportes(bd, ini, fin, "periodo")
    return [{"periodo": k, "ventana": conf, "mes": _extras(m), "semanas": _extras(s)}
            for (k, s), (_, m) in zip(semanas, mes)]


def recargos_resumen(bd, ini, fin):
    """{nombre: {festivo, nocturna, equivalentes}} en horas, sumando los periodos del rango (festivo = domingos y festivos)."""
    out = {}
    for _, filas in _reportes(bd, ini, fin):
        for p, r in filas:
            o = out.setdefault(p.nombre, {"festivo": 0.0, "nocturna": 0.0, "equivalentes": 0.0})
            o["festivo"] += sum(h for c, h in r["cat"].items() if c[2] == "festivo")
            o["nocturna"] += sum(h for c, h in r["cat"].items() if c[1] == "nocturna")
            o["equivalentes"] += r["equivalentes"]
    return {n: {k: round(v, 2) for k, v in o.items()} for n, o in out.items()}


def equidad(bd, ini, fin):
    """Noches, domingos y festivos trabajados por persona (turnos contados por su fecha de inicio)."""
    ctx = bd.contexto(ini.year)
    gente = {p.id: p.nombre for p in ctx.colabs if p.en_solver}
    por = {n: {"noches": 0, "domingos": 0, "festivos": 0} for n in gente.values()}
    for k in (k for k in bd.periodos() if _cruza(k, ini, fin)):
        for (cid, f), cod in bd.asignaciones(k).items():
            t = ctx.turnos.get(cod)
            if cid not in gente or not t or not ini <= f <= fin:
                continue
            o = por[gente[cid]]
            o["noches"] += dem.es_noche(t)
            if f.weekday() == 6:
                o["domingos"] += 1
            elif f in ctx.fest:
                o["festivos"] += 1
    cats = ("noches", "domingos", "festivos")
    disp = {c: (max(o[c] for o in por.values()) - min(o[c] for o in por.values())) if por else 0 for c in cats}
    # Desviación de cada persona respecto de la media del equipo, con los conteos llevados a tiempo completo (÷ dedicación):
    # minimizar la desviación media fue lo más justo en los estudios de turnos de enfermería (Martin et al., MinDev).
    ded = {p.nombre: p.pct or 1 for p in ctx.colabs if p.en_solver}
    ajust = {n: {c: o[c] / ded[n] for c in cats} for n, o in por.items()}
    est, desv = {}, {n: {} for n in por}
    for c in cats:
        vals = [a[c] for a in ajust.values()]
        media = sum(vals) / len(vals) if vals else 0
        for n, a in ajust.items():
            desv[n][c] = round(a[c] - media, 6)
        mad = sum(abs(v - media) for v in vals) / len(vals) if vals else 0
        sd = (sum((v - media) ** 2 for v in vals) / len(vals)) ** 0.5 if vals else 0
        est[c] = {"media": round(media, 6), "mad": round(mad, 6), "cv": round(sd / media, 6) if media else 0}
    return {"por_persona": por, "dispersion": disp, "estadisticas": est, "desviacion": desv}


def concentracion_extra(bd, ini, fin):
    """Horas extra por persona (ventana configurada) y qué % del total hizo el 20 % del equipo con más horas extra."""
    por = defaultdict(float)
    for _, filas in _reportes(bd, ini, fin):
        for p, r in filas:
            por[p.nombre] += sum(h for (tipo, _, _), h in r["cat"].items() if tipo == "extra")
    gente = [p for p in bd.contexto(ini.year).colabs if p.en_solver]
    top_n = ceil(len(gente) * 0.2)
    total = sum(por.values())
    arriba = sum(sorted(por.values(), reverse=True)[:top_n])
    return {"por_persona": {n: round(h, 2) for n, h in por.items() if h}, "top_n": top_n,
            "top_pct": round(arriba / total * 100, 2) if total else None}


def solicitudes_resumen(bd, ini, fin):
    """Solicitudes con días dentro del rango (y con cuadro), evaluadas sobre el cuadro vigente: por persona pedidas,
    cumplidas, parciales y no cumplidas y su tasa; por tipo; y la tasa del equipo. Una solicitud que cruza dos periodos
    se evalúa una sola vez."""
    ctx = bd.contexto(ini.year)
    nombre = {p.id: p.nombre for p in ctx.colabs if p.en_solver}
    periodos = [k for k in bd.periodos() if _cruza(k, ini, fin)]
    fechas = sorted({f for k in periodos for f in flujo.fechas(*flujo.desde_clave(k)) if ini <= f <= fin})
    cuadro = bd.asignaciones_rango(ini, fin)
    fijos = {c for k in periodos for c in bd.fijos(k)}
    por, tipos = {}, {}
    for r in solicitudes.evaluar(ctx, cuadro, fechas, fijos):
        if r.estado == "fuera" or r.solicitud.colab_id not in nombre:
            continue
        o = por.setdefault(nombre[r.solicitud.colab_id], {"pedidas": 0, "cumplidas": 0, "parciales": 0, "no_cumplidas": 0})
        o["pedidas"] += 1
        o[{"cumplida": "cumplidas", "parcial": "parciales", "no cumplida": "no_cumplidas"}[r.estado]] += 1
        t = tipos.setdefault(r.solicitud.tipo, {"pedidas": 0, "cumplidas": 0})
        t["pedidas"] += 1
        t["cumplidas"] += r.estado == "cumplida"
    for o in por.values():
        o["tasa"] = round(o["cumplidas"] / o["pedidas"] * 100, 2)
    pedidas = sum(o["pedidas"] for o in por.values())
    return {"por_persona": por, "por_tipo": tipos,
            "tasa": round(sum(o["cumplidas"] for o in por.values()) / pedidas * 100, 2) if pedidas else None}


# --- entrega 3: banco de horas --------------------------------------------------------------------
def banco(bd, ini, fin):
    """Saldos al fin del rango y serie mensual (favor, deuda). Solo periodos cerrados y movimientos; sin proyecciones."""
    gente = {p.id: p.nombre for p in bd.colaboradores(solo_activos=False) if p.en_solver}
    cierres = [(flujo.desde_clave(per)[1], cid, trab - contr) for per, cid, contr, trab in bd.cierres()]
    movs = [(f, cid, h) for _, cid, f, h, _, _ in bd.movimientos()]

    def saldos(hasta):
        s = {cid: 0.0 for cid in gente}
        for f, cid, h in cierres + movs:
            if f <= hasta and cid in s:
                s[cid] += h
        return s

    serie, m = [], ini.year * 12 + ini.month - 1
    while m <= fin.year * 12 + fin.month - 1:
        y, mes = divmod(m, 12)
        s = saldos(flujo.periodo_mes(y, mes + 1)[1])
        serie.append((f"{mes + 1:02d}/{y % 100:02d}", round(sum(v for v in s.values() if v > 0), 2),
                      round(-sum(v for v in s.values() if v < 0), 2)))
        m += 1
    return {"saldos": {gente[c]: round(v, 2) for c, v in saldos(fin).items()}, "serie": serie}
