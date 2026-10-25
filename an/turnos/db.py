"""Persistencia SQLite: catálogo de turnos, personal, novedades, cuadro (versiones original/cambios), puestos."""
import json
import os
import sqlite3
from datetime import date, datetime, timezone

from .demanda import cobertura_derivada, franjas_de
from .dominio import (COBERTURA_BASE, AsignacionPuesto, Colaborador, Contexto, Demanda, Novedad, Puesto, Solicitud, Turno, festivos,
                     turnos_base)

CAMBIO_TURNO = """
CREATE TABLE IF NOT EXISTS cambio_turno (
  id INTEGER PRIMARY KEY, periodo TEXT, servicio TEXT DEFAULT 'esterilizacion', tipo TEXT, registrado_en TEXT, usuario TEXT,
  colab_a INT, colab_b INT, celdas TEXT, motivo TEXT, excepcion INT DEFAULT 0, anulado_en TEXT, anulado_por TEXT);
"""

SOLICITUD = """
CREATE TABLE IF NOT EXISTS solicitud (
  id INTEGER PRIMARY KEY, servicio TEXT DEFAULT 'esterilizacion', colab_id INT, tipo TEXT, desde TEXT, hasta TEXT,
  turno TEXT, prioridad TEXT, nota TEXT, registrado_en TEXT, usuario TEXT);
"""

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
""" + """
CREATE TABLE periodo_estado (clave TEXT PRIMARY KEY, cerrado_en TEXT);
CREATE TABLE cierre (periodo TEXT, colab_id INT, contratadas REAL, trabajadas REAL, PRIMARY KEY (periodo, colab_id));
CREATE TABLE banco_mov (id INTEGER PRIMARY KEY, colab_id INT, fecha TEXT, horas REAL, concepto TEXT, nota TEXT);
""" + """
CREATE TABLE puesto (id INTEGER PRIMARY KEY, numero INT UNIQUE, nombre TEXT, color TEXT, activo INT);
CREATE TABLE demanda (id INTEGER PRIMARY KEY, puesto_id INT, tipo_dia TEXT, inicio INT, fin INT, personas INT, obligatorio INT);
CREATE TABLE persona_puesto (colab_id INT, puesto_id INT, PRIMARY KEY (colab_id, puesto_id));
""" + """
CREATE TABLE asignacion_puesto (periodo TEXT, fecha TEXT, colab_id INT, puesto_id INT, desde INT, hasta INT, pausa INT);
""" + CAMBIO_TURNO + SOLICITUD

PUESTOS_BASE = [(1, "Lavado", "DDEBF7"), (2, "Autoclave", "E2EFDA"), (3, "Sterrad y esto", "FFF2CC"),
                (4, "Cuarto estéril", "FCE4D6"), (5, "Ropa", "EDEDED"), (6, "Guardia noche", "D9D2E9")]
PRIORIDAD_BASE = [2, 1, 3, 4]  # orden en que la cobertura antigua se reparte entre los puestos de día

TARIFAS_BASE = [  # valores en %; noche_inicio en minutos desde 00:00
    ("dominical", 75, "2000-01-01"), ("dominical", 80, "2025-07-01"), ("dominical", 90, "2026-07-01"),
    ("dominical", 100, "2027-07-01"), ("nocturno", 35, "2000-01-01"), ("extra_diurna", 25, "2000-01-01"),
    ("extra_nocturna", 75, "2000-01-01"), ("noche_inicio", 1260, "2000-01-01"), ("noche_inicio", 1140, "2025-12-25"),
]
PARAMETROS_BASE = {"ventana_semanas": "3", "capacitacion_horas": "2", "periodo_modo": "mes", "periodo_semanas": "4"}


def _dt(s):
    return date.fromisoformat(s)


class BD:
    dialecto = "sqlite"
    _limpiar = None

    def __init__(self, ruta=":memory:"):
        """SQLite (archivo o memoria). Con AN_BD=postgres, `BD()` en memoria crea un esquema temporal en PostgreSQL (pruebas)."""
        self.ruta = ruta
        if ruta == ":memory:" and os.environ.get("AN_BD") == "postgres":
            from an.web.pruebas import esquema_temporal
            self.dialecto = "postgres"
            self.ruta = None
            self.c, self._limpiar = esquema_temporal()
            self.sembrar()
            return
        self.c = sqlite3.connect(ruta)
        self.c.row_factory = sqlite3.Row
        if self.c.execute("PRAGMA user_version").fetchone()[0] == 0:
            self.c.executescript(ESQUEMA)
            self.sembrar()
            self.c.execute("PRAGMA user_version = 7")
            self.c.commit()
        else:
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 1:
                self._migrar_a_2()
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 2:
                self._migrar_a_3()
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 3:
                self._migrar_a_4()
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 4:
                self._migrar_a_5()
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 5:
                self._migrar_a_6()
            if self.c.execute("PRAGMA user_version").fetchone()[0] == 6:
                self._migrar_a_7()

    # --- SQL común a SQLite y PostgreSQL ---------------------------------------------------------
    CLAVES = {"turno": "codigo", "parametro": "clave", "periodo_estado": "clave", "asignacion": "mes, version, colab_id, fecha"}
    COLUMNAS = {"turno": "nombre inicio fin color cubre pausas dom_fest solver activo",
                "parametro": "valor", "periodo_estado": "cerrado_en", "asignacion": "turno origen fijo"}

    def _pk(self, tabla):
        """Columnas de la clave de conflicto de `tabla` (en PostgreSQL llevan además el área)."""
        return ("area_id, " if self.dialecto == "postgres" else "") + self.CLAVES[tabla]

    def _upsert(self, tabla):
        """Cola `ON CONFLICT (clave) DO UPDATE SET …` que reemplaza las columnas no clave."""
        sets = ", ".join(f"{c}=excluded.{c}" for c in self.COLUMNAS[tabla].split())
        return f"ON CONFLICT ({self._pk(tabla)}) DO UPDATE SET {sets}"

    def _insertar(self, sql, params=()):
        """INSERT con `RETURNING id`: devuelve el id nuevo."""
        return self.c.execute(sql + " RETURNING id", params).fetchone()[0]

    @classmethod
    def postgres(cls, conexion):
        """BD sobre una conexión PostgreSQL ya abierta y con alcance (app.clinica/app.area); no siembra nada."""
        bd = cls.__new__(cls)
        bd.dialecto, bd.ruta, bd.c = "postgres", None, conexion
        return bd

    def sembrar(self):
        """Datos base de un servicio nuevo: turnos, puestos con su demanda, tarifas y parámetros."""
        for t in turnos_base():
            self.guardar_turno(t)
        if self.dialecto == "sqlite":
            self.guardar_cobertura(COBERTURA_BASE)
        self._sembrar_puestos(COBERTURA_BASE)
        self.c.executemany("INSERT INTO tarifa VALUES (?,?,?)", TARIFAS_BASE)
        for k, v in PARAMETROS_BASE.items():
            self.set_param(k, v)
        self.c.commit()

    def es_postgres(self):
        return self.dialecto == "postgres"

    def cerrar(self):
        if self._limpiar:
            self._limpiar()
        elif self.dialecto == "sqlite":
            self.c.close()

    def _migrar_a_7(self):
        """v7 agrega las solicitudes personales (deseos blandos para el solver)."""
        self.c.executescript(SOLICITUD)
        self.c.execute("PRAGMA user_version = 7")
        self.c.commit()

    def _migrar_a_6(self):
        """v6 agrega el registro de cambios de turno (permutas, cambios de servicio y ajustes)."""
        self.c.executescript(CAMBIO_TURNO)
        self.c.execute("PRAGMA user_version = 6")
        self.c.commit()

    def _migrar_a_5(self):
        """v5 guarda el reparto de puestos por tramos horarios; las filas antiguas (franja M o T) se convierten."""
        self.c.execute("CREATE TABLE IF NOT EXISTS asignacion_puesto (periodo TEXT, fecha TEXT, colab_id INT, puesto_id INT, "
                       "desde INT, hasta INT, pausa INT)")
        ids = {r["numero"]: r["id"] for r in self.c.execute("SELECT id, numero FROM puesto")}
        horas = {"M": (360, 720), "T": (720, 1080)}
        for r in self.c.execute("SELECT * FROM puesto_dia").fetchall():
            if r["franja"] in horas:
                self.c.execute("INSERT INTO asignacion_puesto VALUES (?,?,?,?,?,?,?)",
                               (r["mes"], r["fecha"], r["colab_id"], ids.get(r["puesto"], 0), *horas[r["franja"]], r["pausa"]))
        self.c.execute("PRAGMA user_version = 5")
        self.c.commit()

    def _migrar_a_4(self):
        """v4 agrega los puestos con reglas de demanda; la cobertura antigua se convierte en demanda."""
        self.c.executescript("CREATE TABLE IF NOT EXISTS puesto (id INTEGER PRIMARY KEY, numero INT UNIQUE, nombre TEXT, color TEXT, activo INT);"
                             "CREATE TABLE IF NOT EXISTS demanda (id INTEGER PRIMARY KEY, puesto_id INT, tipo_dia TEXT, inicio INT, fin INT, "
                             "personas INT, obligatorio INT);"
                             "CREATE TABLE IF NOT EXISTS persona_puesto (colab_id INT, puesto_id INT, PRIMARY KEY (colab_id, puesto_id));")
        if not self.c.execute("SELECT 1 FROM puesto LIMIT 1").fetchone():  # idempotente
            self._sembrar_puestos(self.cobertura())
        ids = {r["numero"]: r["id"] for r in self.c.execute("SELECT id, numero FROM puesto")}
        for r in self.c.execute("SELECT id, puesto_fijo FROM colaborador WHERE puesto_fijo IS NOT NULL").fetchall():
            if r["puesto_fijo"] in ids:
                self.c.execute("INSERT OR IGNORE INTO persona_puesto VALUES (?,?)", (r["id"], ids[r["puesto_fijo"]]))
        self.c.execute("PRAGMA user_version = 4")
        self.c.commit()

    def _sembrar_puestos(self, cobertura):
        """Crea los puestos base y convierte la cobertura {tipo_dia: {franja: n}} en demanda, conservando los totales:
        las primeras personas de cada franja de día se reparten de a una por puesto (orden Autoclave, Lavado, Sterrad,
        Cuarto estéril), el excedente va al primero, y la noche pasa a «Guardia noche». Ropa queda como deseable."""
        ids = {}
        for numero, nombre, color in PUESTOS_BASE:
            ids[numero] = self._insertar("INSERT INTO puesto (numero, nombre, color, activo) VALUES (?,?,?,1)",
                                         (numero, nombre, color))
        filas = []
        for td in ("LS", "DF"):
            cob = cobertura.get(td, {})
            pers = {}
            for fr in ("M", "T"):
                n = cob.get(fr, 0)
                for i, numero in enumerate(PRIORIDAD_BASE[:min(n, len(PRIORIDAD_BASE))]):
                    pers[numero, fr] = 1 + (n - len(PRIORIDAD_BASE) if i == 0 and n > len(PRIORIDAD_BASE) else 0)
            for numero in PRIORIDAD_BASE:
                m, t = pers.get((numero, "M"), 0), pers.get((numero, "T"), 0)
                if m and m == t:
                    filas.append((ids[numero], td, 360, 1080, m, 1))
                else:
                    filas += [(ids[numero], td, a, b, n, 1) for a, b, n in ((360, 720, m), (720, 1080, t)) if n]
            if td == "LS":
                filas.append((ids[5], "LS", 360, 1080, 1, 0))
            if cob.get("N", 0):
                filas.append((ids[6], td, 1080, 360, cob["N"], 1))
        self.c.executemany("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (?,?,?,?,?,?)", filas)

    def _migrar_a_3(self):
        """v3 agrega el cierre de periodos y el banco de horas."""
        self.c.executescript("CREATE TABLE IF NOT EXISTS periodo_estado (clave TEXT PRIMARY KEY, cerrado_en TEXT);"
                             "CREATE TABLE IF NOT EXISTS cierre (periodo TEXT, colab_id INT, contratadas REAL, trabajadas REAL, "
                             "PRIMARY KEY (periodo, colab_id));"
                             "CREATE TABLE IF NOT EXISTS banco_mov (id INTEGER PRIMARY KEY, colab_id INT, fecha TEXT, horas REAL, "
                             "concepto TEXT, nota TEXT);")
        self.c.execute("PRAGMA user_version = 3")
        self.c.commit()

    def _migrar_a_2(self):
        """v1 identificaba el mes como «AAAA-MM»; v2 usa la clave de periodo «inicio/fin»."""
        import calendar
        for tabla in ("asignacion", "puesto_dia", "capacitacion"):
            for (m,) in self.c.execute(f"SELECT DISTINCT mes FROM {tabla} WHERE length(mes)=7").fetchall():  # sql-ok: tabla de una lista constante
                año, mes = int(m[:4]), int(m[5:])
                nueva = f"{m}-01/{m}-{calendar.monthrange(año, mes)[1]:02d}"
                self.c.execute(f"UPDATE {tabla} SET mes=? WHERE mes=?", (nueva, m))  # sql-ok: partes constantes
        self.c.executemany("INSERT OR IGNORE INTO parametro VALUES (?,?)", [(k, v) for k, v in PARAMETROS_BASE.items()])
        self.c.execute("PRAGMA user_version = 2")
        self.c.commit()

    # --- catálogo -------------------------------------------------------------------------------
    def guardar_turno(self, t):
        self.c.execute("INSERT INTO turno VALUES (?,?,?,?,?,?,?,?,?,?) " + self._upsert("turno"),  # sql-ok: partes constantes
                       (t.codigo, t.nombre, t.inicio, t.fin, t.color, json.dumps(t.cubre), json.dumps(t.pausas),
                        t.dom_fest, t.solver, t.activo))
        self.c.commit()

    def turnos(self, solo_activos=True):
        q = "SELECT * FROM turno" + (" WHERE activo=1" if solo_activos else "")  # sql-ok: partes constantes
        out = {}
        for r in self.c.execute(q):
            t = Turno(r["codigo"], r["nombre"], r["inicio"], r["fin"], r["color"], (), tuple(json.loads(r["pausas"])),
                      bool(r["dom_fest"]), bool(r["solver"]), bool(r["activo"]))
            t.cubre = franjas_de(t)  # la franja se calcula del horario; la columna guardada ya no se usa
            out[t.codigo] = t
        return out

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
        self.c.execute("INSERT INTO parametro VALUES (?,?) " + self._upsert("parametro"), (clave, str(valor)))  # sql-ok: partes constantes
        self.c.commit()

    # --- puestos y su demanda --------------------------------------------------------------------
    def catalogo_puestos(self, solo_activos=False):
        q = "SELECT * FROM puesto" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY numero"  # sql-ok: partes constantes
        return {r["id"]: Puesto(r["id"], r["numero"], r["nombre"], r["color"], bool(r["activo"])) for r in self.c.execute(q)}

    def guardar_puesto(self, p):
        if self.c.execute("SELECT 1 FROM puesto WHERE numero=? AND id<>?", (p.numero, p.id or 0)).fetchone():
            raise ValueError(f"Ya existe el puesto número {p.numero}.")
        if p.id:
            self.c.execute("UPDATE puesto SET numero=?, nombre=?, color=?, activo=? WHERE id=?",
                           (p.numero, p.nombre, p.color, p.activo, p.id))
        else:
            p.id = self._insertar("INSERT INTO puesto (numero, nombre, color, activo) VALUES (?,?,?,?)",
                                  (p.numero, p.nombre, p.color, p.activo))
        self.c.commit()
        return p.id

    def borrar_puesto(self, id_):
        """Un puesto con reparto guardado se desactiva para no perder el historial. Devuelve «borrado» o «desactivado»."""
        numero = self.c.execute("SELECT numero FROM puesto WHERE id=?", (id_,)).fetchone()["numero"]
        # quien solo podía ocupar este puesto quedaría con «todos» (sin filas): en ese caso se desactiva en lugar de borrar
        deja_sin_puesto = self.c.execute("SELECT 1 FROM persona_puesto p WHERE p.puesto_id=? AND NOT EXISTS (SELECT 1 FROM persona_puesto q "
                                         "WHERE q.colab_id=p.colab_id AND q.puesto_id<>p.puesto_id) LIMIT 1", (id_,)).fetchone() is not None
        en_uso = (deja_sin_puesto or self.c.execute("SELECT 1 FROM puesto_dia WHERE puesto=? LIMIT 1", (numero,)).fetchone() is not None
                  or self.c.execute("SELECT 1 FROM asignacion_puesto WHERE puesto_id=? LIMIT 1", (id_,)).fetchone() is not None)
        if en_uso:
            self.c.execute("UPDATE puesto SET activo=0 WHERE id=?", (id_,))
        else:
            self.c.execute("DELETE FROM demanda WHERE puesto_id=?", (id_,))
            self.c.execute("DELETE FROM persona_puesto WHERE puesto_id=?", (id_,))
            self.c.execute("DELETE FROM puesto WHERE id=?", (id_,))
        self.c.commit()
        return "desactivado" if en_uso else "borrado"

    def demandas(self, puesto_id=None):
        q = "SELECT * FROM demanda" + (" WHERE puesto_id=?" if puesto_id else "") + " ORDER BY puesto_id, id"  # sql-ok: partes constantes
        return [Demanda(r["puesto_id"], r["tipo_dia"], r["inicio"], r["fin"], r["personas"], bool(r["obligatorio"]), r["id"])
                for r in self.c.execute(q, (puesto_id,) if puesto_id else ())]

    def reemplazar_demandas(self, puesto_id, demandas):
        self.c.execute("DELETE FROM demanda WHERE puesto_id=?", (puesto_id,))
        self.c.executemany("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (?,?,?,?,?,?)",
                           [(puesto_id, d.tipo_dia, d.inicio, d.fin, d.personas, d.obligatorio) for d in demandas])
        self.c.commit()

    # --- personal y novedades -------------------------------------------------------------------
    def guardar_colaborador(self, p):
        if p.puestos_permitidos is not None and not p.puestos_permitidos:
            raise ValueError("Marca al menos un puesto que pueda ocupar.")
        permitidos = None if p.permitidos is None else json.dumps(list(p.permitidos))
        vals = (p.nombre, p.tipo, p.horas_sem, p.pct, permitidos, p.puesto_fijo, json.dumps(p.estudio), p.activo)
        if p.id:
            self.c.execute("UPDATE colaborador SET nombre=?,tipo=?,horas_sem=?,pct=?,permitidos=?,puesto_fijo=?,"
                           "estudio=?,activo=? WHERE id=?", vals + (p.id,))
        else:
            p.id = self._insertar("INSERT INTO colaborador (nombre,tipo,horas_sem,pct,permitidos,puesto_fijo,estudio,"
                                  "activo) VALUES (?,?,?,?,?,?,?,?)", vals)
        self.c.execute("DELETE FROM persona_puesto WHERE colab_id=?", (p.id,))
        self.c.executemany("INSERT INTO persona_puesto VALUES (?,?)", [(p.id, q) for q in p.puestos_permitidos or ()])
        self.c.commit()
        return p.id

    def colaboradores(self, solo_activos=True):
        q = "SELECT * FROM colaborador" + (" WHERE activo=1" if solo_activos else "") + " ORDER BY id"  # sql-ok: partes constantes
        permitidos = {}
        for r in self.c.execute("SELECT * FROM persona_puesto ORDER BY puesto_id"):
            permitidos.setdefault(r["colab_id"], []).append(r["puesto_id"])
        return [Colaborador(r["id"], r["nombre"], r["tipo"], r["horas_sem"], r["pct"],
                            None if r["permitidos"] is None else tuple(json.loads(r["permitidos"])),
                            r["puesto_fijo"], tuple(tuple(e) for e in json.loads(r["estudio"])), bool(r["activo"]),
                            tuple(permitidos[r["id"]]) if r["id"] in permitidos else None)
                for r in self.c.execute(q)]

    def borrar_colaborador(self, id_):
        """Con historial (cuadros o novedades) se desactiva para no perderlo. Devuelve «borrado» o «desactivado»."""
        historia = self.c.execute("SELECT 1 FROM asignacion WHERE colab_id=? UNION SELECT 1 FROM novedad WHERE colab_id=? "
                                  "UNION SELECT 1 FROM solicitud WHERE colab_id=? LIMIT 1", (id_, id_, id_)).fetchone()
        self.c.execute("UPDATE colaborador SET activo=0 WHERE id=?" if historia else "DELETE FROM colaborador WHERE id=?", (id_,))
        self.c.commit()
        return "desactivado" if historia else "borrado"

    def guardar_novedad(self, n):
        vals = (n.colab_id, n.tipo, n.desde.isoformat(), n.hasta.isoformat(), n.nota)
        if n.id:
            self.c.execute("UPDATE novedad SET colab_id=?,tipo=?,desde=?,hasta=?,nota=? WHERE id=?", vals + (n.id,))
        else:
            n.id = self._insertar("INSERT INTO novedad (colab_id,tipo,desde,hasta,nota) VALUES (?,?,?,?,?)", vals)
        self.c.commit()

    def borrar_novedad(self, id_):
        self.c.execute("DELETE FROM novedad WHERE id=?", (id_,))
        self.c.commit()

    def novedades(self):
        return [Novedad(r["colab_id"], r["tipo"], _dt(r["desde"]), _dt(r["hasta"]), r["nota"], r["id"])
                for r in self.c.execute("SELECT * FROM novedad ORDER BY desde")]

    def guardar_solicitud(self, s, usuario=""):
        vals = (s.colab_id, s.tipo, s.desde.isoformat(), s.hasta.isoformat(), s.turno, s.prioridad, s.nota)
        if s.id:
            self.c.execute("UPDATE solicitud SET colab_id=?,tipo=?,desde=?,hasta=?,turno=?,prioridad=?,nota=? WHERE id=?",
                           vals + (s.id,))
        else:
            s.id = self._insertar("INSERT INTO solicitud (colab_id,tipo,desde,hasta,turno,prioridad,nota,registrado_en,usuario) "
                                  "VALUES (?,?,?,?,?,?,?,?,?)",
                                  vals + (datetime.now().isoformat(timespec="seconds"), usuario))
        self.c.commit()

    def borrar_solicitud(self, id_):
        self.c.execute("DELETE FROM solicitud WHERE id=?", (id_,))
        self.c.commit()

    def solicitudes(self):
        return [Solicitud(r["colab_id"], r["tipo"], _dt(r["desde"]), _dt(r["hasta"]), r["turno"] or "", r["prioridad"],
                          r["nota"] or "", r["id"]) for r in self.c.execute("SELECT * FROM solicitud ORDER BY desde, id")]

    def contexto(self, año=None):
        años = {año} if año else {date.today().year}
        fest = {}
        for a in años | {a + 1 for a in años} | {a - 1 for a in años}:
            fest.update(festivos(a))
        puestos = self.catalogo_puestos(solo_activos=True)
        demandas = [d for d in self.demandas() if d.puesto_id in puestos]
        return Contexto(self.turnos(), self.colaboradores(), self.novedades(), cobertura_derivada(demandas), fest,
                        int(self.param("libre_tras_noche", 1)), int(self.param("libres_por_semana", 1)),
                        int(self.param("fines_semana_libres", 1)), int(self.param("max_noches_seguidas", 2)),
                        int(self.param("max_c_seguidos", 2)), int(self.param("max_igual_seguidos", 3)), puestos, demandas,
                        self.solicitudes())

    # --- cuadro: versiones original / cambios ---------------------------------------------------
    def asignaciones(self, mes, version="cambios"):
        return {(r["colab_id"], _dt(r["fecha"])): r["turno"] for r in self.c.execute(
            "SELECT * FROM asignacion WHERE mes=? AND version=?", (mes, version))}

    def periodos(self):
        """Claves de los periodos con cuadro guardado, de más antiguo a más reciente."""
        return [r[0] for r in self.c.execute("SELECT DISTINCT mes FROM asignacion ORDER BY mes")]

    def asignaciones_rango(self, desde, hasta):
        """Cuadro vigente (`cambios`) de cualquier periodo entre dos fechas; sirve para el descanso entre periodos."""
        return {(r["colab_id"], _dt(r["fecha"])): r["turno"] for r in self.c.execute(
            "SELECT * FROM asignacion WHERE version='cambios' AND fecha BETWEEN ? AND ?",
            (desde.isoformat(), hasta.isoformat()))}

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
            self.c.executemany("INSERT INTO asignacion VALUES (?,?,?,?,?,?,0) ON CONFLICT (" + self._pk("asignacion") + ") DO NOTHING",  # sql-ok: partes constantes
                               [(mes, v, cid, f.isoformat(), t, origen) for (cid, f), t in cuadro.items()
                                if (cid, f.isoformat()) not in fijos])
        self.c.commit()

    def set_celda(self, mes, cid, fecha, codigo, fijo=True):
        """Edición manual: solo toca la versión `cambios`."""
        self.c.execute("INSERT INTO asignacion VALUES (?,?,?,?,?,?,?) " + self._upsert("asignacion"),  # sql-ok: partes constantes
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

    # --- cierre de periodos y banco de horas ---------------------------------------------------
    def periodo_cerrado(self, k):
        return self.c.execute("SELECT 1 FROM periodo_estado WHERE clave=?", (k,)).fetchone() is not None

    def cerrar_periodo(self, k, filas):
        """Congela las horas del periodo. filas: [(colab_id, contratadas, trabajadas)]."""
        self.c.execute("INSERT INTO periodo_estado VALUES (?,?) " + self._upsert("periodo_estado"),  # sql-ok: partes constantes
                       (k, datetime.now(timezone.utc).isoformat(timespec="seconds")))
        self.c.execute("DELETE FROM cierre WHERE periodo=?", (k,))
        self.c.executemany("INSERT INTO cierre VALUES (?,?,?,?)", [(k, c, a, b) for c, a, b in filas])
        self.c.commit()

    def reabrir_periodo(self, k):
        self.c.execute("DELETE FROM periodo_estado WHERE clave=?", (k,))
        self.c.execute("DELETE FROM cierre WHERE periodo=?", (k,))
        self.c.commit()

    def cierres(self, colab_id=None):
        """[(periodo, colab_id, contratadas, trabajadas)] de los periodos cerrados, del más antiguo al más reciente."""
        q = "SELECT * FROM cierre" + (" WHERE colab_id=?" if colab_id else "") + " ORDER BY periodo"  # sql-ok: partes constantes
        return [(r["periodo"], r["colab_id"], r["contratadas"], r["trabajadas"])
                for r in self.c.execute(q, (colab_id,) if colab_id else ())]

    def agregar_movimiento(self, colab_id, fecha, horas, concepto, nota=""):
        i = self._insertar("INSERT INTO banco_mov (colab_id,fecha,horas,concepto,nota) VALUES (?,?,?,?,?)",
                           (colab_id, fecha.isoformat(), horas, concepto, nota))
        self.c.commit()
        return i

    def borrar_movimiento(self, id_):
        self.c.execute("DELETE FROM banco_mov WHERE id=?", (id_,))
        self.c.commit()

    def movimientos(self, colab_id=None):
        """[(id, colab_id, fecha, horas, concepto, nota)]; horas positivas = se le deben, negativas = se le descontaron."""
        q = "SELECT * FROM banco_mov" + (" WHERE colab_id=?" if colab_id else "") + " ORDER BY fecha, id"  # sql-ok: partes constantes
        return [(r["id"], r["colab_id"], _dt(r["fecha"]), r["horas"], r["concepto"], r["nota"])
                for r in self.c.execute(q, (colab_id,) if colab_id else ())]

    # --- puestos y capacitación -----------------------------------------------------------------
    def guardar_asignacion_puesto(self, periodo, filas):
        """Reemplaza el reparto de puestos por tramos del periodo."""
        self.c.execute("DELETE FROM asignacion_puesto WHERE periodo=?", (periodo,))
        self.c.executemany("INSERT INTO asignacion_puesto VALUES (?,?,?,?,?,?,?)",
                           [(periodo, f.fecha.isoformat(), f.colab_id, f.puesto_id, f.desde, f.hasta, f.pausa) for f in filas])
        self.c.commit()

    def asignacion_puesto(self, periodo):
        return [AsignacionPuesto(_dt(r["fecha"]), r["colab_id"], r["puesto_id"], r["desde"], r["hasta"], r["pausa"])
                for r in self.c.execute("SELECT * FROM asignacion_puesto WHERE periodo=? ORDER BY fecha, colab_id, desde", (periodo,))]

    def guardar_capacitacion(self, mes, filas):
        self.c.execute("DELETE FROM capacitacion WHERE mes=?", (mes,))
        self.c.executemany("INSERT INTO capacitacion VALUES (?,?,?)", [(mes, f.isoformat(), c) for f, c in filas])
        self.c.commit()

    def capacitacion(self, mes):
        return [(_dt(r["fecha"]), r["colab_id"]) for r in self.c.execute(
            "SELECT * FROM capacitacion WHERE mes=?", (mes,))]
