"""Salidas en Excel: cuadro mensual, planilla de puestos y reporte de horas y recargos. Nunca sobrescribe."""
from datetime import date, datetime, timedelta
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.cell import coordinate_from_string, column_index_from_string
from openpyxl.worksheet.properties import PageSetupProperties

from an.nucleo.xlsx import poner_texto

from . import flujo
from . import recargos
from . import reglas
from .dominio import DIAS, Puesto, intervalo
from .puestos import alertas_reparto, etiqueta, leyenda, por_persona

ABREV_NOVEDAD = {"Vacaciones": "VAC", "Incapacidad": "INC", "Licencia": "LIC", "Libre solicitado": "LIB"}
ENCABEZADO = PatternFill("solid", fgColor="1F3864")
AMARILLO = PatternFill("solid", fgColor="FFFF00")
GRIS = PatternFill("solid", fgColor="D9D9D9")
FESTIVO = PatternFill("solid", fgColor="F8CBAD")
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)


def ruta_libre(carpeta, base):
    """`base.xlsx`, luego `base v2.xlsx`, `base v3.xlsx`…"""
    carpeta, n = Path(carpeta), 1
    while (r := carpeta / (f"{base}.xlsx" if n == 1 else f"{base} v{n}.xlsx")).exists():
        n += 1
    return r


def _encabezado(ws, fila, textos, col=1):
    for i, t in enumerate(textos):
        c = ws.cell(fila, col + i, t)
        c.fill, c.font, c.alignment = ENCABEZADO, Font(bold=True, color="FFFFFF"), CENTRO


class _Pct(float):
    """Porcentaje 0–100 del núcleo: en Excel va como fracción con formato «0,0 %» para que se pueda sumar o graficar."""


def _pct(v):
    return None if v is None else _Pct(v)


def _valor(celda, v):
    """Fecha con formato dd/mm/aaaa, porcentaje como fracción, vacío en vez de «—» y texto que Excel no lea como fórmula."""
    if isinstance(v, _Pct):
        celda.value, celda.number_format = v / 100, "0.0%"
    elif isinstance(v, date):
        celda.value, celda.number_format = v, "dd/mm/yyyy"
    else:
        poner_texto(celda, v)
    return celda


def _tabla(ws):
    """Hoja de una tabla con encabezado en la fila 1: encabezado fijo al desplazarse y filtros en cada columna."""
    ws.freeze_panes = ws.freeze_panes or "B2"
    if ws.max_row > 1:
        ws.auto_filter.ref = f"A1:{get_column_letter(ws.max_column)}{ws.max_row}"


def _terminar(wb, titulo):
    """Lo que lleva todo libro antes de guardarse: A4 apaisado a una página de ancho, las filas y columnas fijas repetidas
    en cada hoja impresa y, en el margen, el título, cuándo se generó y el número de página."""
    hecho = f"Generado el {datetime.now():%d/%m/%Y %H:%M}"
    for ws in wb.worksheets:
        ws.page_setup.orientation, ws.page_setup.paperSize = "landscape", ws.PAPERSIZE_A4
        ws.page_setup.fitToWidth, ws.page_setup.fitToHeight = 1, 0
        ws.sheet_properties.pageSetUpPr = PageSetupProperties(fitToPage=True)
        if ws.freeze_panes:
            letra, fila = coordinate_from_string(ws.freeze_panes)
            if fila > 1:
                ws.print_title_rows = f"1:{fila - 1}"
            if (col := column_index_from_string(letra)) > 1:
                ws.print_title_cols = f"A:{get_column_letter(col - 1)}"
        ws.oddHeader.left.text = f"{titulo} · {ws.title}".replace("&", "&&")
        ws.oddFooter.left.text = hecho
        ws.oddFooter.right.text = "Página &P de &N"


def _ancho(ws, primera, resto, desde=2):
    ws.column_dimensions["A"].width = primera
    for i in range(desde, ws.max_column + 1):
        ws.column_dimensions[get_column_letter(i)].width = resto


