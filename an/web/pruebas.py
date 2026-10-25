"""Ayudas de prueba: un esquema PostgreSQL desechable con una clínica y un área, para correr los tests del núcleo con AN_BD=postgres."""
import atexit
import os
import uuid

from an.turnos.pg import Conexion

from . import esquema


def esquema_temporal():
    """(Conexion con alcance fijado, función que borra el esquema). Los ids empiezan en 1 en cada llamada."""
    c = Conexion.abrir(os.environ["AN_PG_URL"])
    nombre = "t_" + uuid.uuid4().hex[:10]
    c.conn.execute(f'CREATE SCHEMA "{nombre}"')
    c.conn.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(c.conn)
    clinica = c.conn.execute("INSERT INTO clinica (nombre) VALUES ('Prueba') RETURNING id").fetchone()[0]
    c.conn.execute("SELECT set_config('app.clinica', %s, false)", (str(clinica),))
    area = c.conn.execute("INSERT INTO area (nombre) VALUES ('Servicio') RETURNING id").fetchone()[0]
    c.conn.execute("SELECT set_config('app.area', %s, false)", (str(area),))
    c.conn.commit()

    def limpiar():
        if c.conn.closed:
            return
        c.conn.rollback()
        c.conn.execute(f'DROP SCHEMA "{nombre}" CASCADE')
        c.conn.commit()
        c.close()
    atexit.register(limpiar)  # los tests no llaman cerrar(): el esquema se borra al terminar el proceso
    return c, limpiar
