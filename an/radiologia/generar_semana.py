"""Genera la planilla semanal de radiología a partir del cuadro mensual.

Uso:
    python3 generar_semana.py "<cuadro mensual>.xlsx" 2026-10-12 [salida.xlsx]

Lee la hoja "Cambios ..." del cuadro mensual (valores calculados; el archivo
debe estar guardado por Excel) y llena una copia de plantilla_semana.xlsx.
Contingencia, vacaciones, asignación de estudios y notas se llenan a mano.
"""
import sys
from copy import copy
from datetime import date, datetime, timedelta
from pathlib import Path

import openpyxl
from openpyxl.worksheet.datavalidation import DataValidation

PLANTILLA = Path(__file__).with_name("plantilla_semana.xlsx")


class ErrorPlanilla(Exception):
    """Problema del cuadro mensual que el usuario puede corregir; el mensaje va tal cual a pantalla."""
MESES = ["ENERO", "FEBRERO", "MARZO", "ABRIL", "MAYO", "JUNIO", "JULIO",
         "AGOSTO", "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"]

M, T = (7, 13), (13, 19)
# código -> (servicio, [(inicio, fin), ...], remoto)
CODIGOS = {
    "MURG": ("URG", [(6, 14)], False), "TURG": ("URG", [(14, 22)], False),
    "NURG": ("URG", [(22, 30)], False),
    "MPM": ("PM", [M], False), "TPM": ("PM", [(13, 17)], False),
    "CPM": ("PM", [(7, 11), (13, 17)], False),
    "MCJ": ("CJ1", [M], False), "CJ#": ("CJ1", [(7, 11), (13, 17)], False),
    "MCJ#": ("CJ1", [(7, 11)], False), "TCJ#": ("CJ1", [(13, 17)], False),
    "MJ#": ("CJ1", [(7, 11)], False), "TJ#": ("CJ1", [(13, 17)], False),
    "CJ2": ("CJ2", [(7, 11), (13, 17)], False),
    "MCJ2": ("CJ2", [(7, 11)], False), "TCJ2": ("CJ2", [(13, 17)], False),
    "MN": ("NEURO", [M], False), "TN": ("NEURO", [T], False),
    "CN": ("NEURO", [M, T], False),
    "MNR": ("NEURO", [M], True), "TNR": ("NEURO", [T], True),
    "CNR": ("NEURO", [M, T], True), "TN8R": ("NEURO", [(14, 22)], True),
    "TN8": ("NEURO", [(14, 22)], False),
    "MMSK": ("MSK", [M], False), "TMSK": ("MSK", [T], False),
    "CMSK": ("MSK", [M, T], False), "MMSKR": ("MSK", [M], True),
    "TMSKR": ("MSK", [T], True), "CMSKR": ("MSK", [M, T], True),
    "TK8": ("MSK", [(13, 21)], False), "TK8R": ("MSK", [(13, 21)], True),
    "MA": ("ABD", [M], False), "TA": ("ABD", [T], False),
    "CA": ("ABD", [M, T], False), "MAR": ("ABD", [M], True),
    "TAR": ("ABD", [T], True),
    "MT": ("TORAX", [M], False), "TT": ("TORAX", [T], False),
    "CT": ("TORAX", [M, T], False),
    "MC": ("CARDIO", [M], False), "TC": ("CARDIO", [T], False),
    "MM": ("MAMA", [M], False), "TM": ("MAMA", [T], False),
    "CM": ("MAMA", [M, T], False),
    "MD": ("DENSITO", [M], False), "TD": ("DENSITO", [T], False),
    "DENSITO": ("DENSITO", [(7, 19)], False),
}
# Ecógrafos de sede principal: M#, T#, C# y los de Torre A
for _n, _srv in [("1", "ECO1"), ("2", "ECO2"), ("3", "ECO3"), ("4", "ECO4"),
                 ("5", "ECO5"), ("6", "ECO6"), ("TA1", "ECO1"), ("TA2", "ECO6")]:
    CODIGOS["M" + _n] = (_srv, [M], False)
    CODIGOS["T" + _n] = (_srv, [T], False)
    CODIGOS["C" + _n] = (_srv, [M, T], False)
# Códigos que no se publican en la semanal
IGNORAR = {"L", "LP", "VAC", "INC", "INC6", "INC12", "INC.", "LNR", "LR", "HC",
           "HN", "HC&N", "Z", "PTV", "PTV12", "PT6", "CAP4", "DF", "MDX", "TDX"}
