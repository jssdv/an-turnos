import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Un nombre que empieza por «=» sale como texto en el Excel exportado, no como fórmula."""
from datetime import date, timedelta
from types import SimpleNamespace as NS

from openpyxl import Workbook

from an.turnos import exportar


def test_nombre_hostil_sale_como_texto():
    hostil = '=HYPERLINK("https://x","Ver")'
    ctx = NS(colabs=[NS(id=1, nombre=hostil, en_solver=True)], turnos={}, tipo_dia=lambda f: "DL", novedad=lambda i, f: None, demandas=[], festivos=set())
    ws = Workbook().active
    exportar._hoja_cuadro(ws, ctx, {}, [date(2026, 10, 5) + timedelta(i) for i in range(3)])
    assert ws["A2"].value == hostil and ws["A2"].data_type == "s"


if __name__ == "__main__":
    test_nombre_hostil_sale_como_texto()
    print("OK")
