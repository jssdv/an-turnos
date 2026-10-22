"""Pestañas de puestos y dotación (se montan dentro de la ventana principal)."""
from PySide6.QtCore import Qt, QTime
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QColorDialog, QComboBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QHeaderView, QLineEdit, QMessageBox, QPushButton, QSpinBox, QTableWidget, QTimeEdit,
                               QVBoxLayout, QWidget)

import demanda
from dominio import Demanda, Puesto
from ui_base import con_vacio, hhmm, llenar, sin_seleccion, tabla

TIPOS_DIA = (("Lunes a sábado", "LS"), ("Domingo y festivo", "DF"))


class TabPuestos(QWidget):
    """Parámetros → Puestos: lista de puestos y, a la derecha, su ficha con las reglas de demanda."""

    def __init__(self, ventana):
        super().__init__()
        self.v = ventana
        self.puesto_id = None
        self._puestos = []
        self._color = "FFFFFF"
        h = QHBoxLayout(self)
        h.setContentsMargins(16, 14, 16, 16)
        h.setSpacing(16)
        izq = QVBoxLayout()
        nuevo = QPushButton("+ Nuevo puesto", objectName="primario")
        nuevo.clicked.connect(self.nuevo)
        izq.addWidget(nuevo, alignment=Qt.AlignLeft)
        self.t_lista = tabla(["Núm.", "Nombre", "Demanda", "Estado"])
        self.t_lista.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_lista.setSelectionMode(QAbstractItemView.SingleSelection)
        self.t_lista.itemSelectionChanged.connect(self._cargar)
        izq.addWidget(con_vacio(self.t_lista, "Aún no hay puestos", "Usa «+ Nuevo puesto» y agrega sus reglas de demanda."))
        h.addLayout(izq, 2)

        caja = QGroupBox("Puesto")
        caja.setMinimumWidth(560)
        lv = QVBoxLayout(caja)
        f = QFormLayout()
        self.f_numero, self.f_nombre = QSpinBox(), QLineEdit()
        self.f_numero.setRange(1, 99)
        self.f_numero.setFixedWidth(90)
        self.f_color = QPushButton()
        self.f_color.clicked.connect(self._elegir_color)
        self.f_activo = QCheckBox("Activo (cuenta en la cobertura)")
        for et, wd in (("Número", self.f_numero), ("Nombre", self.f_nombre), ("Color", self.f_color), ("", self.f_activo)):
            f.addRow(et, wd)
        lv.addLayout(f)
        lv.addWidget(self._etiqueta("Reglas de demanda: cuántas personas necesita y en qué horario. Las obligatorias se "
                                    "exigen al generar el cuadro; las deseables se buscan si alcanza."))
        self.t_reglas = QTableWidget(0, 5)
        self.t_reglas.setHorizontalHeaderLabels(["Días", "Desde", "Hasta", "Personas", "Obligatoria"])
        self.t_reglas.verticalHeader().setVisible(False)
        self.t_reglas.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.t_reglas.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.t_reglas.setMinimumHeight(170)
        hh = self.t_reglas.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.Stretch)
        lv.addWidget(self.t_reglas)
        reglas_b = QHBoxLayout()
        for texto, fn in (("Agregar regla", self.agregar_regla), ("Quitar regla", self.quitar_regla)):
            b = QPushButton(texto)
            b.clicked.connect(lambda _=False, fn=fn: fn())
            reglas_b.addWidget(b)
        reglas_b.addStretch()
        lv.addLayout(reglas_b)
        botones = QHBoxLayout()
        guardar = QPushButton("Guardar", objectName="primario")
        self.b_eliminar = QPushButton("Eliminar", objectName="peligro")
        guardar.clicked.connect(self.guardar)
        self.b_eliminar.clicked.connect(self.eliminar)
        botones.addWidget(guardar)
        botones.addWidget(self.b_eliminar)
        botones.addStretch()
        lv.addLayout(botones)
        h.addWidget(caja, 3, Qt.AlignTop)
        self.nuevo()

    @staticmethod
    def _etiqueta(texto):
        from PySide6.QtWidgets import QLabel
        e = QLabel(texto, objectName="muted")
        e.setWordWrap(True)
        return e

    # --- reglas ---------------------------------------------------------------------------------
    def agregar_regla(self, d=None):
        d = d or Demanda(0, "LS", 360, 1080, 1)
        r = self.t_reglas.rowCount()
        self.t_reglas.insertRow(r)
        tipo = QComboBox()
        for texto, cod in TIPOS_DIA:
            tipo.addItem(texto, cod)
        tipo.setCurrentIndex(max(0, tipo.findData(d.tipo_dia)))
        ini, fin = QTimeEdit(QTime(d.inicio // 60 % 24, d.inicio % 60)), QTimeEdit(QTime(d.fin // 60 % 24, d.fin % 60))
        for t in (ini, fin):
            t.setDisplayFormat("HH:mm")
        personas = QSpinBox()
        personas.setRange(1, 99)
        personas.setValue(d.personas)
        obligatoria = QCheckBox()
        obligatoria.setChecked(d.obligatorio)
        for w in (ini, fin, personas):
            w.lineEdit().setTextMargins(6, 0, 0, 0)
        for c, w in enumerate((tipo, ini, fin, personas, obligatoria)):
            self.t_reglas.setCellWidget(r, c, w)

    def quitar_regla(self):
        r = self.t_reglas.currentRow()
        if r >= 0:
            self.t_reglas.removeRow(r)

    def reglas(self):
        w = self.t_reglas.cellWidget
        minutos = lambda t: t.time().hour() * 60 + t.time().minute()
        return [Demanda(self.puesto_id or 0, w(r, 0).currentData(), minutos(w(r, 1)), minutos(w(r, 2)), w(r, 3).value(),
                        w(r, 4).isChecked()) for r in range(self.t_reglas.rowCount())]

    # --- color ----------------------------------------------------------------------------------
    def _poner_color(self, color):
        self._color = color
        self.f_color.setStyleSheet(f"background: #{color}; border: 1px solid #C5CCD5; border-radius: 8px; padding: 7px;")
        self.f_color.setText(f"#{color}")

    def _elegir_color(self):
        c = QColorDialog.getColor(QColor("#" + self._color), self, "Color del puesto")
        if c.isValid():
            self._poner_color(c.name()[1:].upper())

    # --- lista ----------------------------------------------------------------------------------
    def refrescar(self):
        self._puestos = list(self.v.bd.catalogo_puestos().values())
        cuenta = {}
        for d in self.v.bd.demandas():
            cuenta[d.puesto_id] = cuenta.get(d.puesto_id, 0) + 1
        llenar(self.t_lista, [(p.numero, p.nombre, f"{cuenta[p.id]} regla(s)" if p.id in cuenta else "Sin demanda",
                               "Activo" if p.activo else "Inactivo") for p in self._puestos],
               lambda r, c: ("#" + self._puestos[r].color) if c == 0 else (None if self._puestos[r].activo else "#EEF0F2"))
        for r, p in enumerate(self._puestos):
            if p.id == self.puesto_id:
                self.t_lista.selectRow(r)

    def _cargar(self):
        r = self.t_lista.currentRow()
        if not 0 <= r < len(self._puestos):
            return
        p = self._puestos[r]
        self.puesto_id = p.id
        self.f_numero.setValue(p.numero)
        self.f_nombre.setText(p.nombre)
        self._poner_color(p.color)
        self.f_activo.setChecked(p.activo)
        self.t_reglas.setRowCount(0)
        for d in self.v.bd.demandas(p.id):
            self.agregar_regla(d)
        self.b_eliminar.setEnabled(True)

    def nuevo(self):
        self.puesto_id = None
        sin_seleccion(self.t_lista)
        usados = [p.numero for p in self.v.bd.catalogo_puestos().values()]
        self.f_numero.setValue(min(max(usados, default=0) + 1, 99))
        self.f_nombre.clear()
        self._poner_color("FFFFFF")
        self.f_activo.setChecked(True)
        self.t_reglas.setRowCount(0)
        self.b_eliminar.setEnabled(False)
        self.f_nombre.setFocus()

    # --- guardar y eliminar ---------------------------------------------------------------------
    def guardar(self):
        nombre = self.f_nombre.text().strip()
        if not nombre:
            return self.v.avisar("Escribe el nombre del puesto.", "error")
        reglas = self.reglas()
        for d in reglas:
            if d.inicio == d.fin:
                return self.v.avisar("El puesto no puede empezar y terminar a la misma hora.", "error")
            if d.inicio % 30 or d.fin % 30:
                return self.v.avisar("Las horas deben ser múltiplos de 30 minutos.", "error")
        try:
            pid = self.v.bd.guardar_puesto(Puesto(self.puesto_id or 0, self.f_numero.value(), nombre, self._color,
                                                  self.f_activo.isChecked()))
        except ValueError as e:
            return self.v.avisar(str(e), "error")
        for d in reglas:
            d.puesto_id = pid
        self.v.bd.reemplazar_demandas(pid, reglas)
        self.puesto_id = pid
        avisos = []
        if self._solapadas(reglas):
            avisos.append("Las reglas solapadas se suman.")
        huecos = demanda.huecos_sin_turno([d for d in reglas if d.obligatorio], self.v.bd.turnos())
        if huecos:
            avisos.append("Ningún turno cubre " + ", ".join(f"{hhmm(a)}–{hhmm(b)}" for a, b in huecos[:3]) + ".")
        self.v.refrescar()
        self.v.avisar(f"Puesto «{nombre}» guardado." + "".join(" " + a for a in avisos), "warn" if avisos else "info")

    @staticmethod
    def _solapadas(reglas):
        vistos = set()
        for d in reglas:
            tramos = {(d.tipo_dia, o * demanda.TRAMOS_DIA + t) for o, t in demanda.tramos_ventana(d.inicio, d.fin)}
            if vistos & tramos:
                return True
            vistos |= tramos
        return False

    def eliminar(self):
        if self.puesto_id is None:
            return self.v.avisar("Selecciona un puesto de la lista.", "warn")
        nombre = self.f_nombre.text()
        if QMessageBox.question(self, "Eliminar puesto", f"¿Eliminar el puesto «{nombre}»?") != QMessageBox.Yes:
            return
        if self.v.bd.borrar_puesto(self.puesto_id) == "borrado":
            self.v.avisar(f"Puesto «{nombre}» eliminado.")
        else:
            self.v.avisar(f"«{nombre}» ya tiene reparto guardado, así que quedó inactivo en lugar de borrarse.", "warn")
        self.nuevo()
        self.v.refrescar()
