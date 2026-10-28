import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Pruebas de la API de edición del cuadro (necesitan AN_PG_URL). Imprime OK."""
from fixtura_api import ORIGEN, entorno

H = {"Origin": ORIGEN}


def sesion(e, correo):
    cli = e.cliente()
    e.entrar(cli, correo)
    return cli


def periodo(e, n="A"):
    return e.su.execute("SELECT id FROM periodo WHERE area_id = %s ORDER BY id", (e.ar[n],)).fetchone()[0]


def test_cuadro_trae_revision_y_fijo():
    with entorno() as e:
        if e is None:
            return
        e.su.execute("UPDATE asignacion SET fijo = 1 WHERE fecha = '2026-10-06' AND area_id = %s", (e.ar["A"],))
        e.su.commit()
        cli = sesion(e, "lector@a.co")
        r = cli.get(f"/api/areas/{e.ar['A']}/periodos/{periodo(e)}/cuadro").json()
        assert r["revision"] == 0
        assert [(c["fecha"], c["fijo"]) for c in r["celdas"]] == [("2026-10-05", False), ("2026-10-06", True), ("2026-10-07", False)]


def test_puesto_fijado_en_la_celda():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        q = cli.get(f"/api/areas/{e.ar['A']}/puestos").json()[0]["id"]
        cambio(cli, e, "ajuste", [(c, "2026-10-05", "M")])
        r = cli.post(url(e, "/cambios"), headers={**H, "If-Match": "1"}, json=dict(tipo="ajuste", motivo="", celdas=[dict(colab_id=c, fecha="2026-10-05", turno="M", puesto=q)]))
        assert r.status_code == 200, r.text
        celda = [x for x in cli.get(f"/api/areas/{e.ar['A']}/periodos/{periodo(e)}/cuadro").json()["celdas"] if x["fecha"] == "2026-10-05"][0]
        assert celda["puesto"] == q and celda["puesto_fijo"] is True
        r = cli.post(url(e, "/cambios"), headers={**H, "If-Match": "2"}, json=dict(tipo="ajuste", motivo="", celdas=[dict(colab_id=c, fecha="2026-10-05", turno="M", puesto=99999)]))
        assert r.status_code == 422


def test_cuadro_version_original():
    with entorno() as e:
        if e is None:
            return
        cli, pid = sesion(e, "lector@a.co"), periodo(e)
        r = cli.get(f"/api/areas/{e.ar['A']}/periodos/{pid}/cuadro?version=original").json()
        assert r["version"] == "original" and not r["usa_puestos"] and all("puesto" not in c and not c["fijo"] for c in r["celdas"])
        assert cli.get(f"/api/areas/{e.ar['A']}/periodos/{pid}/cuadro?version=otra").status_code == 422


def agregar_persona(e, n="A", nombre="P2"):
    """Segunda persona del área con M el 5/10, T el 6/10 y M el 7/10; devuelve su id."""
    from datetime import date
    from an.turnos.db import BD
    from an.turnos.dominio import Colaborador
    from an.turnos.pg import Conexion
    e.su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl[n]), str(e.ar[n])))
    bd = BD.postgres(Conexion(e.su))
    p = Colaborador(0, f"{nombre}-{n}")
    bd.guardar_colaborador(p)
    for d, t in ((5, "M"), (6, "T"), (7, "M")):
        bd.set_celda("2026-10-01/2026-10-31", p.id, date(2026, 10, d), t, fijo=False)
    e.su.execute("RESET app.clinica")
    e.su.execute("RESET app.area")
    e.su.commit()
    return p.id


def url(e, ruta="", n="A", pid=None):
    return f"/api/areas/{e.ar[n]}/periodos/{pid or periodo(e, n)}{ruta}"


def cambio(cli, e, tipo, celdas, rev=0, motivo="", excepcion=False, n="A"):
    return cli.post(url(e, "/cambios", n), headers={**H, "If-Match": str(rev)},
                    json={"tipo": tipo, "celdas": [dict(colab_id=c, fecha=f, turno=t) for c, f, t in celdas], "motivo": motivo, "excepcion": excepcion})


def celdas_de(cli, e):
    return {(c["colab_id"], c["fecha"]): c["turno"] for c in cli.get(url(e, "/cuadro")).json()["celdas"]}


def test_if_match_ausente_malo_y_viejo():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        c = e.colab["A"]
        cuerpo = {"tipo": "ajuste", "celdas": [dict(colab_id=c, fecha="2026-10-07", turno="M")]}
        assert cli.post(url(e, "/cambios"), headers=H, json=cuerpo).status_code == 428
        assert cli.post(url(e, "/cambios"), headers={**H, "If-Match": "abc"}, json=cuerpo).status_code == 422
        assert cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")]).status_code == 200
        r = cambio(cli, e, "ajuste", [(c, "2026-10-07", "T")], rev=0)
        assert r.status_code == 409
        assert r.json()["detalle"] == {"mensaje": "El periodo cambió; recárgalo antes de continuar.", "revision": 1, "modificado_por": "editor@a.co"}
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "M"
        assert cambio(sesion(e, "editor@b.co"), e, "ajuste", [(c, "2026-10-07", "M")], n="A").status_code == 404  # periodo de otra clínica


def test_ajuste_deja_cambio_auditoria_y_revision():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        r = cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")])
        assert r.status_code == 200 and r.json()["revision"] == 1 and len(r.json()["ids"]) == 1
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "M"
        fila = e.su.execute("SELECT tipo, usuario, celdas FROM cambio_turno WHERE area_id = %s", (e.ar["A"],)).fetchone()
        assert (fila["tipo"], fila["usuario"]) == ("ajuste", "editor@a.co") and '"L", "M"' in fila["celdas"]
        aud = e.su.execute("SELECT codigo, evento FROM auditoria WHERE metodo = 'POST' AND ruta LIKE '%/cambios' ORDER BY id DESC").fetchone()
        assert (aud["codigo"], aud["evento"]) == (200, "cambio_ajuste")
        cuadro = cli.get(url(e, "/cuadro")).json()
        assert cuadro["revision"] == 1 and {x["fecha"]: x["fijo"] for x in cuadro["celdas"]}["2026-10-07"] is True


def test_servicio_necesita_motivo_y_ver_no_escribe():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        r = cambio(cli, e, "servicio", [(c, "2026-10-07", "M")])
        assert r.status_code == 422 and r.json()["detalle"] == "Un cambio de servicio necesita motivo."
        assert cambio(cli, e, "servicio", [(c, "2026-10-07", "M")], motivo="cubrir").status_code == 200
        assert cambio(sesion(e, "lector@a.co"), e, "ajuste", [(c, "2026-10-07", "T")], rev=1).status_code == 403


def test_celdas_no_editables_dan_422():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        assert cambio(cli, e, "ajuste", [(c, "2026-10-07", "ZZ")]).status_code == 422
        assert cambio(cli, e, "ajuste", [(c, "2026-11-07", "M")]).status_code == 422
        assert cambio(cli, e, "ajuste", [(e.colab["B"], "2026-10-07", "M")]).status_code == 422  # persona de otra clínica
        assert cambio(cli, e, "ajuste", [(c, "2026-10-07", "M"), (c, "2026-10-07", "T")]).status_code == 422
        e.su.execute("INSERT INTO novedad (colab_id, tipo, desde, hasta, clinica_id, area_id) VALUES (%s, 'Vacaciones', '2026-10-07', '2026-10-07', %s, %s)",
                     (c, e.cl["A"], e.ar["A"]))
        e.su.commit()
        r = cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")])
        assert r.status_code == 422 and "novedad" in r.json()["detalle"]
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "L"


def test_permuta_cupo_y_excepcion():
    with entorno() as e:
        if e is None:
            return
        cli, a, b = sesion(e, "editor@a.co"), e.colab["A"], agregar_persona(e)
        e.su.execute("INSERT INTO parametro (clave, valor, clinica_id, area_id) VALUES ('limite_permutas', '1', %s, %s) ON CONFLICT DO NOTHING",
                     (e.cl["A"], e.ar["A"]))
        e.su.execute("UPDATE parametro SET valor = '1' WHERE clave = 'limite_permutas' AND area_id = %s", (e.ar["A"],))
        e.su.commit()
        assert cambio(cli, e, "permuta", [(a, "2026-10-05", "L")]).status_code == 422  # una permuta son dos celdas
        r = cambio(cli, e, "permuta", [(a, "2026-10-05", "L"), (b, "2026-10-06", "L")])
        assert r.status_code == 200, r.text
        cu = celdas_de(cli, e)
        assert cu[(a, "2026-10-05")] == "T" and cu[(b, "2026-10-06")] == "M"
        assert [x for x in cli.get(url(e, "/cupos")).json() if x["colab_id"] == a] == [{"colab_id": a, "usadas": 1, "limite": 1}]
        r = cambio(cli, e, "permuta", [(a, "2026-10-06", "L"), (b, "2026-10-05", "L")], rev=1)
        assert r.status_code == 409 and sorted(r.json()["detalle"]["ids"]) == sorted([a, b])
        assert r.json()["detalle"]["cupos"][0]["limite"] == 1
        r = cambio(cli, e, "permuta", [(a, "2026-10-06", "L"), (b, "2026-10-05", "L")], rev=1, excepcion=True)
        assert r.status_code == 200
        assert e.su.execute("SELECT count(*) FROM cambio_turno WHERE excepcion = 1").fetchone()[0] == 1


def test_listar_y_anular_todo_o_nada():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")], motivo="uno")
        lista = cli.get(url(e, "/cambios")).json()
        assert len(lista) == 1 and lista[0]["celdas"] == [dict(colab_id=c, fecha="2026-10-07", antes="L", despues="M", puesto_antes=0, puesto_despues=0)]
        assert lista[0]["anulado_en"] is None and lista[0]["excepcion"] is False
        cid = lista[0]["id"]
        cambio(cli, e, "ajuste", [(c, "2026-10-07", "T")], rev=1)  # edita después la misma celda
        r = cli.post(url(e, f"/cambios/{cid}/anular"), headers={**H, "If-Match": "2"})
        assert r.status_code == 409 and r.json()["detalle"]["celdas"] == [dict(colab_id=c, fecha="2026-10-07")]
        assert "se editó después" in r.json()["detalle"]["mensaje"]
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "T"
        ult = cli.get(url(e, "/cambios")).json()[0]["id"]
        r = cli.post(url(e, f"/cambios/{ult}/anular"), headers={**H, "If-Match": "2"})
        assert r.status_code == 200 and r.json()["anulado"] is True and r.json()["revision"] == 3
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "M"
        r = cli.post(url(e, f"/cambios/{ult}/anular"), headers={**H, "If-Match": "3"})
        assert r.json() == {"revision": 3, "anulado": False, "alertas_nuevas": []}
        assert cli.post(url(e, "/cambios/99999/anular"), headers={**H, "If-Match": "3"}).status_code == 404


def test_anular_permuta_devuelve_el_cupo():
    with entorno() as e:
        if e is None:
            return
        cli, a, b = sesion(e, "editor@a.co"), e.colab["A"], agregar_persona(e)
        cambio(cli, e, "permuta", [(a, "2026-10-05", "L"), (b, "2026-10-06", "L")])
        cid = cli.get(url(e, "/cambios")).json()[0]["id"]
        cli.post(url(e, f"/cambios/{cid}/anular"), headers={**H, "If-Match": "1"})
        assert [x["usadas"] for x in cli.get(url(e, "/cupos")).json()] == [0, 0]


def crear(cli, e, ini, fin):
    return cli.post(f"/api/areas/{e.ar['A']}/periodos", headers=H, json={"inicio": ini, "fin": fin})


def test_crear_periodo_rechaza_solapes():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        assert crear(cli, e, "2026-11-01", "2026-11-30").status_code == 201
        for ini, fin in (("2026-11-02", "2026-11-29"), ("2026-10-25", "2026-11-07"), ("2026-11-30", "2026-12-05")):
            r = crear(cli, e, ini, fin)
            assert r.status_code == 409 and "solapa" in r.json()["detalle"], (ini, fin)
        assert crear(cli, e, "2026-12-01", "2026-12-31").status_code == 201
        assert crear(cli, e, "2026-12-31", "2026-12-01").status_code == 422
        assert crear(cli, e, "2026-01-01", "2027-12-31").status_code == 422
        assert sesion(e, "lector@a.co").post(f"/api/areas/{e.ar['A']}/periodos", headers=H, json={"inicio": "2027-01-01", "fin": "2027-01-31"}).status_code == 403
        assert all(p["solapa_con"] == [] for p in cli.get(f"/api/areas/{e.ar['A']}/periodos").json())


def test_periodos_lista_solapes_ya_existentes():
    with entorno() as e:
        if e is None:
            return
        e.su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES ('2026-10-02/2026-10-29', %s, %s)", (e.cl["A"], e.ar["A"]))
        e.su.commit()
        ps = sesion(e, "lector@a.co").get(f"/api/areas/{e.ar['A']}/periodos").json()
        assert [len(p["solapa_con"]) for p in ps] == [1, 1]


def accion(cli, e, nombre, rev):
    return cli.post(url(e, f"/{nombre}"), headers={**H, "If-Match": str(rev)})


def test_publicar_restaurar_cerrar_reabrir():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")])
        assert accion(cli, e, "publicar", 1).json() == {"revision": 2}
        assert e.su.execute("SELECT publicado_en FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] is not None
        cambio(cli, e, "ajuste", [(c, "2026-10-07", "T")], rev=2)
        assert accion(cli, e, "restaurar", 3).json() == {"revision": 4}
        assert celdas_de(cli, e)[(c, "2026-10-07")] == "M"
        assert accion(cli, e, "reabrir", 4).status_code == 409  # no estaba cerrado
        assert accion(cli, e, "cerrar", 4).json() == {"revision": 5}
        assert e.su.execute("SELECT cerrado_en FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] is not None
        assert e.su.execute("SELECT count(*) FROM cierre WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] == 1
        r = cambio(cli, e, "ajuste", [(c, "2026-10-07", "T")], rev=5)
        assert r.status_code == 409 and "cerrado" in r.json()["detalle"]
        assert accion(cli, e, "publicar", 5).status_code == 409
        assert accion(cli, e, "reabrir", 5).json() == {"revision": 6}
        assert e.su.execute("SELECT cerrado_en FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] is None
        assert cambio(cli, e, "ajuste", [(c, "2026-10-07", "T")], rev=6).status_code == 200


def test_cerrar_sin_cuadro_da_409():
    with entorno() as e:
        if e is None:
            return
        cli = sesion(e, "editor@a.co")
        pid = crear(cli, e, "2026-11-01", "2026-11-30").json()["id"]
        r = cli.post(url(e, "/cerrar", pid=pid), headers={**H, "If-Match": "0"})
        assert r.status_code == 409 and "no tiene cuadro" in r.json()["detalle"]


def test_dos_pestanas_la_segunda_recibe_409():
    with entorno() as e:
        if e is None:
            return
        uno, dos, c = sesion(e, "editor@a.co"), sesion(e, "editor@a.co"), e.colab["A"]
        assert cambio(uno, e, "ajuste", [(c, "2026-10-07", "M")]).status_code == 200
        r = cambio(dos, e, "ajuste", [(c, "2026-10-07", "T")])
        assert r.status_code == 409 and r.json()["detalle"]["revision"] == 1
        assert dos.get(url(e, "/cuadro")).json()["revision"] == 1 and celdas_de(dos, e)[(c, "2026-10-07")] == "M"


def test_un_solo_editor_por_area():
    import psycopg
    with entorno() as e:
        if e is None:
            return
        try:
            e.su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, 'editar', %s)",
                         (e.us["lector@a.co"], e.ar["A"], e.cl["A"]))
            raise AssertionError("aceptó un segundo editor")
        except psycopg.errors.UniqueViolation:
            e.su.rollback()


def test_sesion_vencida_da_401_y_no_cambia_nada():
    with entorno() as e:
        if e is None:
            return
        cli, c = sesion(e, "editor@a.co"), e.colab["A"]
        e.su.execute("UPDATE sesion SET ultima = now() - interval '1 day'")
        e.su.commit()
        assert cambio(cli, e, "ajuste", [(c, "2026-10-07", "M")]).status_code == 401
        assert e.su.execute("SELECT count(*) FROM cambio_turno").fetchone()[0] == 0


def test_ver_recibe_403_en_toda_escritura():
    with entorno() as e:
        if e is None:
            return
        lector, pid = sesion(e, "lector@a.co"), periodo(e)
        base = f"/api/areas/{e.ar['A']}/periodos"
        for ruta in (f"{base}/{pid}/cambios", f"{base}/{pid}/cambios/1/anular", base, *(f"{base}/{pid}/{a}" for a in ("publicar", "restaurar", "cerrar", "reabrir"))):
            assert lector.post(ruta, headers={**H, "If-Match": "0"}, json={}).status_code == 403, ruta


if __name__ == "__main__":
    import inspect
    for n, f in list(globals().items()):
        if n.startswith("test_") and inspect.isfunction(f):
            f()
    print("OK")
