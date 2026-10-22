"""Piezas de interfaz comunes: tarjeta KPI, tablas, cursor de espera, encabezado de página y apertura de archivos."""
import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QHeaderView, QLabel, QStackedWidget,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)


def abrir(ruta):
    if sys.platform == "win32":
        os.startfile(ruta)  # solo existe en Windows
    else:
        subprocess.Popen(["open" if sys.platform == "darwin" else "xdg-open", str(ruta)])


def poner_nivel(w, valor, propiedad="nivel"):
    """Fija la propiedad `nivel` (info/warn/error/ok) y repinta: la hoja de estilos solo la relee al «pulir»."""
    w.setProperty(propiedad, valor)
    w.style().unpolish(w)
    w.style().polish(w)


def titulo_pagina(texto, ayuda):
    caja = QVBoxLayout()
    caja.setSpacing(2)
    caja.addWidget(QLabel(texto, objectName="seccion"))
    caja.addWidget(QLabel(ayuda, objectName="muted", wordWrap=True))
    return caja


def tabla(columnas, ayudas=None):
    t = QTableWidget(0, len(columnas))
    t.setHorizontalHeaderLabels(columnas)
    t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.setSelectionBehavior(QAbstractItemView.SelectRows)
    t.verticalHeader().setVisible(False)
    t.horizontalHeader().setStretchLastSection(True)
    t.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
    for c, ayuda in (ayudas or {}).items():
        t.horizontalHeaderItem(c).setToolTip(ayuda)
    return t


def texto_sobre(fondo):
    """Texto oscuro o blanco, el que dé más contraste (WCAG) sobre `fondo`; sirve para colores que elige el usuario."""
    def lum(c):
        v = [x / 255 for x in (c.red(), c.green(), c.blue())]
        v = [x / 12.92 if x <= .03928 else ((x + .055) / 1.055) ** 2.4 for x in v]
        return .2126 * v[0] + .7152 * v[1] + .0722 * v[2]
    f = lum(QColor(fondo))
    return QColor("#1B2733") if (f + .05) / (lum(QColor("#1B2733")) + .05) >= 1.05 / (f + .05) else QColor("white")


def llenar(t, filas, colores=None, orden=None):
    """Llena la tabla sin disparar sus señales. Si se envolvió con `con_vacio`, alterna el mensaje de «sin datos»."""
    t.blockSignals(True)
    t.setSortingEnabled(False)
    t.clearContents()
    t.setRowCount(len(filas))
    for r, fila in enumerate(filas):
        for c, v in enumerate(fila):
            it = QTableWidgetItem()
            it.setData(Qt.DisplayRole, "—" if v is None else v)
            if colores and (color := colores(r, c)):
                it.setBackground(QColor(color))
                it.setForeground(texto_sobre(color))
            t.setItem(r, c, it)
    t.resizeColumnsToContents()
    if orden is not None:
        t.setSortingEnabled(True)
        t.sortByColumn(orden, Qt.AscendingOrder)
    if hasattr(t, "_pila"):
        t._pila.setCurrentIndex(0 if filas else 1)
    t.blockSignals(False)


def con_vacio(t, titulo, texto=""):
    """Envuelve la tabla `t`: si no tiene filas, muestra un mensaje que guía en lugar de un espacio en blanco."""
    pila = QStackedWidget()
    pila.addWidget(t)
    p = QWidget()
    l = QVBoxLayout(p)
    l.addStretch()
    for txt, nombre in ((titulo, "vacio_t"), (texto, "muted")):
        e = QLabel(txt, objectName=nombre, alignment=Qt.AlignCenter)
        e.setWordWrap(True)
        l.addWidget(e)
    l.addStretch()
    pila.addWidget(p)
    t._pila = pila
    return pila


def signo(h):
    """Horas con signo explícito; el cero se escribe sin signo."""
    return "0" if abs(h) < 0.05 else f"{h:+g}"


def hhmm(minutos):
    return f"{minutos // 60 % 24:02d}:{minutos % 60:02d}"


def sin_seleccion(t):
    """Limpia la selección de la tabla sin disparar señales (no debe recargar el registro anterior en un formulario)."""
    t.blockSignals(True)
    t.clearSelection()
    t.setCurrentCell(-1, -1)
    t.blockSignals(False)


class ocupado:
    def __enter__(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)

    def __exit__(self, *exc):
        QApplication.restoreOverrideCursor()


class Tarjeta(QFrame):
    """Cifra grande + etiqueta; al hacer clic lleva a una sección."""

    def __init__(self, titulo, al_clic):
        super().__init__(objectName="tarjeta")
        self.setCursor(Qt.PointingHandCursor)
        self.al_clic = al_clic
        v = QVBoxLayout(self)
        v.setContentsMargins(16, 12, 16, 12)
        v.setSpacing(2)
        self.cifra = QLabel("—", objectName="cifra")
        self.titulo = QLabel(titulo, objectName="muted")
        self.detalle = QLabel("", objectName="muted")
        self.detalle.setWordWrap(True)
        for w in (self.cifra, self.titulo, self.detalle):
            v.addWidget(w)

    def poner(self, cifra, nivel, detalle=""):
        self.cifra.setText(str(cifra))
        self.detalle.setText(detalle)
        poner_nivel(self, nivel)

    def mousePressEvent(self, e):
        self.al_clic()
