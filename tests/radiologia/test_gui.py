"""Ventana de Radiología dentro del shell de An, sin pantalla. Imprime OK."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAIZ))
from PySide6.QtCore import QSettings, Qt

tmp = tempfile.mkdtemp()
QSettings.setDefaultFormat(QSettings.IniFormat)  # no tocar los ajustes reales del usuario
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tmp)

from an.nucleo.shell import Ventana
from an.nucleo.tema import preparar_app
from an.radiologia.paginas import SECCIONES, Planilla

app = preparar_app([])
v = Ventana(Planilla)
assert v.windowTitle() == "An · Radiología"
assert v.nav.count() == len(SECCIONES) and v.paginas.count() == len(SECCIONES)
assert v.pila.currentWidget() is v.area.vacia  # sin cuadro cargado se ve la pantalla de arrastrar

ruta = RAIZ / "ejemplos" / "radiologia" / "Cuadro Octubre 2026 (prueba con fechas).xlsx"
v.area.cargar(str(ruta))
assert v.area.ws is not None and v.area.combo.count() > 0
assert v.pila.currentWidget() is v.principal
assert v.cfg.value("radiologia/ultimo_archivo") == str(ruta)
for i in range(len(SECCIONES)):  # recorrer todas las secciones, incluida la vista previa perezosa
    v.ir_a(i)
    assert v.paginas.currentIndex() == i
assert v.area.previa.count() > 0
assert v.area.t_cob.rowCount() > 0 and v.area.t_equidad.rowCount() > 0
v.contar(2, 3, "warn")
assert v.nav.item(2).data(Qt.UserRole) == (3, "warn")
v.contar(2, 0)
assert v.nav.item(2).data(Qt.UserRole) is None
v.avisar("hola", "warn")
assert not v.aviso.isHidden() and v.aviso.property("nivel") == "warn"
v.avisar("")
assert v.aviso.isHidden()
v.close()
print("OK")