def _hoja_cuadro(ws, ctx, cuadro, fechas, comparar=None, puestos=None, detalle=None, contadores=None):
    """`detalle` ({colab_id: recargos.reporte}): horas, de más/menos y balance por turno como fórmulas sobre las celdas del
    cuadro (hoja «Turnos» del mismo libro) y recargos como valores. `contadores` ([(puesto, días sin cubrir)]): una fila por
    puesto bajo el cuadro; la hoja lleva celdas «M·2»."""
    cols = [p for p in ctx.colabs if p.en_solver]
    col, sumas, c = {}, [], 1  # columna de cada fecha y, tras cada domingo (o el último día), la suma de horas de esa semana
    for f in fechas:
        c += 1
        col[f] = c
        if f.weekday() == 6 or f == fechas[-1]:
            c += 1
            sumas.append((c, [g for g in fechas if g - timedelta(days=g.weekday()) == f - timedelta(days=f.weekday())]))
    ncol = c
    n, ult = len(cols) + 1, get_column_letter(ncol)
    solver = [t for t in ctx.turnos.values() if t.activo and t.solver] if detalle is not None else []
    extra = ["De más", "De menos"] + [t.codigo for t in solver] + ["Horas equiv. recargos", "Horas dom/fest", "Horas nocturnas"] if detalle is not None else []
    contr = ncol + 2
    enc = ["Colaborador"] + [""] * (ncol - 1)
    for f in fechas:
        enc[col[f] - 1] = f"{DIAS[f.weekday()]}\n{f.day}"
    for c, _ in sumas:
        enc[c - 1] = "Σ sem"
    _encabezado(ws, 1, enc + ["Horas"] + (["Contratadas"] + extra if detalle is not None else []))
    for f in fechas:
        if ctx.tipo_dia(f) == "DF":
            ws.cell(1, col[f]).fill = PatternFill("solid", fgColor="C55A11")
    for r, p in enumerate(cols, 2):
        poner_texto(ws.cell(r, 1), p.nombre).font = Font(bold=True)
        horas = 0
        for f in fechas:
            i, cod = col[f], cuadro.get((p.id, f), "L")
            nov = ctx.novedad(p.id, f)
            texto = ABREV_NOVEDAD[nov.tipo] if nov and cod == "L" else cod
            if puestos is not None and cod in ctx.turnos and (p.id, f) in puestos:
                texto = etiqueta(cod, puestos[p.id, f])
            c = poner_texto(ws.cell(r, i), texto)
            c.alignment = CENTRO
            if cod in ctx.turnos:
                c.fill = PatternFill("solid", fgColor=ctx.turnos[cod].color)
                horas += ctx.turnos[cod].horas
            elif nov:
                c.fill = GRIS
            if comparar is not None and comparar.get((p.id, f), "L") != cod:
                c.fill = AMARILLO
        for c, sem in sumas:  # horas de la semana lunes–domingo en la celda tras el domingo
            if detalle is None:
                ws.cell(r, c, sum(ctx.turnos[cuadro.get((p.id, g), "L")].horas for g in sem if cuadro.get((p.id, g), "L") in ctx.turnos))
            else:
                ws.cell(r, c, f"=SUMPRODUCT(COUNTIF({get_column_letter(col[sem[0]])}{r}:{get_column_letter(col[sem[-1]])}{r},Turnos!$A$2:$A${len(ctx.turnos) + 1}),Turnos!$C$2:$C${len(ctx.turnos) + 1})")
            ws.cell(r, c).font = Font(bold=True)
        if detalle is None:
            ws.cell(r, ncol + 1, horas)
            continue
        fila, rep = f"$B{r}:${ult}{r}", detalle[p.id]
        ws.cell(r, ncol + 1, f"=SUMPRODUCT(COUNTIF({fila},Turnos!$A$2:$A${len(ctx.turnos) + 1}),Turnos!$C$2:$C${len(ctx.turnos) + 1})")
        h, c = f"{get_column_letter(ncol + 1)}{r}", f"{get_column_letter(contr)}{r}"
        ws.cell(r, contr, round(rep["contratadas"], 1))
        ws.cell(r, contr + 1, f"=MAX(0,{h}-{c})")
        ws.cell(r, contr + 2, f"=MAX(0,{c}-{h})")
        for k, t in enumerate(solver):
            ws.cell(r, contr + 3 + k, f'=COUNTIF({fila},"{t.codigo}")')
        ws.cell(r, contr + 3 + len(solver), round(rep["equivalentes"], 1))
        ws.cell(r, contr + 4 + len(solver), round(rep["h_dominicales"], 1))
        ws.cell(r, contr + 5 + len(solver), round(rep["h_nocturnas"], 1))
    base = len(cols) + 3
    faltantes = reglas.faltantes_periodo(ctx, cuadro, fechas)
    for k, (fr, nombre) in enumerate((("M", "Mañana"), ("T", "Tarde"), ("N", "Noche"))):
        ws.cell(base + k, 1, f"Cobertura {nombre.lower()}").font = Font(bold=True)
        for f in fechas:
            i = col[f]
            peor, rangos = faltantes[f][fr]
            c = ws.cell(base + k, i, "ok" if not peor else f"−{peor}")
            c.alignment = CENTRO
            if peor:
                c.fill = PatternFill("solid", fgColor="FF7C80")
    fila = base + 3
    activos = [t for t in ctx.turnos.values() if t.activo and t.solver]
    if activos:  # contador por turno: personas con ese código cada día (en la hoja de puestos «M·2» cuenta como M); rojo si la franja que cubre queda corta
        ws.cell(fila, 1, "Contador por turno").font = Font(bold=True)
        for k, t in enumerate(activos, 1):
            ws.cell(fila + k, 1, f"{t.codigo} {t.nombre}")
            for f in fechas:
                i = col[f]
                letra = get_column_letter(i)
                rango = f"{letra}$2:{letra}${n}"
                c = ws.cell(fila + k, i, f'=COUNTIF({rango},"{t.codigo}")+COUNTIF({rango},"{t.codigo}·*")')
                c.alignment = CENTRO
                if any(faltantes[f][fr][0] for fr in t.cubre):
                    c.fill = PatternFill("solid", fgColor="FF7C80")
        fila += len(activos) + 2
    if contadores:  # contador por puesto: personas-día en cada puesto; rojo si la app lo reporta sin cubrir
        ws.cell(fila, 1, "Contador por puesto").font = Font(bold=True)
        for k, (q, sin) in enumerate(contadores, 1):
            ws.cell(fila + k, 1, f"{q.numero} {q.nombre}" if q.numero else "A Apoyo")
            for f in fechas:
                i = col[f]
                letra = get_column_letter(i)
                c = ws.cell(fila + k, i, f'=COUNTIF({letra}$2:{letra}${n},"*·{q.numero or "A"}")')
                c.alignment = CENTRO
                if f in sin:
                    c.fill = PatternFill("solid", fgColor="FF7C80")
    _ancho(ws, 22, 5)
    ws.column_dimensions[get_column_letter(ncol + 1)].width = 8
    for c, _ in sumas:
        ws.column_dimensions[get_column_letter(c)].width = 7
    for i in range(contr, contr + len(extra) + 1):
        ws.column_dimensions[get_column_letter(i)].width = 11 if detalle is not None else 5
    ws.freeze_panes = "B2"


