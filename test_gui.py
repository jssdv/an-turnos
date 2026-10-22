# Prueba de la ventana sin pantalla: crear, editar y eliminar colaboradores y turnos.
import sys, os, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtCore import Qt, QTime
import app
import flujo
P = flujo.periodo_mes(2026, 10)
K = flujo.clave(*P)
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
assert v.t_resumen.text() == "Dura 7 h · se cuentan 6.5 h trabajadas · cuenta en: mañana"
v._nuevo_turno(); v.t_cod.setText("M"); v._guardar_turno(); assert "Ya existe" in v.aviso.text()
assert not hasattr(v, "t_cubre")  # la franja se calcula del horario
v._nuevo_turno(); v.t_cod.setText("ZZ"); v.t_ini.setTime(QTime(6, 0)); v.t_fin.setTime(QTime(18, 0))
assert "mañana, tarde" in v.t_resumen.text()
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
v.bd.guardar_cuadro(K, {(a, d1): "M", (b, d1): "T", (b, d2): "NC"}); v.refrescar()
gente = [p.id for p in v._gente()]; ra, rb = gente.index(a), gente.index(b)
g = v.grilla; c1, c2 = 4, 5
ver = lambda: v.bd.asignaciones(K)
# soltar de verdad: el evento de drop llama a la señal con origen y destino
g._origen = (ra, c1)
pos = g.visualRect(g.model().index(rb, c1)).center()
g.dropEvent(QDropEvent(QPointF(pos), Qt.MoveAction, QMimeData(), Qt.LeftButton, Qt.NoModifier))
assert ver()[(a, d1)] == "T" and ver()[(b, d1)] == "M", ver()
assert v.bd.diferencias(K), "el intercambio debe verse como cambio frente al original"
v.deshacer(); assert ver()[(a, d1)] == "M" and ver()[(b, d1)] == "T" and v.bd.diferencias(K) == []
# no se pisa una celda de totales ni se cambia en la vista Original
v._mover_celda(ra, c1, len(gente), c1); assert "no se puede" in v.aviso.text()
# lote: seleccionar dos celdas y asignar L
v._aplicar([(v._gente()[ra], d1, "L"), (v._gente()[rb], d1, "L")], "lote"); assert (a, d1) not in {k for k, x in ver().items() if x != "L"}
v.deshacer(); assert ver()[(a, d1)] == "M"
# puesto visible: con «Mostrar puesto» la celda dice M·n, y editarla sigue leyendo solo el código
import flujo
flujo.recalcular(v.bd, *P); v.refrescar()
assert v.grilla.item(ra, c1).text() == "M" and v.grilla.item(ra, c1).toolTip().startswith("Puesto: ")
v.ver_puesto.setChecked(True)
txt = v.grilla.item(ra, c1).text(); assert txt.startswith("M·") and txt[2] in "12345A", txt
v.grilla.item(ra, c1).setText("T·2"); assert v.bd.asignaciones(K)[(a, d1)] == "T"
v.deshacer(); v.ver_puesto.setChecked(False)
# esquema por semanas: el selector cambia a «desde el lunes» y avanza de N en N semanas
v.bd.set_param("periodo_modo", "semanas"); v.bd.set_param("periodo_semanas", 4)
from PySide6.QtCore import QDate
v.f_inicio.setDate(QDate(2026, 10, 7)); assert v.f_inicio.date().toPython() == date(2026, 10, 5) and "lunes" in v.aviso.text()  # ajusta al lunes
assert v.periodo() == (date(2026, 10, 5), date(2026, 11, 1)) and v.clave == "2026-10-05/2026-11-01" and len(v.fechas) == 28
assert v.f_inicio.isVisibleTo(v) and not v.mes.isVisibleTo(v)
v._mover_periodo(1); assert v.periodo()[0] == date(2026, 11, 2)
v._mover_periodo(-1); v.bd.set_param("periodo_modo", "mes"); v.refrescar(); assert v.periodo() == P and v.mes.isVisibleTo(v)
# estudio visible: la celda libre de quien estudia ese día lleva aviso
v._nueva_persona(); v.p_nombre.setText("Eva"); v.p_est.item(0, 0).setCheckState(Qt.Checked); v._guardar_persona(); v.refrescar()
fila = [p.nombre for p in v._gente()].index("Eva")
assert v.grilla.item(fila, c1).toolTip() == "Estudia: mañana" and v.grilla.item(fila, c1).background().style() == Qt.BDiagPattern
# --- cierre del periodo y banco de horas
assert v.b_cierre.text() == "Cerrar periodo"
v._alternar_cierre(); assert v.bd.periodo_cerrado(K) and "CERRADO" in v.l_periodo.text() and v.b_cierre.text() == "Reabrir periodo"
assert v._editable(ra, c1) is None  # cerrado: solo lectura
v.generar("cero"); assert "cerrado" in v.aviso.text()
v.publicar(); assert "cerrado" in v.aviso.text()
filas = {b["nombre"]: b for b in v._banco}
assert v.t_banco.rowCount() >= 2 and all(b["cerrado"] for b in v._banco)
fila_a = [b["id"] for b in v._banco].index(a); v.t_banco.selectRow(fila_a)
assert v.persona_banco == a and v.t_movs.rowCount() == 1 and v.t_movs.item(0, 1).text().startswith("Cierre")
v.m_concepto.setCurrentText("Pagado en nómina"); v.m_horas.setValue(3); v._registrar_movimiento()
assert v.bd.movimientos(a)[0][3] == -3 and v.t_movs.rowCount() == 2  # «Pagado» se guarda como resta
v.t_movs.selectRow(1 if v._movs[1][0] else 0); v._borrar_movimiento(); assert v.bd.movimientos(a) == []
assert v.t_hist.rowCount() == 1 and v.t_hist.item(0, 2).text() == "Cerrado"
v.t_hist.selectRow(0); v.sub_banco.setCurrentIndex(1); v._ir_al_periodo(); assert v.periodo() == P and v.pestanas.currentIndex() == 0
v._alternar_cierre(); assert not v.bd.periodo_cerrado(K) and v.bd.cierres() == []
# banco: los topes de compensación se guardan desde Parámetros
assert (v.s_favor.value(), v.s_deuda.value()) == (12, 12)
v.s_favor.setValue(8); v.s_deuda.setValue(0); v._guardar_reglas()
assert (v.bd.param("banco_tope_favor_h"), v.bd.param("banco_tope_deuda_h")) == ("8", "0") and v.s_favor.value() == 8
# --- puestos: crear, editar, eliminar, avisos
from PySide6.QtCore import QTime
tp = v.tab_puestos
celda = lambda r, c: tp.t_reglas.cellWidget(r, c)
por_nombre = lambda n: next((i for i, p in v.bd.catalogo_puestos().items() if p.nombre == n), None)
tp.nuevo(); tp.f_numero.setValue(7); tp.f_nombre.setText("Esterilización de lencería"); tp.agregar_regla()
celda(0, 1).setTime(QTime(8, 0)); celda(0, 2).setTime(QTime(14, 0)); celda(0, 3).setValue(2)
tp.guardar(); pid = por_nombre("Esterilización de lencería")
assert pid and [(d.tipo_dia, d.inicio, d.fin, d.personas, d.obligatorio) for d in v.bd.demandas(pid)] == [("LS", 480, 840, 2, True)], v.aviso.text()
assert v.ctx.cobertura["LS"]["M"] == 6  # pico de 08:00–12:00: 4 de los puestos base + 2
filas = [p for p in tp._puestos]
tp.t_lista.selectRow([p.id for p in tp._puestos].index(pid)); celda(0, 3).setValue(3); tp.guardar()
assert v.bd.demandas(pid)[0].personas == 3
tp.t_lista.selectRow([p.id for p in tp._puestos].index(pid)); tp.eliminar(); assert por_nombre("Esterilización de lencería") is None
# un puesto con reparto guardado se desactiva
v.bd.c.execute("INSERT INTO puesto_dia VALUES (?,?,?,?,?,?)", (K, "2026-10-05", "M", 2, 1, 1))
aut = next(i for i, p in v.bd.catalogo_puestos().items() if p.numero == 2)
tp.t_lista.selectRow([p.id for p in tp._puestos].index(aut)); tp.eliminar()
assert not v.bd.catalogo_puestos()[aut].activo and "inactivo" in v.aviso.text()
v.bd.c.execute("DELETE FROM puesto_dia"); a_ = v.bd.catalogo_puestos()[aut]; a_.activo = True; v.bd.guardar_puesto(a_); v.refrescar()
# ventana con inicio = fin: no guarda
tp.nuevo(); tp.f_numero.setValue(8); tp.f_nombre.setText("Mala"); tp.agregar_regla(); celda(0, 1).setTime(QTime(8, 0)); celda(0, 2).setTime(QTime(8, 0))
tp.guardar(); assert por_nombre("Mala") is None and "no puede empezar y terminar a la misma hora" in v.aviso.text()
# personas ≥ 1 y número repetido
tp.nuevo(); tp.f_numero.setValue(2); tp.f_nombre.setText("Repetido"); tp.guardar(); assert por_nombre("Repetido") is None and "Ya existe el puesto número 2" in v.aviso.text()
# aviso si ningún turno cubre la ventana: se guarda igual
for cod in ("M", "T", "C"):
    t_ = v.bd.turnos(False)[cod]; t_.activo = False; v.bd.guardar_turno(t_)
