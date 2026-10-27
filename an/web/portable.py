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
    primer = None
    with psycopg.connect(url_admin, row_factory=FILAS) as c:
        if c.execute("SELECT 1 FROM clinica LIMIT 1").fetchone() is None:
            cl = admin.crear_clinica(c, CLINICA)
            c.commit()
            area = admin.crear_area(c, cl, AREA)
            uid, clave = admin.crear_usuario(c, cl, CORREO, "Administrador", es_admin=True)
            admin.dar_permiso(c, uid, area, "editar")
            texto = f"Usuario: {CORREO}\nClave temporal: {clave}\n(el sistema pide cambiarla al entrar)\n"
            (datos / "primer_acceso.txt").write_text(texto, encoding="utf-8")
            primer = texto
    return con_usuario(url_admin, "an_app"), primer


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


def en_marcha():
    import socket

    with socket.socket() as sk:
        sk.settimeout(1)
        return sk.connect_ex(("127.0.0.1", PUERTO)) == 0


def servicio(estado):
    """Hilo de fondo: base de datos, API y trabajador. `estado` es el diccionario que lee la ventana ("listo", "web", "error", "fin")."""
    datos, servidor = carpeta_datos(), None
    try:
        url_admin = os.environ.get("AN_PG_ADMIN_URL")
        if not url_admin:
            import pgserver  # solo en el paquete portable

            pg = datos / "pg"
            if pg.exists() and not (pg / "PG_VERSION").exists():  # inicialización interrumpida: sin clúster no hay nada que perder
                shutil.rmtree(pg, ignore_errors=True)
            arrancar_postgres(pg)
            servidor = pgserver.get_server(pg, cleanup_mode="stop")
            url_admin = servidor.get_uri()
        os.environ["AN_PG_URL"], estado["primer"] = preparar_base(url_admin, datos)
        os.environ["AN_ORIGEN"] = f"http://localhost:{PUERTO}"
        pool = conexion.abrir_pool()
        app = crear_app(pool)
        servir_front(app, carpeta_front())
        parar = threading.Event()
        threading.Thread(target=Trabajador(pool).servir, args=(parar,), daemon=True).start()
        estado["web"] = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PUERTO, log_level="warning"))
        threading.Timer(1.0, estado.__setitem__, ("listo", True)).start()
        estado["web"].run()
        parar.set()
        pool.close()
    except BaseException:
        logging.getLogger("an").exception("error de arranque")
        estado["error"] = True
    finally:
        if servidor is not None:
            servidor.cleanup()
        estado["fin"] = True


def sin_consolas():
    """Programa sin consola: los procesos hijos (initdb, pg_ctl…) no deben abrir ventanas negras."""
    original = subprocess.Popen.__init__

    def init(self, *a, **k):
        k["creationflags"] = k.get("creationflags", 0) | 0x08000000  # CREATE_NO_WINDOW
        original(self, *a, **k)

    subprocess.Popen.__init__ = init


def main():
    import tkinter as tk
    from tkinter import messagebox

    for flujo in ("stdout", "stderr"):  # programa sin consola: estos flujos son None y uvicorn llama a isatty() sobre ellos
        if getattr(sys, flujo) is None:
            setattr(sys, flujo, open(os.devnull, "w"))
    datos = carpeta_datos()
    datos.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s",
                        handlers=[logging.FileHandler(datos / "an.log", encoding="utf-8")])  # incluye el stderr de initdb
    url = f"http://localhost:{PUERTO}"
    if en_marcha():  # segunda vez que se abre: solo lleva al navegador
        webbrowser.open(url)
        return
    if sys.platform == "win32":
        sin_consolas()
        # initdb corre con token restringido (sin el grupo Administradores): el usuario debe figurar en la ACL
        subprocess.run(["icacls", str(datos), "/grant", f"{os.environ['USERNAME']}:(OI)(CI)F"], check=True, capture_output=True)
    estado = {}
    hilo = threading.Thread(target=servicio, args=(estado,), daemon=True)
    hilo.start()

    v = tk.Tk()
    v.title("An")
    v.geometry("420x190")
    v.resizable(False, False)
    texto = tk.Label(v, text="Iniciando…\nLa primera vez, o tras un cierre brusco, puede tardar varios minutos.", wraplength=380, pady=18)
    texto.pack()
    abrir = tk.Button(v, text="Abrir An", state="disabled", width=20, command=lambda: webbrowser.open(url))
    abrir.pack(pady=4)
    cerrar = tk.Button(v, text="Cerrar An", width=20)
    cerrar.pack(pady=4)

    def salir():
        cerrar.config(state="disabled")
        abrir.config(state="disabled")
        texto.config(text="Cerrando… (guardando los datos, no apagues el equipo)")
        if "web" in estado:
            estado["web"].should_exit = True
        estado["salir"] = True

    def vigilar():
        if estado.get("error"):
            messagebox.showerror("An no pudo iniciar", f"Ocurrió un problema al iniciar. Intenta abrirlo de nuevo.\n"
                                 f"Si se repite, envía este archivo a soporte:\n{datos / 'an.log'}")
            v.destroy()
        elif estado.get("fin"):
            v.destroy()
        else:
            if estado.get("listo") and not estado.get("salir") and abrir["state"] == "disabled":
                texto.config(text="An está funcionando.\nDeja esta ventana abierta mientras lo uses; ciérrala con «Cerrar An» al terminar.")
                abrir.config(state="normal")
                webbrowser.open(url)
                if estado.get("primer"):
                    messagebox.showinfo("Primer acceso", estado["primer"] + "\nAnota estos datos: se muestran una sola vez (también quedan en primer_acceso.txt, "
                                        f"en {datos}).")
            v.after(500, vigilar)

    cerrar.config(command=salir)
    v.protocol("WM_DELETE_WINDOW", salir)
    v.after(500, vigilar)
    v.mainloop()
    hilo.join(30)


if __name__ == "__main__":
    main()