NIVELES = {"error": "Por corregir", "aviso": "Para revisar", "info": "Deseable sin cubrir"}


def exportar_cuadro(carpeta, mes_txt, ctx, cuadro, original, fechas, diferencias, filas_puestos=(), catalogo=None, detalle=None, alertas=None):
    """Hojas: Cuadro (de `cambios`, celdas modificadas en amarillo; con `detalle`, columnas de horas y contadores por turno),
    Cuadro con puestos (con contador por puesto), Original, Cambios (diferencias), Turnos (catálogo que leen las fórmulas)
    y, con `alertas` ([reglas.Alerta]), Alertas: el registro de lo que el cuadro incumple, para revisarlo o archivarlo."""
    wb = Workbook()
    _hoja_cuadro(wb.active, ctx, cuadro, fechas, comparar=original, detalle=detalle)
    wb.active.title = "Cuadro"
    if filas_puestos:
        con = wb.create_sheet("Cuadro con puestos")
        cat = catalogo or ctx.puestos
        activos = sorted((q for q in cat.values() if q.activo), key=lambda q: q.numero)
        falta = {q.id: {a.fecha for a in alertas_reparto(ctx, filas_puestos, fechas, cat) if f": {q.nombre} sin cubrir" in a.texto} for q in activos}
        _hoja_cuadro(con, ctx, cuadro, fechas, puestos=por_persona(filas_puestos, {i: p.numero for i, p in cat.items()}),
                     contadores=[(q, falta[q.id]) for q in activos] + [(Puesto(0, 0, "Apoyo"), set())] if detalle is not None else None)
        poner_texto(con.cell(con.max_row + 2, 1), leyenda(cat))
    _hoja_cuadro(wb.create_sheet("Original"), ctx, original, fechas)
    ws = wb.create_sheet("Cambios")
    _encabezado(ws, 1, ["Colaborador", "Fecha", "Antes", "Después"])
    nombres = {p.id: p.nombre for p in ctx.colabs}
    for r, (cid, f, antes, ahora) in enumerate(diferencias, 2):
        for c, v in enumerate((nombres.get(cid, cid), f, antes, ahora), 1):
            _valor(ws.cell(r, c), v)
    _ancho(ws, 26, 14)
    _tabla(ws)
    if detalle is not None:  # lo leen las fórmulas de horas del cuadro
        tur = wb.create_sheet("Turnos")
        _encabezado(tur, 1, ["Código", "Nombre", "Horas"])
        for r, t in enumerate(ctx.turnos.values(), 2):
            for c, v in enumerate((t.codigo, t.nombre, round(t.horas, 2)), 1):
                poner_texto(tur.cell(r, c), v) if c < 3 else tur.cell(r, c, v)
        _ancho(tur, 10, 14)
        _tabla(tur)
    if alertas is not None:
        orden = list(NIVELES)
        _hoja(wb, "Alertas", ["Nivel", "Fecha", "Colaborador", "Alerta"],
              [[NIVELES.get(a.nivel, a.nivel), a.fecha, nombres.get(a.colab_id, ""), a.texto]
               for a in sorted(alertas, key=lambda a: (orden.index(a.nivel) if a.nivel in orden else 9, a.fecha or date.min))], primera=16)
        wb["Alertas"].column_dimensions["D"].width = 90
    _terminar(wb, f"Cuadro {mes_txt}")
    ruta = ruta_libre(carpeta, f"CUADRO {mes_txt.upper()}")
    wb.save(ruta)
    return ruta


