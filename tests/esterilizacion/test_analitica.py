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


for t in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
    t()
print("OK")