v.refrescar(); tp.nuevo(); tp.f_numero.setValue(9); tp.f_nombre.setText("Sin turno"); tp.agregar_regla()
celda(0, 1).setTime(QTime(8, 0)); celda(0, 2).setTime(QTime(14, 0)); tp.guardar()
assert por_nombre("Sin turno") and "Ningún turno cubre 08:00–14:00" in v.aviso.text()
for cod in ("M", "T", "C"):
    t_ = v.bd.turnos(False)[cod]; t_.activo = True; v.bd.guardar_turno(t_)
v.refrescar()
# puesto sin reglas y reglas solapadas
tp.nuevo(); tp.f_numero.setValue(10); tp.f_nombre.setText("Vacío"); tp.guardar()
assert por_nombre("Vacío") and tp.t_lista.item([p.id for p in tp._puestos].index(por_nombre("Vacío")), 2).text() == "Sin demanda"
tp.t_lista.selectRow([p.id for p in tp._puestos].index(por_nombre("Vacío"))); tp.agregar_regla(); tp.agregar_regla()
tp.guardar(); assert "Las reglas solapadas se suman" in v.aviso.text()
# --- puestos permitidos en la ficha de personal
v.pestanas.setCurrentIndex(1)
ids_p = {p.numero: i for i, p in v.bd.catalogo_puestos().items()}
n_antes = len(v.bd.colaboradores(solo_activos=False))
v._nueva_persona(); v.p_nombre.setText("Solo tres")
for i, cb in v.p_puestos_cbs.items():
    cb.setChecked(i == ids_p[3])
