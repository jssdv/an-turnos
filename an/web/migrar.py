"""Migración de un turnos.db (SQLite) a un área de una clínica en PostgreSQL, con verificación de cifras.
Uso: python -m an.web.migrar turnos.db --clinica N --area M [--solo-verificar]
Una sola transacción: si el área ya tiene datos se niega, y si alguna cifra difiere entre origen y destino se revierte y sale con 1.
Se conecta con AN_PG_URL como el rol dueño de las tablas (como an.web.admin). Los mensajes nunca traen nombres ni valores."""
import argparse
import json
import os
import sys

import psycopg

from an.turnos import analitica, flujo, reglas
from an.turnos.db import BD
from an.turnos.pg import FILAS, Conexion

from . import conexion

# Orden de copia; los catálogos que `crear-area` siembra se reemplazan por los del origen.
CATALOGOS = ("turno", "puesto", "demanda", "tarifa", "parametro")
DE_USUARIO = ("colaborador", "persona_puesto", "novedad", "asignacion", "puesto_dia", "capacitacion", "periodo_estado", "cierre",
              "banco_mov", "asignacion_puesto", "cambio_turno", "solicitud")
TABLAS = CATALOGOS + DE_USUARIO
CON_ID = ("colaborador", "novedad", "banco_mov", "puesto", "demanda", "cambio_turno", "solicitud")
COMPARAR_CONTEO = TABLAS + ("periodo",)


class ErrorMigracion(Exception):
    pass


# --- cifras ------------------------------------------------------------------------------------------
def _claves(bd):
    """Claves de periodo del origen: las de asignacion y las de periodo_estado."""
    return sorted({r[0] for r in bd.c.execute("SELECT mes FROM asignacion")} | {r[0] for r in bd.c.execute("SELECT clave FROM periodo_estado")})


def _rango(claves):
    pares = [flujo.desde_clave(k) for k in claves]
    return min(p[0] for p in pares), max(p[1] for p in pares)


def _normal(x):
    return json.loads(json.dumps(x, default=str, sort_keys=True))


def cifras(bd, claves=None):
    """Lo que debe salir igual en origen y destino, como {sección: {clave: valor}} (claves: tabla, periodo o «rango»)."""
    claves = _claves(bd) if claves is None else claves
    q = bd.c.execute
    c = {"filas": {t: q("SELECT count(*) FROM " + t).fetchone()[0] for t in TABLAS},  # sql-ok: nombres de la lista constante
         "ids": {t: [None if x is None else int(x) for x in q("SELECT min(id), max(id), sum(id) FROM " + t).fetchone()]  # sql-ok: lista constante; sum es numeric en PostgreSQL
                for t in CON_ID},  # sql-ok: lista constante
         "celdas": {}, "horas": {}, "estado_banco": {}, "alertas": {}, "cambios": {}, "solicitudes": {}, "rango": {}}
    c["filas"]["periodo"] = len(claves)
    for mes, version, turno, n in q("SELECT mes, version, turno, count(*) FROM asignacion GROUP BY mes, version, turno ORDER BY 1, 2, 3"):
        c["celdas"].setdefault(f"{mes}|{version}", {})[turno] = n
    solicitudes = bd.solicitudes()
    for k in claves:
        ini, fin = flujo.desde_clave(k)
        c["horas"][k] = flujo.resumen_horas(bd, ini, fin)
        c["estado_banco"][k] = flujo.estado_banco(bd, ini, fin)
        c["alertas"][k] = len(reglas.validar(bd.contexto(ini.year), bd.asignaciones(k), flujo.fechas(ini, fin), bd.fijos(k)))
        c["solicitudes"][k] = sum(1 for s in solicitudes if s.desde <= fin and s.hasta >= ini)
    for periodo, tipo, total, anulados in q("SELECT periodo, tipo, count(*), count(anulado_en) FROM cambio_turno GROUP BY 1, 2 ORDER BY 1, 2"):
        c["cambios"].setdefault(periodo, {})[tipo] = [total, anulados]
    if claves:
        ini, fin = _rango(claves)
        c["rango"] = {"recargos": analitica.recargos_resumen(bd, ini, fin), "equidad": analitica.equidad(bd, ini, fin),
                      "banco": analitica.banco(bd, ini, fin)}
    return _normal(c)


def diferencias(a, b):
    """['sección/clave', …] donde difieren dos `cifras`. Nunca incluye valores ni nombres."""
    out = []
    for sec in sorted(set(a) | set(b)):
        for k in sorted(set(a.get(sec, {})) | set(b.get(sec, {}))):
            if a.get(sec, {}).get(k) != b.get(sec, {}).get(k):
                out.append(f"{sec}/{k}")
    return out


# --- destino -----------------------------------------------------------------------------------------
def _columnas(conn, tabla):
    return [r[0] for r in conn.execute("SELECT column_name FROM information_schema.columns WHERE table_schema = current_schema() "
                                       "AND table_name = %s AND column_name NOT IN ('clinica_id', 'area_id') ORDER BY ordinal_position", (tabla,))]


def _comprobar_destino(conn, clinica, area):
    conexion.alcance(conn, clinica)
    f = conn.execute("SELECT tipo FROM area WHERE id = %s AND clinica_id = %s", (area, clinica)).fetchone()
    if f is None:
        raise ErrorMigracion("el área no existe en esa clínica")
    if f[0] != "turnos":
        raise ErrorMigracion("el área no es de tipo «turnos»")
    conexion.alcance(conn, clinica, area)
    for t in DE_USUARIO + ("periodo",):
        if conn.execute("SELECT 1 FROM " + t + " WHERE area_id = %s LIMIT 1", (area,)).fetchone():  # sql-ok: nombres de la lista constante
            raise ErrorMigracion("el área ya tiene datos; la migración solo entra a un área vacía")


