# Prueba de la ventana sin pantalla: crear, editar y eliminar colaboradores y turnos.
import sys, os, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTime
import app
qa = QApplication([]); qa.setStyleSheet(app.ESTILO)
QMessageBox.question = staticmethod(lambda *a, **k: QMessageBox.Yes)  # confirmar diálogos
v = app.Ventana(tempfile.mkdtemp() + "/t.db")
# --- colaboradores: crear, editar, eliminar
v._nueva_persona(); v.p_nombre.setText("Ana"); v.p_perm_cbs["NC"].setChecked(False); v.p_est.item(0, 0).setCheckState(Qt.Checked)
v._guardar_persona(); assert v.persona_id and v.t_personal.rowCount() == 1, v.aviso.text()
p = v.bd.colaboradores()[0]; assert p.permitidos == ("M", "T", "C") and p.estudio == ((0, "M"),), p
v.t_personal.selectRow(0); v._cargar_persona(); v.p_nombre.setText("Ana María"); v.p_est.item(1, 1).setCheckState(Qt.Checked); v._guardar_persona()
p = v.bd.colaboradores()[0]; assert p.nombre == "Ana María" and p.estudio == ((0, "M"), (1, "T"))
assert v.t_personal.item(0, 0).text() == "Ana María"
v._eliminar_persona(); assert v.t_personal.rowCount() == 0 and not v.bd.colaboradores(solo_activos=False), v.aviso.text()
# --- con historial: se desactiva y se ve con «Mostrar inactivos»
v._nueva_persona(); v.p_nombre.setText("Luis"); v._guardar_persona()
from datetime import date; from dominio import Novedad
v.bd.guardar_novedad(Novedad(v.persona_id, "Vacaciones", date(2026,10,1), date(2026,10,2))); v.refrescar()
v._eliminar_persona(); assert v.t_personal.rowCount() == 0 and "inactivo" in v.aviso.text(), v.aviso.text()
v.p_inactivos.setChecked(True); assert v.t_personal.rowCount() == 1 and v.t_personal.item(0, 6).text() == "Inactivo"
# --- turnos: crear, editar, eliminar
v._nuevo_turno(); v.t_cod.setText("m7"); v.t_nom.setText("Mañana 7"); v.t_ini.setTime(QTime(7, 0)); v.t_fin.setTime(QTime(13, 0))
v._guardar_turno(); assert "M7" in v.bd.turnos(), v.aviso.text()
v.t_tabla.selectRow([x.codigo for x in v._turnos].index("M7")); v._cargar_turno()
v.t_fin.setTime(QTime(14, 0)); v.t_pmin.setValue(30); v.t_pini.setTime(QTime(10, 0)); v._guardar_turno()
t = v.bd.turnos()["M7"]; assert t.duracion == 420 and t.horas == 6.5 and t.pausas[0]["ini"] == 180, t
assert v.t_resumen.text() == "Dura 7 h · se cuentan 6.5 h trabajadas"
v._nuevo_turno(); v.t_cod.setText("M"); v._guardar_turno(); assert "Ya existe" in v.aviso.text()
v._nuevo_turno(); v.t_cod.setText("ZZ"); [cb.setChecked(False) for cb in v.t_cubre.values()]; v._guardar_turno(); assert "franjas" in v.aviso.text()
v.t_tabla.selectRow([x.codigo for x in v._turnos].index("M7")); v._cargar_turno(); v._eliminar_turno()
assert "M7" not in v.bd.turnos(solo_activos=False)
# --- cuadro: intercambio por arrastre, lote y deshacer
from PySide6.QtCore import QMimeData, QPointF
from PySide6.QtGui import QDropEvent
v.p_inactivos.setChecked(False); v.refrescar()
for n in ("Ana", "Beto"):
    v._nueva_persona(); v.p_nombre.setText(n); v._guardar_persona()
v.año.setValue(2026); v.mes.setCurrentIndex(9)
a, b = [p.id for p in v.bd.colaboradores()][-2:]
d1, d2 = date(2026, 10, 5), date(2026, 10, 6)
v.bd.guardar_cuadro("2026-10", {(a, d1): "M", (b, d1): "T", (b, d2): "NC"}); v.refrescar()
gente = [p.id for p in v._gente()]; ra, rb = gente.index(a), gente.index(b)
g = v.grilla; c1, c2 = 4, 5
ver = lambda: v.bd.asignaciones("2026-10")
# soltar de verdad: el evento de drop llama a la señal con origen y destino
g._origen = (ra, c1)
pos = g.visualRect(g.model().index(rb, c1)).center()
g.dropEvent(QDropEvent(QPointF(pos), Qt.MoveAction, QMimeData(), Qt.LeftButton, Qt.NoModifier))
assert ver()[(a, d1)] == "T" and ver()[(b, d1)] == "M", ver()
assert v.bd.diferencias("2026-10"), "el intercambio debe verse como cambio frente al original"
v.deshacer(); assert ver()[(a, d1)] == "M" and ver()[(b, d1)] == "T" and v.bd.diferencias("2026-10") == []
# no se pisa una celda de totales ni se cambia en la vista Original
v._mover_celda(ra, c1, len(gente), c1); assert "no se puede" in v.aviso.text()
# lote: seleccionar dos celdas y asignar L
v._aplicar([(v._gente()[ra], d1, "L"), (v._gente()[rb], d1, "L")], "lote"); assert (a, d1) not in {k for k, x in ver().items() if x != "L"}
v.deshacer(); assert ver()[(a, d1)] == "M"
# estudio visible: la celda libre de quien estudia ese día lleva aviso
v._nueva_persona(); v.p_nombre.setText("Eva"); v.p_est.item(0, 0).setCheckState(Qt.Checked); v._guardar_persona(); v.refrescar()
fila = [p.nombre for p in v._gente()].index("Eva")
assert v.grilla.item(fila, c1).toolTip() == "Estudia: mañana" and v.grilla.item(fila, c1).background().color().name() == "#e3e6fa"
print("OK")
