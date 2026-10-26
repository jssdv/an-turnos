import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de las rutas de catálogos: solicitudes, personal, novedades, turnos, puestos, parámetros y tarifas (necesitan AN_PG_URL). Imprime OK."""
from fixtura_api import ORIGEN, entorno
from test_edicion import sesion, url

H = {"Origin": ORIGEN}


def base(e, ruta, n="A"):
    return f"/api/areas/{e.ar[n]}{ruta}"


def auditado(e, evento):
    return e.su.execute("SELECT count(*) FROM auditoria WHERE evento = %s AND codigo < 300", (evento,)).fetchone()[0]


def test_solicitudes():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        malo = dict(colab_id=c, tipo="libre", desde="2026-10-10", hasta="2026-10-09")
        r = cli.post(base(e, "/solicitudes"), headers=H, json=malo)
        assert r.status_code == 422 and r.json()["detalle"] == "La fecha final es anterior a la inicial."
        assert cli.post(base(e, "/solicitudes"), headers=H, json={**malo, "hasta": "2026-10-10", "tipo": "quiero"}).status_code == 422  # sin turno
        assert cli.post(base(e, "/solicitudes"), headers=H, json={**malo, "hasta": "2026-10-10", "colab_id": e.colab["B"]}).status_code == 422
        assert cli.post(base(e, "/solicitudes"), headers=H, json={**malo, "hasta": "2026-10-10", "tipo": "raro"}).status_code == 422
        r = cli.post(base(e, "/solicitudes"), headers=H, json={**malo, "hasta": "2026-10-12", "turno": "M", "prioridad": "alta", "nota": "boda"})
        assert r.status_code == 201
        s = cli.get(base(e, "/solicitudes")).json()
        assert [(x["tipo"], x["turno"], x["prioridad"], x["desde"], x["hasta"]) for x in s] == [("libre", "", "alta", "2026-10-10", "2026-10-12")]
        assert e.su.execute("SELECT usuario FROM solicitud").fetchone()[0] == "editor@a.co"
        ev = cli.get(url(e, "/solicitudes")).json()
        assert ev == [dict(id=s[0]["id"], estado="cumplida", motivo="")]  # el cuadro de la fixture no tiene turnos del 10 al 12
        assert cli.delete(base(e, f"/solicitudes/{s[0]['id']}"), headers=H).status_code == 200
        assert cli.delete(base(e, "/solicitudes/9999"), headers=H).status_code == 404
        assert cli.get(base(e, "/solicitudes")).json() == [] and auditado(e, "solicitud_creada") == 1
        assert sesion(e, "lector@a.co").post(base(e, "/solicitudes"), headers=H, json=malo).status_code == 403


def test_evaluacion_de_una_solicitud_incumplida():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]  # el 5/10 la persona trabaja M; pide libre ese día
        cli.post(base(e, "/solicitudes"), headers=H, json=dict(colab_id=c, tipo="libre", desde="2026-10-05", hasta="2026-10-05"))
        cli.post(base(e, "/solicitudes"), headers=H, json=dict(colab_id=c, tipo="libre", desde="2026-10-07", hasta="2026-10-07"))
        r = cli.get(url(e, "/solicitudes")).json()
        assert [x["estado"] for x in r] == ["no cumplida", "cumplida"]


def test_personal():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        ok = dict(nombre=" Ana ", tipo="regular", horas_sem=42, pct=1, permitidos=None, puestos_permitidos=None, estudio=[[1, "M"]], activo=True)
        for malo in ({"nombre": "  "}, {"permitidos": []}, {"permitidos": ["ZZ"]}, {"puestos_permitidos": []}, {"puestos_permitidos": [9999]},
                     {"pct": 0}, {"horas_sem": 100}, {"tipo": "otro"}, {"estudio": [[7, "M"]]}):
            assert cli.post(base(e, "/colaboradores"), headers=H, json={**ok, **malo}).status_code == 422, malo
        r = cli.post(base(e, "/colaboradores"), headers=H, json=ok)
        assert r.status_code == 201
        nuevo = r.json()["id"]
        fila = [x for x in cli.get(base(e, "/colaboradores")).json() if x["id"] == nuevo][0]
        assert fila["nombre"] == "Ana" and fila["estudio"] == [[1, "M"]] and fila["puesto_fijo"] is None
        un_puesto = cli.get(base(e, "/puestos")).json()[0]
        r = cli.put(base(e, f"/colaboradores/{nuevo}"), headers=H, json={**ok, "nombre": "Ana B", "puestos_permitidos": [un_puesto["id"]]})
        assert r.status_code == 200
        fila = [x for x in cli.get(base(e, "/colaboradores")).json() if x["id"] == nuevo][0]
        assert (fila["nombre"], fila["puestos_permitidos"], fila["puesto_fijo"]) == ("Ana B", [un_puesto["id"]], un_puesto["numero"])
        assert cli.put(base(e, f"/colaboradores/{e.colab['B']}"), headers=H, json=ok).status_code == 422
        assert cli.delete(base(e, f"/colaboradores/{nuevo}"), headers=H).json() == {"resultado": "borrado"}
        assert cli.delete(base(e, f"/colaboradores/{e.colab['A']}"), headers=H).json() == {"resultado": "desactivado"}  # tiene cuadro
        assert auditado(e, "persona_creada") == 1


def test_novedades():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        n = dict(colab_id=c, tipo="Vacaciones", desde="2026-10-20", hasta="2026-10-25", nota="")
        assert cli.post(base(e, "/novedades"), headers=H, json={**n, "hasta": "2026-10-19"}).status_code == 422
        assert cli.post(base(e, "/novedades"), headers=H, json={**n, "tipo": "Fiesta"}).status_code == 422
        assert cli.post(base(e, "/novedades"), headers=H, json={**n, "colab_id": e.colab["B"]}).status_code == 422
        i = cli.post(base(e, "/novedades"), headers=H, json=n).json()["id"]
        assert [(x["tipo"], x["desde"], x["hasta"]) for x in cli.get(base(e, "/novedades")).json()] == [("Vacaciones", "2026-10-20", "2026-10-25")]
        assert cli.delete(base(e, f"/novedades/{i}"), headers=H).status_code == 200 and cli.delete(base(e, f"/novedades/{i}"), headers=H).status_code == 404


def test_turnos():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        t = dict(codigo="x1", nombre="Extra", inicio=480, fin=840, color="aabbcc", pausa=None, dom_fest=True, solver=False, activo=True)
        for malo in ({"codigo": "L"}, {"fin": 480}, {"color": "azul"}, {"pausa": {"ini": 200, "min": 300}}):
            assert cli.post(base(e, "/turnos"), headers=H, json={**t, **malo}).status_code == 422, malo
        assert cli.post(base(e, "/turnos"), headers=H, json=t).json() == {"codigo": "X1"}
        assert cli.post(base(e, "/turnos"), headers=H, json=t).status_code == 409
        assert cli.post(base(e, "/turnos"), headers=H, json={**t, "codigo": "m"}).status_code == 409  # M ya existe
        assert cli.put(base(e, "/turnos/X1"), headers=H, json={**t, "nombre": "Extra 2", "pausa": {"ini": 60, "min": 30, "pagada": False}}).status_code == 200
        x = [q for q in cli.get(base(e, "/turnos")).json() if q["codigo"] == "X1"][0]
        assert (x["nombre"], x["color"], x["inicio"], x["fin"]) == ("Extra 2", "AABBCC", 480, 840)
        assert cli.put(base(e, "/turnos/ZZ"), headers=H, json=t).status_code == 404
        assert cli.delete(base(e, "/turnos/X1"), headers=H).json() == {"resultado": "borrado"}
        assert cli.delete(base(e, "/turnos/M"), headers=H).json() == {"resultado": "desactivado"}  # en uso por el cuadro


def test_puestos_y_demandas():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        existentes = cli.get(base(e, "/puestos")).json()
        r = cli.post(base(e, "/puestos"), headers=H, json=dict(numero=existentes[0]["numero"], nombre="Repetido"))
        assert r.status_code == 422 and "Ya existe el puesto" in r.json()["detalle"]
        i = cli.post(base(e, "/puestos"), headers=H, json=dict(numero=50, nombre=" Nuevo ", color="00ff00")).json()["id"]
        assert cli.put(base(e, f"/puestos/{i}"), headers=H, json=dict(numero=51, nombre="Nuevo 2", color="00FF00", activo=False)).status_code == 200
        p = [x for x in cli.get(base(e, "/puestos")).json() if x["id"] == i][0]
        assert (p["numero"], p["nombre"], p["activo"]) == (51, "Nuevo 2", False)
        r = [dict(dia=0, inicio=360, fin=720, personas=2, obligatorio=False), dict(dia=7, inicio=360, fin=720, personas=1, obligatorio=False)]
        ruta = f"/puestos/{i}/requerimiento"
        assert cli.put(base(e, ruta), headers=H, json=[{**r[0], "dia": 9}]).status_code == 422
        assert cli.put(base(e, ruta), headers=H, json=[{**r[0], "fin": 360}]).status_code == 422  # empieza y termina igual
        assert cli.put(base(e, ruta), headers=H, json=[{**r[0], "inicio": 365}]).status_code == 422  # no es múltiplo de 30
        assert cli.put(base(e, ruta), headers=H, json=[r[0], r[0]]).status_code == 422
        assert cli.put(base(e, ruta), headers=H, json=r).status_code == 200
        assert cli.get(base(e, ruta)).json() == r
        assert [(x["tipo_dia"], x["personas"], x["obligatorio"]) for x in cli.get(base(e, "/demandas")).json() if x["puesto_id"] == i] == [("0", 2, False), ("F", 1, False)]
        assert cli.put(base(e, "/puestos/9999/requerimiento"), headers=H, json=r).status_code == 404
        assert cli.delete(base(e, f"/puestos/{i}"), headers=H).json() == {"resultado": "borrado"}


def test_requerimiento_sin_puestos():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        assert cli.put(base(e, "/parametros"), headers=H, json={"usa_puestos": 0}).status_code == 200
        assert cli.get(base(e, "/parametros")).json()["usa_puestos"] == "0"
        r = [dict(dia=0, inicio=360, fin=720, personas=3, obligatorio=True), dict(dia=7, inicio=1080, fin=360, personas=2, obligatorio=True)]
        assert cli.put(base(e, "/requerimiento"), headers=H, json=r).status_code == 200
        assert cli.get(base(e, "/requerimiento")).json() == r
        assert cli.put(base(e, "/requerimiento"), headers=H, json=[{**r[0], "dia": 9}]).status_code == 422
        assert cli.put(base(e, "/requerimiento"), headers=H, json=[r[0], r[0]]).status_code == 422
        assert cli.put(base(e, "/parametros"), headers=H, json={"usa_puestos": 2}).status_code == 422


def test_parametros_todo_o_nada_y_tarifas():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        assert cli.put(base(e, "/parametros"), headers=H, json={"ventana_semanas": 5, "limite_permutas": 21}).status_code == 422
        assert cli.put(base(e, "/parametros"), headers=H, json={"ventana_semanas": 5, "inventado": 1}).status_code == 422
        assert cli.put(base(e, "/parametros"), headers=H, json={"periodo_modo": "dias"}).status_code == 422
        assert cli.put(base(e, "/parametros"), headers=H, json={"ventana_semanas": "5"}).status_code == 422
        assert cli.get(base(e, "/parametros")).json()["ventana_semanas"] == "3"  # nada se guardó
        assert cli.get(base(e, "/parametros")).json()["max_noches_seguidas"] == "2"  # sin guardar: el defecto del núcleo, no vacío
        assert cli.put(base(e, "/parametros"), headers=H, json={"ventana_semanas": 5, "limite_permutas": 1, "periodo_modo": "semanas"}).status_code == 200
        p = cli.get(base(e, "/parametros")).json()
        assert (p["ventana_semanas"], p["limite_permutas"], p["periodo_modo"]) == ("5", "1", "semanas")
        n = len(cli.get(base(e, "/tarifas")).json())
        assert cli.post(base(e, "/tarifas"), headers=H, json=dict(concepto="nocturno", valor=40, desde="2027-01-01")).status_code == 201
        assert len(cli.get(base(e, "/tarifas")).json()) == n + 1
        assert cli.post(base(e, "/tarifas"), headers=H, json=dict(concepto="otro", valor=1, desde="2027-01-01")).status_code == 422
        assert cli.post(base(e, "/tarifas"), headers=H, json=dict(concepto="nocturno", valor=9999, desde="2027-01-01")).status_code == 422


def test_ver_no_escribe_catalogos():
    with entorno() as e:
        if e is None:
            return
        lector = sesion(e, "lector@a.co")
        for metodo, ruta in (("post", "/solicitudes"), ("post", "/colaboradores"), ("put", "/colaboradores/1"), ("delete", "/colaboradores/1"), ("post", "/novedades"),
                             ("delete", "/novedades/1"), ("post", "/turnos"), ("put", "/turnos/M"), ("delete", "/turnos/M"), ("post", "/puestos"), ("put", "/puestos/1"),
                             ("delete", "/puestos/1"), ("put", "/puestos/1/requerimiento"), ("put", "/parametros"), ("post", "/tarifas")):
            assert getattr(lector, metodo)(base(e, ruta), headers=H, **({} if metodo == "delete" else {"json": {}})).status_code == 403, (metodo, ruta)


if __name__ == "__main__":
    import inspect
    for n, f in list(globals().items()):
        if n.startswith("test_") and inspect.isfunction(f):
            f()
    print("OK")
