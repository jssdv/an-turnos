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
