"""An~: personal, novedades, cuadro mensual, puestos, horas y recargos."""
import os
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QSettings, Qt, QThread, QTime, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDateEdit,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTabWidget, QTimeEdit, QVBoxLayout, QWidget)

import db
import exportar
import flujo
import recargos
import reglas
import solver
from dominio import DIAS, TIPOS_COLAB, TIPOS_NOVEDAD, Colaborador, Novedad, Turno, texto_estudio
from puestos import PUESTOS

AQUI = Path(__file__).parent
LOG = AQUI / "errores.log"
BD_RUTA = AQUI / "turnos.db"
MESES = exportar.MESES
AMARILLO = "#FFFF00"
ABREV = exportar.ABREV_NOVEDAD

ESTILO = """
QMainWindow, QWidget#fondo { background: #F5F6F8; }
QLabel { color: #1F2933; }
QLabel#titulo { font-size: 20px; font-weight: 600; }
QLabel#muted { color: #6B7280; }
QLabel#aviso { border-radius: 8px; padding: 10px 12px; background: #E8F1F8; color: #12466B; }
QLabel#aviso[nivel="warn"] { background: #FFF4D6; color: #6B4E00; }
QLabel#aviso[nivel="error"] { background: #FDE8E8; color: #8E1B1B; }
QPushButton { background: white; border: 1px solid #CBD2D9; border-radius: 6px; padding: 7px 14px; color: #1F2933; }
QPushButton:hover { background: #F0F3F6; }
QPushButton:disabled { color: #A0A7B0; background: #F5F6F8; }
QPushButton#primario { background: #0F6E8C; border: 1px solid #0F6E8C; color: white; font-weight: 600; }
QPushButton#primario:hover { background: #0C5C75; }
QPushButton#primario:disabled { background: #9DBFCB; border-color: #9DBFCB; }
QComboBox, QLineEdit, QDateEdit, QSpinBox, QDoubleSpinBox { background: white; border: 1px solid #CBD2D9; border-radius: 6px; padding: 5px 8px; }
QTabWidget::pane { border: 1px solid #E3E6EA; border-radius: 8px; background: white; top: -1px; }
QTabBar::tab { padding: 8px 16px; color: #52606D; border: none; }
QTabBar::tab:selected { color: #0F6E8C; border-bottom: 2px solid #0F6E8C; font-weight: 600; }
QTableWidget { border: none; gridline-color: #EDF0F3; selection-background-color: #D6E9F0; selection-color: #1F2933; background: white; }
QHeaderView::section { background: #F7F8FA; border: none; border-bottom: 1px solid #E3E6EA; padding: 6px; color: #52606D; font-weight: 600; }
QGroupBox { background: white; border: 1px solid #E3E6EA; border-radius: 10px; margin-top: 14px; padding: 14px 12px 10px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: #0F6E8C; }
QPushButton#peligro { color: #B42318; border-color: #F0C4C0; }
QPushButton#peligro:hover { background: #FDE8E8; }
QPushButton#peligro:disabled { color: #D8B4B0; background: #F5F6F8; }
QCheckBox { spacing: 6px; }
QListWidget { border: 1px solid #E3E6EA; border-radius: 6px; background: white; }
"""


def abrir(ruta):
    if sys.platform == "win32":
        os.startfile(ruta)  # noqa: E1101 (solo existe en Windows)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


def tabla(columnas, editable=False):
    t = QTableWidget(0, len(columnas))
    t.setHorizontalHeaderLabels(columnas)
    if not editable:
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    return t


def llenar(t, filas, colores=None):
    t.blockSignals(True)
    t.setRowCount(len(filas))
    for r, fila in enumerate(filas):
        for c, v in enumerate(fila):
            it = QTableWidgetItem("" if v is None else str(v))
            if colores and (col := colores(r, c)):
                it.setBackground(QColor(col))
            t.setItem(r, c, it)
    t.resizeColumnsToContents()
    t.blockSignals(False)


def hhmm(minutos):
    return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


class Trabajo(QThread):
    listo = Signal(object, object)
    fallo = Signal(str)

    def __init__(self, ctx, fechas, kw):
        super().__init__()
        self.ctx, self.fechas, self.kw = ctx, fechas, kw

    def run(self):
        try:
            self.listo.emit(*solver.generar(self.ctx, self.fechas, **self.kw))
        except solver.ErrorSolver as e:
            self.fallo.emit(str(e))
        except Exception:
            self.fallo.emit("Error inesperado al generar:\n" + traceback.format_exc())


