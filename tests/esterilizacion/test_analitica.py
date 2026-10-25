import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de las métricas del dashboard de analíticas (solo lectura). Imprime OK."""
from datetime import date

from an.esterilizacion import analitica, cambios, db
from an.esterilizacion.dominio import Colaborador, Novedad

I, F = date(2026, 10, 1), date(2026, 10, 31)


def nuevo():
    bd = db.BD()
    for n, t in (("A", "regular"), ("B", "regular"), ("C", "regular"), ("R", "refuerzo")):
        bd.guardar_colaborador(Colaborador(None, n, t))
    ids = {p.nombre: p.id for p in bd.colaboradores()}
    return bd, ids


def test_ausentismo_recorta_y_no_duplica():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Vacaciones", date(2026, 9, 28), date(2026, 10, 3)))
    bd.guardar_novedad(Novedad(i["A"], "Licencia", date(2026, 10, 2), date(2026, 10, 5)))
    r = analitica.ausentismo(bd, I, F)
    assert r["por_persona"]["A"] == {"Vacaciones": 3, "Licencia": 2}, r
    assert r["por_tipo"] == {"Vacaciones": 3, "Licencia": 2}
    assert r["por_mes"]["2026-10"] == {"Vacaciones": 3, "Licencia": 2}
    assert abs(r["pct"] - 5 / (31 * 3) * 100) < 1e-6, r["pct"]


def test_ausentismo_ignora_refuerzo_e_inactivo():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["R"], "Vacaciones", I, F))
    c = next(p for p in bd.colaboradores() if p.nombre == "C")
    c.activo = False
    bd.guardar_colaborador(c)
    bd.guardar_novedad(Novedad(i["C"], "Licencia", I, F))
    assert analitica.ausentismo(bd, I, F)["por_tipo"] == {}


def test_ausentismo_vacio():
    bd, _ = nuevo()
    r = analitica.ausentismo(bd, I, F)
    assert r["por_tipo"] == {} and r["pct"] == 0
    assert analitica.ausentismo(db.BD(), I, F)["pct"] == 0  # sin personas


def test_simultaneos_maximo_y_riesgo():
    bd, i = nuevo()
    d5, d6 = date(2026, 10, 5), date(2026, 10, 6)
    bd.guardar_novedad(Novedad(i["A"], "Vacaciones", d5, d5))
    bd.guardar_novedad(Novedad(i["B"], "Incapacidad", d5, d5))
    r = analitica.simultaneos(bd, I, F)
    assert r["maximo"] == 2 and r["fecha_maximo"] == d5 and len(r["serie"]) == 31 and r["dias_riesgo"] == []
    bd.guardar_cuadro("2026-10-01/2026-10-31", {(i["C"], d5): "M", (i["C"], d6): "M"})  # casi nadie: hay déficit
    r = analitica.simultaneos(bd, I, F)
    assert d5 in r["dias_riesgo"] and d6 not in r["dias_riesgo"], r["dias_riesgo"]  # d6: déficit pero sin ausentes
    assert analitica.simultaneos(db.BD(), I, F)["fecha_maximo"] is None

K2 = "2026-10-05/2026-10-11"


def test_cobertura_deficit_y_exceso():
    bd, i = nuevo()
    d5 = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i["A"], d5): "M"})  # casi nadie: déficit
    r = analitica.cobertura(bd, I, F)
    assert len(r) == 1 and r[0]["periodo"] == K2 and r[0]["dias_deficit"] >= 1, r
    assert analitica.cobertura(bd, date(2026, 11, 1), date(2026, 11, 30)) == []  # fuera del rango


def test_cobertura_exceso():
    bd, i = nuevo()
    d = date(2026, 10, 6)
    for dm in bd.demandas():  # sin demanda alguna, cualquier turno es exceso
        bd.c.execute("DELETE FROM demanda WHERE id=?", (dm.id,))
    bd.guardar_cuadro(K2, {(i["A"], d): "M"})
    r = analitica.cobertura(bd, I, F)[0]
    assert r["dias_exceso"] == 1 and r["dias_deficit"] == 0, r


def test_cobertura_sin_cuadro():
    assert analitica.cobertura(nuevo()[0], I, F) == []


def test_cambios_resumen_excluye_anulados():
    bd, i = nuevo()
    d5, d6 = date(2026, 10, 5), date(2026, 10, 6)
    bd.guardar_cuadro(K2, {(i["A"], d5): "M", (i["B"], d5): "T", (i["A"], d6): "L"})
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "pedido", "u")
    [aj] = cambios.ajuste(bd, K2, [(i["A"], d6, "M")], "x", "u")
    cambios.anular(bd, aj, "u")
    r = analitica.cambios_resumen(bd, I, F)
    assert r == {K2: {"permuta": 1, "servicio": 0, "ajuste": 0, "excepciones": 0}}, r
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "otra", "u")
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "tercera", "u", excepcion=True)
    r = analitica.cambios_resumen(bd, I, F)[K2]
    assert r["permuta"] == 3 and r["excepciones"] == 1, r


def test_cambios_sin_filas():
    assert analitica.cambios_resumen(nuevo()[0], I, F) == {}


def _cuadro_octubre(bd, i):
    """A: corrido los primeros 14 días de octubre; B: noche corrida los días 5, 6, 11 y 12."""
    c = {(i["A"], date(2026, 10, d)): "C" for d in range(1, 15)}
    c.update({(i["B"], date(2026, 10, d)): "NC" for d in (5, 6, 11, 12)})
    bd.guardar_cuadro("2026-10-01/2026-10-31", c)


def test_horas_extra_mes_vs_semanas():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    [r] = analitica.horas_extra(bd, I, F)
    assert r["periodo"] == "2026-10-01/2026-10-31" and r["ventana"] == 3, r
    assert r["semanas"] == {"diurna": 42.0, "nocturna": 0.0}, r  # 168 h contra 126 contratadas en la 1.ª ventana
    assert r["mes"] == {"diurna": 0.0, "nocturna": 0.0}, r  # 168 h contra 186 del mes completo
    assert analitica.horas_extra(bd, date(2026, 12, 1), date(2026, 12, 31)) == []


def test_recargos_resumen():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    r = analitica.recargos_resumen(bd, I, F)
    assert r["A"]["festivo"] == 36.0 and r["A"]["nocturna"] == 0.0, r["A"]  # domingos 4 y 11 y festivo del 12
    assert r["B"]["nocturna"] == 44.0 and r["B"]["festivo"] > 0, r["B"]  # 4 noches de 11 h desde las 19:00
    assert r["A"]["equivalentes"] > 0 and set(r) == {"A", "B", "C"}


def test_equidad():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    r = analitica.equidad(bd, I, F)
    assert r["por_persona"]["A"] == {"noches": 0, "domingos": 2, "festivos": 1}, r
    assert r["por_persona"]["B"] == {"noches": 4, "domingos": 1, "festivos": 1}, r
    assert r["dispersion"] == {"noches": 4, "domingos": 2, "festivos": 1}, r
    assert analitica.equidad(bd, date(2026, 12, 1), date(2026, 12, 31))["dispersion"] == {"noches": 0, "domingos": 0, "festivos": 0}


def test_banco():
    bd, i = nuevo()
    bd.cerrar_periodo("2026-10-01/2026-10-31", [(i["A"], 100, 110), (i["B"], 100, 94)])
    bd.cerrar_periodo("2026-09-01/2026-09-30", [(i["A"], 100, 105)])  # anterior al rango: entra en el acumulado
    bd.agregar_movimiento(i["A"], date(2026, 11, 2), -4, "Pagado en nómina")
    r = analitica.banco(bd, I, date(2026, 11, 30))
    assert r["saldos"] == {"A": 11.0, "B": -6.0, "C": 0.0}, r["saldos"]
    assert r["serie"] == [("10/26", 15.0, 6.0), ("11/26", 11.0, 6.0)], r["serie"]
    assert analitica.banco(db.BD(), I, F)["serie"] == [("10/26", 0.0, 0.0)]


for t in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
    t()
print("OK")
