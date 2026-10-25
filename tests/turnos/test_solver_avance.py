import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""solver.generar con progreso (`al_avance`) y cancelación (`detener`). Imprime OK."""
import threading
import time
from datetime import date

from an.turnos import db, flujo, solver
from an.turnos.dominio import Colaborador


def preparar(n, inicio=date(2026, 10, 5), fin=date(2026, 10, 18)):
    bd = db.BD()
    for i in range(n):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    ctx, dias, kw = flujo.preparar(bd, inicio, fin)
    return ctx, dias, kw


def test_al_avance_recibe_soluciones():
    ctx, dias, kw = preparar(13)
    lista = []
    solver.generar(ctx, dias, **{**kw, "tiempo": 10}, al_avance=lista.append)
    assert len(lista) >= 1
    assert all(set(d) == {"soluciones", "objetivo", "cota", "segundos", "limite"} for d in lista)
    assert lista[-1]["soluciones"] == len(lista) and lista[0]["limite"] == 10
    assert lista[-1]["objetivo"] <= lista[0]["objetivo"]


def test_detener_antes_de_empezar():
    ctx, dias, kw = preparar(13)
    ev = threading.Event()
    ev.set()
    for fijos in ({}, {(1, dias[0]): "M"}):
        t0 = time.time()
        try:
            solver.generar(ctx, dias, **{**kw, "fijos": fijos}, detener=ev)
            assert False, "debía cancelarse"
        except solver.ErrorSolver as e:
            assert "cancelad" in str(e) and "fijas" not in str(e)  # sin segundo intento ni el mensaje de las celdas fijas
        assert time.time() - t0 < 2


def test_detener_durante_la_busqueda():
    ctx, dias, kw = preparar(13)
    ev = threading.Event()
    threading.Timer(1.5, ev.set).start()
    t0 = time.time()
    try:
        solver.generar(ctx, dias, **{**kw, "tiempo": 60}, detener=ev)
        assert False, "una búsqueda cortada se descarta"
    except solver.ErrorSolver as e:
        assert "cancelad" in str(e)
    assert ev.is_set() and time.time() - t0 < 8


def test_workers_por_entorno():
    previo = os.environ.get("AN_SOLVER_WORKERS")
    os.environ["AN_SOLVER_WORKERS"] = "1"
    try:
        ctx, dias, kw = preparar(5, fin=date(2026, 10, 11))
        a = solver.generar(ctx, dias, **{**kw, "tiempo": 30})
        b = solver.generar(ctx, dias, **{**kw, "tiempo": 30})
        assert a[0] == b[0]
    finally:
        if previo is None:
            del os.environ["AN_SOLVER_WORKERS"]
        else:
            os.environ["AN_SOLVER_WORKERS"] = previo


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