def _hm(minutos):
    return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def exportar_puestos(carpeta, mes_txt, ctx, cuadro, fechas, filas, capacitacion, catalogo=None):
    """Una hoja por semana: por día, quién ocupa cada puesto (con su horario y grupo de pausa), el apoyo y la capacitación."""
    wb = Workbook()
    wb.remove(wb.active)
    nombres = {p.id: p.nombre for p in ctx.colabs}
    cat = catalogo or ctx.puestos
    usados = sorted({f.puesto_id for f in filas if f.puesto_id and f.puesto_id in cat} | {i for i, p in cat.items() if p.activo},
                    key=lambda i: cat[i].numero)
    cap = {}
    for f, cid in capacitacion:
        cap.setdefault(f, []).append(nombres[cid])
    celdas = {}
    for a in filas:
        txt = f"{nombres.get(a.colab_id, a.colab_id)} ({_hm(a.desde)}–{_hm(a.hasta % 1440 or 1440)}) (P{a.pausa})"
        celdas.setdefault((a.fecha, a.puesto_id), []).append(txt)
    for lunes in sorted({f - timedelta(days=f.weekday()) for f in fechas}):
        ws = wb.create_sheet(f"Semana {lunes:%d-%m}")
        _encabezado(ws, 1, ["Día"] + [f"{cat[i].numero} · {cat[i].nombre}" for i in usados] + ["Apoyo", "Capacitación"])
        for r, f in enumerate((lunes + timedelta(days=i) for i in range(7)), 2):
            c = ws.cell(r, 1, f"{DIAS[f.weekday()]} {f:%d/%m}")
            c.font = Font(bold=True)
            if ctx.tipo_dia(f) == "DF":
                c.fill = FESTIVO
            if f not in fechas:
                continue
            fila = ["\n".join(celdas.get((f, i), [])) for i in usados] + ["\n".join(celdas.get((f, 0), []))] + [", ".join(cap.get(f, []))]
            for i, v in enumerate(fila, 2):
                poner_texto(ws.cell(r, i), v).alignment = CENTRO
        ws.cell(10, 1, "(P1)/(P2): grupo de pausa — el grupo 1 sale primero y el 2 cubre; se alternan cada día.")
        _ancho(ws, 14, 26)
        ws.freeze_panes = "B2"
    _terminar(wb, f"Puestos {mes_txt}")
    ruta = ruta_libre(carpeta, f"PUESTOS {mes_txt.upper()}")
    wb.save(ruta)
    return ruta