def _copiar(origen, conn, tabla):
    en_pg = _columnas(conn, tabla)
    en_origen = {r["name"] for r in origen.c.execute("PRAGMA table_info(" + tabla + ")")}  # sql-ok: nombres de la lista constante
    cols = [c for c in en_pg if c in en_origen]
    filas = [tuple(r) for r in origen.c.execute("SELECT " + ", ".join(cols) + " FROM " + tabla)]  # sql-ok: columnas de information_schema
    if filas:
        Conexion(conn, confirmar=False).executemany(
            "INSERT INTO " + tabla + " (" + ", ".join(cols) + ") VALUES (" + ", ".join("?" * len(cols)) + ")", filas)  # sql-ok: columnas de information_schema
    return len(filas)


def _secuencias(conn):
    """Sube cada identidad a max(lo ya usado, lo migrado). Lee la secuencia, no las filas de otras áreas (RLS no las deja ver)."""
    for t in CON_ID:
        seq = conn.execute("SELECT pg_get_serial_sequence(%s, 'id')", (t,)).fetchone()[0]
        usado = conn.execute("SELECT COALESCE(pg_sequence_last_value(%s::regclass), 0)", (seq,)).fetchone()[0]
        mx = conn.execute("SELECT COALESCE(max(id), 0) FROM " + t).fetchone()[0]  # sql-ok: nombres de la lista constante
        if max(usado, mx) > 0:
            conn.execute("SELECT setval(%s, %s)", (seq, max(usado, mx)))


def _como_app(conn):
    """Si el rol se salta RLS (superusuario de desarrollo), lee como `an_app`, igual que la API; si no, no hace nada."""
    if conn.execute("SELECT rolsuper OR rolbypassrls FROM pg_roles WHERE rolname = current_user").fetchone()[0]:
        conn.execute("SET LOCAL ROLE an_app")


def _cifras_destino(conn, claves):
    _como_app(conn)
    try:
        return cifras(BD.postgres(Conexion(conn, confirmar=False)), claves)
    finally:
        conn.execute("RESET ROLE")


def verificar(origen, conn, clinica, area):
    """Compara el origen con el área ya migrada. Devuelve la lista de diferencias (vacía = iguales)."""
    conexion.alcance(conn, clinica, area)
    claves = _claves(origen)
    try:
        return diferencias(cifras(origen, claves), _cifras_destino(conn, claves))
    finally:
        conn.rollback()


def migrar(origen, conn, clinica, area, antes_de_verificar=None):
    """Copia `origen` (BD sobre SQLite) al área. Devuelve {tabla: filas}; lanza ErrorMigracion si se niega o si algo difiere
    (en ese caso no queda nada escrito). `antes_de_verificar(conn)` es un gancho de prueba."""
    claves = _claves(origen)
    for k in claves:
        try:
            flujo.desde_clave(k)
        except ValueError:
            raise ErrorMigracion(f"clave de periodo no reconocida: «{k}» (se esperaba AAAA-MM-DD/AAAA-MM-DD)")
    try:
        _comprobar_destino(conn, clinica, area)
        for t in CATALOGOS:
            conn.execute("DELETE FROM " + t + " WHERE area_id = %s", (area,))  # sql-ok: nombres de la lista constante; el filtro vale aunque el rol se salte RLS
        copiadas = {t: _copiar(origen, conn, t) for t in TABLAS}
        cerrados = dict(origen.c.execute("SELECT clave, cerrado_en FROM periodo_estado").fetchall())
        for k in claves:
            conn.execute("INSERT INTO periodo (clave, cerrado_en) VALUES (%s, %s)", (k, cerrados.get(k)))
        copiadas["periodo"] = len(claves)
        _secuencias(conn)
        if antes_de_verificar:
            antes_de_verificar(conn)
        if difieren := diferencias(cifras(origen, claves), _cifras_destino(conn, claves)):
            raise ErrorMigracion("las cifras no coinciden en: " + ", ".join(difieren))
        conn.commit()
        return copiadas
    except psycopg.errors.UniqueViolation:
        conn.rollback()
        raise ErrorMigracion("un id del origen ya existe en otra área de la base; no se escribió nada")
    except BaseException:
        conn.rollback()
        raise


def main(argv=None, conn=None):
    p = argparse.ArgumentParser(prog="python -m an.web.migrar", description=__doc__.splitlines()[0])
    p.add_argument("turnos_db")
    p.add_argument("--clinica", type=int, required=True)
    p.add_argument("--area", type=int, required=True)
    p.add_argument("--solo-verificar", action="store_true", help="no escribe: compara el origen con el área ya migrada")
    a = p.parse_args(argv)
    if not os.path.isfile(a.turnos_db):
        print("Error: no existe ese archivo", file=sys.stderr)
        return 1
    propia = conn is None
    origen = BD(a.turnos_db)
    try:
        conn = conn or psycopg.connect(os.environ["AN_PG_URL"], row_factory=FILAS)
        if a.solo_verificar:
            if dif := verificar(origen, conn, a.clinica, a.area):
                print("Difieren: " + ", ".join(dif), file=sys.stderr)
                return 1
            print("Las cifras coinciden.")
            return 0
        copiadas = migrar(origen, conn, a.clinica, a.area)
        print("\n".join(f"{t}: {n}" for t, n in copiadas.items()) + "\nMigración completa; las cifras coinciden.")
        return 0
    except ErrorMigracion as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    finally:
        origen.cerrar()
        if propia and conn is not None:
            conn.close()


if __name__ == "__main__":
    sys.exit(main())
