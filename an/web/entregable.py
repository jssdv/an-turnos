"""Entregable Windows: API + trabajador del solver + front sobre un archivo SQLite, con una ventana mínima (Abrir / Cerrar).
Datos: %LOCALAPPDATA%\\AnTurnos\\an.db (o AN_DATOS). Respaldo al cerrar: Documentos\\An-respaldos (los últimos 10). Arranque: python -m an.web.entregable"""
import logging
import os
import shutil
import sqlite3
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException

from . import admin, conexion, esquema, sqlite_pg
from .app import crear_app
from .trabajador import Trabajador

PUERTO = int(os.environ.get("AN_PUERTO", "8765"))
CLINICA, AREA, CORREO = "Mi clínica", "Esterilización", "admin@an.local"
RESPALDOS_MAX = 10


def carpeta_datos():
    return Path(os.environ.get("AN_DATOS") or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "AnTurnos")


def carpeta_front():
    frozen = hasattr(sys, "_MEIPASS")
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / ("web_dist" if frozen else "web/dist")


def preparar_base(ruta):
    """Crea el esquema, la clínica, el área y el administrador la primera vez. Devuelve el texto del primer acceso (o None)."""
    con = sqlite_pg.abrir(ruta)
    try:
        esquema.aplicar_sqlite(con)
        con.commit()
        if con.execute("SELECT 1 FROM clinica LIMIT 1").fetchone():
            return None
        cl = admin.crear_clinica(con, CLINICA)
        con.commit()
        area = admin.crear_area(con, cl, AREA)
        uid, clave = admin.crear_usuario(con, cl, CORREO, "Administrador", es_admin=True)
        admin.dar_permiso(con, uid, area, "editar")
        con.commit()
        return f"Usuario: {CORREO}\nClave temporal: {clave}\n(el sistema pide cambiarla al entrar)\n"
    finally:
        con.close()


def respaldar(ruta, destino):
    """Copia consistente de la base (API de respaldo de SQLite, válida con la base abierta) y poda a los últimos RESPALDOS_MAX."""
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / f"an_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen, copia = sqlite3.connect(ruta), sqlite3.connect(archivo)
    try:
        origen.backup(copia)
    finally:
        copia.close()
        origen.close()
    for viejo in sorted(destino.glob("an_*.db"))[:-RESPALDOS_MAX]:
        viejo.unlink(missing_ok=True)


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


def en_marcha():
    import socket

    with socket.socket() as sk:
        sk.settimeout(1)
        return sk.connect_ex(("127.0.0.1", PUERTO)) == 0


def servicio(estado, ruta):
    """Hilo de fondo: API y trabajador. `estado` lo lee la ventana ("listo", "web", "primer", "error", "fin")."""
    try:
        estado["primer"] = preparar_base(ruta)
        os.environ["AN_PG_URL"], os.environ["AN_ORIGEN"] = f"sqlite:{ruta}", f"http://localhost:{PUERTO}"
        pool = conexion.abrir_pool()
        app = crear_app(pool)
        servir_front(app, carpeta_front())
        parar = threading.Event()
        threading.Thread(target=Trabajador(pool).servir, args=(parar,), daemon=True).start()
        estado["web"] = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PUERTO, log_level="warning"))
        threading.Timer(1.0, estado.__setitem__, ("listo", True)).start()
        estado["web"].run()
        parar.set()
    except BaseException:
        logging.getLogger("an").exception("error de arranque")
        estado["error"] = True
    finally:
        estado["fin"] = True


def main():
    import tkinter as tk
    from tkinter import messagebox

    for flujo in ("stdout", "stderr"):  # programa sin consola: estos flujos son None y uvicorn llama a isatty() sobre ellos
        if getattr(sys, flujo) is None:
            setattr(sys, flujo, open(os.devnull, "w"))
    datos = carpeta_datos()
    datos.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s", handlers=[logging.FileHandler(datos / "an.log", encoding="utf-8")])
    url = f"http://localhost:{PUERTO}"
    if en_marcha():  # segunda vez que se abre: solo lleva al navegador
        webbrowser.open(url)
        return
    ruta = datos / "an.db"
    estado = {}
    hilo = threading.Thread(target=servicio, args=(estado, ruta), daemon=True)
    hilo.start()

    v = tk.Tk()
    v.title("An")
    v.geometry("420x190")
    v.resizable(False, False)
    texto = tk.Label(v, text="Iniciando…", wraplength=380, pady=18)
    texto.pack()
    abrir = tk.Button(v, text="Abrir An", state="disabled", width=20, command=lambda: webbrowser.open(url))
    abrir.pack(pady=4)
    cerrar = tk.Button(v, text="Cerrar An", width=20)
    cerrar.pack(pady=4)

    def salir():
        cerrar.config(state="disabled")
        abrir.config(state="disabled")
        texto.config(text="Cerrando… (guardando una copia de respaldo)")
        if "web" in estado:
            estado["web"].should_exit = True
        estado["salir"] = True

    def vigilar():
        if estado.get("error"):
            messagebox.showerror("An no pudo iniciar", f"Ocurrió un problema al iniciar. Intenta abrirlo de nuevo.\n"
                                 f"Si se repite, envía este archivo a soporte:\n{datos / 'an.log'}")
            v.destroy()
        elif estado.get("fin"):
            try:
                respaldar(ruta, Path.home() / "Documents" / "An-respaldos")
            except Exception:
                logging.getLogger("an").exception("no se pudo respaldar")
            v.destroy()
        else:
            if estado.get("listo") and not estado.get("salir") and abrir["state"] == "disabled":
                texto.config(text="An está funcionando.\nDeja esta ventana abierta mientras lo uses; ciérrala con «Cerrar An» al terminar.")
                abrir.config(state="normal")
                webbrowser.open(url)
                if estado.get("primer"):
                    messagebox.showinfo("Primer acceso", estado["primer"] + f"\nAnota estos datos: se muestran una sola vez.")
            v.after(500, vigilar)

    cerrar.config(command=salir)
    v.protocol("WM_DELETE_WINDOW", salir)
    v.after(500, vigilar)
    v.mainloop()
    hilo.join(30)


if __name__ == "__main__":
    main()
