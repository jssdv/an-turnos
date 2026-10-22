"""Aspecto de An (el de Radiología): hoja de estilos, ícono dibujado y arranque de la aplicación Qt."""
import sys

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ACENTO = "#0F6E8C"

ESTILO = f"""
QMainWindow, QWidget#fondo {{ background: #F4F6F8; }}
QLabel {{ color: #1F2933; }}
QLabel#muted, QLabel#sub {{ color: #6B7280; }}
QLabel#marca {{ font-size: 16px; font-weight: 700; }}
QLabel#seccion {{ font-size: 18px; font-weight: 650; }}
QLabel#vacio_t {{ font-size: 17px; font-weight: 600; }}
QLabel#campo {{ color: #6B7280; font-size: 11px; font-weight: 600; letter-spacing: .4px; }}
QFrame#cabecera {{ background: white; border-bottom: 1px solid #E3E6EA; }}
QListWidget#nav {{ background: transparent; border: none; outline: 0; font-size: 13px; }}
QListWidget#nav::item {{ padding: 9px 12px; border-radius: 7px; color: #3E4C59; margin: 1px 0; }}
QListWidget#nav::item:hover {{ background: #E9EDF1; }}
QListWidget#nav::item:selected {{ background: #DCECF1; color: {ACENTO}; font-weight: 600; }}
QFrame#tarjeta, QFrame#panel {{ background: white; border: 1px solid #E3E6EA; border-radius: 10px; }}
QFrame#tarjeta:hover {{ border-color: #B7C9D3; }}
QFrame#tarjeta[nivel="warn"] {{ border-left: 4px solid #E0A800; }}
QFrame#tarjeta[nivel="error"] {{ border-left: 4px solid #C53030; }}
QFrame#tarjeta[nivel="ok"] {{ border-left: 4px solid #2F855A; }}
QFrame#tarjeta[nivel="info"] {{ border-left: 4px solid {ACENTO}; }}
QLabel#cifra {{ font-size: 26px; font-weight: 700; }}
QLabel#aviso {{ border-radius: 8px; padding: 10px 12px; }}
QLabel#aviso[nivel="info"] {{ background: #E8F1F8; color: #12466B; }}
QLabel#aviso[nivel="warn"] {{ background: #FFF4D6; color: #6B4E00; }}
QLabel#aviso[nivel="error"] {{ background: #FDE8E8; color: #8E1B1B; }}
QLabel#error {{ background: #FDE8E8; color: #8E1B1B; border-radius: 8px; padding: 10px 14px; }}
QLabel#toast {{ background: #1F2933; color: white; border-radius: 8px; padding: 9px 14px; }}
QFrame#soltar {{ background: white; border: 2px dashed #C5CED6; border-radius: 14px; }}
QFrame#soltar[activo="true"] {{ border-color: {ACENTO}; background: #EEF6F9; }}
QPushButton, QToolButton {{ background: white; border: 1px solid #CBD2D9; border-radius: 6px; padding: 7px 14px; color: #1F2933; }}
QPushButton:hover, QToolButton:hover {{ background: #F0F3F6; }}
QPushButton:focus, QToolButton:focus {{ border-color: {ACENTO}; }}
QPushButton:disabled, QToolButton:disabled {{ color: #A0A7B0; background: #F5F6F8; }}
QPushButton#primario {{ background: {ACENTO}; border: 1px solid {ACENTO}; color: white; font-weight: 600; padding: 8px 18px; }}
QPushButton#primario:hover {{ background: #0C5C75; }}
QPushButton#primario:disabled {{ background: #9DBFCB; border-color: #9DBFCB; }}
QPushButton#peligro {{ color: #B42318; border-color: #E8B8B3; }}
QPushButton#peligro:hover {{ background: #FDE8E8; }}
QPushButton#peligro:disabled {{ color: #C9A6A2; background: #F5F6F8; border-color: #E3E6EA; }}
QPushButton#archivo {{ text-align: left; padding: 7px 12px; max-width: 360px; }}
QToolButton#flecha {{ padding: 6px 9px; font-weight: 700; }}
QComboBox, QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox {{ background: white; border: 1px solid #CBD2D9; border-radius: 6px; padding: 6px 10px; }}
QComboBox#semana {{ min-width: 190px; }}
QComboBox::drop-down {{ border: none; width: 22px; }}
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {ACENTO}; }}
QLineEdit:disabled, QComboBox:disabled {{ background: #F5F6F8; color: #A0A7B0; }}
QCheckBox {{ spacing: 8px; color: #1F2933; }}
QGroupBox {{ background: white; border: 1px solid #E3E6EA; border-radius: 10px; margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 14px; padding: 0 6px; color: {ACENTO}; }}
QTabWidget::pane {{ border: none; background: white; }}
QTabBar::tab {{ padding: 8px 14px; color: #52606D; border: none; }}
QTabBar::tab:selected {{ color: {ACENTO}; border-bottom: 2px solid {ACENTO}; font-weight: 600; }}
QTableWidget {{ border: none; gridline-color: #EDF0F3; selection-background-color: #D6E9F0; selection-color: #1F2933; }}
QHeaderView::section {{ background: #F7F8FA; border: none; border-bottom: 1px solid #E3E6EA; padding: 6px; color: #52606D; font-weight: 600; }}
QListWidget#medicos, QPlainTextEdit {{ border: 1px solid #E3E6EA; border-radius: 6px; background: white; }}
QListWidget#medicos::item {{ padding: 6px 8px; }}
QListWidget#medicos::item:selected {{ background: #DCECF1; color: #1F2933; }}
QSplitter::handle {{ background: transparent; }}
QToolTip {{ background: #1F2933; color: white; border: none; padding: 6px 8px; }}
"""


def icono_app():
    """Ícono dibujado (sin archivos): calendario blanco sobre el color de la app."""
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(ACENTO))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(4, 4, 120, 120), 26, 26)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(26, 34, 76, 66), 9, 9)
    p.setBrush(QColor(ACENTO))
    p.drawRect(QRectF(26, 34, 76, 15))
    p.setPen(QPen(QColor("white"), 6, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(44, 24, 44, 40)
    p.drawLine(84, 24, 84, 40)
    p.setPen(Qt.NoPen)
    for i in range(3):
        for j in range(2):
            p.setBrush(QColor(ACENTO if (i, j) != (1, 1) else "#E0A800"))
            p.drawRoundedRect(QRectF(36 + i * 20, 58 + j * 18, 13, 11), 3, 3)
    p.end()
    return QIcon(pm)


def preparar_app(argv):
    app = QApplication(argv)
    app.setOrganizationName("An")
    app.setApplicationName("An")
    app.setWindowIcon(icono_app())
    app.setStyle("Fusion")
    # Siempre modo claro: con el sistema en oscuro, Qt pondría texto claro sobre nuestros fondos blancos
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setPalette(app.style().standardPalette())
    if sys.platform == "win32":
        app.setFont(QFont("Segoe UI", 10))
    app.setStyleSheet(ESTILO)
    return app
