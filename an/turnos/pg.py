"""Adaptador de psycopg 3 con la forma de sqlite3 que usa BD: `?`, filas por índice y por nombre, execute/commit."""
import re

import psycopg


_TOKEN = re.compile(r"""
    --[^\n]*                                  # comentario de línea
  | /\*(?:[^/*]|/(?!\*)|\*(?!/))*\*/          # comentario de bloque (sin anidar)
  | (?<![\w$])[eE]'(?:[^'\\]|\\.|'')*'          # cadena E'…' con \ de escape
  | '(?:[^']|'')*'                             # cadena normal
  | "(?:[^"]|"")*"                             # identificador entre comillas dobles
  | (?<![\w$])\$([A-Za-z_]\w*|)\$.*?\$\1\$     # cuerpo $$…$$ o $tag$…$tag$
  | (?P<param>\?)
  | (?P<pct>%)
""", re.VERBOSE | re.DOTALL)


def traducir(sql):
    """`?` → `%s` fuera de literales, comentarios, identificadores y cuerpos `$$`; `%` → `%%` en todo el texto (psycopg lo interpreta)."""
    def cambio(m):
        if m.lastgroup == "param":
            return "%s"
        return m.group(0).replace("%", "%%")
    return _TOKEN.sub(cambio, sql)


def _int_si_bool(params):
    """SQLite guarda los bool como 0/1; las columnas INT de PostgreSQL no los aceptan."""
    return tuple(int(p) if isinstance(p, bool) else p for p in params)


class Fila(tuple):
    def __new__(cls, valores, nombres):
        f = super().__new__(cls, valores)
        f._nombres = list(nombres)
        return f

    def __getitem__(self, i):
        return super().__getitem__(self._nombres.index(i) if isinstance(i, str) else i)

    def keys(self):
        return list(self._nombres)


def _fila(cursor):
    nombres = [c.name for c in cursor.description or ()]
    return lambda valores: Fila(valores, nombres)


FILAS = _fila  # row_factory de psycopg para pools y conexiones


class Cursor:
    def __init__(self, cur):
        self._cur = cur

    rowcount = property(lambda self: self._cur.rowcount)

    def fetchone(self):
        return self._cur.fetchone()

    def fetchall(self):
        return self._cur.fetchall()

    def __iter__(self):
        return iter(self._cur)


class Conexion:
    def __init__(self, conn, confirmar=True):
        self.conn, self.confirmar = conn, confirmar  # confirmar=False: commit lo hace quien abrió la transacción (la API)

    @classmethod
    def abrir(cls, url):
        return cls(psycopg.connect(url, row_factory=_fila))

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(traducir(sql), _int_si_bool(params))
        return Cursor(cur)

    def executemany(self, sql, seq):
        cur = self.conn.cursor()
        cur.executemany(traducir(sql), [_int_si_bool(p) for p in seq])
        return Cursor(cur)

    def commit(self):
        if self.confirmar:
            self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
