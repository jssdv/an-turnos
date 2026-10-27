"""Versión portable (Windows): Postgres embebido (pgserver) + API + trabajador del solver + front, todo en un proceso.
Los datos (histórico incluido) viven en %LOCALAPPDATA%\\An (o AN_DATOS). Arranque: python -m an.web.portable
Pruebas sin pgserver: AN_PG_ADMIN_URL=postgresql://…(rol dueño) usa esa base en vez de la embebida."""
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
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


def postgres_vivo(pg):
    import psutil

    try:
        pid = int((pg / "postmaster.pid").read_text().splitlines()[0])
        return psutil.Process(pid).name().lower().startswith("postgres")
    except (OSError, ValueError, IndexError, psutil.Error):
        return False


def arrancar_postgres(pg):
    """pgserver arranca con un tope de 10 s, y tras un cierre brusco la recuperación puede tardar minutos (antivirus). Se arranca aquí,
    con espera larga y sin consola (la X de la ventana ya no lo mata); pgserver reutiliza el servidor que encuentra vivo."""
    if not (pg / "PG_VERSION").exists() or postgres_vivo(pg):
        return
    import socket

    from pgserver._commands import pg_ctl

    with socket.socket() as sk:
        sk.bind(("127.0.0.1", 0))
        puerto = sk.getsockname()[1]
    extra = {"creationflags": 0x00000008} if sys.platform == "win32" else {}  # DETACHED_PROCESS
    # un log nuevo por arranque: un Postgres de la sesión anterior puede seguir teniendo abierto el archivo anterior
    logs = sorted(pg.glob("log*"), key=lambda f: f.stat().st_mtime)
    for viejo in logs[:-4]:
        viejo.unlink(missing_ok=True)
    log = pg / f"log_{int(time.time())}"
    pg_ctl(["-w", "-t", "900", "-o", "-h 127.0.0.1", "-o", f"-p {puerto}", "-l", str(log), "start"], pgdata=pg, timeout=1000, **extra)


def al_cerrar_ventana(servidor, terminado):
    """Windows: la X de la consola mata el proceso a los ~5 s; se pide a uvicorn que salga y se espera a que termine la limpieza."""
    import ctypes

    @ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_uint)
    def manejador(evento):
        if evento in (2, 5, 6):  # CTRL_CLOSE / LOGOFF / SHUTDOWN
            servidor.should_exit = True
            terminado.wait(4)
            return True
        return False

    ctypes.windll.kernel32.SetConsoleCtrlHandler(manejador, True)
    return manejador  # hay que conservar la referencia


def main():
    datos = carpeta_datos()
    datos.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.StreamHandler(), logging.FileHandler(datos / "an.log", encoding="utf-8")])  # incluye el stderr de initdb
    if sys.platform == "win32":  # initdb corre con token restringido (sin el grupo Administradores): el usuario debe figurar en la ACL
        subprocess.run(["icacls", str(datos), "/grant", f"{os.environ['USERNAME']}:(OI)(CI)F"], check=True, capture_output=True)
    servidor, terminado = None, threading.Event()
    url_admin = os.environ.get("AN_PG_ADMIN_URL")
    if not url_admin:
        import pgserver  # solo en el paquete portable

        pg = datos / "pg"
        if pg.exists() and not (pg / "PG_VERSION").exists():  # inicialización interrumpida: sin clúster no hay nada que perder
            shutil.rmtree(pg, ignore_errors=True)
        print("Iniciando la base de datos (tras un cierre brusco puede tardar varios minutos)…")
        arrancar_postgres(pg)
        servidor = pgserver.get_server(datos / "pg", cleanup_mode=None)  # Postgres sigue vivo al salir; el siguiente arranque lo reutiliza
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
        web = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PUERTO, log_level="warning"))
        if sys.platform == "win32":
            manejador = al_cerrar_ventana(web, terminado)  # noqa: F841
        web.run()
        parar.set()
        pool.close()
    finally:
        if servidor is not None:
            servidor.cleanup()
        terminado.set()


def main_seguro():
    """Deja el error en an.log y espera una tecla: la ventana de consola no debe cerrarse antes de poder leerlo."""
    if "--detener" in sys.argv:  # apaga el Postgres que queda en segundo plano (p. ej. para reemplazar la carpeta del programa)
        from pgserver._commands import pg_ctl

        pg_ctl(["-w", "-m", "fast", "stop"], pgdata=carpeta_datos() / "pg", timeout=120)
        print("Base de datos detenida.")
        return
    try:
        main()
    except BaseException:
        import traceback

        texto = traceback.format_exc()
        logging.getLogger("an").error(texto)
        print(texto)
        input("\nHubo un error (copiado en an.log, carpeta de datos). Presiona Enter para cerrar.")
        raise


if __name__ == "__main__":
    main_seguro()