class Ventana(QMainWindow):
    def __init__(self, ruta_bd=BD_RUTA):
        super().__init__()
        self.setWindowTitle("An~ · Esterilización")
        self.resize(1360, 860)
        self.cfg = QSettings("An", "An")
        self.bd = db.BD(str(ruta_bd))
        self.trabajo = None
        hoy = date.today()
        raiz = QWidget(objectName="fondo")
        self.setCentralWidget(raiz)
        v = QVBoxLayout(raiz)
        cab = QHBoxLayout()
        cab.addWidget(QLabel("An~", objectName="titulo"))
        cab.addWidget(QLabel("Gestión de turnos · Central de Esterilización", objectName="muted"))
        cab.addStretch()
        self.mes = QComboBox()
        self.mes.addItems(MESES)
        self.mes.setCurrentIndex(hoy.month - 1)
        self.año = QSpinBox()
        self.año.setRange(2024, 2100)
        self.año.setValue(hoy.year)
        cab.addWidget(QLabel("Mes:"))
        cab.addWidget(self.mes)
        cab.addWidget(self.año)
        v.addLayout(cab)
        self.aviso = QLabel("", objectName="aviso")
        self.aviso.setWordWrap(True)
        self.aviso.hide()
        v.addWidget(self.aviso)
        self.pestanas = QTabWidget()
        v.addWidget(self.pestanas, 1)
        self._pestana_cuadro()
        self._pestana_personal()
        self._pestana_novedades()
        self._pestana_puestos()
        self._pestana_horas()
        self._pestana_parametros()
        for señal in (self.mes.currentIndexChanged, self.año.valueChanged, self.pestanas.currentChanged):
            señal.connect(lambda _: self._cambio_vista())
        self.refrescar()

    # --- utilidades -----------------------------------------------------------------------------
    @property
    def clave(self):
        return flujo.clave(self.año.value(), self.mes.currentIndex() + 1)

    @property
    def fechas(self):
        return flujo.fechas_mes(self.año.value(), self.mes.currentIndex() + 1)

    def avisar(self, texto, nivel="info"):
        self.aviso.setProperty("nivel", nivel)
        self.aviso.style().unpolish(self.aviso)
        self.aviso.style().polish(self.aviso)
        self.aviso.setText(texto)
        self.aviso.setVisible(bool(texto))

    def _cambio_vista(self):
        self.avisar("")
        self.refrescar()

    def refrescar(self):
        self.ctx = self.bd.contexto(self.año.value())
        self.nombres = {p.id: p.nombre for p in self.ctx.colabs}
        for f in (self._ver_cuadro, self._ver_personal, self._ver_novedades, self._ver_puestos, self._ver_horas,
                  self._ver_parametros):
            f()

    # --- cuadro ---------------------------------------------------------------------------------
    def _pestana_cuadro(self):
        w = QWidget()
        v = QVBoxLayout(w)
        barra = QHBoxLayout()
        self.version = QComboBox()
        self.version.addItems(["Cambios", "Original"])
        self.version.currentIndexChanged.connect(lambda _: self._ver_cuadro())
        barra.addWidget(QLabel("Ver:"))
        barra.addWidget(self.version)
        self.b_generar = QPushButton("Generar…", objectName="primario")
        m = QMenu(self.b_generar)
        m.addAction("Generar desde cero (descarta mis cambios)", lambda: self.generar("cero"))
        m.addAction("Regenerar respetando mis cambios", lambda: self.generar("respetar"))
        m.addAction("Regenerar solo una semana…", self.generar_semana)
        self.b_generar.setMenu(m)
        barra.addWidget(self.b_generar)
        for texto, f in (("Publicar como original", self.publicar), ("Restaurar desde original…", self.restaurar),
                         ("Exportar Excel", self.exportar)):
            b = QPushButton(texto)
            b.clicked.connect(f)
            barra.addWidget(b)
        barra.addStretch()
        v.addLayout(barra)
        self.grilla = QTableWidget()
        self.grilla.itemChanged.connect(self._celda_editada)
        v.addWidget(self.grilla, 3)
        v.addWidget(QLabel("Alertas del cuadro (versión Cambios)", objectName="muted"))
        self.alertas = QListWidget()
        v.addWidget(self.alertas, 1)
        self.lista_cambios = QListWidget()
        v.addWidget(QLabel("Cambios respecto al original", objectName="muted"))
        v.addWidget(self.lista_cambios, 1)
        self.pestanas.addTab(w, "Cuadro")

    def _ver_cuadro(self):
        fechas, k = self.fechas, self.clave
        orig = self.bd.asignaciones(k, "original")
        ver_orig = self.version.currentText() == "Original"
        cuadro = orig if ver_orig else self.bd.asignaciones(k)
        gente = [p for p in self.ctx.colabs if p.en_solver]
        g = self.grilla
        g.blockSignals(True)
        g.clear()
        g.setRowCount(len(gente) + 3)
        g.setColumnCount(len(fechas) + 1)
        g.setHorizontalHeaderLabels([f"{DIAS[f.weekday()]}\n{f.day}" for f in fechas] + ["Horas"])
        g.setVerticalHeaderLabels([p.nombre for p in gente] + ["Cubiertos mañana", "Cubiertos tarde", "Cubiertos noche"])
        for r, p in enumerate(gente):
            horas = 0
            for c, f in enumerate(fechas):
                cod = cuadro.get((p.id, f), "L")
                nov = self.ctx.novedad(p.id, f)
                it = QTableWidgetItem(ABREV[nov.tipo] if nov and cod == "L" else cod)
                it.setTextAlignment(Qt.AlignCenter)
                it.setData(Qt.UserRole, cod)
                if cod in self.ctx.turnos:
                    it.setBackground(QColor("#" + self.ctx.turnos[cod].color))
                    horas += self.ctx.turnos[cod].horas
                elif nov:
                    it.setBackground(QColor("#D9D9D9"))
                if not ver_orig and orig.get((p.id, f), "L") != cod:
                    it.setBackground(QColor(AMARILLO))
                if ver_orig or nov and cod == "L":
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                g.setItem(r, c, it)
            h = QTableWidgetItem(f"{horas:g}")
            h.setFlags(Qt.ItemIsEnabled)
            g.setItem(r, len(fechas), h)
        for i, fr in enumerate(("M", "T", "N")):
            for c, f in enumerate(fechas):
                hay = reglas.cobertura_dia(self.ctx, cuadro, f)[fr]
                req = self.ctx.cobertura[self.ctx.tipo_dia(f)][fr]
                it = QTableWidgetItem(f"{hay}/{req}")
                it.setTextAlignment(Qt.AlignCenter)
                it.setFlags(Qt.ItemIsEnabled)
                if hay < req:
                    it.setBackground(QColor("#FF9EA1"))
                g.setItem(len(gente) + i, c, it)
        for c, f in enumerate(fechas):
            if self.ctx.tipo_dia(f) == "DF":
                g.horizontalHeaderItem(c).setBackground(QColor("#F8CBAD"))
        g.resizeColumnsToContents()
        g.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        g.blockSignals(False)
        hay_cuadro = bool(cuadro)
        self.alertas.clear()
        self.lista_cambios.clear()
        if hay_cuadro:
            for a in reglas.validar(self.ctx, self.bd.asignaciones(k), fechas):
                self.alertas.addItem(a.texto)
            for cid, f, antes, ahora in self.bd.diferencias(k):
                self.lista_cambios.addItem(f"{self.nombres.get(cid, cid)} · {f:%d/%m}: {antes} → {ahora}")
        for a in reglas.validar_catalogo(self.ctx.turnos):
            self.alertas.addItem("Aviso: " + a.texto)
        if not hay_cuadro and not self.aviso.text():  # no pisa el mensaje de la acción que acaba de ocurrir
            self.avisar("Este mes aún no tiene cuadro. Pulsa «Generar…».", "warn")
        elif self.aviso.text().startswith("Este mes aún"):
            self.avisar("")

    def _celda_editada(self, it):
        r, c = it.row(), it.column()
        gente = [p for p in self.ctx.colabs if p.en_solver]
        if r >= len(gente) or c >= len(self.fechas):
            return
        p, f = gente[r], self.fechas[c]
        cod = it.text().strip().upper() or "L"
        if cod != "L" and cod not in self.ctx.turnos:
            self.avisar(f"«{cod}» no es un turno. Usa L o uno de: {', '.join(self.ctx.turnos)}.", "error")
        else:
            self.bd.set_celda(self.clave, p.id, f, cod)
            flujo.recalcular(self.bd, self.año.value(), self.mes.currentIndex() + 1, self.ctx)
            motivo = self.ctx.bloqueo(p, self.ctx.turnos[cod], f) if cod != "L" else None
            self.avisar(f"{p.nombre} · {f:%d/%m}: {cod}" + (f" — ojo: {motivo}." if motivo else ""),
                        "warn" if motivo else "info")
        self._ver_cuadro()

    def generar(self, modo, lunes=None):
        if self.trabajo and self.trabajo.isRunning():
            return
        k = self.clave
        if modo == "cero" and self.bd.diferencias(k):
            if QMessageBox.question(self, "Generar desde cero", "Hay cambios manuales sobre el original. "
                                    "¿Descartarlos y generar de nuevo?") != QMessageBox.Yes:
                return
        if not any(p.en_solver for p in self.ctx.colabs):
            return self.avisar("Primero agrega personal en la pestaña «Personal».", "warn")
        ctx, fechas, kw = flujo.preparar(self.bd, self.año.value(), self.mes.currentIndex() + 1, modo, lunes)
        self.b_generar.setEnabled(False)
        self.avisar("Generando el cuadro… puede tardar hasta 20 segundos.")
        self.trabajo = Trabajo(ctx, fechas, kw)
        self.trabajo.listo.connect(lambda cuadro, info: self._generado(ctx, fechas, cuadro, info, modo))
        self.trabajo.fallo.connect(self._fallo)
        self.trabajo.start()

    def _generado(self, ctx, fechas, cuadro, info, modo):
        self.b_generar.setEnabled(True)
        flujo.terminar(self.bd, self.año.value(), self.mes.currentIndex() + 1, ctx, fechas, cuadro, modo)
        if info["faltan"]:
            dias = ", ".join(f"{d:%d/%m} ({fr}: faltan {n})" for d, fr, n in info["faltan"][:6])
            self.avisar("No se pudo cubrir todo: " + dias + ". Revisa novedades y personal disponible.", "warn")
        else:
            self.avisar("Cuadro generado. Cobertura completa y reglas cumplidas.")
        self.refrescar()

    def _fallo(self, texto):
        self.b_generar.setEnabled(True)
        self.avisar(texto, "error")

    def generar_semana(self):
        lunes = sorted({f - timedelta(days=f.weekday()) for f in self.fechas})
        opciones = [f"Semana del {l:%d/%m}" for l in lunes]
        sel, ok = QInputDialog.getItem(self, "Regenerar una semana", "Semana:", opciones, 0, False)
        if ok:
            self.generar("semana", lunes[opciones.index(sel)])

    def publicar(self):
        if QMessageBox.question(self, "Publicar", "El cuadro actual pasará a ser el «original». ¿Continuar?") == QMessageBox.Yes:
            self.bd.publicar(self.clave)
            self.avisar("Cuadro publicado como original.")
            self._ver_cuadro()

    def restaurar(self):
        if QMessageBox.question(self, "Restaurar", "Se devolverán todas las celdas al original. ¿Continuar?") == QMessageBox.Yes:
            self.bd.restaurar(self.clave)
            flujo.recalcular(self.bd, self.año.value(), self.mes.currentIndex() + 1)
            self.refrescar()

    def exportar(self):
        k, fechas = self.clave, self.fechas
        cuadro = self.bd.asignaciones(k)
        if not cuadro:
            return self.avisar("No hay cuadro para exportar.", "warn")
        carpeta = QFileDialog.getExistingDirectory(self, "Carpeta de destino", self.cfg.value("carpeta", str(Path.home())))
        if not carpeta:
            return
        self.cfg.setValue("carpeta", carpeta)
        txt = f"{MESES[self.mes.currentIndex()]} {self.año.value()}"
        tar, ventana = self.bd.tarifas(), int(self.bd.param("ventana_semanas", 3))
        with ocupado():
            a = exportar.exportar_cuadro(carpeta, txt, self.ctx, cuadro, self.bd.asignaciones(k, "original"), fechas,
                                         self.bd.diferencias(k))
            b = exportar.exportar_puestos(carpeta, txt, self.ctx, cuadro, fechas, self.bd.puestos(k),
                                          self.bd.capacitacion(k))
            c = exportar.exportar_horas(carpeta, txt, self.ctx, tar, cuadro, fechas, ventana)
        self.avisar("Guardado: " + ", ".join(r.name for r in (a, b, c)))
        abrir(carpeta)

    # --- personal -------------------------------------------------------------------------------
    def _pestana_personal(self):
        w = QWidget()
        h = QHBoxLayout(w)
        izq = QVBoxLayout()
        barra = QHBoxLayout()
        nuevo = QPushButton("+ Nuevo colaborador", objectName="primario")
        nuevo.clicked.connect(self._nueva_persona)
        self.p_inactivos = QCheckBox("Mostrar inactivos")
        self.p_inactivos.toggled.connect(lambda _: self._ver_personal())
        for x in (nuevo, self.p_inactivos):
            barra.addWidget(x)
        barra.addStretch()
        izq.addLayout(barra)
        self.t_personal = tabla(["Nombre", "Tipo", "Horas/sem", "Turnos", "Puesto fijo", "Estudio", "Estado"])
        self.t_personal.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_personal.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_personal.itemSelectionChanged.connect(self._cargar_persona)
        izq.addWidget(self.t_personal)
        h.addLayout(izq, 3)

        caja = QGroupBox("Colaborador")
        caja.setMinimumWidth(470)
        f = QFormLayout(caja)
        self.p_nombre, self.p_tipo = QLineEdit(), QComboBox()
        self.p_tipo.addItems(TIPOS_COLAB)
        self.p_horas, self.p_pct = QDoubleSpinBox(), QDoubleSpinBox()
        self.p_horas.setRange(1, 60)
        self.p_horas.setSuffix(" h")
        self.p_pct.setRange(1, 100)
        self.p_pct.setSuffix(" %")
        self.p_perm_caja = QHBoxLayout()
        self.p_perm_cbs = {}
        self.p_puesto = QComboBox()
        self.p_puesto.addItem("Ninguno", None)
        for n, nombre in PUESTOS.items():
            if n:
                self.p_puesto.addItem(f"{n} · {nombre}", n)
        self.p_est = QTableWidget(2, 7)
        self.p_est.setHorizontalHeaderLabels(DIAS)
        self.p_est.setVerticalHeaderLabels(["Mañana", "Tarde"])
        self.p_est.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.p_est.setFixedHeight(92)
        self.p_est.horizontalHeader().setStyleSheet("QHeaderView::section { padding: 2px; }")
        self.p_est.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        for r in range(2):
            for c in range(7):
                it = QTableWidgetItem()
                it.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
                it.setCheckState(Qt.Unchecked)
                self.p_est.setItem(r, c, it)
        self.p_activo = QCheckBox("Activo (entra en los cuadros nuevos)")
        for et, wd in (("Nombre", self.p_nombre), ("Tipo", self.p_tipo), ("Jornada semanal", self.p_horas),
                       ("% de jornada", self.p_pct), ("Puede hacer", self.p_perm_caja), ("Puesto fijo", self.p_puesto),
                       ("No disponible por estudio", self.p_est), ("", self.p_activo)):
            f.addRow(et, wd)
        botones = QHBoxLayout()
        guardar = QPushButton("Guardar", objectName="primario")
        self.b_borrar_persona = QPushButton("Eliminar", objectName="peligro")
        guardar.clicked.connect(self._guardar_persona)
        self.b_borrar_persona.clicked.connect(self._eliminar_persona)
        botones.addWidget(guardar)
        botones.addWidget(self.b_borrar_persona)
        botones.addStretch()
        f.addRow(botones)
        h.addWidget(caja, 0, Qt.AlignTop)
        self.persona_id = None
        self.pestanas.addTab(w, "Personal")

    @staticmethod
    def _sin_seleccion(t):
        t.blockSignals(True)  # sin señal: no debe recargar el registro anterior en el formulario
        t.clearSelection()
        t.setCurrentCell(-1, -1)
        t.blockSignals(False)

    def _armar_permitidos(self):
        """Una casilla por turno activo del catálogo; conserva lo marcado."""
        if list(self.p_perm_cbs) == list(self.ctx.turnos):
            return
        marcado = {c: cb.isChecked() for c, cb in self.p_perm_cbs.items()}
        while self.p_perm_caja.count():
            cb = self.p_perm_caja.takeAt(0).widget()
            cb.setParent(None)
            cb.deleteLater()
        self.p_perm_cbs = {}
        for cod in self.ctx.turnos:
            cb = QCheckBox(cod)
            cb.setChecked(marcado.get(cod, True))
            self.p_perm_cbs[cod] = cb
            self.p_perm_caja.addWidget(cb)

    def _ver_personal(self):
        self._personal = [p for p in self.bd.colaboradores(solo_activos=False) if p.activo or self.p_inactivos.isChecked()]
        self._armar_permitidos()
        llenar(self.t_personal,
               [(p.nombre, p.tipo, f"{p.horas_sem:g} h ({p.pct * 100:g} %)",
                 "todos" if p.permitidos is None else ", ".join(p.permitidos), p.puesto_fijo or "",
                 texto_estudio(p.estudio), "Activo" if p.activo else "Inactivo") for p in self._personal],
               lambda r, c: None if self._personal[r].activo else "#EEF0F2")
        for r, p in enumerate(self._personal):
            if p.id == self.persona_id:
                self.t_personal.selectRow(r)

    def _cargar_persona(self):
        r = self.t_personal.currentRow()
        if r < 0 or r >= len(self._personal):
            return
        p = self._personal[r]
        self.persona_id = p.id
        self.p_nombre.setText(p.nombre)
        self.p_tipo.setCurrentText(p.tipo)
        self.p_horas.setValue(p.horas_sem)
        self.p_pct.setValue(p.pct * 100)
        for cod, cb in self.p_perm_cbs.items():
            cb.setChecked(p.permitidos is None or cod in p.permitidos)
        self.p_puesto.setCurrentIndex(max(0, self.p_puesto.findData(p.puesto_fijo)))
        for rr in range(2):
            for c in range(7):
                self.p_est.item(rr, c).setCheckState(Qt.Checked if (c, "MT"[rr]) in p.estudio else Qt.Unchecked)
        self.p_activo.setChecked(p.activo)
        self.b_borrar_persona.setEnabled(True)

    def _nueva_persona(self):
        self.persona_id = None
        self._sin_seleccion(self.t_personal)
        self.p_nombre.clear()
        self.p_tipo.setCurrentIndex(0)
        self.p_horas.setValue(42)
        self.p_pct.setValue(100)
        for cb in self.p_perm_cbs.values():
            cb.setChecked(True)
        self.p_puesto.setCurrentIndex(0)
        for rr in range(2):
            for c in range(7):
                self.p_est.item(rr, c).setCheckState(Qt.Unchecked)
        self.p_activo.setChecked(True)
        self.b_borrar_persona.setEnabled(False)
        self.p_nombre.setFocus()

    def _guardar_persona(self):
        nombre = self.p_nombre.text().strip()
        if not nombre:
            return self.avisar("Escribe el nombre del colaborador.", "error")
        marcados = tuple(c for c, cb in self.p_perm_cbs.items() if cb.isChecked())
        if not marcados:
            return self.avisar("Marca al menos un turno que pueda hacer.", "error")
        estudio = tuple(sorted((c, "MT"[r]) for r in range(2) for c in range(7)
                               if self.p_est.item(r, c).checkState() == Qt.Checked))
        perm = None if len(marcados) == len(self.p_perm_cbs) else marcados
        p = Colaborador(self.persona_id or 0, nombre, self.p_tipo.currentText(), self.p_horas.value(),
                        self.p_pct.value() / 100, perm, self.p_puesto.currentData(), estudio, self.p_activo.isChecked())
        self.persona_id = self.bd.guardar_colaborador(p)
        self.avisar(f"«{nombre}» guardado. Regenera el cuadro para que lo tome en cuenta.")
        self.refrescar()

    def _eliminar_persona(self):
        if self.persona_id is None:
            return self.avisar("Selecciona un colaborador de la lista.", "warn")
        nombre = self.p_nombre.text()
        if QMessageBox.question(self, "Eliminar colaborador", f"¿Eliminar a «{nombre}»?") != QMessageBox.Yes:
            return
        if self.bd.borrar_colaborador(self.persona_id) == "borrado":
            self.avisar(f"«{nombre}» eliminado.")
        else:
            self.avisar(f"«{nombre}» tiene cuadros o novedades en su historial, así que quedó inactivo en lugar de "
                        "borrarse. Ya no entra en cuadros nuevos; márcalo «Mostrar inactivos» para verlo.", "warn")
        self._nueva_persona()
        self.refrescar()

    # --- novedades ------------------------------------------------------------------------------
    def _pestana_novedades(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.t_nov = tabla(["Colaborador", "Tipo", "Desde", "Hasta", "Nota"])
        self.t_nov.setSelectionBehavior(QAbstractItemView.SelectRows)
        v.addWidget(self.t_nov, 2)
        f = QFormLayout()
        self.n_colab, self.n_tipo = QComboBox(), QComboBox()
        self.n_tipo.addItems(TIPOS_NOVEDAD)
        self.n_desde, self.n_hasta = QDateEdit(QDate.currentDate()), QDateEdit(QDate.currentDate())
        for d in (self.n_desde, self.n_hasta):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd/MM/yyyy")
        self.n_nota = QLineEdit()
        for et, wd in (("Colaborador", self.n_colab), ("Tipo", self.n_tipo), ("Desde", self.n_desde),
                       ("Hasta", self.n_hasta), ("Nota", self.n_nota)):
            f.addRow(et, wd)
        v.addLayout(f)
        bs = QHBoxLayout()
        b1, b2 = QPushButton("Agregar novedad", objectName="primario"), QPushButton("Borrar la seleccionada")
        b1.clicked.connect(self._agregar_novedad)
        b2.clicked.connect(self._borrar_novedad)
        bs.addWidget(b1)
        bs.addWidget(b2)
        bs.addStretch()
        v.addLayout(bs)
        self.pestanas.addTab(w, "Novedades")

    def _ver_novedades(self):
        self.n_colab.clear()
        for p in self.ctx.colabs:
            self.n_colab.addItem(p.nombre, p.id)
        self._novs = self.bd.novedades()
        llenar(self.t_nov, [(self.nombres.get(n.colab_id, "—"), n.tipo, f"{n.desde:%d/%m/%Y}", f"{n.hasta:%d/%m/%Y}", n.nota)
                            for n in self._novs])

    def _agregar_novedad(self):
        if self.n_colab.currentData() is None:
            return self.avisar("Primero agrega personal.", "warn")
        d, h = self.n_desde.date().toPython(), self.n_hasta.date().toPython()
        if h < d:
            return self.avisar("La fecha final es anterior a la inicial.", "error")
        self.bd.guardar_novedad(Novedad(self.n_colab.currentData(), self.n_tipo.currentText(), d, h, self.n_nota.text()))
        self.n_nota.clear()
        self.avisar("Novedad guardada. Usa «Regenerar solo una semana» o «respetando mis cambios» para aplicarla.")
        self.refrescar()

    def _borrar_novedad(self):
        r = self.t_nov.currentRow()
        if 0 <= r < len(self._novs):
            self.bd.borrar_novedad(self._novs[r].id)
            self.refrescar()

    # --- puestos y capacitación -----------------------------------------------------------------
    def _pestana_puestos(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.t_puestos = tabla(["Día", "Franja"] + [PUESTOS[p] for p in (1, 2, 3, 4, 5)] + ["Apoyo"])
        v.addWidget(self.t_puestos, 3)
        v.addWidget(QLabel("Capacitación del mes", objectName="muted"))
        self.l_cap = QListWidget()
        v.addWidget(self.l_cap, 1)
        self.pestanas.addTab(w, "Puestos y capacitación")

    def _ver_puestos(self):
        k = self.clave
        celdas, apoyo = {}, {}
        for f, fr, p, cid, g in self.bd.puestos(k):
            nombre = f"{self.nombres.get(cid, cid)} (P{g})"
            if p:
                celdas[f, fr, p] = nombre
            else:
                apoyo.setdefault((f, fr), []).append(nombre)
        filas = [(f"{DIAS[f.weekday()]} {f:%d/%m}", fr, *[celdas.get((f, fr, p), "") for p in (1, 2, 3, 4, 5)],
                  ", ".join(apoyo.get((f, fr), []))) for f in self.fechas for fr in ("M", "T")]
        llenar(self.t_puestos, filas, lambda r, c: "#F8CBAD" if c == 0 and self.ctx.tipo_dia(self.fechas[r // 2]) == "DF" else None)
        self.l_cap.clear()
        por_dia = {}
        for f, cid in self.bd.capacitacion(k):
            por_dia.setdefault(f, []).append(self.nombres.get(cid, str(cid)))
        for f in sorted(por_dia):
            self.l_cap.addItem(f"{DIAS[f.weekday()]} {f:%d/%m}: {', '.join(por_dia[f])}")

    # --- horas y recargos -----------------------------------------------------------------------
    def _pestana_horas(self):
        w = QWidget()
        v = QVBoxLayout(w)
        self.t_horas = tabla(["Colaborador", "Contratadas", "Trabajadas", "Pendientes", "Adicionales", "Extra (h)",
                              "Nocturnas (h)", "Dom/fest (h)", "Días dom/fest", "Habitual", "Horas equivalentes"])
        v.addWidget(self.t_horas)
        self.l_regimen = QLabel("", objectName="muted")
        self.l_regimen.setWordWrap(True)
        v.addWidget(self.l_regimen)
        self.pestanas.addTab(w, "Horas y recargos")

    def _ver_horas(self):
        k, fechas = self.clave, self.fechas
        cuadro = self.bd.asignaciones(k)
        ventana, tar = int(self.bd.param("ventana_semanas", 3)), self.bd.tarifas()
        filas = []
        if cuadro:
            for p in (p for p in self.ctx.colabs if p.en_solver):
                r = recargos.reporte(self.ctx, tar, p, cuadro, fechas, ventana)
                cat = r["cat"]
                filas.append((p.nombre, *(round(r[x], 1) for x in ("contratadas", "trabajadas", "pendientes", "adicionales")),
                              round(sum(h for c, h in cat.items() if c[0] == "extra"), 1),
                              round(sum(h for c, h in cat.items() if c[1] == "nocturna"), 1),
                              round(sum(h for c, h in cat.items() if c[2] == "festivo"), 1),
                              r["festivos_trabajados"], "Sí" if r["habitual"] else "No", round(r["equivalentes"], 1)))
        llenar(self.t_horas, filas)
        f0 = fechas[0]
        self.l_regimen.setText(
            f"Art. 165 CST: promedio en ventanas de {ventana} semanas contra la jornada contratada. Dominical/festivo "
            f"{recargos.tarifa(tar, 'dominical', f0)} %, nocturno {recargos.tarifa(tar, 'nocturno', f0)} % desde las "
            f"{recargos.tarifa(tar, 'noche_inicio', f0) // 60}:00. Cifras de apoyo: confirma con RR. HH./jurídico.")

    # --- parámetros -----------------------------------------------------------------------------
    def _pestana_parametros(self):
        self.sub = QTabWidget()
        w = QWidget()
        h = QHBoxLayout(w)
        izq = QVBoxLayout()
        nuevo = QPushButton("+ Nuevo turno", objectName="primario")
        nuevo.clicked.connect(self._nuevo_turno)
        izq.addWidget(nuevo, alignment=Qt.AlignLeft)
        self.t_tabla = tabla(["Código", "Nombre", "Horario", "Horas", "Cubre", "Estado"])
        self.t_tabla.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_tabla.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_tabla.itemSelectionChanged.connect(self._cargar_turno)
        izq.addWidget(self.t_tabla)
        h.addLayout(izq, 3)
        caja = QGroupBox("Turno")
        caja.setMinimumWidth(470)
        f = QFormLayout(caja)
        self.t_cod, self.t_nom = QLineEdit(), QLineEdit()
        self.t_cod.setMaxLength(4)
        self.t_ini, self.t_fin, self.t_pini = QTimeEdit(), QTimeEdit(), QTimeEdit()
        for t in (self.t_ini, self.t_fin, self.t_pini):
            t.setDisplayFormat("HH:mm")
            t.timeChanged.connect(lambda _: self._resumen_turno())
        self.t_pmin = QSpinBox()
        self.t_pmin.setRange(0, 240)
        self.t_pmin.setSuffix(" min")
        self.t_pmin.setSpecialValueText("Sin pausa")
        self.t_pmin.valueChanged.connect(lambda _: self._resumen_turno())
        self.t_ppag = QCheckBox("La pausa cuenta como trabajada")
        self.t_ppag.toggled.connect(lambda _: self._resumen_turno())
        cubre = QHBoxLayout()
        self.t_cubre = {}
        for fr, et in (("M", "Mañana"), ("T", "Tarde"), ("N", "Noche")):
            self.t_cubre[fr] = QCheckBox(et)
            cubre.addWidget(self.t_cubre[fr])
        self.t_dom = QCheckBox("Se puede usar en domingo y festivo")
        self.t_sol = QCheckBox("El generador puede asignarlo")
        self.t_act = QCheckBox("Activo")
        self.t_color = QPushButton()
        self.t_color.clicked.connect(self._elegir_color)
        self.t_resumen = QLabel("", objectName="muted")
        self.t_resumen.setWordWrap(True)
        for et, wd in (("Código", self.t_cod), ("Nombre", self.t_nom), ("Empieza", self.t_ini), ("Termina", self.t_fin),
                       ("Pausa de almuerzo", self.t_pmin), ("Pausa a las", self.t_pini), ("", self.t_ppag),
                       ("Cubre", cubre), ("", self.t_dom), ("", self.t_sol), ("", self.t_act), ("Color", self.t_color),
                       ("", self.t_resumen)):
            f.addRow(et, wd)
        botones = QHBoxLayout()
        guardar = QPushButton("Guardar", objectName="primario")
        self.b_borrar_turno = QPushButton("Eliminar", objectName="peligro")
        guardar.clicked.connect(self._guardar_turno)
        self.b_borrar_turno.clicked.connect(self._eliminar_turno)
        botones.addWidget(guardar)
        botones.addWidget(self.b_borrar_turno)
        botones.addStretch()
        f.addRow(botones)
        h.addWidget(caja, 0, Qt.AlignTop)
        self.turno_cod = None
        self._nuevo_turno()
        self.sub.addTab(w, "Turnos")

        w = QWidget()
        v = QVBoxLayout(w)
        f = QFormLayout()
        self.s_cob = {}
        for td, nombre in (("LS", "Lunes a sábado"), ("DF", "Domingo y festivo")):
            fila = QHBoxLayout()
            for fr, et in (("M", "Mañana"), ("T", "Tarde"), ("N", "Noche")):
                s = QSpinBox()
                s.setRange(0, 30)
                self.s_cob[td, fr] = s
                fila.addWidget(QLabel(et))
                fila.addWidget(s)
            fila.addStretch()
            f.addRow(nombre, fila)
        self.s_vent = QSpinBox()
        self.s_vent.setRange(1, 8)
        f.addRow("Semanas de la ventana (art. 165)", self.s_vent)
        self.s_noches = QSpinBox()
        self.s_noches.setRange(1, 7)
        f.addRow("Máximo de noches seguidas", self.s_noches)
        v.addLayout(f)
        b = QPushButton("Guardar", objectName="primario")
        b.clicked.connect(self._guardar_reglas)
        v.addWidget(b, alignment=Qt.AlignLeft)
        v.addStretch()
        self.sub.addTab(w, "Cobertura y reglas")

        w = QWidget()
        v = QVBoxLayout(w)
        self.t_tar = tabla(["Concepto", "Valor", "Vigente desde"])
        v.addWidget(self.t_tar)
        fila = QHBoxLayout()
        self.tar_c = QComboBox()
        self.tar_c.addItems(["dominical", "nocturno", "extra_diurna", "extra_nocturna", "noche_inicio"])
        self.tar_v = QDoubleSpinBox()
        self.tar_v.setRange(0, 5000)
        self.tar_d = QDateEdit(QDate.currentDate())
        self.tar_d.setCalendarPopup(True)
        b = QPushButton("Agregar tarifa")
        b.clicked.connect(self._agregar_tarifa)
        for x in (self.tar_c, self.tar_v, self.tar_d, b):
            fila.addWidget(x)
        v.addLayout(fila)
        v.addWidget(QLabel("Porcentajes (noche_inicio en minutos desde las 00:00: 1140 = 7 p. m.). La tarifa vigente en cada fecha es la más reciente.", objectName="muted"))
        self.sub.addTab(w, "Tarifas")

        self.l_fest = QListWidget()
        self.sub.addTab(self.l_fest, "Festivos")
        self.pestanas.addTab(self.sub, "Parámetros")

    def _ver_parametros(self):
        self._turnos = list(self.bd.turnos(solo_activos=False).values())
        llenar(self.t_tabla, [(x.codigo, x.nombre, f"{hhmm(x.inicio)}–{hhmm(x.fin)}", f"{x.horas:g}",
                               ", ".join(x.cubre), "Activo" if x.activo else "Inactivo") for x in self._turnos],
               lambda r, c: ("#" + self._turnos[r].color) if c == 0 else (None if self._turnos[r].activo else "#EEF0F2"))
        for r, x in enumerate(self._turnos):
            if x.codigo == self.turno_cod:
                self.t_tabla.selectRow(r)
        self._resumen_turno()
        for (td, fr), s in self.s_cob.items():
            s.setValue(self.ctx.cobertura.get(td, {}).get(fr, 0))
        self.s_vent.setValue(int(self.bd.param("ventana_semanas", 3)))
        self.s_noches.setValue(int(self.bd.param("max_noches_seguidas", 3)))
        llenar(self.t_tar, sorted(((c, v, f"{d:%d/%m/%Y}") for c, v, d in self.bd.tarifas()), key=lambda x: (x[0], x[2][6:] + x[2][3:5])))
        self.l_fest.clear()
        for f, n in sorted(self.ctx.fest.items()):
            if f.year == self.año.value():
                self.l_fest.addItem(f"{DIAS[f.weekday()]} {f:%d/%m/%Y} · {n}")

    def _nuevo_turno(self):
        self.turno_cod = None
        self._sin_seleccion(self.t_tabla)
        self.t_cod.setReadOnly(False)
        self.t_cod.clear()
        self.t_nom.clear()
        self.t_ini.setTime(QTime(6, 0))
        self.t_fin.setTime(QTime(12, 0))
        self.t_pmin.setValue(0)
        self.t_pini.setTime(QTime(12, 0))
        self.t_ppag.setChecked(False)
        for fr, cb in self.t_cubre.items():
            cb.setChecked(fr == "M")
        self.t_dom.setChecked(True)
        self.t_sol.setChecked(True)
        self.t_act.setChecked(True)
        self._poner_color("FFFFFF")
        self.b_borrar_turno.setEnabled(False)
        self.t_cod.setFocus()

    def _cargar_turno(self):
        r = self.t_tabla.currentRow()
        if r < 0 or r >= len(self._turnos):
            return
        t = self._turnos[r]
        self.turno_cod = t.codigo
        self.t_cod.setText(t.codigo)
        self.t_cod.setReadOnly(True)
        self.t_nom.setText(t.nombre)
        self.t_ini.setTime(QTime(t.inicio // 60 % 24, t.inicio % 60))
        self.t_fin.setTime(QTime(t.fin // 60 % 24, t.fin % 60))
        p = t.pausas[0] if t.pausas else None
        self.t_pmin.setValue(p["min"] if p else 0)
        pa = t.inicio + (p["ini"] if p else 360)
        self.t_pini.setTime(QTime(pa // 60 % 24, pa % 60))
        self.t_ppag.setChecked(bool(p and p["pagada"]))
        for fr, cb in self.t_cubre.items():
            cb.setChecked(fr in t.cubre)
        self.t_dom.setChecked(t.dom_fest)
        self.t_sol.setChecked(t.solver)
        self.t_act.setChecked(t.activo)
        self._poner_color(t.color)
        self.b_borrar_turno.setEnabled(True)

    def _poner_color(self, color):
        self._color = color
        self.t_color.setStyleSheet(f"background: #{color}; border: 1px solid #CBD2D9; border-radius: 6px; padding: 7px;")
        self.t_color.setText(f"#{color}")

    def _elegir_color(self):
        c = QColorDialog.getColor(QColor("#" + self._color), self, "Color del turno")
        if c.isValid():
            self._poner_color(c.name()[1:].upper())

    def _turno_desde_form(self):
        cod = self.t_cod.text().strip().upper()
        if not cod or cod == "L":
            raise ValueError("Escribe un código para el turno (distinto de L).")
        minutos = lambda t: t.hour() * 60 + t.minute()
        ini, fin = minutos(self.t_ini.time()), minutos(self.t_fin.time())
        if ini == fin:
            raise ValueError("El turno no puede empezar y terminar a la misma hora.")
        cubre = tuple(fr for fr, cb in self.t_cubre.items() if cb.isChecked())
        if not cubre:
            raise ValueError("Marca qué franjas cubre (mañana, tarde, noche).")
        pausas = ()
        if self.t_pmin.value() > 0:
            pausas = ({"ini": (minutos(self.t_pini.time()) - ini) % 1440, "min": self.t_pmin.value(),
                       "pagada": self.t_ppag.isChecked()},)
        t = Turno(cod, self.t_nom.text().strip() or cod, ini, fin, self._color, cubre, pausas, self.t_dom.isChecked(),
                  self.t_sol.isChecked(), self.t_act.isChecked())
        if pausas and pausas[0]["ini"] + pausas[0]["min"] > t.duracion:
            raise ValueError("La pausa debe quedar dentro del turno.")
        return t

    def _resumen_turno(self):
        try:
            t = self._turno_desde_form()
            self.t_resumen.setText(f"Dura {t.duracion / 60:g} h · se cuentan {t.horas:g} h trabajadas")
        except ValueError as e:
            self.t_resumen.setText(str(e))

    def _guardar_turno(self):
        try:
            t = self._turno_desde_form()
        except ValueError as e:
            return self.avisar(str(e), "error")
        if self.turno_cod is None and t.codigo in self.bd.turnos(solo_activos=False):
            return self.avisar(f"Ya existe un turno «{t.codigo}».", "error")
        self.bd.guardar_turno(t)
        self.turno_cod = t.codigo
        self.avisar(f"Turno «{t.codigo}» guardado. El cuadro existente se revalidó; regenera si hay alertas.")
        self.refrescar()

    def _eliminar_turno(self):
        if self.turno_cod is None:
            return self.avisar("Selecciona un turno de la lista.", "warn")
        cod = self.turno_cod
        if QMessageBox.question(self, "Eliminar turno", f"¿Eliminar el turno «{cod}»?") != QMessageBox.Yes:
            return
        if self.bd.borrar_turno(cod) == "borrado":
            self.avisar(f"Turno «{cod}» eliminado.")
        else:
            self.avisar(f"«{cod}» ya está en cuadros guardados, así que quedó inactivo en lugar de borrarse.", "warn")
        self._nuevo_turno()
        self.refrescar()

    def _guardar_reglas(self):
        self.bd.guardar_cobertura({td: {fr: self.s_cob[td, fr].value() for fr in "MTN"} for td in ("LS", "DF")})
        self.bd.set_param("ventana_semanas", self.s_vent.value())
        self.bd.set_param("max_noches_seguidas", self.s_noches.value())
        self.avisar("Cobertura y ventana guardadas.")
        self.refrescar()

    def _agregar_tarifa(self):
        self.bd.agregar_tarifa(self.tar_c.currentText(), self.tar_v.value(), self.tar_d.date().toPython())
        self.refrescar()


class ocupado:
    def __enter__(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)

    def __exit__(self, *exc):
        QApplication.restoreOverrideCursor()


def error_inesperado(tipo, valor, tb):
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M}\n{texto}")
    except OSError:
        pass
    QMessageBox.critical(None, "Algo salió mal",
                         f"Ocurrió un error inesperado:\n\n{valor}\n\nSe guardó el detalle en {LOG.name}.")


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    # Siempre modo claro: con el sistema en oscuro, Qt pondría texto claro sobre nuestros fondos blancos
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(app.style().standardPalette())
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(ESTILO)
    sys.excepthook = error_inesperado
    v = Ventana()
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