# ESP2 de las filas "Disp" -> servicio
DISP_SRV = {"NEURO": "NEURO", "MSK": "MSK", "MAMA": "MAMA", "ABDOMEN": "ABD",
            "CARDIO": "CARDIO", "TORAX": "TORAX", "PROCED": "PROCED"}

# Hoja ECO: (servicio, inicio) -> fila
FILAS_ECO = {("URG", 6): 3, ("URG", 14): 4, ("URG", 22): 5,
             ("ECO2", 7): 7, ("ECO2", 13): 8, ("ECO3", 7): 9, ("ECO3", 13): 10,
             ("ECO4", 7): 11, ("ECO4", 13): 12, ("ECO5", 7): 13, ("ECO5", 13): 14,
             ("ECO1", 7): 18, ("ECO1", 13): 19, ("ECO6", 7): 20, ("ECO6", 13): 21,
             ("PM", 7): 23, ("PM", 13): 24}
FILAS_CJ = {"CJ1": {(7, 13): 26, (7, 11): 27, (13, 17): 28},
            "CJ2": {(7, 13): 29, (7, 11): 30, (13, 17): 31}}


def hora(h):
    if h >= 24:
        return "11:59 pm"
    return f"{(h - 1) % 12 + 1}:00 {'am' if h < 12 else 'pm'}"


def franja(a, b):
    return f"{hora(a)} - {hora(b)}"


def norm_codigo(v):
    v = v.strip()
    return "DENSITO" if v.lower() == "densito" else v


# ---------------------------------------------------------------- lectura mensual
def cargar_mensual(ruta):
    """Hoja "Cambios ..." del cuadro mensual, con los valores calculados por Excel."""
    try:
        wb = openpyxl.load_workbook(ruta, data_only=True)
    except FileNotFoundError as e:
        raise ErrorPlanilla("No se encontró el archivo. ¿Se movió o cambió de nombre?") from e
    except PermissionError as e:
        raise ErrorPlanilla("No se pudo leer el archivo. Ciérralo en Excel e inténtalo de nuevo.") from e
    except Exception as e:
        raise ErrorPlanilla("El archivo no es un Excel .xlsx válido (¿está protegido con contraseña?).") from e
    ws = next((s for s in wb if s.title.lower().startswith("cambios")), None)
    if ws is None:
        raise ErrorPlanilla("El archivo no tiene una hoja que empiece por 'Cambios'.")
    if not fechas_mensual(ws):
        raise ErrorPlanilla(
            f"La fila 3 de '{ws.title}' no tiene fechas completas.\nEscribe la primera fecha "
            "(ej. 01/10/2026), deja =+celda_anterior+1 en las demás, usa formato 'd' y guarda en Excel.")
    return ws


def fechas_mensual(ws):
    """{fecha: columna} de la fila 3 (fechas completas; con formato "d" se ven como el día)."""
    return {ws.cell(3, c).value.date(): c for c in range(6, ws.max_column + 1)
            if isinstance(ws.cell(3, c).value, datetime)}


def lunes_disponibles(ws):
    """Lunes con su domingo anterior y los 7 días de la semana en el cuadro."""
    f = fechas_mensual(ws)
    return [d for d in sorted(f) if d.weekday() == 0
            and all(d + timedelta(k) in f for k in range(-1, 7))]


def leer_mensual(ws, lunes):
    fechas = fechas_mensual(ws)
    semana = [lunes + timedelta(d) for d in range(-1, 7)]  # domingo anterior + lunes..domingo
    faltan = [f.strftime("%d/%m/%Y") for f in semana if f not in fechas]
    if faltan:
        raise ErrorPlanilla(f"'{ws.title}' no tiene columnas para: {', '.join(faltan)}")
    dias = [fechas[f] for f in semana]
    festivos = [str(ws.cell(2, c).value).endswith("F") for c in dias[1:]]

    turnos = [[] for _ in range(8)]  # (servicio, inicio, fin, remoto, nombre)
    disp = [dict() for _ in range(8)]
    densito = [[] for _ in range(8)]
    desconocidos = {}  # código -> [(médico, fecha)]
    nombres_esp = {}
    for r in range(4, ws.max_row + 1):
        nombre = ws.cell(r, 5).value
        if isinstance(nombre, str) and nombre.startswith("CONTINGENCIA"):
            break  # debajo solo hay contingencia y filas de control
        if not isinstance(nombre, str) or not nombre.strip():
            continue
        nombre = nombre.strip()
        esp = {str(ws.cell(r, 2).value or "").strip(), str(ws.cell(r, 3).value or "").strip()}
        nombres_esp.setdefault(nombre, set()).update(esp)
        es_disp = str(ws.cell(r, 4).value or "").strip().lower() == "disp"
        srv_disp = DISP_SRV.get(str(ws.cell(r, 3).value or "").strip())
        for d, c in enumerate(dias):
            v = ws.cell(r, c).value
            if not isinstance(v, str):
                continue
            for p in map(norm_codigo, v.split("/")):
                if p.lower() == "disp":
                    if es_disp and srv_disp:
                        disp[d][srv_disp] = nombre
                elif p in CODIGOS:
                    srv, tramos, rem = CODIGOS[p]
                    if srv == "DENSITO":
                        if nombre not in densito[d]:
                            densito[d].append(nombre)
                        continue
                    for a, b in tramos:
                        turnos[d].append((srv, a, b, rem, nombre))
                elif p and p not in IGNORAR:
                    if d:  # d=0 es el domingo anterior
                        desconocidos.setdefault(p, []).append((nombre, semana[d]))
    return dict(turnos=turnos, disp=disp, densito=densito, festivos=festivos,
                nombres_esp=nombres_esp, desconocidos=sorted(desconocidos), dias=semana[1:],
                desconocidos_detalle=desconocidos)


