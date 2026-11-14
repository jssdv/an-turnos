import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Exportes nuevos: banco de horas en Excel y agenda .ics por persona."""
from datetime import date

import openpyxl

from an.turnos import exportar


def test_banco_dos_hojas(tmp_path):
    filas = [{"id": 1, "nombre": "Ana", "anterior": 4.0, "periodo": -2.5, "total": 1.5, "cerrado": False}]
    movs = [(9, 1, date(2026, 10, 3), 4.0, "Ajuste", "")]
    r = exportar.exportar_banco(tmp_path, "octubre 2026", filas, movs, {1: "Ana"})
    wb = openpyxl.load_workbook(r)
    assert r.name == "BANCO DE HORAS OCTUBRE 2026.xlsx"
    assert [c.value for c in wb["Saldos"][2]] == ["Ana", 4.0, -2.5, 1.5, "Proyectado"]
    assert [c.value for c in wb["Movimientos"][2]] == ["03/10/2026", "Ana", 4.0, "Ajuste", None]


def test_banco_vacio(tmp_path):
    wb = openpyxl.load_workbook(exportar.exportar_banco(tmp_path, "octubre 2026", [], [], {}))
    assert wb.sheetnames == ["Saldos", "Movimientos"]
    assert wb["Movimientos"].max_row == 1


def test_eventos_persona_omite_libres():
    from datetime import datetime
    from types import SimpleNamespace as NS
    from an.turnos.dominio import Turno
    ctx = NS(turnos={"M": Turno("M", "Mañana", 7 * 60, 13 * 60), "N": Turno("N", "Noche", 19 * 60, 7 * 60)})
    d1, d2, d3 = date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7)
    cuadro = {(1, d1): "M", (1, d2): "L", (1, d3): "N", (2, d1): "M"}
    assert exportar.eventos_persona(ctx, cuadro, 1, [d1, d2, d3]) == [
        (datetime(2026, 10, 5, 7), datetime(2026, 10, 5, 13), "M · Mañana"),
        (datetime(2026, 10, 7, 19), datetime(2026, 10, 8, 7), "N · Noche")]


def test_ics_vacio_es_valido():
    from an.radiologia import analisis
    t = analisis.ics("Ana", [])
    assert t.startswith("BEGIN:VCALENDAR") and "VEVENT" not in t and t.rstrip().endswith("END:VCALENDAR")
