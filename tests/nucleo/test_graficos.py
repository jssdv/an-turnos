"""Gráficos del núcleo: pintan con datos y sin datos. Imprime OK."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import QSettings

QSettings.setDefaultFormat(QSettings.IniFormat)
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())

from an.nucleo.graficos import Barras, Linea
from an.nucleo.tema import preparar_app

qa = preparar_app([])
datos = [("Sep", {"Vacaciones": 3, "Licencia": 1}), ("Oct", {"Vacaciones": 0, "Licencia": 2})]
for kw in ({}, {"horizontal": True}, {"apilado": True}, {"horizontal": True, "apilado": True}):
    b = Barras(**kw)
    b.poner([])
    assert b.vacio
    b.poner([("Oct", {"x": 0})])
    assert b.vacio  # todo cero = sin datos
    b.poner(datos)
    assert not b.vacio
    b.resize(400, 220)
    assert not b.grab().isNull()
l = Linea()
l.poner([])
assert l.vacio
l.poner([("1", 0), ("2", 3), ("3", 1)])
assert not l.vacio
l.resize(400, 200)
assert not l.grab().isNull()
l.poner([("1", 0)])
assert l.vacio
print("OK")