CATEGORIAS = [(t, n, f) for t in ("ordinaria", "extra") for f in ("hábil", "festivo") for n in ("diurna", "nocturna")]


def exportar_horas(carpeta, mes_txt, ctx, tarifas, cuadro, fechas, ventana_sem):
    wb = Workbook()
    ws = wb.active
    ws.title = "Horas y recargos"
    nombre_cat = lambda c: f"{'Extra' if c[0] == 'extra' else 'Ordinaria'} {c[1]} {'dom/fest' if c[2] == 'festivo' else 'hábil'}"
    _encabezado(ws, 1, ["Colaborador", "Contratadas", "Trabajadas", "Pendientes", "Adicionales"]
                + [nombre_cat(c) for c in CATEGORIAS] + ["Dom/fest trabajados", "Habitual", "Horas equivalentes de recargo"])
    sem = wb.create_sheet("Semanas")
    lunes = sorted({f - timedelta(days=f.weekday()) for f in fechas})
    _encabezado(sem, 1, ["Colaborador"] + [f"Sem {l:%d/%m}" for l in lunes])
    for r, p in enumerate((p for p in ctx.colabs if p.en_solver), 2):
        rep = recargos.reporte(ctx, tarifas, p, cuadro, fechas, ventana_sem)
        fila = [p.nombre] + [round(rep[k], 1) for k in ("contratadas", "trabajadas", "pendientes", "adicionales")] \
            + [round(rep["cat"].get(c, 0), 1) for c in CATEGORIAS] \
            + [rep["festivos_trabajados"], "Sí" if rep["habitual"] else "No", round(rep["equivalentes"], 1)]
        for c, v in enumerate(fila, 1):
            poner_texto(ws.cell(r, c), v)
        poner_texto(sem.cell(r, 1), p.nombre)
        for c, l in enumerate(lunes, 2):
            sem.cell(r, c, round(rep["semanas"].get(l, 0), 1))
    _ancho(ws, 24, 14)
    _ancho(sem, 24, 12)
    _tabla(ws)
    _tabla(sem)
    nota = wb.create_sheet("Régimen")
    f0 = fechas[0]
    filas = [("Régimen de horas", f"Art. 165 CST: promedio en ventanas de {ventana_sem} semanas contra la jornada contratada."),
             ("Ventana", f"Contada desde el primer día del periodo; no cruza periodos."),
             ("Pendientes / adicionales", "Déficit o exceso de la ventana frente a lo contratado (descontando novedades)."),
             ("Horas extra", "Se toman de las últimas horas trabajadas de la ventana."),
             ("Dominical/festivo", f"{recargos.tarifa(tarifas, 'dominical', f0)} %"),
             ("Nocturno", f"{recargos.tarifa(tarifas, 'nocturno', f0)} % desde las {recargos.tarifa(tarifas, 'noche_inicio', f0) // 60}:00"),
             ("Extra diurna / nocturna", f"{recargos.tarifa(tarifas, 'extra_diurna', f0)} % / {recargos.tarifa(tarifas, 'extra_nocturna', f0)} %"),
             ("Horas equivalentes", "Ordinarias: horas × recargo. Extras: horas × (1 + recargo). Los recargos se suman."),
             ("Aviso", "Cifras de apoyo para nómina; confirmar con RR. HH./jurídico.")]
    for r, (a, b) in enumerate(filas, 1):
        nota.cell(r, 1, a).font = Font(bold=True)
        nota.cell(r, 2, b)
    _ancho(nota, 28, 90)
    _terminar(wb, f"Horas y recargos {mes_txt}")
    ruta = ruta_libre(carpeta, f"HORAS Y RECARGOS {mes_txt.upper()}")
    wb.save(ruta)
    return ruta


