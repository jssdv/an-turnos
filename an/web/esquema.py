"""Aplicador de esquema SQLite: esquema base (esquema_sqlite.sql, versión 12) y migraciones en migraciones_sqlite/ desde la 13, con la versión
en `PRAGMA user_version`. Una migración publicada no se edita: se agrega otra."""
import re
import sqlite3
from pathlib import Path

BASE_SQLITE = Path(__file__).with_name("esquema_sqlite.sql")
MIGRACIONES_SQLITE = Path(__file__).with_name("migraciones_sqlite")
VERSION_BASE_SQLITE = 12


class BaseNoUsable(Exception):
    """La base no puede usarse. El mensaje (en español) se muestra tal cual al usuario; la base no se modifica."""


def _migraciones_sqlite(carpeta):
    return sorted((int(r.name[:3]), r) for r in carpeta.glob("[0-9][0-9][0-9]_*.sql"))


def ultima_sqlite(carpeta=None):
    """Versión más alta que conoce esta copia de An."""
    return max([VERSION_BASE_SQLITE] + [v for v, _ in _migraciones_sqlite(carpeta or MIGRACIONES_SQLITE)])


def comprobar_version_sqlite(version, carpeta=None):
    """Rechaza una base de otra versión (más nueva, o de un formato que no existe) sin tocarla."""
    ultima = ultima_sqlite(carpeta)
    if version > ultima:
        raise BaseNoUsable(f"La base de datos es de una versión más nueva de An (esquema {version}); esta copia solo sabe hasta el {ultima}. "
                           "Instala la versión nueva de An. La base no se modificó.")
    if 0 < version < VERSION_BASE_SQLITE:
        raise BaseNoUsable(f"La base de datos tiene un esquema que An no reconoce (versión {version}). La base no se modificó.")


def _script(raw, sql):
    """Ejecuta `sql` en una sola transacción: si algo falla, no queda nada a medias."""
    try:
        raw.executescript(f"BEGIN IMMEDIATE;\n{sql}\nCOMMIT;")
    except sqlite3.Error:
        if raw.in_transaction:
            raw.execute("ROLLBACK")
        raise


def comprobar_base_sin_version(tablas):
    """Base del código anterior (sin versión, con clínica): debe tener todas las tablas del esquema base."""
    faltan = set(re.findall(r"CREATE TABLE (\w+)", BASE_SQLITE.read_text(encoding="utf-8"))) - set(tablas)
    if faltan:
        raise BaseNoUsable(f"La base de datos es del formato anterior y le faltan tablas ({', '.join(sorted(faltan))}). "
                           "An no la modificó. Restaura el respaldo más reciente.")


def aplicar_sqlite(con, carpeta=None):
    """Deja la base al día y devuelve su versión.
    Vacía: crea el esquema base. Del código anterior (sin versión, con tablas): comprueba que estén todas y la marca 12.
    Luego aplica en orden las migraciones pendientes; cada una queda con su versión en la misma transacción."""
    raw = con._raw
    version = raw.execute("PRAGMA user_version").fetchone()[0]
    comprobar_version_sqlite(version, carpeta)
    if version == 0:
        tablas = {r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        if "clinica" in tablas:
            comprobar_base_sin_version(tablas)
            _script(raw, f"PRAGMA user_version = {VERSION_BASE_SQLITE};")
        else:
            _script(raw, f"{BASE_SQLITE.read_text(encoding='utf-8')}\nPRAGMA user_version = {VERSION_BASE_SQLITE};")
        version = VERSION_BASE_SQLITE
    for v, ruta in _migraciones_sqlite(carpeta or MIGRACIONES_SQLITE):
        if v > version:
            _script(raw, f"{ruta.read_text(encoding='utf-8')}\nPRAGMA user_version = {v};")
            version = v
    return version
