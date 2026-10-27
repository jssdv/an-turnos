"""Adaptador de sqlite3 con la forma de psycopg 3 que usa la capa web (`cursor()`, `execute` con `%s`, filas por índice y nombre, pool).
Es la versión portable (un solo archivo, sin servidor): una clínica y un área, ids 1; las funciones `app_*` de Postgres viven aquí en Python."""
import contextlib
import json
import re
import sqlite3
import threading
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb

from an.turnos.pg import Fila

MIN_SESION, HORAS_SESION = 35, 12


def _ahora():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")


def _fecha(b):
    return datetime.fromisoformat(b.decode()).replace(tzinfo=timezone.utc)


sqlite3.register_adapter(Jsonb, lambda j: json.dumps(j.obj))
sqlite3.register_adapter(memoryview, bytes)
sqlite3.register_converter("jsonb", json.loads)
sqlite3.register_converter("boolean", lambda b: bool(int(b)))
sqlite3.register_converter("timestamptz", _fecha)

_FUNCION = re.compile(r"app_(\w+)\(")
_INTERVALO = re.compile(r"now\(\)\s*-\s*interval\s*'(\d+)\s+(\w+?)s?'", re.I)
_MARCA = re.compile(r"%%|%s")
_INSERT = re.compile(r"(INSERT\s+(?:OR\s+\w+\s+)?INTO\s+)(\w+)(\s+(?:VALUES\s*\(|SELECT\s))", re.I)


def _cuantos_valores(sql, desde, select=False):
    """Cuenta los valores de la primera tupla (o de la lista de un SELECT) que empieza en `desde`, respetando comillas y paréntesis."""
    base = 0 if select else 1
    prof, n, i, comilla = base, 1, desde, None
    while i < len(sql) and (prof or select):
        if select and prof == 0 and re.match(r"\sFROM\s", sql[i:i + 6], re.I):
            break
        ch = sql[i]
        if comilla:
            comilla = None if ch == comilla else comilla
        elif ch in "'\"":
            comilla = ch
        elif ch == "(":
            prof += 1
        elif ch == ")":
            prof -= 1
        elif ch == "," and prof == base:
            n += 1
        i += 1
    return n


class _Col:
    def __init__(self, nombre):
        self.name = nombre


class _Vacio:
    """Resultado de las llamadas que en Postgres no devuelven filas (set_config, funciones void)."""
    description, rowcount = (), 0

    def fetchone(self):
        return None

    def fetchall(self):
        return []

    def __iter__(self):
        return iter(())


class Cur:
    def __init__(self, con):
        self._con, self._cur = con, con._raw.cursor()
        self.description = None

    rowcount = property(lambda self: self._cur.rowcount)

    def _completar(self, sql):
        """Postgres rellena con sus defaults las columnas finales de un INSERT … VALUES posicional; SQLite exige nombrarlas."""
        m = _INSERT.search(sql)
        if not m:
            return sql
        cols = self._con._columnas(m.group(2))
        n = _cuantos_valores(sql, m.end(), select=m.group(3).strip().upper() == 'SELECT')
        if n >= len(cols):
            return sql
        return sql[:m.end(2)] + " (" + ", ".join(cols[:n]) + ")" + sql[m.end(2):]

    def _traducir(self, sql):
        sql = self._completar(sql)
        sql = _MARCA.sub(lambda m: "?" if m.group(0) == "%s" else "%", sql)
        sql = _INTERVALO.sub(lambda m: f"datetime('now','-{m.group(1)} {m.group(2)}s')", sql)
        return sql.replace("now()", "CURRENT_TIMESTAMP").replace(" FOR UPDATE", "")

    def execute(self, sql, params=()):
        if "set_config(" in sql or "pg_advisory_xact_lock(" in sql:  # el candado de escritura de SQLite ya serializa las transacciones
            self._cur = _Vacio()
            return self
        m = _FUNCION.search(sql)
        if m:
            self._cur = self._con._funcion(m.group(1), tuple(params))
            self._poner_descripcion()
            return self
        try:
            self._cur.execute(self._traducir(sql), tuple(int(p) if isinstance(p, bool) else p for p in params))
        except sqlite3.IntegrityError as e:
            if "UNIQUE" in str(e):
                raise psycopg.errors.UniqueViolation(str(e)) from e
            raise
        self._poner_descripcion()
        return self

    def executemany(self, sql, seq):
        self._cur.executemany(self._traducir(sql), [tuple(int(p) if isinstance(p, bool) else p for p in f) for f in seq])
        return self

    def _poner_descripcion(self):
        self.description = [_Col(d[0]) for d in (self._cur.description or ())]

    def _fila(self, valores):
        return None if valores is None else Fila(valores, [c.name for c in self.description])

    def fetchone(self):
        return self._fila(self._cur.fetchone())

    def fetchall(self):
        return [self._fila(v) for v in self._cur.fetchall()]

    def __iter__(self):
        return (self._fila(v) for v in self._cur)


