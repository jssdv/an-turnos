"""Siembra datos sintéticos para ver el front sin datos reales: una clínica, un área de turnos, usuarios y octubre 2026 con 40 personas.
Uso (desde la raíz del repo): AN_PG_URL=postgresql://an:an_dev@127.0.0.1:5433/an python web/sembrar_demo.py [esquema]
Crea el esquema `f4_demo` (se borra y se rehace) y escribe la URL para arrancar la API: AN_ROL=an_app AN_ORIGEN=http://localhost:5173 uvicorn …"""
import os
import sys
from datetime import date, timedelta

import psycopg

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from an.turnos.db import BD  # noqa: E402
from an.turnos.dominio import Colaborador, Novedad  # noqa: E402
from an.turnos.pg import FILAS, Conexion  # noqa: E402
from an.web import auth, esquema  # noqa: E402

CLAVE = "clave-larga-1"
PERIODO = "2026-10-01/2026-10-31"
ROTACION = ["M", "M", "T", "T", "NC", "L", "L", "M", "T", "T", "C", "M", "L", "L"]


def main(nombre="f4_demo", personas=40):
    url = os.environ["AN_PG_URL"]
    su = psycopg.connect(url, row_factory=FILAS)
    su.execute(f'DROP SCHEMA IF EXISTS "{nombre}" CASCADE')
    su.execute(f'CREATE SCHEMA "{nombre}"')
    su.execute(f'SET search_path TO "{nombre}"')
    esquema.aplicar(su)
    cl = su.execute("INSERT INTO clinica (nombre) VALUES ('Clínica de prueba') RETURNING id").fetchone()[0]
    ar = su.execute("INSERT INTO area (nombre, clinica_id) VALUES ('Turnos', %s) RETURNING id", (cl,)).fetchone()[0]
    su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(cl), str(ar)))
    bd = BD.postgres(Conexion(su))
    bd.sembrar()
    ids = []
    for i in range(personas):
        p = Colaborador(0, f"Persona {i + 1:02d}")
        bd.guardar_colaborador(p)
        ids.append(p.id)
    su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s)", (PERIODO, cl, ar))
    for k, cid in enumerate(ids):
        for d in range(31):
            f = date(2026, 10, 1) + timedelta(days=d)
            t = ROTACION[(d + k) % len(ROTACION)]
            fijo = int((d * 7 + k * 3) % 41 == 0)  # unas pocas editadas a mano
            for v in ("original", "cambios"):
                su.execute("INSERT INTO asignacion VALUES (%s, %s, %s, %s, %s, 'solver', %s, %s, %s)",
                           (PERIODO, v, cid, f.isoformat(), t, fijo if v == "cambios" else 0, cl, ar))
    bd.guardar_novedad(Novedad(ids[3], "Vacaciones", date(2026, 10, 12), date(2026, 10, 16)))
    su.execute("RESET app.clinica")
    su.execute("RESET app.area")
    for correo, perm, debe in (("editor@demo.co", "editar", False), ("lector@demo.co", "ver", False), ("nuevo@demo.co", "ver", True)):
        uid = su.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, clinica_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                         (correo, correo.split("@")[0].capitalize(), auth.hash_clave(CLAVE), debe, cl)).fetchone()[0]
        su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s)", (uid, ar, perm, cl))
    su.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, es_admin, clinica_id) VALUES ('admin@demo.co', 'Admin', %s, false, true, %s)",
               (auth.hash_clave(CLAVE), cl))  # administra la clínica; sin permiso propio en el área (ve todo)
    su.commit()
    sep = "&" if "?" in url else "?"
    print(f"AN_PG_URL='{url}{sep}options=-csearch_path%3D{nombre}' AN_ROL=an_app AN_ORIGEN=http://localhost:5173")
    print(f"usuarios: editor@demo.co / lector@demo.co / admin@demo.co (administra) / nuevo@demo.co (debe cambiar la clave) · clave {CLAVE} · clínica {cl} · área {ar}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:2])
