"""An~: personal, novedades, cuadro mensual, puestos, horas y recargos."""
import os
import re
import subprocess
import sys
import traceback
from datetime import date, datetime, timedelta
from pathlib import Path
from string import Template

from PySide6.QtCore import QDate, QSettings, Qt, QThread, QTime, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QKeySequence, QShortcut
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QCheckBox, QColorDialog, QComboBox, QDateEdit,
                               QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QHeaderView, QInputDialog, QLabel, QLineEdit,
                               QGridLayout, QListWidget, QMainWindow, QMenu, QMessageBox, QPushButton, QSpinBox, QSplitter, QStackedWidget, QTableWidget,
                               QTableWidgetItem, QTabWidget, QTimeEdit, QVBoxLayout, QWidget)

import db
import exportar
import flujo
import recargos
import reglas
import solver
from demanda import franjas_de
from ui_base import con_vacio, hhmm, llenar, signo, sin_seleccion, tabla
from ui_puestos import TabDotacion, TabPuestos
from dominio import DIAS, TIPOS_COLAB, TIPOS_NOVEDAD, Colaborador, Novedad, Turno, texto_estudio
import puestos as puestos_mod
from puestos import etiqueta, leyenda, por_persona

AQUI = Path(__file__).parent
LOG = AQUI / "errores.log"
BD_RUTA = AQUI / "turnos.db"
MESES = flujo.MESES
AMARILLO = "#FFFF00"
ABREV = exportar.ABREV_NOVEDAD

TOKENS = {  # diseño: color, 8 px de ritmo, radio 8 px; contraste de texto ≥ 4.5:1 sobre blanco
    "fondo": "#F4F6F8", "superficie": "#FFFFFF", "borde": "#DDE2E8", "borde_suave": "#EAEDF1", "texto": "#1B2733",
    "suave": "#5B6673", "primario": "#0F6E8C", "primario_h": "#0B566E", "peligro": "#B42318", "foco": "#0B566E",
}
ESTILO = Template("""
QMainWindow, QWidget#fondo { background: $fondo; }
QLabel { color: $texto; }
QLabel#titulo { font-size: 22px; font-weight: 700; }
QLabel#muted { color: $suave; }
QLabel#vacio_t { font-size: 17px; font-weight: 600; color: $texto; }
QLabel#aviso { border-radius: 8px; border-left: 4px solid #2F7FA6; padding: 10px 14px; background: #E8F1F8; color: #0F3B57; }
QLabel#aviso[nivel="warn"] { background: #FFF4D6; color: #5C4300; border-left-color: #D99A00; }
QLabel#aviso[nivel="error"] { background: #FDE8E8; color: #8E1B1B; border-left-color: $peligro; }
QPushButton { background: $superficie; border: 1px solid #C5CCD5; border-radius: 8px; padding: 7px 14px; color: $texto; }
QPushButton:hover { background: #EEF2F6; }
QPushButton:pressed { background: #E2E8EE; }
QPushButton:focus { border: 2px solid $foco; padding: 6px 13px; }
QPushButton:disabled { color: #8A94A0; background: $fondo; border-color: $borde; }
QPushButton#primario { background: $primario; border-color: $primario; color: white; font-weight: 600; }
QPushButton#primario:hover { background: $primario_h; }
QPushButton#primario:pressed { background: #08485D; }
QPushButton#primario:focus { border: 2px solid #072F3F; }
QPushButton#primario:disabled { background: #9DBFCB; border-color: #9DBFCB; color: white; }
QPushButton#peligro { color: $peligro; border-color: #E8B8B3; }
QPushButton#peligro:hover { background: #FDE8E8; }
QPushButton#peligro:disabled { color: #C9A6A2; background: $fondo; border-color: $borde; }
QComboBox, QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox { background: $superficie; border: 1px solid #C5CCD5; border-radius: 8px; padding: 5px 8px; }
QComboBox:focus, QLineEdit:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid $foco; padding: 4px 7px; }
QComboBox:disabled, QLineEdit:disabled { background: $fondo; color: #8A94A0; }
QTabWidget::pane { border: 1px solid $borde; border-radius: 10px; background: $superficie; top: -1px; }
QTabBar::tab { padding: 9px 16px; color: $suave; border: none; border-bottom: 2px solid transparent; }
QTabBar::tab:hover { color: $texto; }
QTabBar::tab:selected { color: $primario; border-bottom: 2px solid $primario; font-weight: 600; }
QTableWidget { outline: 0; border: none; gridline-color: $borde_suave; selection-background-color: #D6E9F0; selection-color: $texto; background: $superficie; alternate-background-color: #FAFBFC; }
QHeaderView::section { background: #F7F8FA; border: none; border-bottom: 1px solid $borde; padding: 7px 8px; color: $suave; font-weight: 600; }
QGroupBox { background: $superficie; border: 1px solid $borde; border-radius: 10px; margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: $primario; }
QCheckBox { spacing: 8px; color: $texto; }
QLabel#cifra { font-size: 26px; font-weight: 700; color: $primario; }
QListWidget { border: 1px solid $borde; border-radius: 8px; background: $superficie; padding: 4px; }
QSplitter::handle { background: transparent; }
QToolTip { background: #1B2733; color: white; border: none; padding: 6px 8px; }
""").substitute(TOKENS)


def abrir(ruta):
    if sys.platform == "win32":
        os.startfile(ruta)  # noqa: E1101 (solo existe en Windows)
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


