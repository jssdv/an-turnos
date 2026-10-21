"""Persistencia SQLite: catálogo de turnos, personal, novedades, cuadro (versiones original/cambios), puestos."""
import json
import sqlite3
from datetime import date

from dominio import COBERTURA_BASE, Colaborador, Contexto, Novedad, Turno, festivos, turnos_base

ESQUEMA = """
CREATE TABLE turno (codigo TEXT PRIMARY KEY, nombre TEXT, inicio INT, fin INT, color TEXT, cubre TEXT,
                    pausas TEXT, dom_fest INT, solver INT, activo INT);
CREATE TABLE cobertura (tipo_dia TEXT, franja TEXT, cantidad INT, PRIMARY KEY (tipo_dia, franja));
CREATE TABLE colaborador (id INTEGER PRIMARY KEY, nombre TEXT, tipo TEXT, horas_sem REAL, pct REAL,
                          permitidos TEXT, puesto_fijo INT, estudio TEXT, activo INT);
CREATE TABLE novedad (id INTEGER PRIMARY KEY, colab_id INT, tipo TEXT, desde TEXT, hasta TEXT, nota TEXT);
CREATE TABLE asignacion (mes TEXT, version TEXT, colab_id INT, fecha TEXT, turno TEXT, origen TEXT, fijo INT,
                         PRIMARY KEY (mes, version, colab_id, fecha));
CREATE TABLE puesto_dia (mes TEXT, fecha TEXT, franja TEXT, puesto INT, colab_id INT, pausa INT);
CREATE TABLE capacitacion (mes TEXT, fecha TEXT, colab_id INT);
CREATE TABLE tarifa (concepto TEXT, valor REAL, desde TEXT);
CREATE TABLE parametro (clave TEXT PRIMARY KEY, valor TEXT);
"""

TARIFAS_BASE = [  # valores en %; noche_inicio en minutos desde 00:00
    ("dominical", 75, "2000-01-01"), ("dominical", 80, "2025-07-01"), ("dominical", 90, "2026-07-01"),
    ("dominical", 100, "2027-07-01"), ("nocturno", 35, "2000-01-01"), ("extra_diurna", 25, "2000-01-01"),
    ("extra_nocturna", 75, "2000-01-01"), ("noche_inicio", 1260, "2000-01-01"), ("noche_inicio", 1140, "2025-12-25"),
]
PARAMETROS_BASE = {"ventana_semanas": "3", "capacitacion_horas": "2"}


def _dt(s):
    return date.fromisoformat(s)


