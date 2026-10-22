"""Ventana base de An: cabecera, menú lateral de secciones, aviso y toast. Cada área aporta sus secciones.

Una área es una clase con `NOMBRE`, `CLAVE` (prefijo de sus ajustes) y `__init__(self, ventana)`, que expone:
    secciones         lista de (título, QWidget): una entrada del menú lateral cada una (obligatorio)
    cabecera          QWidget con los controles propios del área, junto a la marca (opcional)
    vacia             QWidget que reemplaza el cuerpo mientras el área no tiene datos; ver `mostrar_vacia` (opcional)
    TAMANO            (ancho, alto) inicial de la ventana (opcional)
    iniciar()         se llama cuando la ventana ya está armada, para cargar el último estado (opcional)
    seccion_activa(i) se llama al cambiar de sección (opcional)
    dragEnterEvent / dragLeaveEvent / dropEvent   arrastrar y soltar archivos (opcionales)
    cerrar()          al cerrar la ventana (opcional)
Atajos de teclado: el área los registra con `ventana.atajo(tecla, función)`.
"""
import traceback
from datetime import datetime

from PySide6.QtCore import QSettings, QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QListWidget, QMainWindow, QMessageBox, QStackedWidget,
                               QVBoxLayout, QWidget)

from . import RAIZ
from .tema import icono_app
from .widgets import poner_nivel

LOG = RAIZ / "errores.log"


class Ventana(QMainWindow):
    def __init__(self, Area, usuario=""):
        super().__init__()
        self.setWindowTitle(f"An · {Area.NOMBRE}")
        self.setWindowIcon(icono_app())
        self.cfg = QSettings("An", "An")
        self._clave_geometria = f"{Area.CLAVE}/geometria"

        fondo = QWidget(objectName="fondo")
        self.setCentralWidget(fondo)
        raiz = QVBoxLayout(fondo)
        raiz.setContentsMargins(0, 0, 0, 0)
        raiz.setSpacing(0)

        self.nav = QListWidget(objectName="nav")
        self.nav.setFixedWidth(190)
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
        raiz.addWidget(self._cabecera(Area, usuario))

        cuerpo = QHBoxLayout()
        cuerpo.setContentsMargins(16, 16, 20, 16)
        cuerpo.setSpacing(16)
        cuerpo.addWidget(self.nav)
        der = QVBoxLayout()
        der.setSpacing(12)
        der.addWidget(self.aviso)
        der.addWidget(self.paginas, 1)
        cuerpo.addLayout(der, 1)
        self.principal = QWidget()
        self.principal.setLayout(cuerpo)
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

    def _cabecera(self, Area, usuario):
        cab = QFrame(objectName="cabecera")
        h = QHBoxLayout(cab)
        h.setContentsMargins(20, 12, 20, 12)
        h.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(icono_app().pixmap(QSize(34, 34)))
        h.addWidget(logo)
        marca = QVBoxLayout()
        marca.setSpacing(0)
        marca.addWidget(QLabel("An", objectName="marca"))
        marca.addWidget(QLabel(Area.NOMBRE + (f" · {usuario}" if usuario else ""), objectName="sub"))
        h.addLayout(marca)
        h.addSpacing(24)
        if hasattr(self.area, "cabecera"):
            h.addWidget(self.area.cabecera, 1)
        else:
            h.addStretch(1)
        return cab

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

    def contar(self, i, n):
        """Anota un contador junto al título de la sección (se quita si n es 0)."""
        self.nav.item(i).setText(f"{self._titulos[i]}   ·  {n}" if n else self._titulos[i])

    def mostrar_vacia(self, si):
        self.pila.setCurrentWidget(self.area.vacia if si else self.principal)

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