class Grilla(QTableWidget):
    """Tabla del cuadro: al soltar una celda sobre otra emite `soltada(origen_fila, origen_col, destino_fila, destino_col)`."""
    soltada = Signal(int, int, int, int)

    def startDrag(self, acciones):
        self._origen = (self.currentRow(), self.currentColumn())
        super().startDrag(acciones)

    def dropEvent(self, e):
        d = self.indexAt(e.position().toPoint())
        if d.isValid() and (d.row(), d.column()) != self._origen:
            self.soltada.emit(*self._origen, d.row(), d.column())
        e.setDropAction(Qt.CopyAction)  # evita que Qt vacíe la celda de origen
        e.accept()


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
        self._deshacer = []
        QShortcut(QKeySequence.Undo, self, activated=self.deshacer)
        hoy = date.today()
        raiz = QWidget(objectName="fondo")
        self.setCentralWidget(raiz)
        v = QVBoxLayout(raiz)
        v.setContentsMargins(16, 12, 16, 16)
        v.setSpacing(10)
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
        lunes = hoy - timedelta(days=hoy.weekday())
        self.f_inicio = QDateEdit(QDate(lunes.year, lunes.month, lunes.day))
        self.f_inicio.setCalendarPopup(True)
        self.f_inicio.setDisplayFormat("dd/MM/yyyy")
        self.l_periodo = QLabel("", objectName="muted")
        self.b_ant, self.b_sig = QPushButton("◀"), QPushButton("▶")
        for b, d in ((self.b_ant, -1), (self.b_sig, 1)):
            b.setFixedWidth(36)
            b.clicked.connect(lambda _=False, d=d: self._mover_periodo(d))
        self.e_mes, self.e_semanas = QLabel("Mes:"), QLabel("Desde el lunes:")
        cab.addWidget(self.b_ant)
        for x in (self.e_mes, self.mes, self.año, self.e_semanas, self.f_inicio, self.l_periodo):
            cab.addWidget(x)
        cab.addWidget(self.b_sig)
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
        self._pestana_banco()
        self.tab_dotacion = TabDotacion(self)
        self.pestanas.addTab(self.tab_dotacion, "Dotación")
        self._pestana_parametros()
        for señal in (self.mes.currentIndexChanged, self.año.valueChanged, self.pestanas.currentChanged):
            señal.connect(lambda _: self._cambio_vista())
        self.f_inicio.dateChanged.connect(self._cambio_inicio)
        for sp in self.findChildren(QSpinBox) + self.findChildren(QDoubleSpinBox):
            sp.lineEdit().setTextMargins(6, 0, 0, 0)
        for b in self.findChildren(QPushButton):
            b.setCursor(Qt.PointingHandCursor)
        self.pestanas.tabBar().setCursor(Qt.PointingHandCursor)
        self.pestanas.setFocus()  # el primer foco no cae sobre un botón de navegación
        self.refrescar()

    # --- utilidades -----------------------------------------------------------------------------
    @property
    def modo_periodo(self):
        return self.bd.param("periodo_modo", "mes")

    def periodo(self):
        """(inicio, fin) del esquema en pantalla: un mes calendario o N semanas completas desde un lunes."""
        if self.modo_periodo == "semanas":
            return flujo.periodo_semanas(self.f_inicio.date().toPython(), int(self.bd.param("periodo_semanas", 4)))
        return flujo.periodo_mes(self.año.value(), self.mes.currentIndex() + 1)

    @property
    def clave(self):
        return flujo.clave(*self.periodo())

    @property
    def fechas(self):
        return flujo.fechas(*self.periodo())

    def _mostrar_selector(self):
        semanas = self.modo_periodo == "semanas"
        for x in (self.e_mes, self.mes, self.año):
            x.setVisible(not semanas)
        for x in (self.e_semanas, self.f_inicio):
            x.setVisible(semanas)
        ini, fin = self.periodo()
        self.l_periodo.setText((f"{ini:%d/%m} – {fin:%d/%m/%Y} · {(fin - ini).days // 7 + 1} sem." if semanas
                                else f"{(fin - ini).days + 1} días") + (" · CERRADO" if self.bd.periodo_cerrado(self.clave) else ""))

    def _mover_periodo(self, d):
        if self.modo_periodo == "semanas":
            n = int(self.bd.param("periodo_semanas", 4))
            self.f_inicio.setDate(self.f_inicio.date().addDays(7 * n * d))
        else:
            i = self.mes.currentIndex() + d
            if not 0 <= i < 12:
                self.año.setValue(self.año.value() + (1 if i > 11 else -1))
                i %= 12
            self.mes.setCurrentIndex(i)

    def _cambio_inicio(self, q):
        d = q.toPython()
        if d.weekday() != 0:  # los esquemas por semanas arrancan en lunes
            self.f_inicio.setDate(q.addDays(-d.weekday()))  # dispara de nuevo esta función con el lunes
            self.avisar("El esquema por semanas arranca en lunes; ajusté la fecha al lunes anterior.", "warn")
            return
        self._cambio_vista()

    def avisar(self, texto, nivel="info"):
        self.aviso.setProperty("nivel", nivel)
        self.aviso.style().unpolish(self.aviso)
        self.aviso.style().polish(self.aviso)
        self.aviso.setText(texto)
        self.aviso.setVisible(bool(texto))

    def _cambio_vista(self):
        self._deshacer.clear()
        self.avisar("")
        self.refrescar()

    def refrescar(self):
        self._mostrar_selector()
        self.ctx = self.bd.contexto(self.periodo()[0].year)
        self.nombres = {p.id: p.nombre for p in self.ctx.colabs}
        for f in (self._ver_cuadro, self._ver_personal, self._ver_novedades, self._ver_puestos, self._ver_horas,
                  self._ver_banco, self.tab_dotacion.refrescar, self._ver_parametros):
            f()

    # --- cuadro ---------------------------------------------------------------------------------
    def _pestana_cuadro(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(16, 14, 16, 16)
        v.setSpacing(10)
        barra = QHBoxLayout()
        barra.setSpacing(8)
        self.version = QComboBox()
        self.version.addItems(["Cambios", "Original"])
        self.version.setToolTip("Cambios es la copia de trabajo; Original es la versión publicada")
        self.version.currentIndexChanged.connect(lambda _: self._ver_cuadro())
        barra.addWidget(QLabel("Ver"))
        barra.addWidget(self.version)
        self.ver_puesto = QCheckBox("Mostrar puesto")
        self.ver_puesto.toggled.connect(lambda _: self._ver_cuadro())
        barra.addWidget(self.ver_puesto)
        barra.addSpacing(16)
        self.b_generar = QPushButton("Generar…", objectName="primario")
        m = QMenu(self.b_generar)
        m.addAction("Generar desde cero (descarta mis cambios)", lambda: self.generar("cero"))
        m.addAction("Regenerar respetando mis cambios", lambda: self.generar("respetar"))
        m.addAction("Regenerar solo una semana…", self.generar_semana)
        self.b_generar.setMenu(m)
        barra.addWidget(self.b_generar)
        for texto, f in (("Publicar como original", self.publicar), ("Restaurar desde original…", self.restaurar)):
            b = QPushButton(texto)
            b.clicked.connect(f)
            barra.addWidget(b)
        barra.addStretch()
        b = QPushButton("Exportar Excel")
        b.clicked.connect(self.exportar)
        barra.addWidget(b)
        self.b_cierre = QPushButton("Cerrar periodo")
        self.b_cierre.setToolTip("Congela las horas del periodo en el banco de horas y deja el cuadro en solo lectura")
        self.b_cierre.clicked.connect(self._alternar_cierre)
        barra.addWidget(self.b_cierre)
        v.addLayout(barra)

        self.pila_cuadro = QStackedWidget()
        cuerpo = QSplitter(Qt.Vertical)
        arriba = QWidget()
        va = QVBoxLayout(arriba)
        va.setContentsMargins(0, 0, 0, 0)
        va.setSpacing(8)
        self.grilla = Grilla()
        self.grilla.itemChanged.connect(self._celda_editada)
        self.grilla.soltada.connect(self._mover_celda)
        self.grilla.setDragEnabled(True)
        self.grilla.setAcceptDrops(True)
        self.grilla.setDropIndicatorShown(True)
        self.grilla.setDragDropMode(QAbstractItemView.DragDrop)
        self.grilla.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.grilla.setContextMenuPolicy(Qt.CustomContextMenu)
        self.grilla.customContextMenuRequested.connect(self._menu_lote)
        va.addWidget(self.grilla, 1)
        self.leyenda = QLabel(objectName="muted")
        self.leyenda.setTextFormat(Qt.RichText)
        self.leyenda.setWordWrap(True)
        va.addWidget(self.leyenda)
        cuerpo.addWidget(arriba)
        self.panel_inf = QTabWidget()
        self.alertas, self.lista_cambios = QListWidget(), QListWidget()
        self.panel_inf.addTab(self.alertas, "Alertas")
        self.panel_inf.addTab(self.lista_cambios, "Cambios respecto al original")
        cuerpo.addWidget(self.panel_inf)
        cuerpo.setStretchFactor(0, 5)
        cuerpo.setStretchFactor(1, 1)
        cuerpo.setChildrenCollapsible(False)
        cuerpo.setSizes([620, 150])
        self.pila_cuadro.addWidget(cuerpo)

        vacio = QWidget()
        lv = QVBoxLayout(vacio)
        lv.addStretch()
        for txt, nombre in (("Este periodo aún no tiene cuadro", "vacio_t"),
                            ("Genera una propuesta con las reglas, el personal y las novedades que ya registraste. "
                             "Después puedes ajustar celda por celda.", "muted")):
            e = QLabel(txt, objectName=nombre, alignment=Qt.AlignCenter)
            e.setWordWrap(True)
            lv.addWidget(e)
        self.b_generar_vacio = QPushButton("Generar cuadro", objectName="primario")
        self.b_generar_vacio.clicked.connect(lambda: self.generar("cero"))
        lv.addWidget(self.b_generar_vacio, alignment=Qt.AlignCenter)
        lv.addStretch()
        self.pila_cuadro.addWidget(vacio)
        v.addWidget(self.pila_cuadro, 1)
        self.pestanas.addTab(w, "Cuadro")

    def _leyenda_html(self):
        chip = lambda txt, bg, extra="": f'<span style="background-color:{bg}; color:#1B2733; {extra}">&nbsp;{txt}&nbsp;</span>'
        partes = [chip(c, "#" + t.color) + f" {t.nombre}" for c, t in self.ctx.turnos.items()]
        partes += [chip("L", "#FFFFFF") + " Libre", chip("VAC", "#D9D9D9") + " Novedad", chip("//", "#E3E6FA", "color:#4357A8;") + " Estudia",
                   chip("M", AMARILLO) + " Cambiado", chip("−1", "#FF9EA1") + " Falta cobertura"]
        ayuda = "Arrastra una celda sobre otra para intercambiarlas · clic derecho: asignar a varias · Ctrl+Z: deshacer"
        if self.ver_puesto.isChecked():
            ayuda = leyenda(self.bd.catalogo_puestos()) + "<br>" + ayuda
        return "&nbsp;&nbsp;&nbsp;".join(partes) + "<br>" + ayuda

    def _ver_cuadro(self):
        fechas, k = self.fechas, self.clave
        orig = self.bd.asignaciones(k, "original")
        ver_orig = self.version.currentText() == "Original"
        cerrado = self.bd.periodo_cerrado(k)
        self.b_cierre.setText("Reabrir periodo" if cerrado else "Cerrar periodo")
        self.leyenda.setText(self._leyenda_html())
        cuadro = orig if ver_orig else self.bd.asignaciones(k)
        cat = self.bd.catalogo_puestos()
        filas_pu = [] if ver_orig else self.bd.asignacion_puesto(k)  # el reparto se calcula sobre «Cambios»
        puesto = por_persona(filas_pu, {i: q.numero for i, q in cat.items()})
        detalle = {}
        for a in filas_pu:
            nombre = cat[a.puesto_id].nombre if a.puesto_id in cat else "Apoyo"
            detalle.setdefault((a.colab_id, a.fecha), []).append(f"{nombre} {hhmm(a.desde)}–{hhmm(a.hasta % 1440 or 1440)}")
        gente = [p for p in self.ctx.colabs if p.en_solver]
        g = self.grilla
        g.blockSignals(True)
        g.clear()
        g.setRowCount(len(gente) + 3)
        g.setColumnCount(len(fechas) + 1)
        g.setHorizontalHeaderLabels([f"{DIAS[f.weekday()]}\n{f.day}" for f in fechas] + ["Horas"])
        g.setVerticalHeaderLabels([p.nombre for p in gente] + ["Cobertura mañana", "Cobertura tarde", "Cobertura noche"])
        for r, p in enumerate(gente):
            horas = 0
            for c, f in enumerate(fechas):
                cod = cuadro.get((p.id, f), "L")
                nov = self.ctx.novedad(p.id, f)
                pu = puesto.get((p.id, f))
                texto = ABREV[nov.tipo] if nov and cod == "L" else cod
                if pu is not None and cod in self.ctx.turnos:
                    texto = etiqueta(cod, pu) if self.ver_puesto.isChecked() else cod
                it = QTableWidgetItem(texto)
                it.setTextAlignment(Qt.AlignCenter)
                it.setData(Qt.UserRole, cod)
                if cod in self.ctx.turnos:
                    it.setBackground(QColor("#" + self.ctx.turnos[cod].color))
                    horas += self.ctx.turnos[cod].horas
                elif nov:
                    it.setBackground(QColor("#D9D9D9"))
                if pu is not None and cod in self.ctx.turnos:
                    it.setToolTip("Puesto: " + "; ".join(detalle[p.id, f]))
                estudia = [("Mañana", "Tarde")["MT".index(fr)] for dia, fr in p.estudio if dia == f.weekday()]
                if estudia:
                    it.setToolTip((it.toolTip() + "\n" if it.toolTip() else "") + "Estudia: " + " y ".join(x.lower() for x in estudia))
                    if cod == "L" and not nov:
                        it.setBackground(QBrush(QColor("#9AA8E0"), Qt.BDiagPattern))  # trama: no se confunde con la noche
                if not ver_orig and orig.get((p.id, f), "L") != cod:
                    it.setBackground(QColor(AMARILLO))
                if ver_orig or cerrado or nov and cod == "L":
                    it.setFlags(it.flags() & ~Qt.ItemIsEditable)
                g.setItem(r, c, it)
            h = QTableWidgetItem(f"{horas:g}")
            h.setFlags(Qt.ItemIsEnabled)
            g.setItem(r, len(fechas), h)
        faltantes = reglas.faltantes_periodo(self.ctx, cuadro, fechas)
        for i, fr in enumerate(("M", "T", "N")):
            for c, f in enumerate(fechas):
                peor, rangos = faltantes[f][fr]
                it = QTableWidgetItem("ok" if not peor else f"−{peor}")
                it.setTextAlignment(Qt.AlignCenter)
                it.setFlags(Qt.ItemIsEnabled)
                if peor:
                    it.setBackground(QColor("#FF9EA1"))
                    it.setToolTip("Faltan personas: " + "; ".join(f"{reglas.texto_tramos(a, b)} (−{n})" for a, b, n in rangos))
                g.setItem(len(gente) + i, c, it)
        for c, f in enumerate(fechas):
            if self.ctx.tipo_dia(f) == "DF":
                g.horizontalHeaderItem(c).setBackground(QColor("#F8CBAD"))
        g.horizontalHeader().setDefaultSectionSize(40)
        g.setColumnWidth(len(fechas), 56)
        g.setEditTriggers(QAbstractItemView.DoubleClicked | QAbstractItemView.EditKeyPressed)
        g.blockSignals(False)
        hay_cuadro = bool(cuadro)
        self.pila_cuadro.setCurrentIndex(0 if hay_cuadro else 1)
        self.alertas.clear()
        self.lista_cambios.clear()
        alertas = [a.texto for a in reglas.validar(self.ctx, self.bd.asignaciones(k), fechas, self.bd.fijos(k))] if hay_cuadro else []
        if hay_cuadro:
            alertas += [a.texto for a in puestos_mod.alertas_reparto(self.ctx, self.bd.asignacion_puesto(k), fechas, cat)]
        alertas += ["Aviso: " + a.texto for a in reglas.validar_catalogo(self.ctx.turnos)]
        cambios = [f"{self.nombres.get(cid, cid)} · {f:%d/%m}: {antes} → {ahora}"
                   for cid, f, antes, ahora in self.bd.diferencias(k)] if hay_cuadro else []
        self.alertas.addItems(alertas or ["Todo en orden: sin alertas."])
        self.lista_cambios.addItems(cambios or ["Sin cambios respecto al original."])
        self.panel_inf.setTabText(0, f"Alertas ({len(alertas)})")
        self.panel_inf.setTabText(1, f"Cambios respecto al original ({len(cambios)})")

    def _gente(self):
        return [p for p in self.ctx.colabs if p.en_solver]

    def _editable(self, r, c):
        """Persona y fecha de la celda (r, c) si se puede cambiar; None si es de totales, novedad u original."""
        gente = self._gente()
        if r >= len(gente) or c >= len(self.fechas) or self.version.currentText() == "Original" or self.bd.periodo_cerrado(self.clave):
            return None
        p, f = gente[r], self.fechas[c]
        nov = self.ctx.novedad(p.id, f)
        return None if nov and self.bd.asignaciones(self.clave).get((p.id, f), "L") == "L" else (p, f)

    def _aplicar(self, cambios, texto):
        """cambios: [(persona, fecha, código)]. Guarda, recalcula, deja deshacer y avisa de reglas que se rompen."""
        k, cuadro = self.clave, self.bd.asignaciones(self.clave)
        self._deshacer.append([(p.id, f, cuadro.get((p.id, f), "L")) for p, f, _ in cambios])
        motivos = []
        for p, f, cod in cambios:
            self.bd.set_celda(k, p.id, f, cod)
            if cod != "L" and (m := self.ctx.bloqueo(p, self.ctx.turnos[cod], f)):
                motivos.append(f"{p.nombre} {f:%d/%m}: {m}")
        flujo.recalcular(self.bd, *self.periodo(), self.ctx)
        self.avisar(texto + (" — ojo: " + "; ".join(motivos[:3]) + "." if motivos else ""), "warn" if motivos else "info")
        self._ver_cuadro()

    def _celda_editada(self, it):
        celda = self._editable(it.row(), it.column())
        if not celda:
            return
        p, f = celda
        cod = it.text().split("·")[0].strip().upper() or "L"  # «M·2» (con puesto) se lee como M
        if cod != "L" and cod not in self.ctx.turnos:
            self.avisar(f"«{cod}» no es un turno. Usa L o uno de: {', '.join(self.ctx.turnos)}.", "error")
            self._ver_cuadro()
        else:
            self._aplicar([(p, f, cod)], f"{p.nombre} · {f:%d/%m}: {cod}")

    def _mover_celda(self, r1, c1, r2, c2):
        """Intercambia el contenido de dos celdas (arrastrar y soltar)."""
        a, b = self._editable(r1, c1), self._editable(r2, c2)
        if not (a and b):
            return self.avisar("Esa celda no se puede cambiar (novedad, totales, vista Original o periodo cerrado).", "warn")
        cuadro = self.bd.asignaciones(self.clave)
        x, y = cuadro.get((a[0].id, a[1]), "L"), cuadro.get((b[0].id, b[1]), "L")
        if x == y:
            return
        self._aplicar([(a[0], a[1], y), (b[0], b[1], x)],
                      f"Intercambio: {a[0].nombre} {a[1]:%d/%m} ({x}) ⇄ {b[0].nombre} {b[1]:%d/%m} ({y})")

    def _menu_lote(self, pos):
        celdas = [c for i in self.grilla.selectedIndexes() if (c := self._editable(i.row(), i.column()))]
        if not celdas:
            return
        m = QMenu(self)
        m.addSection(f"Asignar a {len(celdas)} celda(s)")
        for cod in [*self.ctx.turnos, "L"]:
            m.addAction(cod if cod != "L" else "L · libre", lambda cod=cod: self._aplicar(
                [(p, f, cod) for p, f in celdas], f"{len(celdas)} celda(s) → {cod}"))
        m.exec(self.grilla.viewport().mapToGlobal(pos))

    def deshacer(self):
        if not self._deshacer or self.version.currentText() == "Original" or self.bd.periodo_cerrado(self.clave):
            return
        k, orig = self.clave, self.bd.asignaciones(self.clave, "original")
        for cid, f, antes in self._deshacer.pop():
            if orig.get((cid, f), "L") == antes:
                self.bd.restaurar(k, {cid}, {f})
            else:
                self.bd.set_celda(k, cid, f, antes)
        flujo.recalcular(self.bd, *self.periodo(), self.ctx)
        self.avisar("Cambio deshecho.")
        self._ver_cuadro()

    def generar(self, modo, lunes=None):
        if self.trabajo and self.trabajo.isRunning():
            return
        if self.bd.periodo_cerrado(self.clave):
            return self.avisar("Este periodo está cerrado. Reábrelo para volver a generar o editar.", "warn")
        k = self.clave
        if modo == "cero" and self.bd.diferencias(k):
            if QMessageBox.question(self, "Generar desde cero", "Hay cambios manuales sobre el original. "
                                    "¿Descartarlos y generar de nuevo?") != QMessageBox.Yes:
                return
        if not any(p.en_solver for p in self.ctx.colabs):
            return self.avisar("Primero agrega personal en la pestaña «Personal».", "warn")
        ctx, fechas, kw = flujo.preparar(self.bd, *self.periodo(), modo, lunes)
        self.b_generar.setEnabled(False)
        self.avisar("Generando el cuadro… puede tardar hasta 20 segundos.")
        self.trabajo = Trabajo(ctx, fechas, kw)
        self.trabajo.listo.connect(lambda cuadro, info: self._generado(ctx, fechas, cuadro, info, modo))
        self.trabajo.fallo.connect(self._fallo)
        self.trabajo.start()

    def _generado(self, ctx, fechas, cuadro, info, modo):
        self._deshacer.clear()
        self.b_generar.setEnabled(True)
        flujo.terminar(self.bd, *self.periodo(), ctx, fechas, cuadro, modo)
        if info["faltan"]:
            dias = ", ".join(f"{d:%d/%m} {hhmm(t * 30)} (faltan {n})" for d, t, n in info["faltan"][:6])
            self.avisar("No se pudo cubrir todo: " + dias + ". Revisa novedades y personal disponible.", "warn")
        else:
            comp = info.get("ajuste") or {}
            extra = (f" Se compensó el banco de horas de {len(comp)} persona(s): " + ", ".join(
                f"{self.nombres.get(c, c)} {h:+g} h" for c, h in list(comp.items())[:4]) + ("…" if len(comp) > 4 else ".")) if comp else ""
            self.avisar("Cuadro generado. Cobertura completa y reglas cumplidas." + extra)
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

    def _cerrado_aviso(self):
        if self.bd.periodo_cerrado(self.clave):
            self.avisar("Este periodo está cerrado. Reábrelo para cambiarlo.", "warn")
            return True

    def publicar(self):
        if self._cerrado_aviso():
            return
        if QMessageBox.question(self, "Publicar", "El cuadro actual pasará a ser el «original». ¿Continuar?") == QMessageBox.Yes:
            self.bd.publicar(self.clave)
            self._deshacer.clear()
            self.avisar("Cuadro publicado como original.")
            self._ver_cuadro()

    def restaurar(self):
        if self._cerrado_aviso():
            return
        if QMessageBox.question(self, "Restaurar", "Se devolverán todas las celdas al original. ¿Continuar?") == QMessageBox.Yes:
            self.bd.restaurar(self.clave)
            self._deshacer.clear()
            flujo.recalcular(self.bd, *self.periodo())
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
        txt = flujo.etiqueta(*self.periodo())
        tar, ventana = self.bd.tarifas(), int(self.bd.param("ventana_semanas", 3))
        with ocupado():
            a = exportar.exportar_cuadro(carpeta, txt, self.ctx, cuadro, self.bd.asignaciones(k, "original"), fechas,
                                         self.bd.diferencias(k), self.bd.asignacion_puesto(k), self.bd.catalogo_puestos())
            b = exportar.exportar_puestos(carpeta, txt, self.ctx, cuadro, fechas, self.bd.asignacion_puesto(k),
                                          self.bd.capacitacion(k), self.bd.catalogo_puestos())
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
        self.t_personal = tabla(["Nombre", "Tipo", "Horas/sem", "Turnos", "Puestos", "Estudio", "Estado"])
        self.t_personal.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_personal.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_personal.itemSelectionChanged.connect(self._cargar_persona)
        izq.addWidget(con_vacio(self.t_personal, "Aún no hay colaboradores", "Usa «+ Nuevo colaborador» para agregar al personal del servicio."))
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
        self.p_puestos_caja = QGridLayout()
        self.p_puestos_caja.setHorizontalSpacing(16)
        self.p_puestos_cbs = {}  # id de puesto -> casilla
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
                       ("% de jornada", self.p_pct), ("Puede hacer", self.p_perm_caja), ("Puestos que puede ocupar", self.p_puestos_caja),
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

    def _armar_puestos_permitidos(self):
        """Una casilla por puesto activo; conserva lo marcado."""
        activos = self.bd.catalogo_puestos(solo_activos=True)
        if list(self.p_puestos_cbs) == list(activos):
            return
        marcado = {i: cb.isChecked() for i, cb in self.p_puestos_cbs.items()}
        while self.p_puestos_caja.count():
            cb = self.p_puestos_caja.takeAt(0).widget()
            cb.setParent(None)
            cb.deleteLater()
        self.p_puestos_cbs = {}
        for k, (i, p) in enumerate(activos.items()):
            cb = QCheckBox(f"{p.numero} · {p.nombre}")
            cb.setChecked(marcado.get(i, True))
            self.p_puestos_cbs[i] = cb
            self.p_puestos_caja.addWidget(cb, k // 2, k % 2)

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
        self._armar_puestos_permitidos()
        numeros = {i: p.numero for i, p in self.bd.catalogo_puestos().items()}
        llenar(self.t_personal,
               [(p.nombre, p.tipo, f"{p.horas_sem:g} h ({p.pct * 100:g} %)",
                 "todos" if p.permitidos is None else ", ".join(p.permitidos),
                 "todos" if p.puestos_permitidos is None else ", ".join(str(numeros.get(i, "?")) for i in p.puestos_permitidos),
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
        for i, cb in self.p_puestos_cbs.items():
            cb.setChecked(p.puestos_permitidos is None or i in p.puestos_permitidos)
        for rr in range(2):
            for c in range(7):
                self.p_est.item(rr, c).setCheckState(Qt.Checked if (c, "MT"[rr]) in p.estudio else Qt.Unchecked)
        self.p_activo.setChecked(p.activo)
        self.b_borrar_persona.setEnabled(True)

    def _nueva_persona(self):
        self.persona_id = None
        sin_seleccion(self.t_personal)
        self.p_nombre.clear()
        self.p_tipo.setCurrentIndex(0)
        self.p_horas.setValue(42)
        self.p_pct.setValue(100)
        for cb in self.p_perm_cbs.values():
            cb.setChecked(True)
        for cb in self.p_puestos_cbs.values():
            cb.setChecked(True)
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
        puestos = tuple(i for i, cb in self.p_puestos_cbs.items() if cb.isChecked())
        if not puestos:
            return self.avisar("Marca al menos un puesto que pueda ocupar.", "error")
        perm_puestos = None if len(puestos) == len(self.p_puestos_cbs) else puestos
        fijo = self.bd.catalogo_puestos()[puestos[0]].numero if perm_puestos and len(puestos) == 1 else None
        p = Colaborador(self.persona_id or 0, nombre, self.p_tipo.currentText(), self.p_horas.value(),
                        self.p_pct.value() / 100, perm, fijo, estudio, self.p_activo.isChecked(), perm_puestos)
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
        h = QHBoxLayout(w)
        h.setContentsMargins(16, 14, 16, 16)
        h.setSpacing(16)
        self.t_nov = tabla(["Colaborador", "Tipo", "Desde", "Hasta", "Nota"])
        self.t_nov.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_nov.setSelectionMode(QAbstractItemView.SingleSelection)
        h.addWidget(con_vacio(self.t_nov, "Sin novedades registradas", "Registra vacaciones, incapacidades, licencias o "
                                                                        "días libres para que el generador los respete."), 3)
        caja = QGroupBox("Nueva novedad")
        caja.setMinimumWidth(420)
        f = QFormLayout(caja)
        self.n_colab, self.n_tipo = QComboBox(), QComboBox()
        self.n_tipo.addItems(TIPOS_NOVEDAD)
        self.n_desde, self.n_hasta = QDateEdit(QDate.currentDate()), QDateEdit(QDate.currentDate())
        for d in (self.n_desde, self.n_hasta):
            d.setCalendarPopup(True)
            d.setDisplayFormat("dd/MM/yyyy")
        self.n_nota = QLineEdit()
        self.n_nota.setPlaceholderText("Opcional")
        for et, wd in (("Colaborador", self.n_colab), ("Tipo", self.n_tipo), ("Desde", self.n_desde),
                       ("Hasta", self.n_hasta), ("Nota", self.n_nota)):
            f.addRow(et, wd)
        bs = QHBoxLayout()
        b1, b2 = QPushButton("Agregar novedad", objectName="primario"), QPushButton("Borrar la seleccionada", objectName="peligro")
        b1.clicked.connect(self._agregar_novedad)
        b2.clicked.connect(self._borrar_novedad)
        bs.addWidget(b1)
        bs.addWidget(b2)
        bs.addStretch()
        f.addRow(bs)
        h.addWidget(caja, 0, Qt.AlignTop)
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
        self.t_puestos = tabla(["Día", "Apoyo"])  # las columnas por puesto se arman al mostrar
        v.addWidget(con_vacio(self.t_puestos, "Sin puestos asignados", "Se calculan al generar el cuadro del periodo."), 3)
        v.addWidget(QLabel("Capacitación del mes", objectName="muted"))
        self.l_cap = QListWidget()
        v.addWidget(self.l_cap, 1)
        self.pestanas.addTab(w, "Puestos y capacitación")

    def _ver_puestos(self):
        k = self.clave
        cat = self.bd.catalogo_puestos()
        filas_pu = self.bd.asignacion_puesto(k)
        usados = sorted({a.puesto_id for a in filas_pu if a.puesto_id in cat} | {i for i, q in cat.items() if q.activo},
                        key=lambda i: cat[i].numero)
        t = self.t_puestos
        t.setColumnCount(len(usados) + 2)
        t.setHorizontalHeaderLabels(["Día"] + [f"{cat[i].numero} · {cat[i].nombre}" for i in usados] + ["Apoyo"])
        celdas = {}
        for a in filas_pu:
            celdas.setdefault((a.fecha, a.puesto_id), []).append(
                f"{self.nombres.get(a.colab_id, a.colab_id)} {hhmm(a.desde)}–{hhmm(a.hasta % 1440 or 1440)} (P{a.pausa})")
        filas = [(f"{DIAS[f.weekday()]} {f:%d/%m}", *["\n".join(celdas.get((f, i), [])) for i in usados],
                  "\n".join(celdas.get((f, 0), []))) for f in self.fechas] if filas_pu else []
        llenar(t, filas, lambda r, c: "#F8CBAD" if c == 0 and self.ctx.tipo_dia(self.fechas[r]) == "DF" else None)
        t.resizeRowsToContents()
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
        v.addWidget(con_vacio(self.t_horas, "Sin horas que mostrar", "Genera el cuadro de este periodo en la pestaña Cuadro."), 1)
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

    # --- historial y banco de horas -------------------------------------------------------------
    def _pestana_banco(self):
        self.sub_banco = QTabWidget()
        w = QWidget()
        h = QHBoxLayout(w)
        izq = QVBoxLayout()
        izq.addWidget(QLabel("Saldo de horas por persona. Positivo: se le deben horas. Negativo: debe horas. «Este periodo» "
                             "es proyectado hasta que lo cierres.", objectName="muted"))
        self.t_banco = tabla(["Colaborador", "Saldo anterior", "Este periodo", "Saldo total", "Estado"])
        self.t_banco.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_banco.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_banco.itemSelectionChanged.connect(self._ver_movimientos)
        izq.addWidget(con_vacio(self.t_banco, "Sin personal para mostrar", "Agrega colaboradores en la pestaña Personal."))
        h.addLayout(izq, 3)
        caja = QGroupBox("Movimientos de la persona")
        caja.setMinimumWidth(470)
        v = QVBoxLayout(caja)
        self.t_movs = tabla(["Fecha", "Concepto", "Horas", "Detalle"])
        self.t_movs.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_movs.setSelectionMode(QAbstractItemView.SingleSelection)
        v.addWidget(con_vacio(self.t_movs, "Sin movimientos", "Selecciona una persona. Los cierres de periodo y los movimientos que registres aparecen aquí."))
        f = QFormLayout()
        self.m_fecha = QDateEdit(QDate.currentDate())
        self.m_fecha.setCalendarPopup(True)
        self.m_fecha.setDisplayFormat("dd/MM/yyyy")
        self.m_concepto = QComboBox()
        self.m_concepto.addItems(list(flujo.CONCEPTOS_BANCO))
        self.m_horas = QDoubleSpinBox()
        self.m_horas.setRange(-500, 500)
        self.m_horas.setDecimals(1)
        self.m_horas.setSingleStep(0.5)
        self.m_horas.setSuffix(" h")
        self.m_nota = QLineEdit()
        self.m_concepto.currentTextChanged.connect(self._pista_movimiento)
        self.l_pista = QLabel("", objectName="muted")
        self.l_pista.setWordWrap(True)
        for et, wd in (("Fecha", self.m_fecha), ("Concepto", self.m_concepto), ("Horas", self.m_horas),
                       ("Nota", self.m_nota), ("", self.l_pista)):
            f.addRow(et, wd)
        v.addLayout(f)
        botones = QHBoxLayout()
        reg = QPushButton("Registrar", objectName="primario")
        self.b_borrar_mov = QPushButton("Borrar el seleccionado", objectName="peligro")
        reg.clicked.connect(self._registrar_movimiento)
        self.b_borrar_mov.clicked.connect(self._borrar_movimiento)
        botones.addWidget(reg)
        botones.addWidget(self.b_borrar_mov)
        botones.addStretch()
        v.addLayout(botones)
        h.addWidget(caja, 0)
        self.sub_banco.addTab(w, "Banco de horas")

        w = QWidget()
        v = QVBoxLayout(w)
        barra = QHBoxLayout()
        ir = QPushButton("Abrir el periodo seleccionado", objectName="primario")
        ir.clicked.connect(self._ir_al_periodo)
        barra.addWidget(ir)
        barra.addStretch()
        v.addLayout(barra)
        self.t_hist = tabla(["Periodo", "Días", "Estado", "Personas", "Horas trabajadas", "Saldo del periodo",
                             "Cambios vs original", "Alertas"])
        self.t_hist.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_hist.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_hist.itemDoubleClicked.connect(lambda _: self._ir_al_periodo())
        v.addWidget(con_vacio(self.t_hist, "Aún no hay esquemas con cuadro", "Cuando generes un cuadro, el periodo queda en este historial."))
        v.addWidget(QLabel("«Saldo del periodo» = horas trabajadas − contratadas de todo el personal; solo existe al cerrar. "
                           "Doble clic abre el periodo en el cuadro.", objectName="muted"))
        self.sub_banco.addTab(w, "Historial de esquemas")
        self.pestanas.addTab(self.sub_banco, "Historial y banco de horas")
        self.persona_banco = None

    @staticmethod
    def _texto_saldo(h):
        return "Al día" if abs(h) < 0.05 else (f"Se le deben {h:g} h" if h > 0 else f"Debe {-h:g} h")

    def _ver_banco(self):
        self._banco = flujo.estado_banco(self.bd, *self.periodo())
        verde, rojo = "#E3F4E8", "#FDE8E8"
        color = lambda h: verde if h >= 0.05 else (rojo if h <= -0.05 else None)
        llenar(self.t_banco, [(b["nombre"], signo(b["anterior"]), signo(b["periodo"]) + ("" if b["cerrado"] else " (proy.)"),
                               signo(b["total"]), self._texto_saldo(b["total"])) for b in self._banco],
               lambda r, c: color(self._banco[r]["total"]) if c >= 3 else None)
        for r, b in enumerate(self._banco):
            if b["id"] == self.persona_banco:
                self.t_banco.selectRow(r)
        self._ver_movimientos()
        self._pista_movimiento(self.m_concepto.currentText())
        self._hist = flujo.historial(self.bd)
        llenar(self.t_hist, [(flujo.etiqueta(h["inicio"], h["fin"]), h["dias"], "Cerrado" if h["cerrado"] else "Abierto",
                              h["personas"], f"{h['trabajadas']:g}", "—" if h["saldo"] is None else signo(h["saldo"]),
                              h["cambios"], h["alertas"]) for h in self._hist],
               lambda r, c: "#EEF0F2" if self._hist[r]["cerrado"] else ("#FDE8E8" if c == 7 and self._hist[r]["alertas"] else None))

    def _persona_banco_actual(self):
        r = self.t_banco.currentRow()
        return self._banco[r]["id"] if 0 <= r < len(self._banco) else None

    def _ver_movimientos(self):
        self.persona_banco = self._persona_banco_actual()
        filas = []
        if self.persona_banco:
            for per, cid, contr, trab in self.bd.cierres(self.persona_banco):
                ini, fin = flujo.desde_clave(per)
                filas.append((None, fin, f"Cierre {flujo.etiqueta(ini, fin)}", trab - contr, f"{trab:g} h trabajadas de {contr:g} contratadas"))
            filas += [(i, f, c, h, n) for i, _, f, h, c, n in self.bd.movimientos(self.persona_banco)]
        filas.sort(key=lambda x: (x[1], x[0] or 0))
        self._movs = filas
        llenar(self.t_movs, [(f"{f:%d/%m/%Y}", c, signo(h), n) for _, f, c, h, n in filas])
        self.b_borrar_mov.setEnabled(bool(filas))

    def _pista_movimiento(self, concepto):
        resta = flujo.CONCEPTOS_BANCO.get(concepto, False)
        self.l_pista.setText("Escribe las horas en positivo: se restan del saldo." if resta else
                             "Positivo: se le deben más horas. Negativo: debe horas.")

    def _registrar_movimiento(self):
        if self.persona_banco is None:
            return self.avisar("Selecciona una persona de la lista.", "warn")
        horas = self.m_horas.value()
        if not horas:
            return self.avisar("Escribe las horas del movimiento.", "error")
        concepto = self.m_concepto.currentText()
        if flujo.CONCEPTOS_BANCO[concepto]:
            horas = -abs(horas)
        self.bd.agregar_movimiento(self.persona_banco, self.m_fecha.date().toPython(), horas, concepto, self.m_nota.text().strip())
        self.m_horas.setValue(0)
        self.m_nota.clear()
        self.avisar(f"Movimiento registrado: {concepto} {horas:+g} h.")
        self._ver_banco()

    def _borrar_movimiento(self):
        r = self.t_movs.currentRow()
        if not 0 <= r < len(self._movs):
            return self.avisar("Selecciona un movimiento de la lista.", "warn")
        if self._movs[r][0] is None:
            return self.avisar("Los cierres de periodo no se borran aquí: reabre el periodo en el cuadro.", "warn")
        self.bd.borrar_movimiento(self._movs[r][0])
        self._ver_banco()

    def _ir_al_periodo(self):
        r = self.t_hist.currentRow()
        if not 0 <= r < len(self._hist):
            return self.avisar("Selecciona un periodo de la lista.", "warn")
        ini, fin = self._hist[r]["inicio"], self._hist[r]["fin"]
        if (ini, fin) == flujo.periodo_mes(ini.year, ini.month):
            self.bd.set_param("periodo_modo", "mes")
            self.año.setValue(ini.year)
            self.mes.setCurrentIndex(ini.month - 1)
        elif ini.weekday() == 0 and (fin - ini).days % 7 == 6:
            self.bd.set_param("periodo_modo", "semanas")
            self.bd.set_param("periodo_semanas", (fin - ini).days // 7 + 1)
            self.f_inicio.setDate(QDate(ini.year, ini.month, ini.day))
        else:
            return self.avisar("Ese periodo no se puede abrir con los esquemas disponibles.", "warn")
        self.pestanas.setCurrentIndex(0)
        self.refrescar()

    # --- cierre del periodo ---------------------------------------------------------------------
    def _alternar_cierre(self):
        ini, fin = self.periodo()
        if self.bd.periodo_cerrado(self.clave):
            if QMessageBox.question(self, "Reabrir periodo", "El cuadro volverá a ser editable y se borrará el cierre "
                                    "de este periodo del banco de horas. ¿Continuar?") != QMessageBox.Yes:
                return
            self.bd.reabrir_periodo(self.clave)
            self.avisar("Periodo reabierto. Su cierre salió del banco de horas.")
        else:
            if QMessageBox.question(self, "Cerrar periodo", "Se guardarán las horas trabajadas y contratadas de cada "
                                    "persona en el banco de horas y el cuadro quedará en solo lectura. ¿Continuar?") != QMessageBox.Yes:
                return
            try:
                flujo.cerrar(self.bd, ini, fin)
            except ValueError as e:
                return self.avisar(str(e), "warn")
            self.avisar("Periodo cerrado. Las horas ya están en el banco.")
        self._deshacer.clear()
        self.refrescar()

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
        izq.addWidget(con_vacio(self.t_tabla, "Aún no hay turnos", "Usa «+ Nuevo turno» para crear el primero."))
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
        self.t_dom = QCheckBox("Se puede usar en domingo y festivo")
        self.t_sol = QCheckBox("El generador puede asignarlo")
        self.t_act = QCheckBox("Activo")
        self.t_color = QPushButton()
        self.t_color.clicked.connect(self._elegir_color)
        self.t_resumen = QLabel("", objectName="muted")
        self.t_resumen.setWordWrap(True)
        for et, wd in (("Código", self.t_cod), ("Nombre", self.t_nom), ("Empieza", self.t_ini), ("Termina", self.t_fin),
                       ("Pausa de almuerzo", self.t_pmin), ("Pausa a las", self.t_pini), ("", self.t_ppag),
                       ("", self.t_dom), ("", self.t_sol), ("", self.t_act), ("Color", self.t_color),
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
        self.tab_puestos = TabPuestos(self)
        self.sub.addTab(self.tab_puestos, "Puestos")

        w = QWidget()
        g = QGridLayout(w)
        g.setContentsMargins(16, 14, 16, 16)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(8)

        def spin(minimo, maximo, sufijo="", especial="", tip=""):
            x = QSpinBox()
            x.setRange(minimo, maximo)
            x.setFixedWidth(130)
            if sufijo:
                x.setSuffix(sufijo)
            if especial:
                x.setSpecialValueText(especial)
            if tip:
                x.setToolTip(tip)
            return x

        def tarjeta(titulo, ayuda):
            caja = QGroupBox(titulo)
            f = QFormLayout(caja)
            f.setVerticalSpacing(10)
            a = QLabel(ayuda, objectName="muted")
            a.setWordWrap(True)
            f.addRow(a)
            return caja, f

        caja2, f = tarjeta("Esquema y horas", "Cada cuánto se programa y cómo se promedian las horas (art. 165 CST).")
        self.s_modo = QComboBox()
        self.s_modo.addItem("Mes calendario", "mes")
        self.s_modo.addItem("Semanas desde un lunes", "semanas")
        self.s_modo.setFixedWidth(200)
        self.s_semanas = spin(1, 8, " semana(s)")
        self.s_vent = spin(1, 8, " semana(s)")
        for et, wd in (("Esquema", self.s_modo), ("Duración por semanas", self.s_semanas), ("Ventana de horas", self.s_vent)):
            f.addRow(et, wd)
        caja3, f = tarjeta("Descansos", "Se cumplen por defecto; una edición manual puede saltarlos en un caso puntual.")
        self.s_libre = spin(0, 3, " día(s)", "Sin regla")
        self.s_sem = spin(1, 3, " día(s)")
        self.s_fines = spin(0, 4, "", "Sin regla", "Sábado y domingo libres, por persona y esquema")
        for et, wd in (("Libre después de una noche", self.s_libre), ("Libres por semana (mínimo)", self.s_sem),
                       ("Fines de semana libres", self.s_fines)):
            f.addRow(et, wd)
        caja4, f = tarjeta("Límites de repetición", "Evitan rachas pesadas y reparten mejor los turnos.")
        self.s_noches = spin(0, 7, "", "Sin tope", "Noches en racha NC, L, NC, L…")
        self.s_c = spin(0, 7, "", "Sin tope")
        self.s_igual = spin(0, 7, "", "Sin tope", "Mismo turno de 6 h (M o T) en días seguidos")
        for et, wd in (("Noches en racha (NC, L, NC…)", self.s_noches), ("Corridos (C) seguidos", self.s_c),
                       ("Mismo turno (M, T) seguido", self.s_igual)):
            f.addRow(et, wd)
        caja5, f = tarjeta("Banco de horas", "Al generar, la meta de horas de cada persona se ajusta con su saldo anterior: "
                                              "a quien se le deben horas se le baja y a quien las debe se le sube. 0 = no compensar.")
        self.s_favor = spin(0, 48, " h", "No compensar", "Máximo de horas que se descuentan por periodo a quien se le deben")
        self.s_deuda = spin(0, 48, " h", "No compensar", "Máximo de horas que se suman por periodo a quien las debe")
        for et, wd in (("Descontar a quien se le deben (máx.)", self.s_favor), ("Sumar a quien las debe (máx.)", self.s_deuda)):
            f.addRow(et, wd)
        g.addWidget(caja2, 0, 0)
        g.addWidget(caja3, 0, 1)
        g.addWidget(caja4, 1, 0)
        g.addWidget(caja5, 1, 1)
        b = QPushButton("Guardar cambios", objectName="primario")
        b.clicked.connect(self._guardar_reglas)
        g.addWidget(b, 2, 0, 1, 2, Qt.AlignLeft)
        g.setRowStretch(3, 1)
        g.setColumnStretch(0, 1)
        g.setColumnStretch(1, 1)
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
        self.tab_puestos.refrescar()
        self.s_vent.setValue(int(self.bd.param("ventana_semanas", 3)))
        self.s_favor.setValue(int(self.bd.param("banco_tope_favor_h", 12)))
        self.s_deuda.setValue(int(self.bd.param("banco_tope_deuda_h", 12)))
        self.s_modo.setCurrentIndex(max(0, self.s_modo.findData(self.modo_periodo)))
        self.s_semanas.setValue(int(self.bd.param("periodo_semanas", 4)))
        self.s_noches.setValue(self.ctx.max_noches)
        self.s_c.setValue(self.ctx.max_c)
        self.s_igual.setValue(self.ctx.max_igual)
        self.s_libre.setValue(self.ctx.libre_tras_noche)
        self.s_sem.setValue(self.ctx.libres_semana)
        self.s_fines.setValue(self.ctx.fines_libres)
        llenar(self.t_tar, sorted(((c, v, f"{d:%d/%m/%Y}") for c, v, d in self.bd.tarifas()), key=lambda x: (x[0], x[2][6:] + x[2][3:5])))
        self.l_fest.clear()
        for f, n in sorted(self.ctx.fest.items()):
            if f.year == self.año.value():
                self.l_fest.addItem(f"{DIAS[f.weekday()]} {f:%d/%m/%Y} · {n}")

    def _nuevo_turno(self):
        self.turno_cod = None
        sin_seleccion(self.t_tabla)
        self.t_cod.setReadOnly(False)
        self.t_cod.clear()
        self.t_nom.clear()
        self.t_ini.setTime(QTime(6, 0))
        self.t_fin.setTime(QTime(12, 0))
        self.t_pmin.setValue(0)
        self.t_pini.setTime(QTime(12, 0))
        self.t_ppag.setChecked(False)
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
        pausas = ()
        if self.t_pmin.value() > 0:
            pausas = ({"ini": (minutos(self.t_pini.time()) - ini) % 1440, "min": self.t_pmin.value(),
                       "pagada": self.t_ppag.isChecked()},)
        t = Turno(cod, self.t_nom.text().strip() or cod, ini, fin, self._color, (), pausas, self.t_dom.isChecked(),
                  self.t_sol.isChecked(), self.t_act.isChecked())
        if pausas and pausas[0]["ini"] + pausas[0]["min"] > t.duracion:
            raise ValueError("La pausa debe quedar dentro del turno.")
        return t

    def _resumen_turno(self):
        try:
            t = self._turno_desde_form()
            nombres = {"M": "mañana", "T": "tarde", "N": "noche"}
            fr = ", ".join(nombres[x] for x in franjas_de(t)) or "ninguna franja"
            self.t_resumen.setText(f"Dura {t.duracion / 60:g} h · se cuentan {t.horas:g} h trabajadas · cuenta en: {fr}")
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
        self.bd.set_param("ventana_semanas", self.s_vent.value())
        self.bd.set_param("banco_tope_favor_h", self.s_favor.value())
        self.bd.set_param("banco_tope_deuda_h", self.s_deuda.value())
        self.bd.set_param("periodo_modo", self.s_modo.currentData())
        self.bd.set_param("periodo_semanas", self.s_semanas.value())
        self.bd.set_param("max_noches_seguidas", self.s_noches.value())
        self.bd.set_param("max_c_seguidos", self.s_c.value())
        self.bd.set_param("max_igual_seguidos", self.s_igual.value())
        self.bd.set_param("libre_tras_noche", self.s_libre.value())
        self.bd.set_param("libres_por_semana", self.s_sem.value())
        self.bd.set_param("fines_semana_libres", self.s_fines.value())
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
