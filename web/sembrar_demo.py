"""Siembra datos sintéticos para ver el front sin datos reales: una clínica, un área de turnos, usuarios y octubre 2026 con 40 personas.
Uso (desde la raíz del repo): python web/sembrar_demo.py [ruta.db]   (por defecto web/.demo/an.db; se borra y se rehace)"""
import os
import shutil
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from an.turnos.db import BD  # noqa: E402
from an.turnos.dominio import Colaborador, Novedad  # noqa: E402
from an.turnos.puente import Conexion  # noqa: E402
from an.web import admin, auth, esquema, sqlite_pg  # noqa: E402

CLAVE = "clave-larga-1"
PERIODO = "2026-10-01/2026-10-31"
ROTACION = ["M", "M", "T", "T", "NC", "L", "L", "M", "T", "T", "C", "M", "L", "L"]


def main(ruta=None, personas=40):
    ruta = Path(ruta or Path(__file__).with_name(".demo") / "an.db")
    shutil.rmtree(ruta.parent, ignore_errors=True) if ruta.name == "an.db" else ruta.unlink(missing_ok=True)
    ruta.parent.mkdir(parents=True, exist_ok=True)
    su = sqlite_pg.abrir(str(ruta))
    esquema.aplicar_sqlite(su)
    cl = admin.crear_clinica(su, "Clínica de prueba")
    su.commit()
    ar = admin.crear_area(su, cl, "Turnos")
    bd = BD.web(Conexion(su))
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
    for correo, perm, debe in (("editor@demo.co", "editar", 0), ("lector@demo.co", "ver", 0), ("nuevo@demo.co", "ver", 1)):
        uid = su.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, clinica_id) VALUES (%s, %s, %s, %s, %s) RETURNING id",
                         (correo, correo.split("@")[0].capitalize(), auth.hash_clave(CLAVE), debe, cl)).fetchone()[0]
        su.execute("INSERT INTO usuario_area (usuario_id, area_id, permiso, clinica_id) VALUES (%s, %s, %s, %s)", (uid, ar, perm, cl))
    su.execute("INSERT INTO usuario (correo, nombre, hash_clave, debe_cambiar, es_admin, clinica_id) VALUES ('admin@demo.co', 'Admin', %s, 0, 1, %s)",
               (auth.hash_clave(CLAVE), cl))  # administra la clínica; sin permiso propio en el área (ve todo)
    su.commit()
    su.close()
    print(ruta)
    print(f"usuarios: editor@demo.co / lector@demo.co / admin@demo.co (administra) / nuevo@demo.co (debe cambiar la clave) · clave {CLAVE}", file=sys.stderr)


if __name__ == "__main__":
    main(*sys.argv[1:2])
