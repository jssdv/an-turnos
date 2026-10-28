import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de las solicitudes personales (datos, solver como deseo blando, evaluación). Imprime OK."""
import tempfile
from datetime import date

from datetime import timedelta

from an.turnos import db, reglas, solicitudes, solver
from an.turnos.dominio import Colaborador, Novedad, Solicitud

F = [date(2026, 10, 5) + timedelta(days=i) for i in range(14)]  # lunes 5 a domingo 18


def test_esquema_v7():
    bd = db.BD()
    if bd.es_postgres():  # PRAGMA es de SQLite
        return
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 8
    cols = [r["name"] for r in bd.c.execute("PRAGMA table_info(solicitud)")]
    assert cols == ["id", "servicio", "colab_id", "tipo", "desde", "hasta", "turno", "prioridad", "nota", "registrado_en", "usuario"]


def test_migra_v6_a_v7():
    ruta = tempfile.mkdtemp() + "/t.db"
    bd = db.BD(ruta)
    bd.c.execute("DROP TABLE solicitud")
    bd.c.execute("PRAGMA user_version = 6")
    bd.c.commit()
    bd.c.close()
    bd = db.BD(ruta)
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 8
    assert bd.c.execute("SELECT count(*) FROM solicitud").fetchone()[0] == 0


def test_crud():
    bd = db.BD()
    pid = bd.guardar_colaborador(Colaborador(0, "Ana"))
    s = Solicitud(pid, "quiero", date(2026, 10, 14), date(2026, 10, 16), "T", "alta", "cita")
    bd.guardar_solicitud(s, "coord")
    assert s.id and bd.solicitudes() == [s]
    assert bd.contexto(2026).solicitudes == [s]
    assert bd.borrar_colaborador(pid) == "desactivado"
    bd.borrar_solicitud(s.id)
    assert bd.solicitudes() == []


def equipo(n=17):
    bd = db.BD()
    for i in range(n):
        bd.guardar_colaborador(Colaborador(0, f"P{i + 1}"))
    return bd


def trabaja(cuadro, pid, d):
    return cuadro.get((pid, d), "L")


def test_solver_cumple_libre_evitar_y_quiero():
    bd = equipo()
    bd.guardar_solicitud(Solicitud(1, "libre", F[2], F[2]))
    bd.guardar_solicitud(Solicitud(2, "evitar", F[3], F[3], "NC"))
    bd.guardar_solicitud(Solicitud(3, "quiero", F[7], F[11], "T", "alta"))
    ctx = bd.contexto(2026)
    cuadro, _ = solver.generar(ctx, F, tiempo=20)
    assert trabaja(cuadro, 1, F[2]) == "L" and trabaja(cuadro, 2, F[3]) != "NC"
    assert all(trabaja(cuadro, 3, d) in ("L", "T") for d in F[7:12])
    assert all(r.estado == "cumplida" for r in solicitudes.evaluar(ctx, cuadro, F)), solicitudes.evaluar(ctx, cuadro, F)


def test_libre_imposible_cede_y_se_informa():
    bd = db.BD()
    id3 = next(i for i, q in bd.catalogo_puestos().items() if q.numero == 3)
    solo = Colaborador(0, "Sola")
    solo.tipo, solo.permitidos, solo.puestos_permitidos = "restringido", ("M", "T"), (id3,)
    bd.guardar_colaborador(solo)
    for i in range(6):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    bd.guardar_solicitud(Solicitud(1, "libre", F[0], F[6], "", "alta"))  # una semana entera libre
    ctx = bd.contexto(2026)
    cuadro, _ = solver.generar(ctx, F, tiempo=10)  # no lanza
    r = solicitudes.evaluar(ctx, cuadro, F)[0]
    assert r.estado in ("parcial", "no cumplida") and r.motivo


def test_alta_gana_a_normal():
    bd = db.BD()
    for i in range(2):
        bd.guardar_colaborador(Colaborador(0, f"P{i + 1}"))
    bd.guardar_solicitud(Solicitud(1, "libre", F[0], F[13], "", "normal"))
    bd.guardar_solicitud(Solicitud(2, "libre", F[0], F[13], "", "alta"))
    ctx = bd.contexto(2026)
    cuadro, _ = solver.generar(ctx, F, tiempo=20)
    dias = lambda pid: sum(trabaja(cuadro, pid, d) != "L" for d in F)
    assert dias(2) <= dias(1)


def test_inactivo_con_solicitud_no_rompe():
    bd = equipo(8)
    bd.guardar_solicitud(Solicitud(1, "libre", F[0], F[0]))
    bd.c.execute("UPDATE colaborador SET activo=0 WHERE id=1")
    ctx = bd.contexto(2026)
    solver.generar(ctx, F, tiempo=10)


def test_evaluar_motivos():
    bd = equipo(3)
    bd.guardar_colaborador(Colaborador(0, "Restr", permitidos=("M",)))
    ctx = bd.contexto(2026)
    ctx.novedades.append(Novedad(1, "Vacaciones", F[0], F[0]))
    ctx._nov[(1, F[0])] = ctx.novedades[0]
    quiero = Solicitud(4, "quiero", F[1], F[1], "T")
    sols = [Solicitud(1, "libre", F[0], F[0]), Solicitud(2, "libre", F[3], F[3]), Solicitud(3, "libre", F[5], F[5]),
            quiero, Solicitud(2, "libre", F[12], F[13] + timedelta(days=7)), Solicitud(3, "evitar", date(2027, 1, 1), date(2027, 1, 2), "M")]
    ctx.solicitudes = sols
    cuadro = {(1, F[0]): "M", (2, F[3]): "M", (3, F[4]): "NC", (3, F[5]): "M", (4, F[1]): "M", (2, F[12]): "M"}
    r = solicitudes.evaluar(ctx, cuadro, F, fijos={(2, F[3])})
    assert [x.estado for x in r] == ["no cumplida"] * 4 + ["parcial", "fuera"]
    assert r[0].motivo == "tiene novedad" and r[1].motivo == "edición manual"
    assert r[2].motivo == "libre obligatorio tras noche" and r[3].motivo == "turno no permitido"
    assert r[4].dias_fallidos == [F[12]]  # solo cuentan los días dentro del periodo


def test_evaluar_parcial():
    bd = equipo(2)
    ctx = bd.contexto(2026)
    ctx.solicitudes = [Solicitud(1, "libre", F[0], F[1])]
    r = solicitudes.evaluar(ctx, {(1, F[0]): "M"}, F)[0]
    assert r.estado == "parcial" and r.dias_fallidos == [F[0]]


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
