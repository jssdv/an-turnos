import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Paridad de la grilla (Fase 4): las celdas de octubre 2026 en la base migrada (PostgreSQL) son las de `turnos.db` (la app Qt).

Necesita `AN_PG_URL`, una base migrada con `an.web.migrar` (clínica `AN_CLINICA`, área `AN_AREA`, por defecto 1) y el `turnos.db` de origen en la raíz del repo (no está en Git). Si falta algo, se omite. Imprime OK."""
import contextlib
import tempfile

import psycopg

from an.turnos.db import BD
from an.turnos.pg import FILAS, Conexion

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
ORIGEN = os.path.join(RAIZ, "turnos.db")


def _omitir(motivo):
    try:
        import pytest
        pytest.skip(motivo)
    except ImportError:
        print("omitida:", motivo)


@contextlib.contextmanager
def destino():
    """BD sobre PostgreSQL con el alcance RLS de la clínica y el área de la prueba (la misma `BD` que usa la API)."""
    c = psycopg.connect(os.environ["AN_PG_URL"], row_factory=FILAS)
    clinica = os.environ.get("AN_CLINICA", "1")
    area = os.environ.get("AN_AREA", "1")
    c.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (clinica, area))
    try:
        yield BD.postgres(Conexion(c))
    finally:
        c.close()


def test_celdas_iguales_a_qt():
    if not os.environ.get("AN_PG_URL"):
        return _omitir("sin AN_PG_URL")
    if not os.path.exists(ORIGEN):
        return _omitir("sin turnos.db en la raíz del repo")
    origen = BD(ORIGEN)
    claves = sorted({r[0] for r in origen.c.execute("SELECT DISTINCT mes FROM asignacion")})
    assert claves, "turnos.db no tiene asignaciones"
    with destino() as bd:
        for clave in claves:
            qt, web = origen.asignaciones(clave), bd.asignaciones(clave)
            faltan, sobran = set(qt) - set(web), set(web) - set(qt)
            cambian = [k for k in set(qt) & set(web) if qt[k] != web[k]]
            assert not (faltan or sobran or cambian), f"{clave}: faltan {len(faltan)}, sobran {len(sobran)}, distintas {len(cambian)}; ej. {sorted(cambian)[:3]}"
            print(f"OK {clave}: {len(qt)} celdas iguales a la app Qt")


if __name__ == "__main__":
    test_celdas_iguales_a_qt()
