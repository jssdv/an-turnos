import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""flujo.preparar en modo «desde»: lo anterior a la fecha queda fijo al cuadro actual y las celdas manuales posteriores
se conservan. Imprime OK."""
from datetime import date, timedelta

from an.turnos import db, flujo
from an.turnos.dominio import Colaborador

INI, FIN, DESDE = date(2026, 10, 1), date(2026, 10, 7), date(2026, 10, 4)


def bd_con_cuadro():
    bd = db.BD()
    ids = []
    for i in range(2):
        p = Colaborador(0, f"P{i}")
        bd.guardar_colaborador(p)
        ids.append(p.id)
    k = flujo.clave(INI, FIN)
    cuadro = {(c, INI + timedelta(days=i)): "M" for c in ids for i in range(7)}
    bd.guardar_cuadro(k, cuadro, versiones=("cambios",))
    bd.set_celda(k, ids[0], DESDE + timedelta(days=1), "T")  # manual posterior a `desde`
    return bd, ids, k


def test_desde_fija_lo_anterior_y_conserva_manuales():
    bd, ids, k = bd_con_cuadro()
    actual = bd.asignaciones(k)
    _, dias, kw = flujo.preparar(bd, INI, FIN, "desde", desde=DESDE)
    fijos = kw["fijos"]
    for (c, d), t in actual.items():
        if d < DESDE:
            assert fijos[c, d] == t, (c, d)  # antes de `desde`: el cuadro actual
    assert fijos[ids[0], DESDE + timedelta(days=1)] == "T"  # manual posterior, fijo=1
    assert (ids[1], DESDE + timedelta(days=1)) not in fijos  # celda sin manual en la ventana: libre


def test_desde_respeta_racha_de_noches_con_dias_fijos_antes_del_corte():
    # NC fijas el día 0 y el 2 (NC-L-NC-L…): con max_noches=2 el día 4 no puede ser NC, aunque esté en la ventana
    bd = db.BD()
    p = Colaborador(0, "P0")
    bd.guardar_colaborador(p)
    k = flujo.clave(INI, FIN)
    bd.guardar_cuadro(k, {(p.id, INI): "NC", (p.id, INI + timedelta(days=2)): "NC"}, versiones=("cambios",))
    flujo.generar(bd, INI, FIN, "desde", desde=INI + timedelta(days=3), tiempo=10)
    assert bd.asignaciones(k).get((p.id, INI + timedelta(days=4))) != "NC"


if __name__ == "__main__":
    test_desde_fija_lo_anterior_y_conserva_manuales()
    test_desde_respeta_racha_de_noches_con_dias_fijos_antes_del_corte()
    print("OK")