# ---------------------------------------------------------------- reglas de lectura
def linea_tiempo(turnos, slots, disp_ant, disp_hoy, dia_completo):
    """Filas (inicio, texto franja, nombre, etiqueta, tipo) de un servicio en un día.

    turnos: [(inicio, fin, remoto, nombre)]; slots: franjas estándar que se
    muestran vacías si nadie las cubre. Los huecos sin turno van a
    disponibilidad: hasta las 7 am el del día anterior, después el del día.
    """
    if not turnos and not slots and (disp_ant is None or disp_hoy is None or disp_ant == disp_hoy):
        return [(dia_completo[0], disp_hoy or disp_ant, dia_completo[1], "disp")]
    filas = []
    for a, b, rem, n in sorted(turnos):
        filas.append(((2 if rem else 1, a), franja(a, b), n, "Remoto" if rem else None,
                      "remoto" if rem else "turno"))
    for a, b, rem in slots:
        if not any(t[0] == a and t[1] == b and (t[2] or not rem) for t in turnos):
            filas.append(((2 if rem else 1, a), franja(a, b), None, "Remoto" if rem else None,
                          "remoto" if rem else "turno"))
    # huecos de 0 a 24
    cubiertos = sorted((a, min(b, 24)) for a, b, _, _ in turnos)
    huecos, t0 = [], 0
    for a, b in cubiertos:
        if a > t0:
            huecos.append((t0, a))
        t0 = max(t0, b)
    if t0 < 24:
        huecos.append((t0, 24))
    tramos = []
    for a, b in huecos:
        if a < 7 < b:
            tramos += [(a, 7, disp_ant), (7, b, disp_hoy)]
        else:
            tramos.append((a, b, disp_ant if b <= 7 else disp_hoy))
    unidos = []
    for a, b, n in tramos:
        if unidos and unidos[-1][1] == a and unidos[-1][2] == n:
            unidos[-1] = (unidos[-1][0], b, n)
        else:
            unidos.append((a, b, n))
    for a, b, n in unidos:
        filas.append(((0 if a == 0 else 3, a), franja(a, b), n, "Disponibilidad", "disp"))
    return [f[1:] for f in sorted(filas, key=lambda f: f[0])]


SLOTS = {"NEURO": [(7, 13, False), (13, 19, False), (7, 13, True), (14, 22, True)],
         "MSK": [(7, 13, False), (13, 21, False)],
         "ABD": [(7, 13, False), (13, 19, False)],
         "TORAX": [(7, 13, False), (13, 19, False)]}
DIA_COMPLETO = {"TORAX": ("Disponibilidad", "Disponibilidad Torax")}
DIA_COMPLETO_DEF = ("12:00 am - 11:59 pm (24h)", "Disponibilidad")


