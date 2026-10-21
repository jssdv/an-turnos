from datetime import date, timedelta

import capacitacion
import db
import exportar
import flujo
import tempfile
import openpyxl
import puestos
import recargos
import reglas
import solver
from dominio import Colaborador, Novedad, Turno, festivos


def cuadro_vacio(bd):
    return bd.contexto(2026)


def test_festivos():
    f = festivos(2026)
    assert date(2026, 10, 12) in f and date(2026, 11, 2) in f and date(2026, 8, 17) in f
    assert date(2026, 4, 2) in f and date(2026, 4, 3) in f  # Semana Santa (Pascua 5-abr)
    assert date(2026, 5, 18) in f and date(2026, 6, 8) in f and date(2026, 6, 15) in f
    assert len(f) == 18


def test_turnos_y_pausas():
    t = Turno("C", "Corrido", 360, 1080)
    assert t.duracion == 720 and t.horas == 12
    t.pausas = ({"ini": 360, "min": 60, "pagada": False},)
    assert t.horas == 11
    t.pausas = ({"ini": 360, "min": 60, "pagada": True},)
    assert t.horas == 12
    assert Turno("NC", "", 1080, 360).duracion == 720


def test_recargos():
    bd = db.BD()
    ctx, tar = bd.contexto(2026), bd.tarifas()
    # NC dominical 18:00-06:00 (domingo 18-oct-2026): 1 h antes de las 19 ya es noche → 18:00 diurno hasta 19:00
    segs = list(recargos.segmentos(ctx.turnos["NC"], date(2026, 10, 18), ctx, tar))
    horas = lambda cond: sum((b - a).total_seconds() / 3600 for a, b, n, f in segs if cond(n, f))
    assert horas(lambda n, f: n) == 11 and horas(lambda n, f: not n) == 1
    assert horas(lambda n, f: f) == 6  # 18:00-24:00 domingo; el lunes de 0 a 6 es hábil
    # Tarifas por vigencia
    assert recargos.tarifa(tar, "dominical", date(2026, 6, 30)) == 80
    assert recargos.tarifa(tar, "dominical", date(2026, 7, 1)) == 90
    assert recargos.tarifa(tar, "dominical", date(2027, 7, 1)) == 100
    assert recargos.tarifa(tar, "noche_inicio", date(2025, 12, 24)) == 1260
    assert recargos.tarifa(tar, "noche_inicio", date(2025, 12, 25)) == 1140
    # Pausa no pagada de 60 min en C baja 12→11 h y esa hora no recibe recargo
    c = ctx.turnos["C"]
    c.pausas = ({"ini": 360, "min": 60, "pagada": False},)
    assert sum((b - a).total_seconds() / 3600 for a, b, n, f in recargos.segmentos(c, date(2026, 10, 20), ctx, tar)) == 11


def test_reporte_y_ventana():
    bd = db.BD()
    p = Colaborador(0, "A")
    p.id = bd.guardar_colaborador(p)
    ctx, tar = bd.contexto(2026), bd.tarifas()
    p = ctx.colabs[0]
    fechas = [date(2026, 10, 1) + timedelta(days=i) for i in range(21)]  # 3 semanas
    cuadro = {(p.id, f): "M" for f in fechas[:7]}  # 7 × 6 = 42 h
    r = recargos.reporte(ctx, tar, p, cuadro, fechas, 3)
    assert r["trabajadas"] == 42 and r["contratadas"] == 126 and r["pendientes"] == 84 and r["adicionales"] == 0
    cuadro = {(p.id, f): "C" for f in fechas[:11]}  # 132 h en 126 → 6 h extra
    r = recargos.reporte(ctx, tar, p, cuadro, fechas, 3)
    assert r["adicionales"] == 6 and r["cat"][("extra", "diurna", "hábil")] + r["cat"][("extra", "diurna", "festivo")] == 6
    # Novedad: 7 días de vacaciones bajan lo contratado en 42 h
    ctx2 = bd.contexto(2026)
    ctx2.novedades.append(Novedad(p.id, "Vacaciones", fechas[0], fechas[6]))
    ctx2.__post_init__()
    assert recargos.reporte(ctx2, tar, p, {}, fechas, 3)["contratadas"] == 84


