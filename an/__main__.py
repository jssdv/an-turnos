"""Arranque de An: `python -m an [radiologia]`."""
import sys

from .nucleo.shell import Ventana, error_inesperado
from .nucleo.tema import preparar_app
from .esterilizacion.paginas import Turnos
from .radiologia.paginas import Planilla

AREAS = {"radiologia": Planilla, "esterilizacion": Turnos}


def main():
    app = preparar_app(sys.argv)
    sys.excepthook = error_inesperado
    v = Ventana(AREAS[sys.argv[1] if len(sys.argv) > 1 else "radiologia"])
    v.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
