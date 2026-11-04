"""Entregable Windows: API + trabajador del solver + front sobre un archivo SQLite, con una ventana mínima (Abrir / Cerrar).
Datos: %LOCALAPPDATA%\\AnTurnos\\an.db (o AN_DATOS). Respaldo al abrir (antes de tocar la base) y al cerrar: Documentos\\An-respaldos (los últimos 10). Arranque: python -m an.web.entregable"""
import logging
import os
import socket
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
from .esquema import BaseNoUsable
from .trabajador import Trabajador

PUERTO = int(os.environ.get("AN_PUERTO", "8765"))
CLINICA, AREA, CORREO = "Mi clínica", "Turnos", "admin@an.local"
RESPALDOS_MAX = 10


def carpeta_datos():
    return Path(os.environ.get("AN_DATOS") or Path(os.environ.get("LOCALAPPDATA") or Path.home()) / "AnTurnos")


def carpeta_respaldos():
    return Path.home() / "Documents" / "An-respaldos"


def carpeta_front():
    frozen = hasattr(sys, "_MEIPASS")
    return Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[2])) / ("web_dist" if frozen else "web/dist")


def ultimo_respaldo(destino):
    respaldos = sorted(destino.glob("an_*.db"))
    return respaldos[-1] if respaldos else None


def _error_base(e, ruta, respaldos):
    """Traduce un error de SQLite al mensaje para el usuario. Ningún caso borra ni sobrescribe la base."""
    txt = str(e).lower()
    if "locked" in txt or "busy" in txt:
        return ("La base de datos está en uso: puede haber otra copia de An abierta. Cierra las otras ventanas de An "
                "(revisa también que no quede un proceso de An en el Administrador de tareas) y vuelve a intentar.\n"
                f"Base: {ruta}")
    if isinstance(e, sqlite3.OperationalError) and any(p in txt for p in ("readonly", "read-only", "unable to open", "disk i/o")):
        return (f"No se puede escribir en la carpeta de datos: {ruta.parent}. Revisa que no sea de solo lectura "
                "(por ejemplo, una carpeta de OneDrive sin conexión o un USB protegido) y que tengas permisos sobre ella.\n"
                f"Detalle: {e}")
    if isinstance(e, sqlite3.OperationalError):
        return f"La base de datos no se pudo usar: {e}\nBase: {ruta}"
    return _mensaje_danada(ruta, respaldos)


def _mensaje_danada(ruta, respaldos):
    ultimo = ultimo_respaldo(respaldos)
    if ultimo:
        recuperar = f"3. Copia el respaldo más reciente ({ultimo}) a {ruta.parent} con el nombre {ruta.name}.\n"
    else:
        recuperar = f"3. Todavía no hay respaldos en {respaldos}. Envía el archivo dañado a soporte.\n"
    return ("La base de datos está dañada:\n"
            f"{ruta}\n\n"
            "An no la modificó ni la borró. Para recuperar tus datos:\n"
            "1. Cierra An.\n"
            "2. Cambia el nombre del archivo dañado (por ejemplo, an_danado.db) para conservarlo.\n"
            f"{recuperar}"
            "4. Vuelve a abrir An.")


def revisar_base(ruta, respaldos):
    """Antes de tocar nada: integridad (PRAGMA quick_check) y versión, con la base abierta solo para leer.
    Devuelve la versión, o None si la base no existe o está vacía."""
    if not ruta.exists() or ruta.stat().st_size == 0:
        return None
    try:
        con = sqlite3.connect(f"{ruta.resolve().as_uri()}?mode=ro", uri=True, timeout=5)
        try:
            integridad = con.execute("PRAGMA quick_check").fetchall()
            version = con.execute("PRAGMA user_version").fetchone()[0]
            tablas = {r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        finally:
            con.close()
    except sqlite3.Error as e:
        raise BaseNoUsable(_error_base(e, ruta, respaldos)) from e
    if integridad != [("ok",)]:
        raise BaseNoUsable(_mensaje_danada(ruta, respaldos))
    esquema.comprobar_version_sqlite(version)
    if version == 0 and "clinica" in tablas:
        esquema.comprobar_base_sin_version(tablas)  # antes de abrirla para escribir (Con cambia el modo de journal)
    return version


def preparar_base(ruta, respaldos):
    """Revisa la base, la copia (si ya tiene datos) y crea o actualiza el esquema. La primera vez crea clínica, área y administrador.
    Devuelve el texto del primer acceso (o None)."""
    ruta = Path(ruta)
    version = revisar_base(ruta, respaldos)
    if version is not None:
        try:
            respaldar(ruta, respaldos)
        except (OSError, sqlite3.Error) as e:
            if version < esquema.ultima_sqlite():  # hay migraciones por aplicar: sin copia no se toca la base
                raise BaseNoUsable(f"No se pudo guardar la copia de respaldo en {respaldos} antes de actualizar la base ({e}). "
                                   "Por seguridad no se actualizó. Revisa que la carpeta exista y no sea de solo lectura.") from e
            logging.getLogger("an").warning("no se pudo respaldar al abrir: %s", e)
    try:
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
    except sqlite3.Error as e:
        raise BaseNoUsable(_error_base(e, ruta, respaldos)) from e


def respaldar(ruta, destino):
    """Copia consistente de la base (API de respaldo de SQLite, válida con la base abierta) y poda a los últimos RESPALDOS_MAX."""
    destino.mkdir(parents=True, exist_ok=True)
    archivo = destino / f"an_{datetime.now():%Y%m%d_%H%M%S}.db"
    origen, copia = sqlite3.connect(ruta), sqlite3.connect(archivo)
    ok = False
    try:
        origen.backup(copia)
        ok = True
    finally:
        copia.close()
        origen.close()
        if not ok:  # una copia a medias sería el «último respaldo» que se ofrece al recuperar
            archivo.unlink(missing_ok=True)
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
    with socket.socket() as sk:
        sk.settimeout(1)
        return sk.connect_ex(("127.0.0.1", PUERTO)) == 0


def servicio(estado, ruta):
    """Hilo de fondo: API y trabajador. `estado` lo lee la ventana ("listo", "web", "primer", "error", "fin")."""
    try:
        estado["primer"] = preparar_base(ruta, carpeta_respaldos())
        os.environ["AN_ORIGEN"] = f"http://localhost:{PUERTO}"
        pool = conexion.abrir_pool(ruta)
        app = crear_app(pool)
        servir_front(app, carpeta_front())
        parar = threading.Event()
        threading.Thread(target=Trabajador(pool).servir, args=(parar,), daemon=True).start()
        estado["web"] = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=PUERTO, log_level="warning"))
        threading.Timer(1.0, estado.__setitem__, ("listo", True)).start()
        estado["web"].run()
        parar.set()
    except BaseNoUsable as e:
        logging.getLogger("an").error("base no usable: %s", e)
        estado["error"] = str(e)
    except BaseException:
        logging.getLogger("an").exception("error de arranque")
        estado["error"] = "Ocurrió un problema al iniciar. Intenta abrirlo de nuevo; si se repite, envía el registro a soporte."
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
            messagebox.showerror("An no pudo iniciar", f"{estado['error']}\n\nRegistro: {datos / 'an.log'}")
            v.destroy()
        elif estado.get("fin"):
            try:
                respaldar(ruta, carpeta_respaldos())
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
