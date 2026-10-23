"""Aspecto de An (diseño en docs/diseno/An_UI.figcraft): colores, hoja de estilos, fuentes, ícono y arranque Qt."""
from pathlib import Path

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QIcon, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QApplication

# Tokens de color: los mismos nombres que las variables «Color» del archivo de FigCraft
C = dict(
    fondo="#F5F7FA", superficie="#FFFFFF", superficie_sutil="#F3F5F8", borde="#E3E8EE", borde_control="#C9D1DB",
    borde_campo="#8D99A6", texto="#1A2633", titulo="#0F1D2B", atenuado="#5E6B7A", deshabilitado="#7A828C",
    acento="#0B7A75", acento_hover="#08625E", acento_suave="#E3F3F1", marca="#2BB3A3",
    lateral="#0F1D2B", lateral_sel="#1D3347", lateral_hover="#16293A", lateral_texto="#B9C7D5", lateral_tenue="#6F849A",
    info="#0B6B8C", info_texto="#0B4A61", info_fondo="#E6F2F7", info_borde="#B9D9E6",
    warn="#A86F00", warn_texto="#5C4300", warn_fondo="#FFF6E0", warn_borde="#F1D58F", warn_celda="#FFEFC2",
    warn_insignia="#F2B43C",
    error="#B42318", error_texto="#7A1A12", error_fondo="#FDECEA", error_borde="#F2C1BC",
    ok="#1E7A47", ok_texto="#14512F", ok_fondo="#E7F5EC", ok_borde="#B8E0C6",
)
ACENTO = C["acento"]
TITULOS = "Sora"  # títulos, cifras y marca; el resto en Inter
FUENTES = Path(__file__).with_name("fuentes")