class BD:
    def __init__(self, ruta=":memory:"):
        self.c = sqlite3.connect(ruta)
        self.c.row_factory = sqlite3.Row
        if self.c.execute("PRAGMA user_version").fetchone()[0] == 0:
            self.c.executescript(ESQUEMA)
            for t in turnos_base():
                self.guardar_turno(t)
            self.guardar_cobertura(COBERTURA_BASE)
            self.c.executemany("INSERT INTO tarifa VALUES (?,?,?)", TARIFAS_BASE)
            for k, v in PARAMETROS_BASE.items():
                self.set_param(k, v)
            self.c.execute("PRAGMA user_version = 1")
            self.c.commit()

    # --- catálogo -------------------------------------------------------------------------------
    def guardar_turno(self, t):
        self.c.execute("INSERT OR REPLACE INTO turno VALUES (?,?,?,?,?,?,?,?,?,?)",
                       (t.codigo, t.nombre, t.inicio, t.fin, t.color, json.dumps(t.cubre), json.dumps(t.pausas),
                        t.dom_fest, t.solver, t.activo))
        self.c.commit()

    def turnos(self, solo_activos=True):
        q = "SELECT * FROM turno" + (" WHERE activo=1" if solo_activos else "")
        return {r["codigo"]: Turno(r["codigo"], r["nombre"], r["inicio"], r["fin"], r["color"],
                                   tuple(json.loads(r["cubre"])), tuple(json.loads(r["pausas"])),
                                   bool(r["dom_fest"]), bool(r["solver"]), bool(r["activo"]))
                for r in self.c.execute(q)}

    def turno_en_uso(self, codigo):
        return self.c.execute("SELECT 1 FROM asignacion WHERE turno=? LIMIT 1", (codigo,)).fetchone() is not None

    def borrar_turno(self, codigo):
        """Un turno en uso no se borra: se desactiva. Devuelve «borrado» o «desactivado»."""
        en_uso = self.turno_en_uso(codigo)
        self.c.execute("UPDATE turno SET activo=0 WHERE codigo=?" if en_uso else "DELETE FROM turno WHERE codigo=?", (codigo,))
        self.c.commit()
        return "desactivado" if en_uso else "borrado"

    def guardar_cobertura(self, cob):
        self.c.execute("DELETE FROM cobertura")
        self.c.executemany("INSERT INTO cobertura VALUES (?,?,?)",
                           [(td, fr, n) for td, d in cob.items() for fr, n in d.items()])
        self.c.commit()

    def cobertura(self):
        cob = {}
        for r in self.c.execute("SELECT * FROM cobertura"):
            cob.setdefault(r["tipo_dia"], {})[r["franja"]] = r["cantidad"]
        return cob

    def tarifas(self):
        return [(r["concepto"], r["valor"], _dt(r["desde"])) for r in self.c.execute("SELECT * FROM tarifa")]

    def param(self, clave, defecto=None):
        r = self.c.execute("SELECT valor FROM parametro WHERE clave=?", (clave,)).fetchone()
        return r["valor"] if r else defecto

    def set_param(self, clave, valor):
        self.c.execute("INSERT OR REPLACE INTO parametro VALUES (?,?)", (clave, str(valor)))
        self.c.commit()

    # --- personal y novedades -------------------------------------------------------------------
    def guardar_colaborador(self, p):
        permitidos = None if p.permitidos is None else json.dumps(list(p.permitidos))
        vals = (p.nombre, p.tipo, p.horas_sem, p.pct, permitidos, p.puesto_fijo, json.dumps(p.estudio), p.activo)
        if p.id:
            self.c.execute("UPDATE colaborador SET nombre=?,tipo=?,horas_sem=?,pct=?,permitidos=?,puesto_fijo=?,"
                           "estudio=?,activo=? WHERE id=?", vals + (p.id,))
        else:
            p.id = self.c.execute("INSERT INTO colaborador (nombre,tipo,horas_sem,pct,permitidos,puesto_fijo,estudio,"
                                  "activo) VALUES (?,?,?,?,?,?,?,?)", vals).lastrowid
        self.c.commit()
        return p.id

    def colaboradores(self, solo_activos=True):
        q = "SELECT * FROM colaborador" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY id"
        return [Colaborador(r["id"], r["nombre"], r["tipo"], r["horas_sem"], r["pct"],
                            None if r["permitidos"] is None else tuple(json.loads(r["permitidos"])),
                            r["puesto_fijo"], tuple(tuple(e) for e in json.loads(r["estudio"])), bool(r["activo"]))
                for r in self.c.execute(q)]

    def borrar_colaborador(self, id_):
        """Con historial (cuadros o novedades) se desactiva para no perderlo. Devuelve «borrado» o «desactivado»."""
        historia = self.c.execute("SELECT 1 FROM asignacion WHERE colab_id=? UNION SELECT 1 FROM novedad WHERE colab_id=? LIMIT 1",
                                  (id_, id_)).fetchone()
        self.c.execute("UPDATE colaborador SET activo=0 WHERE id=?" if historia else "DELETE FROM colaborador WHERE id=?", (id_,))
        self.c.commit()
        return "desactivado" if historia else "borrado"

    def guardar_novedad(self, n):
        vals = (n.colab_id, n.tipo, n.desde.isoformat(), n.hasta.isoformat(), n.nota)
        if n.id:
            self.c.execute("UPDATE novedad SET colab_id=?,tipo=?,desde=?,hasta=?,nota=? WHERE id=?", vals + (n.id,))
        else:
            n.id = self.c.execute("INSERT INTO novedad (colab_id,tipo,desde,hasta,nota) VALUES (?,?,?,?,?)",
                                  vals).lastrowid
        self.c.commit()

    def borrar_novedad(self, id_):
        self.c.execute("DELETE FROM novedad WHERE id=?", (id_,))
        self.c.commit()

    def novedades(self):
        return [Novedad(r["colab_id"], r["tipo"], _dt(r["desde"]), _dt(r["hasta"]), r["nota"], r["id"])
                for r in self.c.execute("SELECT * FROM novedad ORDER BY desde")]

    def contexto(self, año=None):
        años = {año} if año else {date.today().year}
        fest = {}
        for a in años | {a + 1 for a in años} | {a - 1 for a in años}:
            fest.update(festivos(a))
        return Contexto(self.turnos(), self.colaboradores(), self.novedades(), self.cobertura(), fest,
                        int(self.param("libre_tras_noche", 1)), int(self.param("libres_por_semana", 1)),
                        int(self.param("fines_semana_libres", 1)), int(self.param("max_noches_seguidas", 2)),
                        int(self.param("max_c_seguidos", 2)), int(self.param("max_igual_seguidos", 3)))

    # --- cuadro: versiones original / cambios ---------------------------------------------------
    def asignaciones(self, mes, version="cambios"):
        return {(r["colab_id"], _dt(r["fecha"])): r["turno"] for r in self.c.execute(
            "SELECT * FROM asignacion WHERE mes=? AND version=?", (mes, version))}

    def meses(self):
        return [r[0] for r in self.c.execute("SELECT DISTINCT mes FROM asignacion ORDER BY mes")]

    def agregar_tarifa(self, concepto, valor, desde):
        self.c.execute("INSERT INTO tarifa VALUES (?,?,?)", (concepto, valor, desde.isoformat()))
        self.c.commit()

    def fijos(self, mes):
        return {(r["colab_id"], _dt(r["fecha"])): r["turno"] for r in self.c.execute(
            "SELECT * FROM asignacion WHERE mes=? AND version='cambios' AND fijo=1", (mes,))}

    def guardar_cuadro(self, mes, cuadro, origen="solver", versiones=("original", "cambios"), reiniciar=False):
        """Reemplaza las celdas no fijas de cada versión con `cuadro` {(colab_id, fecha): código}.
        `reiniciar` borra todo el mes (también las ediciones manuales)."""
        if reiniciar:
            self.c.execute("DELETE FROM asignacion WHERE mes=?", (mes,))
        for v in versiones:
            fijos = {(r["colab_id"], r["fecha"]) for r in self.c.execute(
                "SELECT * FROM asignacion WHERE mes=? AND version=? AND fijo=1", (mes, v))}
            self.c.execute("DELETE FROM asignacion WHERE mes=? AND version=? AND fijo=0", (mes, v))
            self.c.executemany("INSERT OR IGNORE INTO asignacion VALUES (?,?,?,?,?,?,0)",
                               [(mes, v, cid, f.isoformat(), t, origen) for (cid, f), t in cuadro.items()
                                if (cid, f.isoformat()) not in fijos])
        self.c.commit()

    def set_celda(self, mes, cid, fecha, codigo, fijo=True):
        """Edición manual: solo toca la versión `cambios`."""
        self.c.execute("INSERT OR REPLACE INTO asignacion VALUES (?,?,?,?,?,?,?)",
                       (mes, "cambios", cid, fecha.isoformat(), codigo, "manual", int(fijo)))
        self.c.commit()

    def restaurar(self, mes, cids=None, fechas=None):
        """Devuelve celdas de `cambios` a lo que dice `original` (todas si no se filtra). Una celda libre en el
        original deja de tener fila en `cambios`."""
        orig, cam = self.asignaciones(mes, "original"), self.asignaciones(mes, "cambios")
        for (cid, f) in set(orig) | set(cam):
            if (cids is None or cid in cids) and (fechas is None or f in fechas):
                self.c.execute("DELETE FROM asignacion WHERE mes=? AND version='cambios' AND colab_id=? AND fecha=?",
                               (mes, cid, f.isoformat()))
                if (cid, f) in orig:
                    self.c.execute("INSERT INTO asignacion VALUES (?,?,?,?,?,?,0)",
                                   (mes, "cambios", cid, f.isoformat(), orig[cid, f], "restaurado"))
        self.c.commit()

    def publicar(self, mes):
        """Congela `cambios` como nueva `original`."""
        self.c.execute("DELETE FROM asignacion WHERE mes=? AND version='original'", (mes,))
        self.c.execute("INSERT INTO asignacion SELECT mes,'original',colab_id,fecha,turno,origen,0 FROM asignacion "
                       "WHERE mes=? AND version='cambios'", (mes,))
        self.c.commit()

    def diferencias(self, mes):
        """[(colab_id, fecha, antes, después)] entre original y cambios."""
        o, c = self.asignaciones(mes, "original"), self.asignaciones(mes, "cambios")
        return sorted(((cid, f, o.get((cid, f), "L"), c.get((cid, f), "L"))
                       for cid, f in set(o) | set(c) if o.get((cid, f), "L") != c.get((cid, f), "L")),
                      key=lambda x: (x[1], x[0]))

    # --- puestos y capacitación -----------------------------------------------------------------
    def guardar_puestos(self, mes, filas):
        """filas: [(fecha, franja, puesto, colab_id, pausa)]"""
        self.c.execute("DELETE FROM puesto_dia WHERE mes=?", (mes,))
        self.c.executemany("INSERT INTO puesto_dia VALUES (?,?,?,?,?,?)",
                           [(mes, f.isoformat(), fr, p, cid, pa) for f, fr, p, cid, pa in filas])
        self.c.commit()

    def puestos(self, mes):
        return [(_dt(r["fecha"]), r["franja"], r["puesto"], r["colab_id"], r["pausa"])
                for r in self.c.execute("SELECT * FROM puesto_dia WHERE mes=?", (mes,))]

    def guardar_capacitacion(self, mes, filas):
        self.c.execute("DELETE FROM capacitacion WHERE mes=?", (mes,))
        self.c.executemany("INSERT INTO capacitacion VALUES (?,?,?)", [(mes, f.isoformat(), c) for f, c in filas])
        self.c.commit()

    def capacitacion(self, mes):
        return [(_dt(r["fecha"]), r["colab_id"]) for r in self.c.execute(
            "SELECT * FROM capacitacion WHERE mes=?", (mes,))]
