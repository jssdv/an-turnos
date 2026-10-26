"""Versión portable (Windows): Postgres embebido (pgserver) + API + trabajador del solver + front, todo en un proceso.
Los datos (histórico incluido) viven en %LOCALAPPDATA%\\An (o AN_DATOS). Arranque: python -m an.web.portable
Pruebas sin pgserver: AN_PG_ADMIN_URL=postgresql://…(rol dueño) usa esa base en vez de la embebida."""
import logging
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

import psycopg
import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from an.turnos.pg import FILAS

from . import admin, conexion, esquema
from .app import crear_app
from .trabajador import Trabajador

PUERTO = int(os.environ.get("AN_PUERTO", "8765"))
CLINICA, AREA, CORREO = "Mi clínica", "Esterilización", "admin@an.local"


def carpeta_datos():
    base = os.environ.get("AN_DATOS") or os.path.join(os.environ.get("LOCALAPPDATA") or Path.home(), "An")
    return Path(base)


def carpeta_front():
    """Junto al .exe de PyInstaller (sys._MEIPASS) o, en desarrollo, web/dist."""
    raiz = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2]))
    return raiz / ("web_dist" if hasattr(sys, "_MEIPASS") else "web/dist")


def con_usuario(url, usuario):
    p = urlsplit(url)
    return urlunsplit(p._replace(netloc=f"{usuario}@{p.hostname}:{p.port}"))


def preparar_base(url_admin, datos):
    """Migra, crea la clínica/área/administrador la primera vez y deja la clave temporal en primer_acceso.txt."""
    with psycopg.connect(url_admin, autocommit=True) as c:
        if not c.execute("SELECT 1 FROM pg_database WHERE datname = 'an'").fetchone():
            c.execute("CREATE DATABASE an")
    url_an = urlsplit(url_admin)._replace(path="/an")
    url_admin = urlunsplit(url_an)
    with psycopg.connect(url_admin) as c:
        esquema.aplicar(c)
        c.execute("ALTER ROLE an_app LOGIN")
        c.commit()
    with psycopg.connect(url_admin, row_factory=FILAS) as c:
        if c.execute("SELECT 1 FROM clinica LIMIT 1").fetchone() is None:
            cl = admin.crear_clinica(c, CLINICA)
            c.commit()
            area = admin.crear_area(c, cl, AREA)
            uid, clave = admin.crear_usuario(c, cl, CORREO, "Administrador", es_admin=True)
            admin.dar_permiso(c, uid, area, "editar")
            texto = f"Usuario: {CORREO}\nClave temporal: {clave}\n(el sistema pide cambiarla al entrar)\n"
            (datos / "primer_acceso.txt").write_text(texto, encoding="utf-8")
            print(texto)
    return con_usuario(url_admin, "an_app")


def servir_front(app, dist):
    """Sirve web/dist; cualquier ruta que no sea archivo ni /api devuelve index.html (rutas del front)."""
    class Spa(StaticFiles):
        async def get_response(self, path, scope):
            try:
                return await super().get_response(path, scope)
            except HTTPException as e:
                if e.status_code != 404 or scope["path"].startswith("/api"):
                    raise
                return FileResponse(dist / "index.html")

    app.mount("/", Spa(directory=dist, html=True))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    datos = carpeta_datos()
    datos.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":  # initdb corre con token restringido (sin el grupo Administradores): el usuario debe figurar en la ACL
        subprocess.run(["icacls", str(datos), "/grant", f"{os.environ['USERNAME']}:(OI)(CI)F"], check=True, capture_output=True)
    servidor = None
    url_admin = os.environ.get("AN_PG_ADMIN_URL")
    if not url_admin:
        import pgserver  # solo en el paquete portable

        servidor = pgserver.get_server(datos / "pg", cleanup_mode="stop")
        url_admin = servidor.get_uri()
    try:
        os.environ["AN_PG_URL"] = preparar_base(url_admin, datos)
        os.environ["AN_ORIGEN"] = f"http://localhost:{PUERTO}"
        pool = conexion.abrir_pool()
        app = crear_app(pool)
        servir_front(app, carpeta_front())
        parar = threading.Event()
        threading.Thread(target=Trabajador(pool).servir, args=(parar,), daemon=True).start()
        threading.Timer(1.5, webbrowser.open, (os.environ["AN_ORIGEN"],)).start()
        print(f"An corriendo en {os.environ['AN_ORIGEN']} · datos en {datos} · cierra esta ventana para detenerlo")
        uvicorn.run(app, host="127.0.0.1", port=PUERTO, log_level="warning")
        parar.set()
        pool.close()
    finally:
        if servidor is not None:
            servidor.cleanup()


def main_seguro():
    """Deja el error en an.log y espera una tecla: la ventana de consola no debe cerrarse antes de poder leerlo."""
    try:
        main()
    except BaseException:
        import traceback

        texto = traceback.format_exc()
        try:
            (carpeta_datos() / "an.log").write_text(texto, encoding="utf-8")
        except OSError:
            pass
        print(texto)
        input("\nHubo un error (copiado en an.log, carpeta de datos). Presiona Enter para cerrar.")
        raise


if __name__ == "__main__":
    main_seguro()
