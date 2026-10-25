"""Base SQLite sintética de 3 meses (ago–oct 2026) para probar an.web.migrar. Sin datos reales."""
from datetime import date

from an.turnos import cambios, db, flujo
from an.turnos.dominio import Colaborador, Novedad, Solicitud

MESES = ((2026, 8), (2026, 9), (2026, 10))
CODIGOS = ("M", "T", "N", "L")


def crear_sintetica(ruta):
    """7 personas (la tercera se borra: hueco en los ids; una de refuerzo), cuadro (i + día) % 4 en ambas versiones, novedades,
    solicitudes, en octubre una permuta, un cambio de servicio, un ajuste y una anulación, y agosto/septiembre cerrados con banco."""
    bd = db.BD(ruta)
    for i in range(1, 8):
        bd.guardar_colaborador(Colaborador(None, f"Persona {i}", "refuerzo" if i == 7 else "regular"))
    bd.borrar_colaborador(3)
    ids = [p.id for p in bd.colaboradores()]
    for año, mes in MESES:
        ini, fin = flujo.periodo_mes(año, mes)
        dias = flujo.fechas(ini, fin)
        cuadro = {(cid, d): CODIGOS[(n + d.day) % 4] for n, cid in enumerate(ids) for d in dias}
        bd.guardar_cuadro(flujo.clave(ini, fin), cuadro)
        flujo.recalcular(bd, ini, fin)
    bd.guardar_novedad(Novedad(ids[0], "Vacaciones", date(2026, 9, 28), date(2026, 10, 3)))
    bd.guardar_novedad(Novedad(ids[1], "Licencia", date(2026, 10, 12), date(2026, 10, 14)))
    bd.guardar_novedad(Novedad(ids[2], "Incapacidad", date(2026, 8, 3), date(2026, 8, 5), "x"))
    bd.guardar_solicitud(Solicitud(ids[0], "libre", date(2026, 10, 9), date(2026, 10, 9)), "coord")
    bd.guardar_solicitud(Solicitud(ids[1], "quiero", date(2026, 10, 10), date(2026, 10, 11), "T", "alta"), "coord")
    bd.guardar_solicitud(Solicitud(ids[2], "evitar", date(2026, 9, 30), date(2026, 10, 2), "N"), "coord")
    k = "2026-10-01/2026-10-31"
    a, b, c = ids[:3]
    cambios.permuta(bd, k, a, date(2026, 10, 5), b, date(2026, 10, 5), "pedido", "coord")
    cambios.servicio(bd, k, [(a, date(2026, 10, 6), "M")], "necesidad", "coord")
    [aj] = cambios.ajuste(bd, k, [(c, date(2026, 10, 7), "N")], "ajuste", "coord")
    cambios.ajuste(bd, k, [(c, date(2026, 10, 8), "T")], "otro", "coord")
    cambios.anular(bd, aj, "coord")
    for año, mes in MESES[:2]:
        flujo.cerrar(bd, *flujo.periodo_mes(año, mes))
    bd.agregar_movimiento(a, date(2026, 9, 30), 4.5, "Saldo inicial")
    bd.agregar_movimiento(b, date(2026, 10, 15), -2.0, "Pagado en nómina", "n")
    bd.cerrar()
    return ids
