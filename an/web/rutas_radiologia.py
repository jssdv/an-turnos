"""Radiología en la web: cuadro mensual subido (`archivo`) y, sobre él, las funciones de `an/radiologia/`. La API no reimplementa reglas."""
import re
import tempfile
import zipfile
from datetime import date, timedelta
from io import BytesIO
from pathlib import Path

from urllib.parse import quote

import openpyxl
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from starlette.concurrency import run_in_threadpool

from an.radiologia import analisis
from an.radiologia import generar_semana as gs

from .deps import Contexto, contexto_area, contexto_area_lectura

router = APIRouter(prefix="/api")
MAX_ARCHIVO = 10 * 1024 * 1024
MAX_DESCOMPRIMIDO = 10 * 1024 * 1024
RUTA_ARCHIVOS = re.compile(r"^/api/areas/\d+/archivos$")


def _exigir_radiologia(ctx, area):
    f = ctx.conn.execute("SELECT tipo FROM area WHERE id = ?", (area,)).fetchone()
    if f is None or f["tipo"] != "radiologia":
        raise HTTPException(404, "Área no encontrada")


def _validar_xlsx(nombre, datos):
    """Rechaza con un mensaje en español lo que no sea un cuadro mensual .xlsx usable; devuelve el nombre limpio."""
    limpio = Path(nombre or "").name.strip()[:120]
    if not limpio.lower().endswith(".xlsx"):
        raise HTTPException(422, "Sube un archivo .xlsx.")
    if len(datos) > MAX_ARCHIVO:
        raise HTTPException(413, "El archivo pasa de 10 MB.")
    try:  # un .xlsx es un zip: se mide lo que descomprime antes de que openpyxl lo abra
        with zipfile.ZipFile(BytesIO(datos)) as z:
            if sum(i.file_size for i in z.infolist()) > MAX_DESCOMPRIMIDO:
                raise HTTPException(422, "El archivo es demasiado grande al abrirlo.")
    except zipfile.BadZipFile:
        pass  # cargar_mensual da el mensaje
    try:
        if not gs.lunes_disponibles(gs.cargar_mensual(BytesIO(datos))):
            raise gs.ErrorPlanilla("El cuadro no tiene ninguna semana completa (lunes a domingo).")
    except gs.ErrorPlanilla as e:
        raise HTTPException(422, str(e))
    return limpio


def _fila(f):
    return dict(id=f["id"], nombre=f["nombre"], tamano=f["tamano"], subido=f["subido"], subido_por=f["subido_por"])


COLUMNAS = ("SELECT a.id, a.nombre, octet_length(a.contenido) AS tamano, a.subido, u.nombre AS subido_por "
            "FROM archivo a LEFT JOIN usuario u ON u.id = a.subido_por ")


