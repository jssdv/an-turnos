"""Ventana base de An: menú lateral oscuro (marca, secciones, usuario), barra del área, aviso y toast.

Una área es una clase con `NOMBRE`, `CLAVE` (prefijo de sus ajustes) y `__init__(self, ventana)`, que expone:
    secciones         lista de (título, QWidget): una entrada del menú lateral cada una (obligatorio)
    cabecera          QWidget con los controles propios del área, en una barra sobre las secciones (opcional)
    vacia             QWidget que reemplaza barra y secciones mientras el área no tiene datos; ver `mostrar_vacia` (opcional)
    TAMANO            (ancho, alto) inicial de la ventana (opcional)
    iniciar()         se llama cuando la ventana ya está armada, para cargar el último estado (opcional)
    seccion_activa(i) se llama al cambiar de sección (opcional)
    dragEnterEvent / dragLeaveEvent / dropEvent   arrastrar y soltar archivos (opcionales)
    cerrar()          al cerrar la ventana (opcional)
Atajos de teclado: el área los registra con `ventana.atajo(tecla, función)`.
"""
import traceback
from datetime import datetime

from PySide6.QtCore import QRectF, QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QColor, QKeySequence, QPainter
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox, QPushButton,
                               QStackedWidget, QStyledItemDelegate, QVBoxLayout, QWidget)

from . import RAIZ
from .tema import C, icono_app
from .widgets import poner_nivel

LOG = RAIZ / "errores.log"


class _ItemNav(QStyledItemDelegate):
    """Entrada del menú lateral: barra de color en la seleccionada e insignia con el contador de `contar`."""

    def paint(self, p, opt, idx):
        super().paint(p, opt, idx)
        r = opt.rect.adjusted(0, 1, 0, -1)  # el margen de 1 px de la hoja de estilos
        p.save()
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        if idx.row() == self.parent().currentRow() and self.parent().isEnabled():
            p.setBrush(QColor(C["marca"]))
            p.drawRoundedRect(QRectF(r.left() + 12, r.center().y() - 7, 3, 16), 1.5, 1.5)
        if marca := idx.data(Qt.UserRole):
            n, nivel = marca
            texto = str(n)
            f = p.font()
            f.setPixelSize(11)
            f.setBold(True)
            p.setFont(f)
            ancho = max(20, p.fontMetrics().horizontalAdvance(texto) + 12)
            caja = QRectF(r.right() - 10 - ancho, r.center().y() - 8, ancho, 18)
            p.setBrush(QColor(C["warn_insignia"] if nivel == "warn" else "#2A4459"))
            p.drawRoundedRect(caja, 9, 9)
            p.setPen(QColor("#2B1D00" if nivel == "warn" else "#DCE6EF"))
            p.drawText(caja, Qt.AlignCenter, texto)
        p.restore()


