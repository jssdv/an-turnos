"""Arranque de An: `python -m an [usuario]`. El usuario local decide el área que se abre."""
import sys

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QInputDialog, QMessageBox

from .esterilizacion.paginas import Turnos
from .nucleo import usuarios as usuarios_mod
from .nucleo.shell import Ventana, error_inesperado
from .nucleo.tema import preparar_app
from .radiologia.paginas import Planilla

AREAS = {"radiologia": Planilla, "esterilizacion": Turnos}


def main():
    app = preparar_app(sys.argv)
    sys.excepthook = error_inesperado
    try:
        usuarios = usuarios_mod.cargar(AREAS)
    except usuarios_mod.ErrorUsuarios as e:
        QMessageBox.critical(None, "An", str(e))
        return 1
    cfg = QSettings()
    nombre = sys.argv[1] if len(sys.argv) > 1 else None
    while True:
        if nombre not in usuarios:
            nombres = list(usuarios)
            ultimo = cfg.value("usuario", "")
            nombre, ok = QInputDialog.getItem(None, "An · Ingresar", "Usuario:", nombres,
                                              nombres.index(ultimo) if ultimo in nombres else 0, False)
            if not ok:
                return 0
        cfg.setValue("usuario", nombre)
        v = Ventana(AREAS[usuarios[nombre]], nombre)
        v.show()
        app.exec()
        if not v.cambiar_usuario:
            return 0
        nombre = None


if __name__ == "__main__":
    sys.exit(main())
