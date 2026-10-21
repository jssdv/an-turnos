"""Turnos Esterilización: personal, novedades, cuadro mensual, puestos, horas y recargos."""
import os
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path

from PySide6.QtCore import QDate, QSettings, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QComboBox, QDateEdit, QDoubleSpinBox,
                               QFileDialog, QFormLayout, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QSpinBox, QTableWidget,
                               QTableWidgetItem, QTabWidget, QVBoxLayout, QWidget)

import db
import exportar
import flujo
import recargos
import reglas
import solver
from dominio import (DIAS, TIPOS_COLAB, TIPOS_NOVEDAD, Colaborador, Novedad, Turno, parsear_estudio, texto_estudio)
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


def minutos(texto):
    h, m = texto.strip().split(":")
    if not (0 <= int(h) < 24 and 0 <= int(m) < 60):
        raise ValueError
    return int(h) * 60 + int(m)


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
        self.setWindowTitle("Turnos · Esterilización")
        self.resize(1360, 860)
        self.cfg = QSettings("Esterilizacion", "Turnos")
        self.bd = db.BD(str(ruta_bd))
        self.trabajo = None
        hoy = date.today()
        raiz = QWidget(objectName="fondo")
        self.setCentralWidget(raiz)
        v = QVBoxLayout(raiz)
        cab = QHBoxLayout()
        cab.addWidget(QLabel("Turnos · Esterilización", objectName="titulo"))
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
        self.mes.currentIndexChanged.connect(self.refrescar)
        self.año.valueChanged.connect(self.refrescar)
        self.pestanas.currentChanged.connect(lambda _: self.refrescar())
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

    def refrescar(self, *_):
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
        if not hay_cuadro:
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
        v = QVBoxLayout(w)
        self.t_personal = tabla(["Nombre", "Tipo", "Horas/sem", "% jornada", "Turnos permitidos", "Puesto fijo", "Estudio", "Activo"])
        self.t_personal.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_personal.itemSelectionChanged.connect(self._cargar_persona)
        v.addWidget(self.t_personal, 2)
        f = QFormLayout()
        self.p_nombre, self.p_tipo = QLineEdit(), QComboBox()
        self.p_tipo.addItems(TIPOS_COLAB)
        self.p_horas, self.p_pct = QDoubleSpinBox(), QDoubleSpinBox()
        self.p_horas.setRange(1, 60)
        self.p_horas.setValue(42)
        self.p_pct.setRange(1, 100)
        self.p_pct.setValue(100)
        self.p_perm, self.p_puesto, self.p_estudio = QLineEdit(), QComboBox(), QLineEdit()
        self.p_perm.setPlaceholderText("vacío = todos; ej. M, T (sin noches)")
        self.p_puesto.addItem("Ninguno", None)
        for n, nombre in PUESTOS.items():
            if n:
                self.p_puesto.addItem(f"{n} · {nombre}", n)
        self.p_estudio.setPlaceholderText("ej. Lun M, Jue M, Vie, Mar T  (sin franja = todo el día)")
        self.p_activo = QCheckBox("Activo")
        self.p_activo.setChecked(True)
        for et, wd in (("Nombre", self.p_nombre), ("Tipo", self.p_tipo), ("Horas por semana", self.p_horas),
                       ("% de jornada", self.p_pct), ("Turnos permitidos", self.p_perm), ("Puesto fijo", self.p_puesto),
                       ("Horario de estudio", self.p_estudio), ("", self.p_activo)):
            f.addRow(et, wd)
        v.addLayout(f)
        bs = QHBoxLayout()
        for texto, fn in (("Nuevo", self._nueva_persona), ("Guardar", self._guardar_persona)):
            b = QPushButton(texto, objectName="primario" if texto == "Guardar" else "")
            b.clicked.connect(fn)
            bs.addWidget(b)
        bs.addStretch()
        v.addLayout(bs)
        self.persona_id = None
        self.pestanas.addTab(w, "Personal")

    def _ver_personal(self):
        todos = self.bd.colaboradores(solo_activos=False)
        self._personal = todos
        llenar(self.t_personal, [(p.nombre, p.tipo, p.horas_sem, p.pct * 100,
                                  "todos" if p.permitidos is None else ", ".join(p.permitidos), p.puesto_fijo or "",
                                  texto_estudio(p.estudio), "Sí" if p.activo else "No") for p in todos])

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
        self.p_perm.setText("" if p.permitidos is None else ", ".join(p.permitidos))
        self.p_puesto.setCurrentIndex(max(0, self.p_puesto.findData(p.puesto_fijo)))
        self.p_estudio.setText(texto_estudio(p.estudio))
        self.p_activo.setChecked(p.activo)

    def _nueva_persona(self):
        self.persona_id = None
        self.t_personal.clearSelection()
        for e in (self.p_nombre, self.p_perm, self.p_estudio):
            e.clear()
        self.p_tipo.setCurrentIndex(0)
        self.p_horas.setValue(42)
        self.p_pct.setValue(100)
        self.p_puesto.setCurrentIndex(0)
        self.p_activo.setChecked(True)
        self.p_nombre.setFocus()

    def _guardar_persona(self):
        nombre = self.p_nombre.text().strip()
        if not nombre:
            return self.avisar("Escribe el nombre del colaborador.", "error")
        try:
            estudio = parsear_estudio(self.p_estudio.text())
        except ValueError as e:
            return self.avisar(str(e), "error")
        perm = tuple(c.strip().upper() for c in self.p_perm.text().split(",") if c.strip()) or None
        mal = [c for c in perm or () if c not in self.ctx.turnos]
        if mal:
            return self.avisar(f"Turnos desconocidos: {', '.join(mal)}. Disponibles: {', '.join(self.ctx.turnos)}.", "error")
        p = Colaborador(self.persona_id or 0, nombre, self.p_tipo.currentText(), self.p_horas.value(),
                        self.p_pct.value() / 100, perm, self.p_puesto.currentData(), estudio, self.p_activo.isChecked())
        self.bd.guardar_colaborador(p)
        self.avisar(f"«{nombre}» guardado. Regenera el cuadro para que lo tome en cuenta.")
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
        v = QVBoxLayout(w)
        v.addWidget(QLabel("Turnos. Hora en formato 24 h (06:00). La pausa se pone a la hora del reloj; «Pagada» la cuenta como trabajada. "
                           "«Cubre» usa M, T y/o N. Un turno en uso se desactiva en lugar de borrarse.", objectName="muted"))
        self.t_turnos = tabla(["Código", "Nombre", "Inicio", "Fin", "Pausa (min)", "Pausa a las", "Pagada", "Cubre",
                               "Dom/fest", "Solver", "Activo", "Color"], editable=True)
        v.addWidget(self.t_turnos)
        bs = QHBoxLayout()
        for texto, fn in (("Nuevo turno", self._nuevo_turno), ("Guardar turnos", self._guardar_turnos)):
            b = QPushButton(texto, objectName="primario" if texto.startswith("Guardar") else "")
            b.clicked.connect(fn)
            bs.addWidget(b)
        bs.addStretch()
        v.addLayout(bs)
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
        t = self.t_turnos
        t.blockSignals(True)
        turnos = list(self.bd.turnos(solo_activos=False).values())
        t.setRowCount(len(turnos))
        for r, x in enumerate(turnos):
            p = x.pausas[0] if x.pausas else None
            vals = [x.codigo, x.nombre, hhmm(x.inicio), hhmm(x.fin), p["min"] if p else 0,
                    hhmm(x.inicio + p["ini"]) if p else "", "Sí" if p and p["pagada"] else "No", ",".join(x.cubre),
                    "Sí" if x.dom_fest else "No", "Sí" if x.solver else "No", "Sí" if x.activo else "No", x.color]
            for c, val in enumerate(vals):
                it = QTableWidgetItem(str(val))
                if c == 0:
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                if c == 11:
                    it.setBackground(QColor("#" + x.color))
                t.setItem(r, c, it)
        t.resizeColumnsToContents()
        t.blockSignals(False)
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
        t = self.t_turnos
        r = t.rowCount()
        t.insertRow(r)
        for c, val in enumerate(["", "", "06:00", "12:00", "0", "", "No", "M", "Sí", "Sí", "Sí", "FFFFFF"]):
            t.setItem(r, c, QTableWidgetItem(val))
        t.editItem(t.item(r, 0))

    def _guardar_turnos(self):
        t, nuevos = self.t_turnos, []
        si = lambda r, c: t.item(r, c).text().strip().lower() in ("sí", "si", "s", "1", "true")
        try:
            for r in range(t.rowCount()):
                txt = lambda c: t.item(r, c).text().strip()
                cod = txt(0).upper()
                if not cod or cod == "L":
                    raise ValueError("Cada turno necesita un código (distinto de L).")
                ini, fin = minutos(txt(2)), minutos(txt(3))
                cubre = tuple(x.strip().upper() for x in txt(7).split(",") if x.strip())
                if any(x not in ("M", "T", "N") for x in cubre):
                    raise ValueError(f"{cod}: «Cubre» solo admite M, T y N.")
                pausas = ()
                if int(txt(4) or 0) > 0:
                    pausas = ({"ini": (minutos(txt(5)) - ini) % 1440, "min": int(txt(4)), "pagada": si(r, 6)},)
                color = txt(11).lstrip("#")
                if len(color) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in color):
                    raise ValueError(f"{cod}: el color debe ser 6 dígitos hexadecimales, ej. FFF2CC.")
                nuevos.append(Turno(cod, txt(1), ini, fin, color.upper(), cubre, pausas, si(r, 8), si(r, 9), si(r, 10)))
            if len({x.codigo for x in nuevos}) != len(nuevos):
                raise ValueError("Hay códigos de turno repetidos.")
            for x in nuevos:
                if x.pausas and not 0 <= x.pausas[0]["ini"] < x.duracion:
                    raise ValueError(f"{x.codigo}: la pausa debe empezar dentro del turno.")
        except (ValueError, AttributeError) as e:
            return self.avisar(f"No se guardó: {e if str(e) and 'int()' not in str(e) else 'revisa horas (06:00) y números.'}", "error")
        for x in nuevos:
            self.bd.guardar_turno(x)
        self.avisar("Turnos guardados. El cuadro existente se revalidó; regenera si hay alertas.")
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
