import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del núcleo de puestos, demanda por tramos y dotación. Imprime OK."""
from datetime import date, timedelta

import tempfile

from an.esterilizacion import db
from an.esterilizacion import demanda
from an.esterilizacion import dotacion
from an.esterilizacion import puestos
from an.esterilizacion import solver
from an.esterilizacion.dominio import AsignacionPuesto, Colaborador, Contexto, Demanda, Puesto, Turno


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
        assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 5  # la cadena termina en la versión vigente


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


def _bd(puestos_demandas, n):
    """BD con solo estos puestos con demanda: {nombre: [(tipo, ini, fin, personas[, obligatorio])]} y n personas."""
    bd = db.BD()
    for pid in list(bd.catalogo_puestos()):
        bd.reemplazar_demandas(pid, [])
    ids = {}
    for k, (nombre, reglas) in enumerate(puestos_demandas.items(), start=20):
        pid = bd.guardar_puesto(Puesto(0, k, nombre))
        ids[nombre] = pid
        bd.reemplazar_demandas(pid, [Demanda(pid, *r) for r in reglas])
    for i in range(n):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    return bd, ids


LUN = date(2026, 10, 5)
DIA = [date(2026, 10, 5 + i) for i in range(4)]  # lunes a jueves


def _ocupacion(filas):
    occ = {}
    for a in filas:
        if a.puesto_id:
            for t in range(a.desde // 30, a.hasta // 30):
                occ[(a.fecha, a.puesto_id, t)] = occ.get((a.fecha, a.puesto_id, t), 0) + 1
    return occ


def _sin_solape(filas):
    vistos = set()
    for a in filas:
        for t in range(a.desde // 30, a.hasta // 30):
            k = (a.fecha, a.colab_id, t)
            assert k not in vistos, k
            vistos.add(k)


def test_asignar_cubre_la_demanda_por_tramo():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)], "B": [("LS", 720, 1080, 1)]}, 3)
    ctx = bd.contexto(2026)
    p0, p1, p2 = [c.id for c in ctx.colabs]
    cuadro = {(p0, LUN): "C", (p1, LUN): "M", (p2, LUN): "T"}
    filas = puestos.asignar_tramos(ctx, cuadro, [LUN])
    _sin_solape(filas)
    occ = _ocupacion(filas)
    assert all(occ.get((LUN, ids["A"], t), 0) >= 1 for t in range(12, 36))
    assert all(occ.get((LUN, ids["B"], t), 0) >= 1 for t in range(24, 36))


def test_respeta_puestos_permitidos():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)], "B": [("LS", 360, 1080, 1)]}, 2)
    a, b = bd.colaboradores()
    a.puestos_permitidos = (ids["B"],)
    bd.guardar_colaborador(a)
    ctx = bd.contexto(2026)
    filas = puestos.asignar_tramos(ctx, {(a.id, LUN): "C", (b.id, LUN): "C"}, [LUN])
    assert {x.puesto_id for x in filas if x.colab_id == a.id} == {ids["B"]}
    assert {x.puesto_id for x in filas if x.colab_id == b.id} == {ids["A"]}


def test_varias_personas_en_un_puesto():
    bd, ids = _bd({"A": [("LS", 360, 1080, 2)]}, 2)
    ctx = bd.contexto(2026)
    c0, c1 = [c.id for c in ctx.colabs]
    filas = puestos.asignar_tramos(ctx, {(c0, LUN): "C", (c1, LUN): "C"}, [LUN])
    occ = _ocupacion(filas)
    assert all(occ[(LUN, ids["A"], t)] == 2 for t in range(12, 36))


def test_corrido_conserva_el_puesto_si_puede():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)], "B": [("LS", 360, 1080, 1)]}, 2)
    ctx = bd.contexto(2026)
    c0, c1 = [c.id for c in ctx.colabs]
    filas = puestos.asignar_tramos(ctx, {(c0, LUN): "C", (c1, LUN): "C"}, [LUN])
    for cid in (c0, c1):
        propias = [x for x in filas if x.colab_id == cid]
        assert len(propias) == 1 and (propias[0].desde, propias[0].hasta) == (360, 1080)


def test_apoyo_cuando_sobra_gente():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)]}, 2)
    ctx = bd.contexto(2026)
    c0, c1 = [c.id for c in ctx.colabs]
    filas = puestos.asignar_tramos(ctx, {(c0, LUN): "C", (c1, LUN): "C"}, [LUN])
    assert sorted(x.puesto_id for x in filas) == sorted([0, ids["A"]])


def test_rota_entre_dias():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)], "B": [("LS", 360, 1080, 1)]}, 2)
    ctx = bd.contexto(2026)
    c0, c1 = [c.id for c in ctx.colabs]
    cuadro = {(c, d): "C" for c in (c0, c1) for d in DIA}
    filas = puestos.asignar_tramos(ctx, cuadro, DIA)
    puesto = {(x.colab_id, x.fecha): x.puesto_id for x in filas}
    assert all(puesto[(c0, d)] != puesto[(c0, d + timedelta(days=1))] for d in DIA[:-1])


def test_noche_cuenta_en_su_dia_y_en_la_madrugada():
    bd, ids = _bd({"G": [("LS", 1080, 360, 1), ("DF", 1080, 360, 1)]}, 1)
    ctx = bd.contexto(2026)
    c0 = ctx.colabs[0].id
    filas = puestos.asignar_tramos(ctx, {(c0, LUN): "NC"}, [LUN, LUN + timedelta(days=1)])
    assert (LUN, 1080, 1440) in {(x.fecha, x.desde, x.hasta) for x in filas if x.puesto_id == ids["G"]}
    assert (LUN + timedelta(days=1), 0, 360) in {(x.fecha, x.desde, x.hasta) for x in filas if x.puesto_id == ids["G"]}


def test_asignacion_puesto_roundtrip_y_migracion_v5():
    with tempfile.TemporaryDirectory() as tmp:
        ruta = tmp + "/v4.db"
        bd = db.BD(ruta)
        aut = next(i for i, p in bd.catalogo_puestos().items() if p.numero == 2)
        fila = AsignacionPuesto(LUN, 1, aut, 360, 720, 1)
        bd.guardar_asignacion_puesto("p", [fila])
        assert bd.asignacion_puesto("p") == [fila]
        bd.guardar_asignacion_puesto("p", [])
        assert bd.asignacion_puesto("p") == []
        bd.c.execute("INSERT INTO puesto_dia VALUES ('p','2026-10-05','M',2,1,1)")
        bd.c.execute("INSERT INTO puesto_dia VALUES ('p','2026-10-05','T',0,2,2)")
        bd.c.executescript("DROP TABLE asignacion_puesto;")
        bd.c.execute("PRAGMA user_version = 4")
        bd.c.commit()
        bd.c.close()
        bd = db.BD(ruta)
        assert sorted(bd.asignacion_puesto("p")) == sorted([AsignacionPuesto(LUN, 1, aut, 360, 720, 1),
                                                           AsignacionPuesto(LUN, 2, 0, 720, 1080, 2)])
        assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 5


class _Simulado:
    """Reemplaza solver.generar: factible solo con al menos `minimo` personas."""

    def __init__(self, minimo):
        self.minimo, self.llamadas = minimo, []

    def __enter__(self):
        self.original = solver.generar
        solver.generar = self
        return self

    def __exit__(self, *exc):
        solver.generar = self.original

    def __call__(self, ctx, fechas, **kw):
        self.llamadas.append((len(ctx.colabs), kw))
        if self.minimo is None or len(ctx.colabs) < self.minimo:
            raise solver.ErrorSolver("no cabe")
        return {}, {"faltan": []}


def _ctx_pequeno():
    bd, ids = _bd({"A": [("LS", 360, 1080, 1)]}, 0)  # 72 h por semana → cota por horas de 2 personas
    return bd, bd.contexto(2026)


SEMANAS = [date(2026, 10, 5) + timedelta(days=i) for i in range(14)]


def test_biseccion_con_resolutor_simulado():
    bd, ctx = _ctx_pequeno()
    with _Simulado(7) as sim:
        r = dotacion.verificar_minimo(ctx, SEMANAS, 0.10, activos=5)
    assert r["minimo"] == 7 and len(r["pruebas"]) <= 6 and r["motivo"] is None and not r["cancelado"]
    assert all(kw.get("estricto") for _, kw in sim.llamadas)
    assert r["pruebas"][-1] == (7, True) and (6, False) in r["pruebas"]
    assert r["con_margen"] == 8 and r["diferencia"] == 5 - 8  # ceil(7 / 0,9) = 8


def test_cancelar_devuelve_lo_hecho():
    bd, ctx = _ctx_pequeno()
    vistos = []
    with _Simulado(7):
        r = dotacion.verificar_minimo(ctx, SEMANAS, 0.10, activos=5, cancelar=lambda: len(vistos) >= 2,
                                      progreso=lambda n, total: vistos.append(n))
    assert r["cancelado"] and r["minimo"] is None and len(r["pruebas"]) == 2


def test_sin_solucion_explica():
    """Review Focus 5: si ninguna cantidad de personas cumple, se explica en lugar de fallar."""
    bd, ctx = _ctx_pequeno()
    with _Simulado(None):
        r = dotacion.verificar_minimo(ctx, SEMANAS, 0.10, activos=5)
    assert r["minimo"] is None and r["con_margen"] is None and r["diferencia"] is None
    assert "Ninguna cantidad de personas" in r["motivo"]


def test_verificar_minimo_con_el_generador_real():
    bd, ctx = _ctx_pequeno()
    r = dotacion.verificar_minimo(ctx, SEMANAS, 0.0, activos=0, tiempo=4)
    assert 2 <= r["minimo"] <= 6 and r["pruebas"][-1][1] is True and r["con_margen"] == r["minimo"]


def test_alerta_si_un_puesto_obligatorio_queda_vacio():
    """Final review #1: hay gente de sobra por cabezas, pero nadie que pueda ocupar el puesto con demanda."""
    bd, ids = _bd({"A": [("LS", 360, 720, 1)], "B": []}, 1)
    p = bd.colaboradores()[0]
    p.puestos_permitidos = (ids["B"],)
    bd.guardar_colaborador(p)
    ctx = bd.contexto(2026)
    filas = puestos.asignar_tramos(ctx, {(p.id, LUN): "M"}, [LUN])
    al = puestos.alertas_reparto(ctx, filas, [LUN], bd.catalogo_puestos())
    assert [a.texto for a in al] == ["05/10: A sin cubrir 06:00–12:00 (falta 1)"]
    p.puestos_permitidos = None
    bd.guardar_colaborador(p)
    ctx = bd.contexto(2026)
    assert puestos.alertas_reparto(ctx, puestos.asignar_tramos(ctx, {(p.id, LUN): "M"}, [LUN]), [LUN], bd.catalogo_puestos()) == []


