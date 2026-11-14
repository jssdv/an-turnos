import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""¿Quién cubre?: candidatos para un turno sin cubrir, que cumplen las reglas, ordenados por carga."""
from datetime import date, timedelta

from an.turnos import cubrir, db
from an.turnos.dominio import Colaborador, Novedad

DIAS = [date(2026, 10, 5) + timedelta(i) for i in range(7)]  # lunes 5 a domingo 11
D = DIAS[2]  # miércoles 7


def armar(*nombres, novedades=()):
    bd = db.BD()
    ids = {n: bd.guardar_colaborador(Colaborador(0, n)) for n in nombres}
    for n, tipo in novedades:
        bd.guardar_novedad(Novedad(ids[n], tipo, D, D))
    return bd.contexto(2026), ids


def nombres(lista):
    return [c["nombre"] for c in lista]


def test_descarta_novedad_y_ocupados():
    ctx, i = armar("Ana", "Beto", "Carla", novedades=[("Ana", "Vacaciones")])
    cuadro = {(i["Beto"], D): "T"}
    assert nombres(cubrir.candidatos(ctx, cuadro, DIAS, D, "M")) == ["Carla"]


def test_descarta_descanso_12h():
    ctx, i = armar("Carla")
    cuadro = {(i["Carla"], D - timedelta(1)): "NC"}  # la noche termina a las 06:00 y la M empieza a las 06:00
    assert cubrir.candidatos(ctx, cuadro, DIAS, D, "M") == []


def test_ordena_por_menos_horas_y_trae_datos():
    ctx, i = armar("Dani", "Eva")
    cuadro = {(i["Dani"], DIAS[0]): "T", (i["Dani"], DIAS[1]): "T", (i["Dani"], DIAS[4]): "M", (i["Eva"], DIAS[0]): "T"}
    out = cubrir.candidatos(ctx, cuadro, DIAS, D, "M")
    assert nombres(out) == ["Eva", "Dani"]
    assert (out[0]["minutos"], out[0]["turnos_iguales"]) == (360, 0)
    assert (out[1]["minutos"], out[1]["turnos_iguales"]) == (1080, 1)


def test_limite():
    ctx, _ = armar(*[f"P{k}" for k in range(8)])
    assert len(cubrir.candidatos(ctx, {}, DIAS, D, "M")) == 5
    assert len(cubrir.candidatos(ctx, {}, DIAS, D, "M", limite=2)) == 2


def test_turno_desconocido():
    ctx, _ = armar("Ana")
    try:
        cubrir.candidatos(ctx, {}, DIAS, D, "ZZ")
    except ValueError as e:
        assert "ZZ" in str(e)
    else:
        raise AssertionError("no lanzó ValueError")


def test_turno_inactivo_no_cuenta_como_libre():
    ctx, i = armar("Ana")
    assert cubrir.candidatos(ctx, {(i["Ana"], D): "VIEJO"}, DIAS, D, "M") == []  # código fuera del catálogo activo