def exportar_banco(carpeta, mes_txt, filas, movimientos, nombres):
    """Banco de horas para RR. HH.: «Saldos» (de `flujo.estado_banco`) y «Movimientos» manuales (de `bd.movimientos()`)."""
    wb = Workbook()
    ws = wb.active
    ws.title = "Saldos"
    _encabezado(ws, 1, ["Colaborador", "Anterior", "Periodo", "Total", "Estado"])
    for r, f in enumerate(filas, 2):
        for c, v in enumerate([f["nombre"], f["anterior"], f["periodo"], f["total"], "Cerrado" if f["cerrado"] else "Proyectado"], 1):
            poner_texto(ws.cell(r, c), v)
    _ancho(ws, 24, 12)
    _tabla(ws)
    mv = wb.create_sheet("Movimientos")
    _encabezado(mv, 1, ["Fecha", "Colaborador", "Horas", "Concepto", "Nota"])
    for r, (_, cid, fecha, horas, concepto, nota) in enumerate(movimientos, 2):
        for c, v in enumerate([fecha, nombres.get(cid, ""), horas, concepto, nota], 1):
            _valor(mv.cell(r, c), v)
    _ancho(mv, 12, 24)
    _tabla(mv)
    _terminar(wb, f"Banco de horas {mes_txt}")
    ruta = ruta_libre(carpeta, f"BANCO DE HORAS {mes_txt.upper()}")
    wb.save(ruta)
    return ruta


def _hoja(wb, titulo, columnas, filas, primera=24):
    ws = wb.create_sheet(titulo)
    _encabezado(ws, 1, columnas)
    for r, fila in enumerate(filas, 2):
        for c, v in enumerate(fila, 1):
            _valor(ws.cell(r, c), v)
    _ancho(ws, primera, 14)
    _tabla(ws)
    return ws