def test_reglas():
    bd = db.BD()
    ids = [bd.guardar_colaborador(Colaborador(0, f"P{i}")) for i in range(2)]
    ctx = bd.contexto(2026)
    a, b = ctx.colabs
    lunes = date(2026, 10, 19)
    cuadro = {(a.id, lunes): "NC", (a.id, lunes + timedelta(days=1)): "M"}  # NC termina 6:00, M empieza 6:00
    al = reglas.validar(ctx, cuadro, [lunes, lunes + timedelta(days=1)])
    assert any("menos de 12 h" in x.texto for x in al)
    assert any("faltan" in x.texto for x in al)  # sin cobertura
    # Persona restringida y estudio
    r = Colaborador(0, "R", tipo="restringido", permitidos=("M", "T"), estudio=((0, "M"),))
    r.id = bd.guardar_colaborador(r)
    ctx = bd.contexto(2026)
    r = ctx.colabs[-1]
    assert ctx.bloqueo(r, ctx.turnos["NC"], lunes) == "turno no permitido"
    assert ctx.bloqueo(r, ctx.turnos["M"], lunes) == "estudio"
    assert ctx.bloqueo(r, ctx.turnos["T"], lunes) is None
    assert ctx.bloqueo(a, ctx.turnos["C"], date(2026, 10, 18)) == "turno no permitido en domingo/festivo"
    assert reglas.validar_catalogo(ctx.turnos)  # C y NC sin pausa → aviso


def test_versiones():
    bd = db.BD()
    pid = bd.guardar_colaborador(Colaborador(0, "A"))
    f = date(2026, 10, 5)
    bd.guardar_cuadro("2026-10", {(pid, f): "M"})
    bd.set_celda("2026-10", pid, f, "T")
    assert bd.asignaciones("2026-10", "original")[(pid, f)] == "M"
    assert bd.diferencias("2026-10") == [(pid, f, "M", "T")]
    bd.guardar_cuadro("2026-10", {(pid, f): "NC"})  # regenerar respeta la celda fija
    assert bd.asignaciones("2026-10")[(pid, f)] == "T"
    bd.restaurar("2026-10")
    assert bd.diferencias("2026-10") == []
    bd.set_celda("2026-10", pid, f, "C")
    bd.publicar("2026-10")
    assert bd.diferencias("2026-10") == []
    assert bd.turno_en_uso("C")
    bd.borrar_turno("C")
    assert "C" not in bd.turnos() and "C" in bd.turnos(solo_activos=False)
    # eliminar: sin historial se borra; con historial se desactiva
    nuevo = bd.guardar_colaborador(Colaborador(0, "Sin historia"))
    assert bd.borrar_colaborador(nuevo) == "borrado" and len(bd.colaboradores(solo_activos=False)) == 1
    assert bd.borrar_colaborador(pid) == "desactivado" and bd.colaboradores() == []
    bd.guardar_turno(Turno("X", "X", 0, 360))
    assert bd.borrar_turno("X") == "borrado" and "X" not in bd.turnos(solo_activos=False)


