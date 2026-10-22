"""Piezas de interfaz comunes: tarjeta KPI, tablas, cursor de espera, encabezado de página y apertura de archivos."""
import os
import subprocess
import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QFrame, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout)


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


def llenar(t, filas, colores=None, orden=None):
    t.setSortingEnabled(False)
    t.clearContents()
    t.setRowCount(len(filas))
    for r, fila in enumerate(filas):
        for c, v in enumerate(fila):
            it = QTableWidgetItem()
            it.setData(Qt.DisplayRole, "—" if v is None else v)
            if colores and (color := colores(r, c)):
                it.setBackground(QColor(color))
            t.setItem(r, c, it)
    t.resizeColumnsToContents()
    if orden is not None:
        t.setSortingEnabled(True)
        t.sortByColumn(orden, Qt.AscendingOrder)


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