def exportar_analiticas(carpeta, base, d, titulo="Analíticas", desde=None, hasta=None):
    """Analíticas de un rango para gerencia o RR. HH.: una hoja por bloque, con los datos de `datos_analiticas`.
    Porcentajes como fracción con formato %, periodos con su nombre («Octubre 2026») y celdas vacías donde no hay dato."""
    tipos = list(ABREV_NOVEDAD)
    est = d["estabilidad"]["periodos"]
    celdas = sum(p["celdas_total"] for p in est)
    nom = lambda k: flujo.etiqueta(*flujo.desde_clave(k))
    ct, av = d["cobertura_tramos"], d["avisos_ausencia"]
    wb = Workbook()
    wb.remove(wb.active)
    ws = _hoja(wb, "Resumen", ["Indicador", "Valor"], [
        ["Ausentismo (%)", _pct(d["ausentismo"]["pct"])],
        ["Ausentes a la vez (máximo)", d["simultaneos"]["maximo"]],
        ["Días con déficit", sum(c["dias_deficit"] for c in d["cobertura"])],
        ["Cobertura por tramo (%)", _pct(ct["cobertura_pct"])],
        ["Horas faltantes (personas × horas)", ct["horas_faltantes"]],
        ["Horas sobrantes (personas × horas)", ct["horas_sobrantes"]],
        ["Cambios de turno", sum(c["permuta"] + c["servicio"] + c["ajuste"] for c in d["cambios"].values())],
        ["Cambios tras publicar (%)", _pct(sum(p["celdas_cambiadas"] for p in est) / celdas * 100 if celdas else None)],
        ["Cambios con poco aviso", sum(p["aviso_corto"] for p in est)],
        ["Personas con señales de fatiga", sum(f["senales"] > 0 for f in d["fatiga"].values())],
        ["Solicitudes cumplidas (%)", _pct(d["solicitudes"]["tasa"])],
        ["Ausencias estimadas el mes siguiente (días)", d["pronostico"]["estimado"]],
        ["Ausencias no planeadas avisadas con menos de 24 h", av["avisos"]["tarde"] + av["avisos"]["menos_24h"]],
        ["Días de ausencia con turno que se reemplazaron (%)", _pct(av["pct_cubiertos"])],
        *([[f"Próximo recargo dominical: {d['proximo_recargo']['actual']:g} % → {d['proximo_recargo']['nuevo']:g} % desde el {d['proximo_recargo']['desde']:%d/%m/%Y} (h equivalentes más al mes)",
            d["proximo_recargo"]["horas_mes"]]] if d["proximo_recargo"] else []),
        ["Horas extra del 20 % con más (%)", _pct(d["concentracion_extra"]["top_pct"])],
    ], primera=32)
    if desde and hasta:  # bajo la tabla, para que los filtros no la incluyan
        for k, (a, b) in enumerate((("Rango", f"{desde:%d/%m/%Y} a {hasta:%d/%m/%Y}"), ("Generado", f"{datetime.now():%d/%m/%Y %H:%M}")), ws.max_row + 2):
            ws.cell(k, 1, a).font = Font(bold=True)
            ws.cell(k, 2, b)
    _hoja(wb, "Ausentismo", ["Persona", "Total", *tipos],
          [[p, sum(t.values()), *(t.get(x, 0) for x in tipos)] for p, t in sorted(d["ausentismo"]["por_persona"].items())])
    tramos = {t["periodo"]: t for t in ct["por_periodo"]}
    _hoja(wb, "Cobertura", ["Periodo", "Días con déficit", "Días con exceso", "Puestos sin cubrir", "Horas faltantes", "Horas sobrantes", "Cobertura (%)", "Eficiencia (%)"],
          [[nom(c["periodo"]), c["dias_deficit"], c["dias_exceso"], c["puestos_sin_cubrir"],
            *((t["horas_faltantes"], t["horas_sobrantes"], _pct(t["cobertura_pct"]), _pct(t["eficiencia_pct"])) if (t := tramos.get(c["periodo"])) else (None,) * 4)]
           for c in d["cobertura"]])
    if (cp := d.get("cobertura_puestos")) is not None:  # el área no usa puestos: no hay reparto que mostrar
        _hoja(wb, "Cobertura por puesto", ["Puesto", "Horas obligatorias", "Horas faltantes", "Horas sobrantes", "Cobertura (%)", "Eficiencia (%)"],
              [[q["puesto"], q["horas_requeridas"], q["horas_faltantes"], q["horas_sobrantes"], _pct(q["cobertura_pct"]), _pct(q["eficiencia_pct"])] for q in cp])
    _hoja(wb, "Cambios", ["Periodo", "Permutas", "Servicio", "Ajustes", "Excepciones"],
          [[nom(k), c["permuta"], c["servicio"], c["ajuste"], c["excepciones"]] for k, c in d["cambios"].items()])
    _hoja(wb, "Estabilidad", ["Periodo", "% cambiado", "Celdas cambiadas", "Con poco aviso", "Publicado con (días)"],
          [[nom(p["periodo"]), _pct(p["pct"]), p["celdas_cambiadas"], p["aviso_corto"], p["dias_anticipacion"]] for p in est])
    _hoja(wb, "Horas extra", ["Periodo", "Ventana (sem.)", "Diurnas (mes)", "Nocturnas (mes)", "Diurnas (ventana)", "Nocturnas (ventana)"],
          [[nom(h["periodo"]), h["ventana"], h["mes"]["diurna"], h["mes"]["nocturna"], h["semanas"]["diurna"], h["semanas"]["nocturna"]] for h in d["horas_extra"]])
    _hoja(wb, "Recargos", ["Persona", "Dominical/festivo (h)", "Nocturno (h)", "Equivalentes (h)"],
          [[p, r["festivo"], r["nocturna"], r["equivalentes"]] for p, r in sorted(d["recargos"].items())])
    dv = d["equidad"]["desviacion"]
    _hoja(wb, "Equidad", ["Persona", "Noches", "Domingos", "Festivos", "Noches vs media", "Dom. y festivos vs media"],
          [[p, o["noches"], o["domingos"], o["festivos"], round(dv[p]["noches"], 2), round(dv[p]["domingos"] + dv[p]["festivos"], 2)]
           for p, o in sorted(d["equidad"]["por_persona"].items())])
    _hoja(wb, "Fatiga", ["Persona", "Señales", "Rachas largas", "Días seguidos (máx.)", "Turnos largos seguidos (máx.)", "Noches seguidas (máx.)", "Descansos cortos", "Fines trabajados", "Horas en 4 semanas (máx.)"],
          [[p, f["senales"], f["rachas_largas"], f["max_dias_seguidos"], f["max_largos_seguidos"], f["max_noches_seguidas"], f["descansos_cortos"], f["fines_trabajados"], f["horas_4_sem_max"]]
           for p, f in sorted(d["fatiga"].items(), key=lambda x: (-x[1]["senales"], x[0]))])
    pa = d["patrones"]
    ws = _hoja(wb, "Patrones", ["Día", "% ausencias no planeadas"], [[DIAS[w], _pct(v)] for w, v in enumerate(pa["por_dia_semana"])])
    fila = ws.max_row + 2
    ws.cell(fila, 1, f"Ausencias que empezaron tras un festivo: {pa['tras_festivo']}")
    ws.cell(fila + 1, 1, f"Factor Bradford (ausencias² × días) de los 12 meses desde el {pa['bradford']['desde']:%d/%m/%Y}. Indicador de patrones; no usar para sanciones.")
    _encabezado(ws, fila + 3, ["Persona", "Ausencias", "Días", "Puntaje"])
    for r, (p, o) in enumerate(sorted(pa["bradford"]["por_persona"].items(), key=lambda x: (-x[1]["puntaje"], x[0])), fila + 4):
        for c, v in enumerate([p, o["rachas"], o["dias"], o["puntaje"]], 1):
            poner_texto(ws.cell(r, c), v)
    _hoja(wb, "Banco", ["Persona", "Saldo (h)"], sorted(d["banco"]["saldos"].items()))
    so = d["solicitudes"]
    _hoja(wb, "Solicitudes", ["Persona", "Pedidas", "Cumplidas", "Parciales", "No cumplidas", "Cumplidas (%)"],
          [[p, o["pedidas"], o["cumplidas"], o["parciales"], o["no_cumplidas"], _pct(o["tasa"])] for p, o in sorted(so["por_persona"].items())])
    _hoja(wb, "Solicitudes por tipo", ["Tipo", "Pedidas", "Cumplidas"],
          [[{"libre": "Libre", "quiero": "Quiero turno", "evitar": "Evitar turno"}.get(t, t), o["pedidas"], o["cumplidas"]] for t, o in so["por_tipo"].items()])
    _hoja(wb, "Concentración extra", ["Persona", "Horas extra"], [[p, round(h, 1)] for p, h in sorted(d["concentracion_extra"]["por_persona"].items(), key=lambda x: (-x[1], x[0]))])
    _hoja(wb, "Avisos", ["Aviso frente al turno", "Ausencias"],
          [["Ya empezado el turno", av["avisos"]["tarde"]], ["Menos de 24 h", av["avisos"]["menos_24h"]], ["De 24 a 72 h", av["avisos"]["24_72h"]],
           ["Más de 72 h", av["avisos"]["mas_72h"]], ["Sin dato (registradas antes de guardar la hora)", av["sin_dato"]]], primera=40)
    _hoja(wb, "Pronóstico", ["Mes", "Días de ausencia"], [[f"{flujo.MESES[int(m[5:]) - 1]} {m[:4]}", n] for m, n in d["pronostico"]["serie"]], primera=12)
    _hoja(wb, "Generaciones", ["Periodo", "Corridas", "Terminadas bien (%)", "Duración típica (s)", "Personas-tramo faltantes (última)", "Solicitudes sin cumplir (última)"],
          [[nom(c["periodo"]), c["corridas"], _pct(c["pct_bien"]), None if c["mediana_seg"] is None else round(c["mediana_seg"]), c["faltan_ultima"], c["solicitudes_ultima"]] for c in d["corridas"]])
    _terminar(wb, titulo)
    ruta = ruta_libre(carpeta, base)
    wb.save(ruta)
    return ruta


def eventos_persona(ctx, cuadro, colab_id, fechas):
    """[(inicio, fin, descripción)] de los turnos de una persona, para `radiologia.analisis.ics`. L y códigos desconocidos no van."""
    return [(*intervalo(t, f), f"{t.codigo} · {t.nombre}") for f in fechas if (t := ctx.turnos.get(cuadro.get((colab_id, f), "L")))]
