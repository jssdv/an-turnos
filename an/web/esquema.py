"""Aplicador de esquema SQLite: esquema base (esquema_sqlite.sql, versión 12) y migraciones en migraciones_sqlite/ desde la 13, con la versión
en `PRAGMA user_version`. Cada archivo de área (area_<id>.db) lleva su propia cadena: esquema_area_sqlite.sql (versión 1) y migraciones_area/
desde la 2. Una migración publicada no se edita: se agrega otra."""
import re
import sqlite3
from pathlib import Path

BASE_SQLITE = Path(__file__).with_name("esquema_sqlite.sql")
MIGRACIONES_SQLITE = Path(__file__).with_name("migraciones_sqlite")
VERSION_BASE_SQLITE = 12
BASE_AREA = Path(__file__).with_name("esquema_area_sqlite.sql")
MIGRACIONES_AREA = Path(__file__).with_name("migraciones_area")
VERSION_BASE_AREA = 1


class BaseNoUsable(Exception):
    """La base no puede usarse. El mensaje (en español) se muestra tal cual al usuario; la base no se modifica."""


def _migraciones_sqlite(carpeta):
    return sorted((int(r.name[:3]), r) for r in carpeta.glob("[0-9][0-9][0-9]_*.sql"))


def ultima_sqlite(carpeta=None):
    """Versión más alta que conoce esta copia de An."""
    return max([VERSION_BASE_SQLITE] + [v for v, _ in _migraciones_sqlite(carpeta or MIGRACIONES_SQLITE)])


def ultima_area():
    return max([VERSION_BASE_AREA] + [v for v, _ in _migraciones_sqlite(MIGRACIONES_AREA)])


def _mas_nueva(version, ultima):
    raise BaseNoUsable(f"La base de datos es de una versión más nueva de An (esquema {version}); esta copia solo sabe hasta el {ultima}. "
                       "Instala la versión nueva de An. La base no se modificó.")


def comprobar_version_sqlite(version, carpeta=None):
    """Rechaza una base de otra versión (más nueva, o de un formato que no existe) sin tocarla."""
    ultima = ultima_sqlite(carpeta)
    if version > ultima:
        _mas_nueva(version, ultima)
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
            if v == 14:
                _separar_areas(raw, Path(con.ruta))
            raw.execute("PRAGMA foreign_keys = OFF")  # la 014 rehace trabajo y quita tablas con claves foráneas entre sí
            try:
                _script(raw, f"{ruta.read_text(encoding='utf-8')}\nPRAGMA user_version = {v};")
            finally:
                raw.execute("PRAGMA foreign_keys = ON")
            version = v
    for f in sorted(Path(con.ruta).parent.glob("area_*.db")):
        aplicar_area(f)
    return version


TABLAS_AREA = re.findall(r"CREATE TABLE (\w+)", BASE_AREA.read_text(encoding="utf-8"))


def _separar_areas(raw, ruta):
    """Pre-paso de la 014: copia las filas de cada área de an.db a su area_<id>.db (ids originales). Fuera de transacción; los archivos
    quedan escritos antes de que la 014 borre las tablas de an.db, y un intento a medias se rehace (se borran los archivos previos)."""
    areas = [r[0] for r in raw.execute("SELECT id FROM area")]
    for t in TABLAS_AREA:
        marcas = ",".join("?" * len(areas)) or "NULL"
        if raw.execute(f"SELECT 1 FROM {t} WHERE area_id NOT IN ({marcas}) LIMIT 1", areas).fetchone():  # sql-ok: nombre de tabla del esquema y marcas
            raise BaseNoUsable(f"La tabla {t} tiene filas de un área que no existe. La base no se modificó; envíala a soporte.")
    for a in areas:
        archivo = ruta.with_name(f"area_{a}.db")
        for sufijo in ("", "-wal", "-shm"):
            Path(str(archivo) + sufijo).unlink(missing_ok=True)
        aplicar_area(archivo)
        raw.execute("ATTACH DATABASE ? AS nueva", (str(archivo),))
        try:
            raw.execute("BEGIN IMMEDIATE")
            for t in TABLAS_AREA:
                raw.execute(f"INSERT INTO nueva.{t} SELECT * FROM main.{t} WHERE area_id = ?", (a,))  # sql-ok: nombre de tabla del esquema
            raw.execute("COMMIT")
        except BaseException:
            raw.execute("ROLLBACK")
            raise
        finally:
            raw.execute("DETACH DATABASE nueva")


def aplicar_area(ruta):
    """Crea (vacío → esquema base, en WAL) o actualiza el archivo de un área y devuelve su versión."""
    raw = sqlite3.connect(ruta, isolation_level=None)
    try:
        version = raw.execute("PRAGMA user_version").fetchone()[0]
        if version > ultima_area():
            _mas_nueva(version, ultima_area())
        if version == 0:
            raw.execute("PRAGMA journal_mode = WAL")
            _script(raw, f"{BASE_AREA.read_text(encoding='utf-8')}\nPRAGMA user_version = {VERSION_BASE_AREA};")
            version = VERSION_BASE_AREA
        for v, m in _migraciones_sqlite(MIGRACIONES_AREA):
            if v > version:
                _script(raw, f"{m.read_text(encoding='utf-8')}\nPRAGMA user_version = {v};")
                version = v
        return version
    finally:
        raw.close()
