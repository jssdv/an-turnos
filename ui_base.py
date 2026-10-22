"""Helpers de interfaz compartidos por app.py y ui_puestos.py: tablas, estados vacíos y formato de números."""
import re

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QHeaderView, QLabel, QStackedWidget, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

NUMERO = re.compile(r"[+\-−]?\d+([.,]\d+)?( \(proy\.\))?")


def tabla(columnas, editable=False):
    t = QTableWidget(0, len(columnas))
    t.setHorizontalHeaderLabels(columnas)
    if not editable:
        t.setEditTriggers(QAbstractItemView.NoEditTriggers)
    t.verticalHeader().setVisible(False)
    t.setAlternatingRowColors(True)
    t.setShowGrid(False)
    t.verticalHeader().setDefaultSectionSize(34)
    return t


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


def llenar(t, filas, colores=None):
    t.blockSignals(True)
    t.setRowCount(len(filas))
    n = t.columnCount()
    numericas = [bool(filas)] * n
    for r, fila in enumerate(filas):
        for c, v in enumerate(fila):
            txt = "" if v is None else (f"{v:g}" if isinstance(v, float) else str(v))
            it = QTableWidgetItem(txt)
            if NUMERO.fullmatch(txt):
                it.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                numericas[c] = False
            if colores and (col := colores(r, c)):
                it.setBackground(QColor(col))
            t.setItem(r, c, it)
    h = t.horizontalHeader()
    estirar = n - 1 if not numericas[n - 1] else 0
    for c in range(n):
        h.setSectionResizeMode(c, QHeaderView.Stretch if c == estirar else QHeaderView.ResizeToContents)
        if t.horizontalHeaderItem(c):
            t.horizontalHeaderItem(c).setTextAlignment((Qt.AlignRight if numericas[c] else Qt.AlignLeft) | Qt.AlignVCenter)
    if hasattr(t, "_pila"):
        t._pila.setCurrentIndex(0 if filas else 1)
    t.blockSignals(False)


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