class Ventana(QMainWindow):
    def __init__(self, Area, usuario=""):
        super().__init__()
        self.setWindowTitle(f"An · {Area.NOMBRE}")
        self.setWindowIcon(icono_app())
        self.cfg = QSettings()  # organización y nombre de la app los fija preparar_app
        self.cambiar_usuario = False  # lo pone en True el botón del menú lateral; `main` vuelve a pedir usuario
        self._clave_geometria = f"{Area.CLAVE}/geometria"

        fondo = QWidget(objectName="fondo")
        self.setCentralWidget(fondo)
        raiz = QHBoxLayout(fondo)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        self.nav = QListWidget(objectName="nav")
        self.nav.setItemDelegate(_ItemNav(self.nav))
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.nav.setCursor(Qt.PointingHandCursor)
        self.aviso = QLabel(objectName="aviso", wordWrap=True)
        self.aviso.setTextInteractionFlags(Qt.TextSelectableByMouse)
        self.aviso.hide()
        self.paginas = QStackedWidget()
        self.area = Area(self)
        self.setAcceptDrops(hasattr(self.area, "dropEvent"))

        self._titulos = [t for t, _ in self.area.secciones]
        self.nav.addItems(self._titulos)
        for _, pagina in self.area.secciones:
            self.paginas.addWidget(pagina)
        self.nav.currentRowChanged.connect(self._ir)
        raiz.addWidget(self._lateral(Area, usuario))

        der = QVBoxLayout()
        der.setContentsMargins(28, 18, 28, 24)
        der.setSpacing(16)
        if hasattr(self.area, "cabecera"):
            der.addWidget(self.area.cabecera)
        der.addWidget(self.aviso)
        der.addWidget(self.paginas, 1)
        self.principal = QWidget()
        self.principal.setLayout(der)
        self.pila = QStackedWidget()
        self.pila.addWidget(self.principal)
        if hasattr(self.area, "vacia"):
            self.pila.addWidget(self.area.vacia)
        raiz.addWidget(self.pila, 1)

        self.toast = QLabel(self, objectName="toast")
        self.toast.hide()
        self._toast_timer = QTimer(self, singleShot=True, interval=4500, timeout=self.toast.hide)

        for i in range(len(self._titulos)):
            self.atajo(f"Ctrl+{i + 1}", lambda i=i: self.ir_a(i))
        if geo := self.cfg.value(self._clave_geometria):
            self.restoreGeometry(geo)
        else:
            self.resize(*getattr(Area, "TAMANO", (1280, 840)))
        self.nav.setCurrentRow(0)
        if hasattr(self.area, "iniciar"):
            self.area.iniciar()
        self.nav.setFocus()  # el primer foco no cae sobre un botón de la cabecera

    def _lateral(self, Area, usuario):
        """Columna oscura: marca y área, menú de secciones y, abajo, el usuario."""
        lat = QFrame(objectName="lateral")
        lat.setFixedWidth(232)
        v = QVBoxLayout(lat)
        v.setContentsMargins(14, 20, 14, 16)
        v.setSpacing(4)
        h = QHBoxLayout()
        h.setContentsMargins(6, 0, 0, 18)
        h.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icono_app().pixmap(QSize(34, 34)))
        h.addWidget(logo)
        marca = QVBoxLayout()
        marca.setSpacing(0)
        marca.addWidget(QLabel("An", objectName="marca"))
        marca.addWidget(QLabel(Area.NOMBRE, objectName="area"))
        h.addLayout(marca, 1)
        v.addLayout(h)
        v.addWidget(QLabel("SECCIONES", objectName="lateral_campo"))
        v.addWidget(self.nav, 1)
        if usuario:
            caja = QFrame(objectName="usuario")
            u = QVBoxLayout(caja)
            u.setContentsMargins(12, 12, 12, 12)
            u.setSpacing(8)
            u.addWidget(QLabel(usuario, objectName="usuario_n"))
            b = QPushButton("Cambiar usuario", objectName="lateral_boton",
                            toolTip="Volver a elegir usuario (y con él, el área)")
            b.clicked.connect(self._cambiar_usuario)
            u.addWidget(b)
            v.addWidget(caja)
        return lat

    def _cambiar_usuario(self):
        self.cambiar_usuario = True
        self.close()

    # ---------------------------------------------------------------- navegación y estado
    def atajo(self, tecla, funcion):
        a = QAction(self, shortcut=QKeySequence(tecla))
        a.triggered.connect(lambda _=False: funcion())
        self.addAction(a)

    def ir_a(self, i):
        self.nav.setCurrentRow(i)

    def _ir(self, i):
        self.paginas.setCurrentIndex(i)
        if hasattr(self.area, "seccion_activa"):
            self.area.seccion_activa(i)

    def contar(self, i, n, nivel=""):
        """Insignia con un contador junto al título de la sección (se quita si n es 0); nivel «warn» la resalta."""
        self.nav.item(i).setData(Qt.UserRole, (n, nivel) if n else None)

    def mostrar_vacia(self, si):
        self.pila.setCurrentWidget(self.area.vacia if si else self.principal)
        self.nav.setEnabled(not si)

    def avisar(self, texto, nivel="info"):
        if not texto:
            return self.aviso.hide()
        self.aviso.setText(texto)
        poner_nivel(self.aviso, nivel)
        self.aviso.show()

    def notificar(self, texto):
        self.toast.setText(texto)
        self.toast.adjustSize()
        self._ubicar_toast()
        self.toast.show()
        self.toast.raise_()
        self._toast_timer.start()

    def _ubicar_toast(self):
        self.toast.move(self.width() - self.toast.width() - 24, self.height() - self.toast.height() - 20)

    # ---------------------------------------------------------------- eventos
    def dragEnterEvent(self, e):
        if hasattr(self.area, "dragEnterEvent"):
            self.area.dragEnterEvent(e)

    def dragLeaveEvent(self, e):
        if hasattr(self.area, "dragLeaveEvent"):
            self.area.dragLeaveEvent(e)

    def dropEvent(self, e):
        if hasattr(self.area, "dropEvent"):
            self.area.dropEvent(e)

    def closeEvent(self, e):
        self.cfg.setValue(self._clave_geometria, self.saveGeometry())
        if hasattr(self.area, "cerrar"):
            self.area.cerrar()
        super().closeEvent(e)

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._ubicar_toast()


def error_inesperado(tipo, valor, tb):
    texto = "".join(traceback.format_exception(tipo, valor, tb))
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(f"\n--- {datetime.now():%Y-%m-%d %H:%M}\n{texto}")
    except OSError:
        pass
    QMessageBox.critical(None, "Algo salió mal",
                         f"Ocurrió un error inesperado:\n\n{valor}\n\nSe guardó el detalle en {LOG.name}.")
