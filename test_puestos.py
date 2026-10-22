"""Pruebas del núcleo de puestos, demanda por tramos y dotación. Imprime OK."""
from datetime import date

import tempfile

import db
import demanda
import dotacion
from dominio import Colaborador, Contexto, Demanda, Puesto, Turno


def ctx_con(demandas):
    return Contexto({}, [], [], {}, {}, demandas=demandas)


def test_tramos_ventana():
    assert demanda.tramos_ventana(360, 720) == [(0, t) for t in range(12, 24)]
    noche = demanda.tramos_ventana(1080, 360)
    assert len(noche) == 24 and noche[0] == (0, 36) and noche[-1] == (1, 11)


def test_franjas_de():
    assert demanda.franjas_de(Turno("M7", "", 420, 780)) == ("M",)
    assert demanda.franjas_de(Turno("C", "", 360, 1080)) == ("M", "T")
    assert demanda.franjas_de(Turno("NC", "", 1080, 360)) == ("N",)
    assert demanda.franjas_de(Turno("MAD", "", 0, 360)) == ("N",)  # empieza a las 00:00


def test_demanda_cruza_medianoche_y_tipo_de_dia():
    """Review Focus 1: la madrugada del domingo viene del sábado de noche (tipo LS)."""
    guardia = [Demanda(1, "LS", 1080, 360, 2), Demanda(1, "DF", 1080, 360, 1)]
    ctx = ctx_con(guardia)
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 17))  # sábado
    assert len(obl) == 48 and obl[40] == 2 and obl[2] == 2  # la madrugada del sábado viene del viernes (LS)
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 18))  # domingo
    assert obl[2] == 2 and obl[40] == 1  # madrugada del domingo: del sábado (LS); noche del domingo: DF
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 19))  # lunes
    assert obl[2] == 1  # madrugada del lunes: del domingo (DF)


def test_deseables_van_aparte():
    ctx = ctx_con([Demanda(1, "LS", 480, 720, 1, obligatorio=False)])
    obl, des = demanda.demanda_fecha(ctx, date(2026, 10, 14))
    assert sum(obl) == 0 and des[16] == 1 and des[23] == 1 and des[24] == 0


def test_cobertura_derivada_a_mano():
    ds = [Demanda(1, "LS", 360, 1080, 2), Demanda(2, "LS", 480, 840, 1)]
    assert demanda.cobertura_derivada(ds) == {"LS": {"M": 3, "T": 3, "N": 0}, "DF": {"M": 0, "T": 0, "N": 0}}


def test_huecos_sin_turno():
    m, t, nc = Turno("M", "", 360, 720), Turno("T", "", 720, 1080), Turno("NC", "", 1080, 360)
    ds = [Demanda(1, "LS", 480, 840, 1)]
    assert demanda.huecos_sin_turno(ds, {"M": m, "T": t}) == []
    assert demanda.huecos_sin_turno(ds, {"NC": nc}) == [(480, 840)]
    sin_dom = Turno("M", "", 360, 720, dom_fest=False)
    assert demanda.huecos_sin_turno([Demanda(1, "DF", 480, 720, 1)], {"M": sin_dom}) == [(480, 720)]


def test_estimar_personas():
    ds = [Demanda(1, "LS", 360, 1080, 2), Demanda(1, "DF", 360, 720, 1), Demanda(2, "LS", 360, 1080, 1, obligatorio=False)]
    assert demanda.horas_persona_semana(ds) == 150
    e = demanda.estimar_personas(ds, 42, 0.10)
    assert e["horas_semana"] == 150 and e["personas"] == 4 and e["por_puesto"] == {1: 150}
    assert e["por_franja"]["M"] + e["por_franja"]["T"] + e["por_franja"]["N"] == 150
    assert demanda.estimar_personas(ds, 42, 0.10, incluir_deseables=True)["horas_semana"] == 150 + 72


def test_semilla_y_cobertura_derivada():
    bd = db.BD()
    pu = bd.catalogo_puestos()
    assert [(p.numero, p.nombre) for p in pu.values()] == [(1, "Lavado"), (2, "Autoclave"), (3, "Sterrad y esto"),
                                                           (4, "Cuarto estéril"), (5, "Ropa"), (6, "Guardia noche")]
    ds = bd.demandas()
    assert len(ds) == 9 and sum(1 for d in ds if d.tipo_dia == "LS") == 6 and sum(1 for d in ds if d.tipo_dia == "DF") == 3
    ropa = [d for d in ds if pu[d.puesto_id].numero == 5]
    assert len(ropa) == 1 and not ropa[0].obligatorio
    ctx = bd.contexto(2026)
    assert ctx.cobertura == {"LS": {"M": 4, "T": 4, "N": 2}, "DF": {"M": 2, "T": 2, "N": 2}}
    assert len(ctx.puestos) == 6 and len(ctx.demandas) == 9


