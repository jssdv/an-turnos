"""Punto de entrada del ejecutable portable (PyInstaller)."""
import multiprocessing

from an.web.portable import main_seguro

if __name__ == "__main__":
    multiprocessing.freeze_support()
    main_seguro()