def test_mes_completo():
    """Octubre 2026: 13 personas (1 restringida, 2 estudiantes), novedades; el solver cumple todas las reglas."""
    bd = db.BD()
    for i in range(1, 14):
        p = Colaborador(0, f"P{i}")
        if i == 11:
            p.tipo, p.permitidos, p.puesto_fijo = "restringido", ("M", "T"), 3
        if i == 12:
            p.tipo, p.estudio = "estudiante", ((0, "M"), (3, "M"), (4, "M"), (1, "T"))
        if i == 13:
            p.tipo, p.estudio = "estudiante", ((3, "M"), (4, "M"), (4, "T"))
        bd.guardar_colaborador(p)
    fechas = [date(2026, 10, 1) + timedelta(days=i) for i in range(31)]
    bd.guardar_novedad(Novedad(3, "Vacaciones", date(2026, 10, 12), date(2026, 10, 18)))
    ctx = bd.contexto(2026)
    cuadro, info = solver.generar(ctx, fechas, tiempo=15)
    assert not info["faltan"] and not reglas.validar(ctx, cuadro, fechas)
    assert all((3, date(2026, 10, d)) not in cuadro for d in range(12, 19))
    assert all(cuadro.get((11, f), "M") in ("M", "T") for f in fechas)  # la restringida nunca hace noche
    noche = lambda p, f: cuadro.get((p, f)) == "NC"  # nunca más de 3 noches seguidas
    assert not any(all(noche(p.id, fechas[i + k]) for k in range(4)) for p in ctx.colabs for i in range(len(fechas) - 3))
    # una celda fija se respeta al regenerar
    c2, _ = solver.generar(ctx, fechas, fijos={(1, fechas[0]): "NC"}, tiempo=10)
    assert c2[(1, fechas[0])] == "NC"
    # puestos: la restringida siempre en el 3; sin repetir puesto en una misma franja
    filas = puestos.asignar(ctx, cuadro, fechas)
    assert all(p == 3 for f, fr, p, c, g in filas if c == 11)
    assert len({(f, fr, p) for f, fr, p, c, g in filas if p}) == len([1 for f, fr, p, c, g in filas if p])
    # capacitación: lunes, máx. 1 por semana, festivo corre al siguiente hábil (12-oct-2026 es festivo)
    ses, sin = capacitacion.programar(ctx, cuadro, fechas)
    dias = {f for f, _ in ses}
    assert date(2026, 10, 12) not in dias and all(f.weekday() in (0, 1) for f in dias)
    assert len({f - timedelta(days=f.weekday()) for f in dias}) == len(dias)
    assert len(ses) + len(sin) == 13
    # exportación: tres libros, el cuadro marca en amarillo lo cambiado y nunca sobrescribe
    bd.guardar_cuadro("2026-10", cuadro)
    bd.set_celda("2026-10", 1, fechas[0], "NC")
    cam = bd.asignaciones("2026-10")
    with tempfile.TemporaryDirectory() as tmp:
        r1 = exportar.exportar_cuadro(tmp, "Octubre 2026", ctx, cam, bd.asignaciones("2026-10", "original"), fechas,
                                      bd.diferencias("2026-10"))
        assert exportar.exportar_cuadro(tmp, "Octubre 2026", ctx, cam, cam, fechas, []).name.endswith("v2.xlsx")
        exportar.exportar_puestos(tmp, "Octubre 2026", ctx, cam, fechas, filas, ses)
        r3 = exportar.exportar_horas(tmp, "Octubre 2026", ctx, bd.tarifas(), cam, fechas, 3)
        wb = openpyxl.load_workbook(r1)
        assert wb.sheetnames == ["Cuadro", "Original", "Cambios"]
        assert wb["Cuadro"].cell(2, 2).fill.fgColor.rgb.endswith("FFFF00") or bd.asignaciones("2026-10", "original").get((1, fechas[0])) == "NC"
        assert openpyxl.load_workbook(r3)["Horas y recargos"].max_row == 14


def test_flujo_y_estudio():
    from dominio import texto_estudio
    assert texto_estudio(((0, "M"), (1, "T"), (3, "M"), (4, "M"), (4, "T"))) == "Lun M, Mar T, Jue M, Vie"
    bd = db.BD()
    for i in range(13):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    info = flujo.generar(bd, 2026, 10, tiempo=8)
    assert not info["faltan"] and bd.diferencias("2026-10") == [] and bd.puestos("2026-10") and bd.capacitacion("2026-10")
    # edición manual → aparece como diferencia; «respetar» la conserva y no toca original
    cambios = bd.asignaciones("2026-10")
    f = date(2026, 10, 7)
    bd.set_celda("2026-10", 1, f, "L")
    flujo.generar(bd, 2026, 10, "respetar", tiempo=8)
    assert bd.asignaciones("2026-10").get((1, f), "L") == "L"  # regenerar todo el mes sí puede mover otras celdas (por eso existe «semana»)
    # novedad sobrevenida + regenerar solo esa semana: nada fuera de la semana cambia
    bd.guardar_novedad(Novedad(2, "Incapacidad", date(2026, 10, 14), date(2026, 10, 16)))
    antes = bd.asignaciones("2026-10")
    flujo.generar(bd, 2026, 10, "semana", lunes=date(2026, 10, 12), tiempo=8)
    despues = bd.asignaciones("2026-10")
    fuera = lambda d: not date(2026, 10, 12) <= d <= date(2026, 10, 18)
    assert {k: v for k, v in antes.items() if fuera(k[1])} == {k: v for k, v in despues.items() if fuera(k[1])}
    assert all((2, date(2026, 10, d)) not in despues for d in (14, 15, 16))


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