def filas_servicio(datos, srv, d):
    """Filas del día d (0=lunes) para un panel de lectura."""
    i = d + 1  # índice con domingo anterior en 0
    habil = d < 5 and not datos["festivos"][d]
    turnos = [(a, b, rem, n) for s, a, b, rem, n in datos["turnos"][i] if s == srv]
    disp_hoy = datos["disp"][i].get(srv)
    if srv in SLOTS:
        return linea_tiempo(turnos, SLOTS[srv] if habil else [],
                            datos["disp"][i - 1].get(srv), disp_hoy,
                            DIA_COMPLETO.get(srv, DIA_COMPLETO_DEF))
    if srv == "CARDIO":
        filas = [(franja(a, b), n, "CORAZON", "turno") for a, b, _, n in sorted(turnos)]
        return filas + [("Disponibilidad", disp_hoy, "Disponibilidad Corazon", "disp")]
    if srv == "MAMA":
        filas = [(franja(a, b), n, None, "turno") for a, b, _, n in sorted(turnos)]
        if habil:
            for a, b in (M, T):
                if not any(t[0] == a and t[1] == b for t in turnos):
                    filas.append((franja(a, b), None, None, "turno"))
            filas.sort(key=lambda f: f[0] != franja(*M))
        if disp_hoy or not habil:
            filas.append(("Disponibilidad", disp_hoy, "Disponibilidad Resonancia Mama", "disp"))
        return filas
    if srv == "DENSITO":
        return [("7:00 am - 7:00 pm", " / ".join(datos["densito"][i]) or None, None, "turno")]
    raise ValueError(srv)


# ---------------------------------------------------------------- escritura
def estilos(ws, col, fila_turno, fila_disp, celda_remoto):
    """Copia los estilos de la plantilla para un panel que empieza en `col`."""
    def s(r, dc=0):
        return copy(ws.cell(r, col + dc)._style)
    return {"fecha": s(5), "turno": [s(fila_turno, k) for k in range(3)],
            "disp": [s(fila_disp, k) for k in range(3)],
            "remoto": copy(ws[celda_remoto]._style)}


HOJAS_LECTURA = {
    # hoja: [(columna, servicio, fila turno normal, fila disp, celda "Remoto")], ESP del listado
    "Lectura - Neuro": ([(3, "NEURO", 7, 6, "E17")], {"NEURO"}),
    "Lectura - MSK": ([(3, "MSK", 13, 12, "E26")], {"MSK"}),
    "Lectura - Abdomen": ([(3, "ABD", 13, 12, "E26")], {"ABDOMEN"}),
    "Lectura - CARDIO-TORAX AMBULATO": ([(3, "TORAX", 13, 12, "E15"), (7, "CARDIO", 12, 13, "E15")],
                                        {"CARDIO", "TORAX"}),
    "Lectura - Mamografia-Densitomet": ([(3, "MAMA", 10, 6, "E6"), (7, "DENSITO", 6, 6, "E6")],
                                        {"MAMA", "DENSITO"}),
}


def escribir_lectura(ws, datos, lunes, paneles, esp):
    """Reescribe la hoja; devuelve [(fecha, franja, servicio, tipo)] de filas sin nombre."""
    est = {col: estilos(ws, col, ft, fd, rem) for col, _, ft, fd, rem in paneles}
    for rng in [r for r in ws.merged_cells.ranges if r.min_row >= 4]:
        ws.unmerge_cells(str(rng))
    ws.delete_rows(4, ws.max_row)
    for r in range(1, 4):
        ws.cell(r, 1).value = None
    nombres = sorted(n for n, e in datos["nombres_esp"].items() if e & esp)
    for k, n in enumerate(nombres, 1):
        ws.cell(k, 1).value = n

    fila, celdas_nombre, pendientes = 5, [], []
    for d in range(7):
        bloques = [(col, filas_servicio(datos, srv, d)) for col, srv, *_ in paneles]
        for col, filas in bloques:
            c = ws.cell(fila, col, datetime.combine(lunes + timedelta(d), datetime.min.time()))
            c._style = copy(est[col]["fecha"])
            ws.merge_cells(start_row=fila, start_column=col, end_row=fila, end_column=col + 2)
            for k, (fr, nombre, etiqueta, tipo) in enumerate(filas, fila + 1):
                base = est[col]["disp" if tipo == "disp" else "turno"]
                for j, v in enumerate((fr, nombre, etiqueta)):
                    cel = ws.cell(k, col + j, v)
                    cel._style = copy(base[j])
                if tipo == "remoto":
                    ws.cell(k, col + 2)._style = copy(est[col]["remoto"])
                celdas_nombre.append(ws.cell(k, col + 1).coordinate)
                if not nombre:
                    srv = next(p[1] for p in paneles if p[0] == col)
                    pendientes.append((lunes + timedelta(d), fr, srv, tipo))
        fila += 1 + max(len(f) for _, f in bloques) + 1

    ws.data_validations.dataValidation = []
    dv = DataValidation(type="list", formula1=f"$A$1:$A${max(len(nombres), 1)}", allow_blank=True)
    for cel in celdas_nombre:
        dv.add(cel)
    ws.add_data_validation(dv)
    return pendientes