class _Resultado(_Vacio):
    """Filas ya calculadas por una función `app_*` (con nombres de columna)."""

    def __init__(self, nombres, filas):
        self.description, self._filas = [(n,) for n in nombres], list(filas)

    def fetchone(self):
        return self._filas.pop(0) if self._filas else None

    def fetchall(self):
        f, self._filas = self._filas, []
        return f

    def __iter__(self):
        return iter(self.fetchall())


class Con:
    closed = False

    def __init__(self, ruta):
        self._raw = sqlite3.connect(ruta, detect_types=sqlite3.PARSE_DECLTYPES, isolation_level=None, check_same_thread=False, timeout=60)
        self._raw.execute("PRAGMA journal_mode = WAL")
        self._raw.execute("PRAGMA foreign_keys = ON")
        self._cols = {}

    def cursor(self):
        if not self._raw.in_transaction:  # una transacción por unidad de trabajo; escribir exige el candado desde el inicio (sin carreras de MAX+1)
            self._raw.execute("BEGIN IMMEDIATE")
        return Cur(self)

    def execute(self, sql, params=()):
        return self.cursor().execute(sql, params)

    def commit(self):
        if self._raw.in_transaction:
            self._raw.execute("COMMIT")

    def rollback(self):
        if self._raw.in_transaction:
            self._raw.execute("ROLLBACK")

    def close(self):
        self.rollback()
        self._raw.close()
        self.closed = True

    def _columnas(self, tabla):
        if tabla not in self._cols:
            self._cols[tabla] = [r[1] for r in self._raw.execute(f"PRAGMA table_info({tabla})")]
        return self._cols[tabla]

    def _sql(self, sql, params=()):
        c = self._raw.execute(sql, params)
        return c

    def _funcion(self, nombre, p):
        """Las funciones SECURITY DEFINER de las migraciones 002–008 y el trabajador, en Python."""
        q, ahora = self._sql, _ahora()
        if nombre == "buscar_usuario":
            f = q("SELECT id, clinica_id, nombre, hash_clave, es_admin, activo, debe_cambiar FROM usuario WHERE correo = lower(?)", p).fetchone()
            return _Resultado(["id", "clinica_id", "nombre", "hash_clave", "es_admin", "activo", "debe_cambiar"], [f] if f else [])
        if nombre == "intentos":
            n = q("SELECT count(*) FROM intento_login WHERE correo = lower(?) AND ip = ? AND fecha > datetime('now','-15 minutes')", p).fetchone()[0]
            return _Resultado(["intentos"], [(n,)])
        if nombre == "registrar_intento":
            q("INSERT INTO intento_login (correo, ip) VALUES (lower(?), ?)", p)
        elif nombre == "limpiar_intentos":
            q("DELETE FROM intento_login WHERE correo = lower(?) AND ip = ?", p)
        elif nombre == "crear_sesion":
            q("INSERT INTO sesion (hash_token, usuario_id, creada, ultima) VALUES (?, ?, ?, ?)", (p[0], p[1], ahora, ahora))
        elif nombre == "sesion":
            limite_ultima = (datetime.now(timezone.utc) - timedelta(minutes=MIN_SESION)).strftime("%Y-%m-%d %H:%M:%S.%f")
            limite_creada = (datetime.now(timezone.utc) - timedelta(hours=HORAS_SESION)).strftime("%Y-%m-%d %H:%M:%S.%f")
            q("UPDATE sesion SET ultima = ? WHERE hash_token = ? AND ultima > ? AND creada > ? AND usuario_id IN (SELECT id FROM usuario WHERE activo)",
              (ahora, p[0], limite_ultima, limite_creada))
            f = q("SELECT u.id, u.clinica_id, u.correo, u.nombre, u.es_admin, u.debe_cambiar FROM sesion s JOIN usuario u ON u.id = s.usuario_id "
                  "WHERE s.hash_token = ? AND s.ultima = ?", (p[0], ahora)).fetchone()
            return _Resultado(["id", "clinica_id", "correo", "nombre", "es_admin", "debe_cambiar"],
                              [(f[0], f[1], f[2], f[3], bool(f[4]), bool(f[5]))] if f else [])
        elif nombre == "cerrar_sesion":
            q("DELETE FROM sesion WHERE hash_token = ?", p)
        elif nombre == "cerrar_sesiones":
            q("DELETE FROM sesion WHERE usuario_id = ?", p)
        elif nombre == "hash_clave":
            f = q("SELECT hash_clave FROM usuario WHERE id = ?", p).fetchone()
            return _Resultado(["app_hash_clave"], [f] if f else [])
        elif nombre == "poner_clave":
            usuario, hash_, conservar = p
            if q("UPDATE usuario SET hash_clave = ?, debe_cambiar = 0 WHERE id = ?", (hash_, usuario)).rowcount:
                q("DELETE FROM sesion WHERE usuario_id = ? AND (? IS NULL OR hash_token <> ?)", (usuario, conservar, conservar))
        elif nombre == "purgar":
            q("DELETE FROM sesion WHERE ultima < datetime('now','-35 minutes') OR creada < datetime('now','-12 hours')")
            q("DELETE FROM intento_login WHERE fecha < datetime('now','-1 day')")
        elif nombre == "auditar_ingreso":
            q("INSERT INTO auditoria (usuario_id, correo, metodo, ruta, codigo, ip, evento, clinica_id) "
              "SELECT id, correo, 'POST', '/api/auth/entrar', ?, ?, ?, clinica_id FROM usuario WHERE correo = lower(?)", (p[3], p[1], p[2], p[0]))
        elif nombre == "tomar_trabajo":
            f = q("SELECT id, clinica_id, area_id, periodo_id, tipo, params, revision_base FROM trabajo WHERE estado = 'en_cola' ORDER BY creado, id LIMIT 1").fetchone()
            if not f:
                return _Resultado(["id"], [])
            q("UPDATE trabajo SET estado = 'corriendo', latido = ? WHERE id = ?", (ahora, f[0]))
            return _Resultado(["id", "clinica_id", "area_id", "periodo_id", "tipo", "params", "revision_base"], [f])
        elif nombre == "marcar_fallidos":
            limite = (datetime.now(timezone.utc) - timedelta(seconds=float(p[0]))).strftime("%Y-%m-%d %H:%M:%S.%f")
            n = q("UPDATE trabajo SET estado = 'fallido', error = 'Se interrumpió; vuelve a generar.', terminado = ? WHERE estado = 'corriendo' AND latido < ?",
                  (ahora, limite)).rowcount
            return _Resultado(["n"], [(n,)])
        else:
            raise NotImplementedError(f"app_{nombre}")
        return _Vacio()


class Pool:
    """Hace de ConnectionPool: `connection()` abre una conexión por unidad de trabajo y confirma al salir (revierte si hubo error)."""

    def __init__(self, ruta):
        self.ruta, self._cierre = ruta, threading.Lock()

    @contextlib.contextmanager
    def connection(self, timeout=None):
        con = Con(self.ruta)
        try:
            yield con
            con.commit()
        except BaseException:
            con.rollback()
            raise
        finally:
            con.close()

    def close(self):
        pass


def abrir(ruta):
    return Con(ruta)
