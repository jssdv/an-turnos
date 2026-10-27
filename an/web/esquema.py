"""Aplicador de migraciones SQL (an/web/migraciones/NNN_*.sql). Una migración publicada no se edita: se agrega otra."""
from pathlib import Path

MIGRACIONES = Path(__file__).with_name("migraciones")


def aplicar(conn):
    """Aplica en orden las migraciones aún no registradas en `esquema_version`; devuelve los nombres aplicados."""
    conn.execute("CREATE TABLE IF NOT EXISTS esquema_version (version int PRIMARY KEY, nombre text NOT NULL, aplicada timestamptz NOT NULL DEFAULT now())")
    hechas = {r[0] for r in conn.execute("SELECT version FROM esquema_version")}
    aplicadas = []
    for ruta in sorted(MIGRACIONES.glob("[0-9][0-9][0-9]_*.sql")):
        version = int(ruta.name[:3])
        if version in hechas:
            continue
        conn.execute(ruta.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO esquema_version (version, nombre) VALUES (%s, %s)", (version, ruta.name))
        aplicadas.append(ruta.name)
    conn.commit()
    return aplicadas


def aplicar_sqlite(con):
    """Versión portable: crea el esquema completo si la base está vacía (no hay migraciones incrementales)."""
    if not con.execute("SELECT name FROM sqlite_master WHERE name = 'clinica'").fetchone():
        con._raw.executescript((Path(__file__).with_name("esquema_sqlite.sql")).read_text(encoding="utf-8"))


if __name__ == "__main__":  # python -m an.web.esquema: aplica las migraciones al esquema `public` de AN_PG_URL
    import os

    import psycopg

    with psycopg.connect(os.environ["AN_PG_URL"]) as c:
        print("aplicadas:", aplicar(c) or "ninguna")