def test_el_puesto_de_menor_numero_se_cubre_primero():
    """Final review #2: si falta gente, queda vacío siempre el de mayor número, no uno distinto cada día."""
    bd, ids = _bd({"A": [("LS", 360, 720, 1)], "B": [("LS", 360, 720, 1)]}, 1)
    ctx = bd.contexto(2026)
    c = ctx.colabs[0].id
    filas = puestos.asignar_tramos(ctx, {(c, d): "M" for d in DIA}, DIA)
    assert {x.puesto_id for x in filas if x.puesto_id} == {ids["A"]}


def test_borrar_puesto_no_libera_a_quien_solo_podia_ese():
    """Final review #4: borrar el único puesto permitido no debe dejar a la persona con permiso para todos."""
    bd = db.BD()
    pid = bd.guardar_puesto(Puesto(0, 7, "Solo"))
    c = bd.guardar_colaborador(Colaborador(0, "A", puestos_permitidos=(pid,)))
    assert bd.borrar_puesto(pid) == "desactivado"
    assert next(x for x in bd.colaboradores() if x.id == c).puestos_permitidos == (pid,)


def test_noche_y_corrido_segun_el_horario():
    """Final review #5: noche = al menos 6 h entre las 18:00 y las 06:00; corrido = 10 h o más y no de noche."""
    assert demanda.es_noche(Turno("NC", "", 1080, 360)) and demanda.es_noche(Turno("X", "", 1200, 120))  # 20:00–02:00
    assert not demanda.es_noche(Turno("T2", "", 840, 1320))  # 14:00–22:00 solo tiene 4 h de noche
    assert demanda.es_corrido(Turno("C", "", 360, 1080))
    assert not demanda.es_corrido(Turno("M9", "", 540, 900)) and not demanda.es_corrido(Turno("NC", "", 1080, 360))
    assert not demanda.es_corrido(Turno("T2", "", 840, 1320))


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