def escribir_eco(ws, datos, lunes):
    # Celdas de nombres: blancas si tienen médico, gris si quedan vacías (la plantilla traía las
    # marcas de la semana con que se hizo; así no se arrastran a otras semanas)
    blanco, gris = copy(ws["G7"]._style), copy(ws["F7"]._style)
    filas_nombres = set(FILAS_ECO.values()) | {f for d in FILAS_CJ.values() for f in d.values()}
    for r in range(3, 35):
        for c in range(6, 13):
            ws.cell(r, c).value = None
    for r in range(1, ws.max_row + 1):
        ws.cell(r, 2).value = None
    for k, n in enumerate(sorted(datos["nombres_esp"]), 1):
        ws.cell(k, 2).value = n

    ws["F2"] = datetime.combine(lunes, datetime.min.time())
    for d in range(7):
        col = 6 + d
        letra = ws.cell(2, col).column_letter
        ws.cell(1, col).value = (f'=TEXT({letra}2,"dddd")&" FESTIVO"' if datos["festivos"][d]
                                 else f"=+{letra}2")
        celdas = {}
        for srv, a, b, _, n in datos["turnos"][d + 1]:
            fila = FILAS_CJ[srv].get((a, b)) if srv in FILAS_CJ else FILAS_ECO.get((srv, a))
            if fila:
                celdas.setdefault(fila, []).append(n)
        if datos["disp"][d + 1].get("PROCED"):
            celdas[16] = [datos["disp"][d + 1]["PROCED"]]
        for fila, ns in celdas.items():
            ws.cell(fila, col).value = " / ".join(dict.fromkeys(ns))
        for fila in filas_nombres:
            ws.cell(fila, col)._style = copy(blanco if ws.cell(fila, col).value else gris)


def limpiar_manuales(wb):
    vac = wb["VACACIONES"]
    for r in range(3, vac.max_row + 1):
        for c in range(2, 5):
            vac.cell(r, c).value = None
    est = wb["Asignación de estudios"]
    for r in (6, 7, 8, 9, 14, 15, 19, 20, 24, 25):
        for c in range(4, 8):
            est.cell(r, c).value = None
    est["B14"] = None


def construir(ws, lunes):
    """Planilla semanal en memoria + resumen (festivos, códigos desconocidos, filas sin nombre)."""
    datos = leer_mensual(ws, lunes)
    wb = openpyxl.load_workbook(PLANTILLA)
    escribir_eco(wb["Ecografía - ECO"], datos, lunes)
    pendientes = []
    for hoja, (paneles, esp) in HOJAS_LECTURA.items():
        pendientes += escribir_lectura(wb[hoja], datos, lunes, paneles, esp)
    limpiar_manuales(wb)
    resumen = dict(festivos=[f for f, es in zip(datos["dias"], datos["festivos"]) if es],
                   desconocidos=datos["desconocidos"], pendientes=sorted(pendientes))
    return wb, resumen, datos


def nombre_semana(lunes):
    dom = lunes + timedelta(6)
    return f"SEMANA {lunes.day} AL {dom.day} DE {MESES[dom.month - 1]}"


def ruta_libre(carpeta, lunes):
    """Primera ruta que no existe: SEMANA ....xlsx, luego ... v2.xlsx, v3..."""
    base = Path(carpeta) / nombre_semana(lunes)
    ruta, n = base.with_suffix(".xlsx"), 2
    while ruta.exists():
        ruta, n = base.with_name(f"{base.name} v{n}.xlsx"), n + 1
    return ruta


def generar(mensual, lunes, salida=None):
    wb, resumen, _ = construir(cargar_mensual(mensual), lunes)
    salida = salida or ruta_libre(Path(mensual).parent, lunes)
    wb.save(salida)
    return salida, resumen


if __name__ == "__main__":
    if len(sys.argv) not in (3, 4):
        sys.exit(__doc__)
    lunes = date.fromisoformat(sys.argv[2])
    if lunes.weekday() != 0:
        sys.exit("La fecha debe ser un lunes.")
    try:
        salida, resumen = generar(sys.argv[1], lunes, sys.argv[3] if len(sys.argv) == 4 else None)
    except ErrorPlanilla as e:
        sys.exit(str(e))
    if resumen["desconocidos"]:
        print("Aviso: códigos sin mapear (no se publican):", ", ".join(resumen["desconocidos"]))
    print("Generado:", salida)
