import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""peso_corrido: un costo mayor por corrido no genera más C que sin costo. Imprime OK."""
from datetime import date

from an.turnos import db, solver
from an.turnos.dominio import Colaborador
from test_solver_avance import preparar


def _corridos(peso):
    ctx, dias, kw = preparar(13)
    ctx.peso_corrido = peso
    cuadro, _ = solver.generar(ctx, dias, **{**kw, "tiempo": 10})
    return sum(1 for cod in cuadro.values() if cod == "C")


def test_peso_corrido_no_aumenta_los_corridos():
    assert _corridos(10) <= _corridos(0)


def test_peso_corrido_en_parametros():
    bd = db.BD()
    assert bd.contexto(2026).peso_corrido == 1
    bd.set_param("peso_corrido", 4)
    assert bd.contexto(2026).peso_corrido == 4


if __name__ == "__main__":
    test_peso_corrido_en_parametros(); test_peso_corrido_no_aumenta_los_corridos(); print("OK")