def test_migracion_v3_a_v4():
    with tempfile.TemporaryDirectory() as tmp:
        ruta = tmp + "/v3.db"
        bd = db.BD(ruta)
        bd.c.execute("INSERT INTO colaborador (nombre,tipo,horas_sem,pct,permitidos,puesto_fijo,estudio,activo) "
                     "VALUES ('A','regular',42,1,NULL,3,'[]',1)")
        bd.c.executescript("DROP TABLE puesto; DROP TABLE demanda; DROP TABLE persona_puesto; DELETE FROM cobertura;")
        bd.c.executemany("INSERT INTO cobertura VALUES (?,?,?)", [("LS", "M", 5), ("LS", "T", 4), ("LS", "N", 2),
                                                                  ("DF", "M", 2), ("DF", "T", 2), ("DF", "N", 2)])
        bd.c.execute("PRAGMA user_version = 3")
        bd.c.commit()
        bd.c.close()
        bd = db.BD(ruta)
        pu = bd.catalogo_puestos()
        autoclave = next(i for i, p in pu.items() if p.numero == 2)
        extra = [d for d in bd.demandas(autoclave) if d.tipo_dia == "LS" and d.inicio == 360 and d.fin == 720]
        assert len(extra) == 1 and extra[0].personas == 2  # el excedente de mañana (5 − 4) se suma al primer puesto
        assert bd.contexto(2026).cobertura["LS"] == {"M": 5, "T": 4, "N": 2}
        sterrad = next(i for i, p in pu.items() if p.numero == 3)
        assert bd.colaboradores()[0].puestos_permitidos == (sterrad,)
        assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 4


def test_borrar_puesto_en_uso():
    """Review Focus 4: un puesto con historial se desactiva; uno sin uso se borra."""
    bd = db.BD()
    autoclave = next(i for i, p in bd.catalogo_puestos().items() if p.numero == 2)
    bd.c.execute("INSERT INTO puesto_dia VALUES ('p','2026-10-05','M',2,1,1)")
    assert bd.borrar_puesto(autoclave) == "desactivado"
    assert autoclave not in bd.catalogo_puestos(solo_activos=True) and autoclave in bd.catalogo_puestos()
    nuevo = bd.guardar_puesto(Puesto(0, 9, "Prueba"))
    assert bd.borrar_puesto(nuevo) == "borrado" and nuevo not in bd.catalogo_puestos()


def test_numero_de_puesto_unico():
    bd = db.BD()
    try:
        bd.guardar_puesto(Puesto(0, 2, "Repetido"))
        assert False
    except ValueError:
        pass


def test_demandas_roundtrip():
    bd = db.BD()
    pid = bd.guardar_puesto(Puesto(0, 9, "Lencería"))
    bd.reemplazar_demandas(pid, [Demanda(pid, "LS", 480, 840, 2), Demanda(pid, "DF", 480, 720, 1, obligatorio=False)])
    ds = bd.demandas(pid)
    assert [(d.tipo_dia, d.inicio, d.fin, d.personas, d.obligatorio) for d in ds] == [("LS", 480, 840, 2, True), ("DF", 480, 720, 1, False)]
    assert bd.contexto(2026).cobertura["LS"]["M"] == 6  # 4 de los puestos base + 2 del pico de 08:00–12:00
    bd.reemplazar_demandas(pid, [])
    assert bd.demandas(pid) == []


def test_puestos_permitidos_roundtrip():
    bd = db.BD()
    ids = list(bd.catalogo_puestos())
    a = bd.guardar_colaborador(Colaborador(0, "A", puestos_permitidos=(ids[0], ids[1])))
    b = bd.guardar_colaborador(Colaborador(0, "B"))
    por_id = {c.id: c for c in bd.colaboradores()}
    assert por_id[a].puestos_permitidos == (ids[0], ids[1]) and por_id[b].puestos_permitidos is None
    p = por_id[a]
    p.puestos_permitidos = None
    bd.guardar_colaborador(p)
    assert {c.id: c for c in bd.colaboradores()}[a].puestos_permitidos is None
    try:
        bd.guardar_colaborador(Colaborador(0, "C", puestos_permitidos=()))
        assert False
    except ValueError:
        pass


def test_estimar_con_la_base():
    bd = db.BD()
    for i in range(13):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    e = dotacion.estimar(bd)
    # 4 puestos de día × 12 h × 6 días + 2 puestos × 12 h × 1 domingo + guardia noche 2 × 12 h × 7 días
    assert e["horas_semana"] == 288 + 24 + 168 == 480 and e["personas"] == 13
    assert e["activos"] == 13 and e["diferencia"] == 0 and e["margen"] == 0.10 and e["jornada_media"] == 42
    bd.set_param("dotacion_margen_pct", 0)
    assert dotacion.estimar(bd)["personas"] == 12 and dotacion.estimar(bd)["diferencia"] == 1
    assert dotacion.estimar(bd, incluir_deseables=True)["horas_semana"] == 480 + 72  # Ropa deseable: 12 h × 6 días


def test_estimar_ignora_puestos_inactivos_y_refuerzo():
    bd = db.BD()
    bd.guardar_colaborador(Colaborador(0, "P"))
    bd.guardar_colaborador(Colaborador(0, "R", tipo="refuerzo"))
    guardia = next(i for i, p in bd.catalogo_puestos().items() if p.numero == 6)
    p = bd.catalogo_puestos()[guardia]
    p.activo = False
    bd.guardar_puesto(p)
    e = dotacion.estimar(bd)
    assert e["horas_semana"] == 288 + 24 and e["activos"] == 1


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