ESTILO = """
QMainWindow, QWidget#fondo { background: $fondo; }
QWidget { font-family: "Inter"; font-size: 13px; }
QLabel { color: $texto; }
QLabel#muted, QLabel#sub { color: $atenuado; }
QLabel#seccion { font-family: "Sora"; font-size: 22px; font-weight: 600; color: $titulo; }
QLabel#panel_t { font-size: 15px; font-weight: 600; color: $titulo; }
QLabel#vacio_t { font-family: "Sora"; font-size: 18px; font-weight: 600; color: $titulo; }
QLabel#campo { color: $atenuado; font-size: 11px; font-weight: 600; letter-spacing: .4px; }

QFrame#lateral { background: $lateral; }
QLabel#marca { font-family: "Sora"; font-size: 17px; font-weight: 600; color: white; }
QLabel#area { font-size: 12px; font-weight: 500; color: #8FA3B8; }
QLabel#lateral_campo { font-size: 11px; font-weight: 600; letter-spacing: .6px; color: $lateral_tenue; }
QListWidget#nav { background: transparent; border: none; outline: 0; }
QListWidget#nav::item { padding: 9px 12px 9px 25px; border-radius: 8px; color: $lateral_texto; margin: 1px 0; font-weight: 500; }
QListWidget#nav::item:hover { background: $lateral_hover; color: #DCE6EF; }
QListWidget#nav::item:selected { background: $lateral_sel; color: white; font-weight: 600; }
QListWidget#nav::item:disabled { color: #4A5E72; }
QFrame#usuario { background: $lateral_hover; border-radius: 10px; }
QLabel#usuario_n { font-weight: 600; color: white; }
QPushButton#lateral_boton { background: transparent; border: 1px solid #3A5268; color: #C9D6E2; padding: 6px 10px; font-size: 12px; }
QPushButton#lateral_boton:hover { background: $lateral_sel; }

QFrame#tarjeta, QFrame#panel { background: $superficie; border: 1px solid $borde; border-radius: 12px; }
QFrame#tarjeta:hover { border-color: $borde_control; }
QFrame#tarjeta QLabel#muted { font-weight: 500; }
QLabel#cifra { font-family: "Sora"; font-size: 30px; font-weight: 600; color: $titulo; }
QLabel#detalle { font-size: 12px; font-weight: 500; color: $atenuado; }
QFrame#tarjeta[nivel="warn"] QLabel#detalle { color: $warn; }
QFrame#tarjeta[nivel="error"] QLabel#detalle { color: $error; }
QFrame#tarjeta[nivel="ok"] QLabel#detalle { color: $ok; }
QFrame#tarjeta[nivel="info"] QLabel#detalle { color: $info; }

QLabel#aviso { border-radius: 10px; padding: 10px 14px; font-weight: 500; border: 1px solid transparent; }
QLabel#aviso[nivel="info"] { background: $info_fondo; color: $info_texto; border-color: $info_borde; }
QLabel#aviso[nivel="warn"] { background: $warn_fondo; color: $warn_texto; border-color: $warn_borde; }
QLabel#aviso[nivel="error"] { background: $error_fondo; color: $error_texto; border-color: $error_borde; }
QLabel#aviso[nivel="ok"] { background: $ok_fondo; color: $ok_texto; border-color: $ok_borde; }
QLabel#error { background: $error_fondo; color: $error_texto; border: 1px solid $error_borde; border-radius: 10px; padding: 10px 14px; }
QLabel#toast { background: $titulo; color: white; border-radius: 10px; padding: 10px 16px; }
QFrame#soltar { background: $superficie; border: 2px dashed #B7C2CE; border-radius: 16px; }
QFrame#soltar[activo="true"] { border-color: $acento; background: $acento_suave; }

QPushButton, QToolButton { background: $superficie; border: 1px solid $borde_control; border-radius: 8px; padding: 7px 14px; color: $texto; font-weight: 500; }
QPushButton:hover, QToolButton:hover { background: #F0F3F6; }
QPushButton:focus, QToolButton:focus { border-color: $acento; }
QPushButton:disabled, QToolButton:disabled { color: $deshabilitado; background: #F5F6F8; border-color: $borde; }
QPushButton#primario { background: $acento; border: 1px solid $acento; color: white; font-weight: 600; padding: 7px 16px; }
QPushButton#primario:hover { background: $acento_hover; border-color: $acento_hover; }
QPushButton#primario:disabled { background: #A9CFCC; border-color: #A9CFCC; color: #0B3F3C; }
QPushButton#primario::menu-indicator { subcontrol-position: right center; right: 8px; }
QPushButton#fantasma { background: transparent; border-color: transparent; color: #3C4A59; }
QPushButton#fantasma:hover { background: #E9EDF2; }
QPushButton#peligro { color: $error; border-color: #E8B8B3; }
QPushButton#peligro:hover { background: $error_fondo; }
QPushButton#peligro:disabled { color: #A8645D; background: #F5F6F8; border-color: $borde; }
QPushButton#archivo { text-align: left; padding: 7px 12px; max-width: 360px; }
QToolButton#flecha { padding: 6px 10px; font-weight: 700; }

QComboBox, QLineEdit, QDateEdit, QTimeEdit, QSpinBox, QDoubleSpinBox { background: $superficie; color: $texto; border: 1px solid $borde_campo; border-radius: 8px; padding: 6px 10px; }
QComboBox#semana { min-width: 190px; font-weight: 600; }
QComboBox::drop-down { border: none; width: 22px; }
QComboBox QAbstractItemView { background: $superficie; color: $texto; border: 1px solid $borde_campo; selection-background-color: $acento; selection-color: white; outline: 0; }
QLineEdit:focus, QComboBox:focus, QDateEdit:focus, QTimeEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid $acento; padding: 5px 9px; }
QLineEdit:disabled, QComboBox:disabled { background: #F5F6F8; color: $deshabilitado; border-color: $borde; }
QCheckBox { spacing: 8px; color: $texto; }
QGroupBox { background: $superficie; border: 1px solid $borde; border-radius: 12px; margin-top: 14px; padding: 16px 12px 12px 12px; font-weight: 600; }
QGroupBox::title { subcontrol-origin: margin; left: 14px; padding: 0 6px; color: $acento; }
QTabWidget::pane { border: none; background: $superficie; }
QTabBar::tab { padding: 9px 12px; color: $atenuado; border: none; font-weight: 500; }
QTabBar::tab:selected { color: $titulo; border-bottom: 2px solid $acento; font-weight: 600; }
QTableWidget::item { border-bottom: 1px solid #EEF1F4; }
QTableWidget { border: none; gridline-color: #EEF1F4; selection-background-color: $acento_suave; selection-color: $texto; }
QHeaderView::section { background: $superficie_sutil; border: none; border-bottom: 1px solid $borde; padding: 7px 6px; color: #4A5766; font-weight: 600; font-size: 12px; }
QListWidget#medicos, QPlainTextEdit { border: 1px solid $borde; border-radius: 8px; background: $superficie; }
QListWidget#medicos::item { padding: 6px 8px; }
QListWidget#medicos::item:selected { background: $acento_suave; color: $texto; }
QSplitter::handle { background: transparent; }
QToolTip { background: $titulo; color: white; border: none; padding: 6px 8px; }
"""
for _k in sorted(C, key=len, reverse=True):  # los nombres largos primero: «$warn_fondo» antes que «$warn»
    ESTILO = ESTILO.replace("$" + _k, C[_k])


def icono_app():
    """Ícono dibujado (sin archivos): calendario blanco sobre el color de la marca."""
    pm = QPixmap(128, 128)
    pm.fill(Qt.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor(C["marca"]))
    p.setPen(Qt.NoPen)
    p.drawRoundedRect(QRectF(4, 4, 120, 120), 30, 30)
    p.setBrush(QColor("white"))
    p.drawRoundedRect(QRectF(26, 34, 76, 66), 9, 9)
    p.setBrush(QColor(C["lateral"]))
    p.drawRect(QRectF(26, 34, 76, 15))
    p.setPen(QPen(QColor("white"), 6, Qt.SolidLine, Qt.RoundCap))
    p.drawLine(44, 24, 44, 40)
    p.drawLine(84, 24, 84, 40)
    p.setPen(Qt.NoPen)
    for i in range(3):
        for j in range(2):
            p.setBrush(QColor(C["lateral"] if (i, j) != (1, 1) else C["warn_insignia"]))
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
    for f in FUENTES.glob("*.ttf"):  # Inter y Sora van con la app: el PC corporativo no permite instalarlas
        QFontDatabase.addApplicationFont(str(f))
    fuente = QFont("Inter")
    fuente.setPixelSize(13)
    app.setFont(fuente)
    app.setStyleSheet(ESTILO)
    return app
