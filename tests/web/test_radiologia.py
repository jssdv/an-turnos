import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""API de Radiología (necesitan AN_PG_URL). Imprime OK."""
import io
import zipfile

from fixtura_api import ORIGEN, entorno
from fixtura_radiologia import MEDICO, cuadro_minimo

from an.web.rutas_radiologia import MAX_ARCHIVO

CABECERAS = {"Origin": ORIGEN, "Content-Type": "application/octet-stream"}


def con_area_radiologia(e):
    """Un área `radiologia` por clínica; el editor/lector de A y el editor de B reciben permiso."""
    e.rad = {}
    for n in ("A", "B"):
        e.rad[n] = e.su.execute("INSERT INTO area (nombre, tipo, clinica_id) VALUES ('Radiología', 'radiologia', %s) RETURNING id", (e.cl[n],)).fetchone()[0]
    for correo, n, perm in (("editor@a.co", "A", "editar"), ("lector@a.co", "A", "ver"), ("editor@b.co", "B", "editar")):
        e.su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s)", (e.us[correo], e.rad[n], perm, e.cl[n]))
    e.su.commit()


def subir(cli, area, datos, nombre="cuadro.xlsx"):
    return cli.post(f"/api/areas/{area}/archivos?nombre={nombre}", content=datos, headers=CABECERAS)


def test_subir_y_listar():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        datos = cuadro_minimo()
        r = subir(cli, e.rad["A"], datos)
        assert r.status_code == 201 and r.json()["tamano"] == len(datos) and r.json()["nombre"] == "cuadro.xlsx", r.text
        lista = cli.get(f"/api/areas/{e.rad['A']}/archivos").json()
        assert [f["id"] for f in lista] == [r.json()["id"]] and "contenido" not in lista[0]
        assert cli.delete(f"/api/areas/{e.rad['A']}/archivos/{r.json()['id']}", headers={"Origin": ORIGEN}).status_code == 204
        assert cli.get(f"/api/areas/{e.rad['A']}/archivos").json() == []


def test_rechaza_lo_que_no_es_xlsx():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        r = subir(cli, e.rad["A"], cuadro_minimo(), "cuadro.txt")
        assert r.status_code == 422 and r.json()["detalle"] == "Sube un archivo .xlsx."
        r = subir(cli, e.rad["A"], b"hola")
        assert r.status_code == 422 and r.json()["detalle"] == "El archivo no es un Excel .xlsx válido (¿está protegido con contraseña?)."


def test_rechaza_pasa_de_10_mb():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        r = subir(cli, e.rad["A"], b"x" * (MAX_ARCHIVO + 1))
        assert r.status_code == 413 and r.json()["detalle"] == "El archivo pasa de 10 MB."
        r = subir(cli, e.rad["A"], b"x" * (MAX_ARCHIVO + 5000))
        assert r.status_code == 413 and r.json()["detalle"] == "El archivo pasa de 10 MB."
        assert subir(cli, e.rad["A"], b"x" * MAX_ARCHIVO).status_code == 422  # llega a la validación del contenido


def test_rechaza_zip_bomba():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("relleno.bin", bytes(101 * 1024 * 1024))
        assert len(buf.getvalue()) < MAX_ARCHIVO
        r = subir(cli, e.rad["A"], buf.getvalue())
        assert r.status_code == 422 and r.json()["detalle"] == "El archivo es demasiado grande al abrirlo."


def test_cuadro_sin_excel_y_sin_semana():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        cli = e.cliente()
        e.entrar(cli, "editor@a.co")
        r = subir(cli, e.rad["A"], cuadro_minimo(fila3=False))
        assert r.status_code == 422 and r.json()["detalle"] == (
            "La fila 3 de 'Cambios Octubre 2026' no tiene fechas completas.\nEscribe la primera fecha (ej. 01/10/2026), "
            "deja =+celda_anterior+1 en las demás, usa formato 'd' y guarda en Excel.")
        r = subir(cli, e.rad["A"], cuadro_minimo(dias=3))
        assert r.status_code == 422 and r.json()["detalle"] == "El cuadro no tiene ninguna semana completa (lunes a domingo)."


def test_permisos_y_aislamiento():
    with entorno() as e:
        if e is None:
            return
        con_area_radiologia(e)
        lector, editor, otro = e.cliente(), e.cliente(), e.cliente()
        e.entrar(lector, "lector@a.co")
        e.entrar(editor, "editor@a.co")
        e.entrar(otro, "editor@b.co")
        id_ = subir(editor, e.rad["A"], cuadro_minimo()).json()["id"]
        assert subir(lector, e.rad["A"], cuadro_minimo()).status_code == 403
        assert lector.delete(f"/api/areas/{e.rad['A']}/archivos/{id_}", headers={"Origin": ORIGEN}).status_code == 403
        assert len(lector.get(f"/api/areas/{e.rad['A']}/archivos").json()) == 1
        assert otro.get(f"/api/areas/{e.rad['A']}/archivos").status_code == 404  # otra clínica
        assert otro.delete(f"/api/areas/{e.rad['B']}/archivos/{id_}", headers={"Origin": ORIGEN}).status_code == 404  # archivo ajeno
        assert editor.get(f"/api/areas/{e.ar['A']}/archivos").status_code == 404  # área de turnos
        assert editor.get(f"/api/areas/{e.rad['B']}/archivos").status_code == 404  # sin permiso en esa área
        fila = e.su.execute("SELECT ruta FROM auditoria WHERE metodo = 'POST' AND ruta LIKE '%archivos%' ORDER BY id DESC LIMIT 1").fetchone()
        assert fila and "cuadro" not in fila["ruta"] and "xlsx" not in fila["ruta"], fila["ruta"]  # el nombre del archivo no llega a la auditoría


def test_semana_por_defecto():
    from datetime import date
    from an.radiologia.analisis import semana_por_defecto
    lunes = [date(2026, 10, d) for d in (5, 12, 19)]
    assert semana_por_defecto(lunes, date(2026, 10, 14)) == date(2026, 10, 12)  # la de esa semana
    assert semana_por_defecto(lunes, date(2026, 10, 3)) == date(2026, 10, 5)
    assert semana_por_defecto(lunes, date(2027, 1, 1)) == date(2026, 10, 19)


def con_cuadro(e, usuario="lector@a.co"):
    """(cliente lector, id del archivo subido por el editor, área de Radiología)."""
    con_area_radiologia(e)
    editor, cli = e.cliente(), e.cliente()
    e.entrar(editor, "editor@a.co")
    e.entrar(cli, usuario)
    return cli, subir(editor, e.rad["A"], cuadro_minimo()).json()["id"], e.rad["A"]


def test_semanas_y_analisis():
    with entorno() as e:
        if e is None:
            return
        cli, id_, area = con_cuadro(e)
        s = cli.get(f"/api/areas/{area}/archivos/{id_}/semanas").json()
        assert s["hoja"] == "Cambios Octubre 2026"
        assert [(x["lunes"], x["etiqueta"]) for x in s["semanas"]] == [
            ("2026-10-05", "5 – 11 oct 2026"), ("2026-10-12", "12 – 18 oct 2026"), ("2026-10-19", "19 – 25 oct 2026")]
        assert s["defecto"] in {x["lunes"] for x in s["semanas"]}
        d = cli.get(f"/api/areas/{area}/archivos/{id_}/semanas/2026-10-05").json()
        r = d["resumen"]
        assert r["semana"] == "Semana del 5 de octubre al 11 de octubre"
        assert [(t["titulo"], t["valor"]) for t in r["tarjetas"]] == [
            ("Franjas sin médico", 104), ("Alertas de descanso", 0), ("Problemas en el cuadro", 0),
            ("Cambios desde la última versión", "—"), ("Médicos con turnos", 1), ("Festivos", 0)]
        abd = next(f for f in r["cobertura"] if f["servicio"] == "Lectura Abdomen")
        assert abd["dias"][0] == {"n": 1, "faltan": ["12:00 am - 7:00 am", "1:00 pm - 11:59 pm", "1:00 pm - 7:00 pm"]}
        assert r["aviso"] == "" and d["alertas"]["descanso"] == [] and d["alertas"]["revision"] == []
        assert len(d["alertas"]["pendientes"]) == 104
        assert d["equidad"][0]["medico"] == MEDICO and d["equidad"][0]["semana"] == 6
        assert list(d["agendas"]) == [MEDICO] and d["agendas"][MEDICO].strip()
        assert d["cambios"] == {"version_anterior": None, "lista": []}
        for malo in ("2026-10-06", "2026-11-02", "no-es-fecha"):  # martes, fuera del cuadro, basura
            x = cli.get(f"/api/areas/{area}/archivos/{id_}/semanas/{malo}")
            assert x.status_code == 422 and x.json()["detalle"] == "La fecha debe ser un lunes del cuadro."
        assert cli.get(f"/api/areas/{area}/archivos/9999/semanas").status_code == 404
