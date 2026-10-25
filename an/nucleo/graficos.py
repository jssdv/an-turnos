"""Gráficos sencillos con QPainter y los colores de `tema.C` (sin dependencias). Reciben datos ya calculados."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from .tema import C

SERIES = [C["acento"], C["info"], C["warn_insignia"], C["error"], C["ok"]]
MARGEN = 8


class _Base(QWidget):
    vacio = True

    def _sin_datos(self, p):
        p.setPen(QColor(C["atenuado"]))
        p.drawText(self.rect(), Qt.AlignCenter, "Sin datos")


class Barras(_Base):
    """`poner([(etiqueta, {serie: valor})])`. Apiladas o agrupadas, verticales u horizontales."""

    def __init__(self, horizontal=False, apilado=False):
        super().__init__()
        self.horizontal, self.apilado, self.datos, self.series = horizontal, apilado, [], []
        self.setMinimumHeight(180)

    def poner(self, datos):
        self.datos = datos
        self.series = list(dict.fromkeys(s for _, v in datos for s in v))
        self.vacio = not any(x > 0 for _, v in datos for x in v.values())
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.vacio:
            return self._sin_datos(p)
        alto_leyenda = 18 if len(self.series) > 1 else 0
        if alto_leyenda:
            x = MARGEN
            for i, s in enumerate(self.series):
                p.fillRect(QRectF(x, 4, 10, 10), QColor(SERIES[i % len(SERIES)]))
                p.setPen(QColor(C["atenuado"]))
                p.drawText(int(x + 14), 14, s)
                x += 28 + p.fontMetrics().horizontalAdvance(s)
        eti = max(p.fontMetrics().horizontalAdvance(e) for e, _ in self.datos) + 6 if self.horizontal else 0
        area = QRectF(MARGEN + eti, MARGEN + alto_leyenda, self.width() - 2 * MARGEN - eti,
                      self.height() - 2 * MARGEN - alto_leyenda - (0 if self.horizontal else 16))
        tope = max((sum(v.values()) if self.apilado else max(v.values(), default=0)) for _, v in self.datos) or 1
        n, k = len(self.datos), (1 if self.apilado else len(self.series))
        paso = (area.height() if self.horizontal else area.width()) / n
        grosor = paso * 0.7 / k
        p.setPen(QPen(QColor(C["borde"])))
        for j, (eti_, vals) in enumerate(self.datos):
            ini, acum = paso * j + paso * 0.15, 0.0
            for i, s in enumerate(self.series):
                v = vals.get(s, 0)
                largo = v / tope * (area.width() if self.horizontal else area.height())
                off = acum if self.apilado else 0
                pos = ini + (0 if self.apilado else i * grosor)
                r = (QRectF(area.left() + off, area.top() + pos, largo, grosor) if self.horizontal
                     else QRectF(area.left() + pos, area.bottom() - off - largo, grosor, largo))
                p.fillRect(r, QColor(SERIES[i % len(SERIES)]))
                acum += largo
            p.setPen(QColor(C["atenuado"]))
            if self.horizontal:
                p.drawText(QRectF(MARGEN, area.top() + paso * j, eti - 4, paso), Qt.AlignRight | Qt.AlignVCenter, eti_)
            else:
                p.drawText(QRectF(area.left() + paso * j, area.bottom() + 2, paso, 14), Qt.AlignCenter, eti_)


class Linea(_Base):
    """`poner([(etiqueta, valor)])`; marca el máximo."""

    def __init__(self):
        super().__init__()
        self.puntos = []
        self.setMinimumHeight(160)

    def poner(self, puntos):
        self.puntos = puntos
        self.vacio = not any(v > 0 for _, v in puntos)
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        if self.vacio:
            return self._sin_datos(p)
        tope = max(v for _, v in self.puntos)
        a = QRectF(MARGEN + 20, MARGEN + 14, self.width() - 2 * MARGEN - 20, self.height() - 2 * MARGEN - 30)
        xy = [(a.left() + a.width() * i / max(1, len(self.puntos) - 1), a.bottom() - a.height() * v / tope)
              for i, (_, v) in enumerate(self.puntos)]
        p.setPen(QPen(QColor(C["borde"])))
        p.drawLine(a.bottomLeft(), a.bottomRight())
        p.setPen(QPen(QColor(C["acento"]), 2))
        for (x0, y0), (x1, y1) in zip(xy, xy[1:]):
            p.drawLine(int(x0), int(y0), int(x1), int(y1))
        im = max(range(len(xy)), key=lambda i: self.puntos[i][1])
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(C["error"]))
        p.drawEllipse(xy[im][0] - 4, xy[im][1] - 4, 8, 8)
        p.setPen(QColor(C["atenuado"]))
        p.drawText(int(xy[im][0]) - 40, int(xy[im][1]) - 8, 80, 14, Qt.AlignCenter, f"{self.puntos[im][1]:g}")
        p.drawText(QRectF(a.left(), a.bottom() + 2, 80, 14), Qt.AlignLeft, self.puntos[0][0])
        p.drawText(QRectF(a.right() - 80, a.bottom() + 2, 80, 14), Qt.AlignRight, self.puntos[-1][0])