@router.get("/areas/{area}/archivos")
def listar_archivos(area: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    _exigir_radiologia(ctx, area)
    return [_fila(f) for f in ctx.conn.execute(COLUMNAS + "ORDER BY a.subido DESC, a.id DESC")]


def _guardar(ctx, area, nombre, datos, request):
    _exigir_radiologia(ctx, area)
    limpio = _validar_xlsx(nombre, datos)
    id_ = ctx.conn.execute("INSERT INTO archivo (nombre, contenido, subido_por) VALUES (?, ?, ?) RETURNING id", (limpio, datos, ctx.usuario.id)).fetchone()[0]
    request.state.evento = f"archivo_subido id={id_} nombre={limpio}"
    return _fila(ctx.conn.execute(COLUMNAS + "WHERE a.id = ?", (id_,)).fetchone())


@router.post("/areas/{area}/archivos", status_code=201)
async def subir_archivo(area: int, request: Request, nombre: str = "", ctx: Contexto = Depends(contexto_area, scope="function")):
    datos = await request.body()  # crudo (sin multipart): el nombre va en la consulta
    return await run_in_threadpool(_guardar, ctx, area, nombre, datos, request)


@router.delete("/areas/{area}/archivos/{id}", status_code=204)
def borrar_archivo(area: int, id: int, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    _exigir_radiologia(ctx, area)
    if ctx.conn.execute("DELETE FROM archivo WHERE id = ? RETURNING id", (id,)).fetchone() is None:
        raise HTTPException(404, "Archivo no encontrado")
    request.state.evento = f"archivo_borrado id={id}"


# ---------------------------------------------------------------- semanas
def _cuadro(ctx, area, id):
    """La hoja «Cambios …» del archivo (404 si no es de esta área)."""
    _exigir_radiologia(ctx, area)
    f = ctx.conn.execute("SELECT contenido FROM archivo WHERE id = ?", (id,)).fetchone()
    if f is None:
        raise HTTPException(404, "Archivo no encontrado")
    try:
        return gs.cargar_mensual(BytesIO(bytes(f["contenido"])))
    except gs.ErrorPlanilla as e:  # subido válido, pero ilegible hoy (no debería pasar)
        raise HTTPException(422, str(e))


def _lunes(ws, texto):
    try:
        lunes = date.fromisoformat(texto)
    except ValueError:
        lunes = None
    if lunes not in gs.lunes_disponibles(ws):
        raise HTTPException(422, "La fecha debe ser un lunes del cuadro.")
    return lunes


def _clave_semana(lunes):
    return f"{lunes}/{lunes + timedelta(6)}"


def _version_anterior(ctx, lunes):
    """(nombre, libro openpyxl) del último `exporte` de tipo `semana` de esa semana, o None."""
    f = ctx.conn.execute(
        "SELECT e.nombre_archivo, e.contenido FROM exporte e JOIN periodo p ON p.id = e.periodo_id "
        "WHERE p.clave = ? AND e.tipo = 'semana' ORDER BY e.numero DESC LIMIT 1", (_clave_semana(lunes),)).fetchone()
    return (f["nombre_archivo"], openpyxl.load_workbook(BytesIO(bytes(f["contenido"])))) if f else None


@router.get("/areas/{area}/archivos/{id}/semanas")
def semanas(area: int, id: int, ctx: Contexto = Depends(contexto_area, scope="function")):
    ws = _cuadro(ctx, area, id)
    lunes = gs.lunes_disponibles(ws)
    return dict(hoja=ws.title, semanas=[dict(lunes=l.isoformat(), etiqueta=analisis.semana_texto(l)) for l in lunes],
                defecto=analisis.semana_por_defecto(lunes, date.today()).isoformat())


def _calcular(ctx, ws, lunes):
    try:
        wb, resumen, datos = gs.construir(ws, lunes)
    except gs.ErrorPlanilla as e:
        raise HTTPException(422, str(e))
    previa = _version_anterior(ctx, lunes)
    cambios = analisis.comparar_libros(previa[1], wb, lunes) if previa else None
    return wb, resumen, datos, previa, cambios


QUE_FALTA = {"disp": "Disponibilidad sin asignar", "turno": "Turno sin médico", "remoto": "Remoto sin médico"}


@router.get("/areas/{area}/archivos/{id}/semanas/{lunes}")
def semana(area: int, id: int, lunes: str, ctx: Contexto = Depends(contexto_area, scope="function")):
    ws = _cuadro(ctx, area, id)
    lunes = _lunes(ws, lunes)
    _, resumen, datos, previa, cambios = _calcular(ctx, ws, lunes)
    alertas, revision = analisis.alertas(ws, lunes), analisis.revisar_cuadro(datos)
    agendas = analisis.agenda_por_medico(datos)
    corta = analisis.fecha_corta
    nombre = previa[0] if previa else None
    return dict(
        resumen=dict(analisis.resumen_semana(lunes, datos, resumen, alertas, revision, len(agendas), nombre, cambios),
                     festivos=resumen["festivos"]),
        alertas=dict(
            revision=[dict(fecha=f, corta=corta(f) if f else "Toda la semana", medico=m, problema=t) for f, m, t in revision],
            descanso=[dict(fecha=f, corta=corta(f), medico=m, regla=t) for f, m, t in alertas],
            pendientes=[dict(fecha=f, corta=corta(f), servicio=analisis.SERVICIOS.get(s, s), franja=fr, que=QUE_FALTA[t])
                        for f, fr, s, t in resumen["pendientes"]]),
        equidad=analisis.equidad(ws, lunes),
        agendas={n: analisis.texto_agenda(n, ev, lunes) for n, ev in agendas.items()},
        cambios=dict(version_anterior=nombre, lista=cambios or []))


@router.get("/areas/{area}/archivos/{id}/semanas/{lunes}/previa")
def previa(area: int, id: int, lunes: str, ctx: Contexto = Depends(contexto_area, scope="function")):
    ws = _cuadro(ctx, area, id)
    wb = _calcular(ctx, ws, _lunes(ws, lunes))[0]
    tema = analisis.paleta_tema(wb)
    return [dict(hoja=hoja, titulo=titulo, **analisis.hoja_a_json(wb[hoja], 1 if hoja == "Cambios" else 3, tema))
            for hoja, titulo in analisis.PESTANAS_PREVIA.items() if hoja in wb.sheetnames]


MAX_CUADROS = 12


@router.get("/areas/{area}/equidad-meses")
def equidad_meses(area: int, archivos: str, ctx: Contexto = Depends(contexto_area, scope="function")):
    _exigir_radiologia(ctx, area)
    try:
        ids = list(dict.fromkeys(int(x) for x in archivos.split(",") if x.strip()))
    except ValueError:
        raise HTTPException(422, "Indica los cuadros como una lista de números separados por comas.")
    if not ids or len(ids) > MAX_CUADROS:
        raise HTTPException(422, f"Elige entre 1 y {MAX_CUADROS} cuadros.")
    hojas, fallidos, vistos = [], [], 0
    for id_ in ids:
        f = ctx.conn.execute("SELECT nombre, contenido FROM archivo WHERE id = ?", (id_,)).fetchone()
        if f is None:
            continue
        vistos += 1
        try:
            ws = gs.cargar_mensual(BytesIO(bytes(f["contenido"])))
            hojas.append((ws.title.replace("Cambios ", ""), ws))
        except gs.ErrorPlanilla:
            fallidos.append(f["nombre"])
    if not vistos:
        raise HTTPException(404, "Archivo no encontrado")
    return dict(meses=[e for e, _ in hojas], fallidos=fallidos, filas=analisis.equidad_meses(hojas))


def _descarga(contenido, tipo, nombre):
    ascii_ = nombre.encode("ascii", "ignore").decode().replace('"', "")
    return Response(contenido, media_type=tipo, headers={"Content-Disposition": f"attachment; filename=\"{ascii_}\"; filename*=UTF-8''{quote(nombre)}"})


@router.get("/areas/{area}/archivos/{id}/semanas/{lunes}/agenda.ics")
def agenda_ics(area: int, id: int, lunes: str, medico: str, ctx: Contexto = Depends(contexto_area, scope="function")):
    ws = _cuadro(ctx, area, id)
    lunes = _lunes(ws, lunes)
    agendas = analisis.agenda_por_medico(_calcular(ctx, ws, lunes)[2])
    if medico not in agendas:
        raise HTTPException(404, "Ese médico no tiene turnos esa semana")
    return _descarga(analisis.ics(medico, agendas[medico]).encode("utf-8"), "text/calendar; charset=utf-8", analisis.nombre_archivo(medico) + ".ics")


@router.get("/areas/{area}/archivos/{id}/semanas/{lunes}/agendas.zip")
def agendas_zip(area: int, id: int, lunes: str, ctx: Contexto = Depends(contexto_area, scope="function")):
    ws = _cuadro(ctx, area, id)
    lunes = _lunes(ws, lunes)
    buf = BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nombre, ev in analisis.agenda_por_medico(_calcular(ctx, ws, lunes)[2]).items():
            base = analisis.nombre_archivo(nombre)
            z.writestr(base + ".ics", analisis.ics(nombre, ev))
            z.writestr(base + ".txt", analisis.texto_agenda(nombre, ev, lunes))
    return _descarga(buf.getvalue(), "application/zip", f"Agendas {gs.nombre_semana(lunes)}.zip")


XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
EXPORTE = ("e.id, e.periodo_id, e.numero, e.nombre_archivo, octet_length(e.contenido) AS bytes, e.creado, u.nombre AS creado_por "
           "FROM exporte e LEFT JOIN usuario u ON u.id = e.creado_por")


@router.post("/areas/{area}/archivos/{id}/semanas/{lunes}/exportes", status_code=201)
def exportar_libro(area: int, id: int, lunes: str, request: Request, ctx: Contexto = Depends(contexto_area, scope="function")):
    """Guarda el libro de la semana en `exporte` (tipo `semana`) y lo marca contra la versión anterior, como «Generar» en Qt. Exige `editar` (el exporte pasa a ser la versión contra la que se marcan los cambios). Nunca sobrescribe: `v2`, `v3`…
    Cada semana es un periodo del área (`lunes/domingo`) para colgar sus exportes."""
    ws = _cuadro(ctx, area, id)
    lunes = _lunes(ws, lunes)
    clave = _clave_semana(lunes)
    ctx.conn.execute("INSERT INTO periodo (clave) VALUES (?) ON CONFLICT (area_id, clave) DO NOTHING", (clave,))
    periodo = ctx.conn.execute("SELECT id FROM periodo WHERE clave = ? FOR UPDATE", (clave,)).fetchone()[0]  # serializa `numero`
    wb, _, _, _, cambios = _calcular(ctx, ws, lunes)
    with tempfile.TemporaryDirectory() as tmp:
        for (n,) in ctx.conn.execute("SELECT nombre_archivo FROM exporte WHERE periodo_id = ? AND tipo = 'semana'", (periodo,)).fetchall():
            (Path(tmp) / n).touch()
        nombre = gs.ruta_libre(tmp, lunes).name
    buf = BytesIO()
    wb.save(buf)
    nuevo = ctx.conn.execute(
        "INSERT INTO exporte (periodo_id, tipo, numero, nombre_archivo, contenido, creado_por) "
        "SELECT ?, 'semana', COALESCE(MAX(numero), 0) + 1, ?, ?, ? FROM exporte WHERE periodo_id = ? AND tipo = 'semana' RETURNING id",
        (periodo, nombre, buf.getvalue(), ctx.usuario.id, periodo)).fetchone()[0]
    request.state.evento = "exportacion"
    f = ctx.conn.execute(f"SELECT {EXPORTE} WHERE e.id = ?", (nuevo,)).fetchone()  # sql-ok: columnas constantes
    return {**{k: f[k] for k in f.keys()}, "cambios": len(cambios or [])}


@router.get("/areas/{area}/archivos/{id}/semanas/{lunes}/exportes")
def exportes_semana(area: int, id: int, lunes: str, ctx: Contexto = Depends(contexto_area_lectura, scope="function")):
    """Versiones guardadas de la semana; se descargan con `/periodos/{periodo_id}/exportes/{id}/descargar`."""
    lunes = _lunes(_cuadro(ctx, area, id), lunes)
    return [{k: f[k] for k in f.keys()} for f in ctx.conn.execute(
        f"SELECT {EXPORTE} JOIN periodo p ON p.id = e.periodo_id WHERE p.clave = ? AND e.tipo = 'semana' ORDER BY e.numero DESC",  # sql-ok: columnas constantes
        (_clave_semana(lunes),)).fetchall()]
