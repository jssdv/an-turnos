"""Punto de entrada del ejecutable (PyInstaller)."""
import multiprocessing

from an.web.entregable import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