v._guardar_persona()
sol = next(c for c in v.bd.colaboradores() if c.nombre == "Solo tres")
assert sol.puestos_permitidos == (ids_p[3],) and sol.puesto_fijo == 3
v.t_personal.selectRow([c.nombre for c in v._personal].index("Solo tres")); v._cargar_persona()
assert [i for i, cb in v.p_puestos_cbs.items() if cb.isChecked()] == [ids_p[3]]
for cb in v.p_puestos_cbs.values():
    cb.setChecked(True)
v._guardar_persona()
sol = next(c for c in v.bd.colaboradores() if c.nombre == "Solo tres")
assert sol.puestos_permitidos is None and sol.puesto_fijo is None
for cb in v.p_puestos_cbs.values():
    cb.setChecked(False)
n = len(v.bd.colaboradores(solo_activos=False)); v._guardar_persona()
assert "Marca al menos un puesto que pueda ocupar" in v.aviso.text() and len(v.bd.colaboradores(solo_activos=False)) == n
# --- pestaña Dotación (estimación por horas)
import tempfile as _tf
from dominio import Colaborador
v2 = app.Ventana(_tf.mkdtemp() + "/d.db")
for i in range(13):
    v2.bd.guardar_colaborador(Colaborador(0, f"P{i}"))
v2.refrescar()
td = v2.tab_dotacion
assert td.l_horas.text() == "480" and td.l_personas.text() == "13" and td.l_activos.text() == "13" and td.l_diferencia.text() == "Al día"
assert td.t_puesto.rowCount() == 5 and td.t_franja.rowCount() == 3  # Ropa es deseable: no entra sin la casilla
suma = sum(float(td.t_franja.item(r, 1).text()) for r in range(3))
assert suma == 480
td.s_margen.setValue(20)
assert td.l_personas.text() == "15" and td.l_diferencia.text() == "Faltan 2" and v2.bd.param("dotacion_margen_pct") == "20"
td.c_deseables.setChecked(True)
assert td.t_puesto.rowCount() == 6 and td.l_horas.text() == "552"
td.s_margen.setValue(0); td.c_deseables.setChecked(False)
assert td.l_personas.text() == "12" and td.l_diferencia.text() == "Sobran 1"
print("OK")
