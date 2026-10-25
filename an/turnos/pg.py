"""Adaptador de psycopg 3 con la forma de sqlite3 que usa BD: `?`, filas por índice y por nombre, execute/commit."""
import psycopg


def traducir(sql):
    """`?` → `%s` fuera de literales; `%` → `%%` en todo el texto (psycopg lo interpreta como parámetro)."""
    salida, en_texto = [], False
    for ch in sql:
        if ch == "'":
            en_texto = not en_texto
        salida.append("%%" if ch == "%" else "%s" if ch == "?" and not en_texto else ch)
    return "".join(salida)


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
    def __init__(self, conn):
        self.conn = conn

    @classmethod
    def abrir(cls, url):
        return cls(psycopg.connect(url, row_factory=_fila))

    def execute(self, sql, params=()):
        cur = self.conn.cursor()
        cur.execute(traducir(sql), params)
        return Cursor(cur)

    def executemany(self, sql, seq):
        cur = self.conn.cursor()
        cur.executemany(traducir(sql), list(seq))
        return Cursor(cur)

    def commit(self):
        self.conn.commit()

    def rollback(self):
        self.conn.rollback()

    def close(self):
        self.conn.close()
