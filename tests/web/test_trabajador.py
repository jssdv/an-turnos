import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""El trabajador del solver: cola, progreso, cancelación, conflicto y caída (necesitan AN_PG_URL). Los tiempos son holgados: la CI es lenta."""
import contextlib
import subprocess
import tempfile
import threading
import time
from datetime import date

from psycopg.types.json import Jsonb

from an.turnos import flujo
from an.turnos.db import BD
from an.turnos.dominio import Colaborador
from an.turnos.pg import Conexion
from an.web import conexion
from an.web.trabajador import Trabajador
from fixtura_api import CLAVE_PERIODO, URL, entorno

RAIZ = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
SEMANA = "2026-10-05/2026-10-11"


@contextlib.contextmanager
def bd_a(e):
    """BD del núcleo como `an_app` con el alcance de la clínica A: solo ve sus filas (un superusuario se salta RLS y vería también la B)."""
    with conexion.transaccion(e.pool, e.cl["A"], e.ar["A"]) as c:
        yield BD.postgres(c)


@contextlib.contextmanager
def alcance_a(e):
    """Sesión de superusuario con el alcance de la clínica A, para sembrar."""
    e.su.execute("SELECT set_config('app.clinica', %s, false), set_config('app.area', %s, false)", (str(e.cl["A"]), str(e.ar["A"])))
    try:
        yield BD.postgres(Conexion(e.su))
    finally:
        e.su.commit()
        e.su.execute("RESET app.clinica")
        e.su.execute("RESET app.area")
        e.su.commit()


def sembrar(e, total):
    """Deja `total` colaboradores en la clínica A (la fixture ya trae uno)."""
    with alcance_a(e) as bd:
        for i in range(total - 1):
            bd.guardar_colaborador(Colaborador(0, f"X{i}"))


def encolar(e, clave=CLAVE_PERIODO, revision=0, **params):
    e.su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s) ON CONFLICT (area_id, clave) DO NOTHING", (clave, e.cl["A"], e.ar["A"]))
    pid = e.su.execute("SELECT id FROM periodo WHERE area_id = %s AND clave = %s", (e.ar["A"], clave)).fetchone()[0]
    params = {"modo": "cero", "lunes": None, "tiempo": 20, "semilla": 0, **params}
    tid = e.su.execute("INSERT INTO trabajo (periodo_id, tipo, params, revision_base, clinica_id, area_id) VALUES (%s, 'generar', %s, %s, %s, %s) RETURNING id",
                       (pid, Jsonb(params), revision, e.cl["A"], e.ar["A"])).fetchone()[0]
    e.su.commit()
    return tid


def fila(e, tid):
    e.su.rollback()
    return e.su.execute("SELECT * FROM trabajo WHERE id = %s", (tid,)).fetchone()


def esperar(e, tid, estados, limite=60):
    t0 = time.time()
    while time.time() - t0 < limite:
        f = fila(e, tid)
        if f["estado"] in estados:
            return f
        time.sleep(0.1)
    raise AssertionError(f"el trabajo {tid} sigue en {f['estado']}")


def celdas(e, clave):
    return e.su.execute("SELECT count(*) FROM asignacion WHERE mes = %s AND area_id = %s", (clave, e.ar["A"])).fetchone()[0]


def en_hilo(trab):
    h = threading.Thread(target=trab.correr_uno)
    h.start()
    return h


@contextlib.contextmanager
def un_hilo_de_cp_sat():
    """Con un solo hilo CP-SAT y semilla fija, un problema que llega al óptimo da siempre el mismo cuadro."""
    previo = os.environ.get("AN_SOLVER_WORKERS")
    os.environ["AN_SOLVER_WORKERS"] = "1"
    try:
        yield
    finally:
        if previo is None:
            del os.environ["AN_SOLVER_WORKERS"]
        else:
            os.environ["AN_SOLVER_WORKERS"] = previo


def test_trabajo_termina_listo_con_el_cuadro_de_flujo_generar():
    with entorno() as e, un_hilo_de_cp_sat():
        if e is None:
            return
        sembrar(e, 5)
        inicio, fin = flujo.desde_clave(SEMANA)
        with bd_a(e) as bd:
            flujo.generar(bd, inicio, fin, tiempo=30)
            esperado = bd.asignaciones(SEMANA)
        assert esperado
        tid = encolar(e, SEMANA, tiempo=30)
        trab = Trabajador(e.pool)
        assert trab.correr_uno() is True
        f = fila(e, tid)
        assert f["estado"] == "listo" and f["terminado"] is not None and f["error"] is None, f["error"]
        assert set(f["resultado"]) == {"estado", "objetivo", "faltan", "solicitudes"}
        assert e.su.execute("SELECT revision FROM periodo WHERE clave = %s AND area_id = %s", (SEMANA, e.ar["A"])).fetchone()[0] == 1
        with bd_a(e) as bd:
            assert bd.asignaciones(SEMANA) == esperado
        assert trab.correr_uno() is False


def test_cancelar_a_los_2s_no_escribe():
    with entorno() as e:
        if e is None:
            return
        sembrar(e, 13)
        tid = encolar(e, tiempo=60)
        h = en_hilo(Trabajador(e.pool))
        time.sleep(2)
        e.su.execute("UPDATE trabajo SET cancelar = true WHERE id = %s", (tid,))
        e.su.commit()
        t0 = time.time()
        f = esperar(e, tid, {"cancelado", "listo", "fallido"}, 20)
        demora = time.time() - t0
        h.join()
        assert f["estado"] == "cancelado" and f["terminado"] is not None, (f["estado"], f["error"])
        assert demora < 3, demora
        assert celdas(e, CLAVE_PERIODO) == 3  # solo las de la fixture
        assert e.su.execute("SELECT revision FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] == 0


def test_cancelar_antes_de_arrancar():
    with entorno() as e:
        if e is None:
            return
        sembrar(e, 13)
        tid = encolar(e, tiempo=60)
        e.su.execute("UPDATE trabajo SET cancelar = true WHERE id = %s", (tid,))
        e.su.commit()
        t0 = time.time()
        assert Trabajador(e.pool).correr_uno()
        assert fila(e, tid)["estado"] == "cancelado" and time.time() - t0 < 5
        assert celdas(e, CLAVE_PERIODO) == 3


def test_conflicto_si_el_periodo_cambia_mientras_corre():
    with entorno() as e:
        if e is None:
            return
        sembrar(e, 13)
        tid = encolar(e, tiempo=4)
        h = en_hilo(Trabajador(e.pool))
        time.sleep(1)
        e.su.execute("UPDATE periodo SET revision = revision + 1 WHERE area_id = %s", (e.ar["A"],))
        e.su.commit()
        f = esperar(e, tid, {"listo", "conflicto", "fallido", "cancelado"})
        h.join()
        assert f["estado"] == "conflicto" and "cambió" in f["error"], (f["estado"], f["error"])
        assert celdas(e, CLAVE_PERIODO) == 3
        assert e.su.execute("SELECT revision FROM periodo WHERE area_id = %s", (e.ar["A"],)).fetchone()[0] == 1


def test_error_del_solver_da_fallido_y_libera_la_clinica():
    with entorno() as e:
        if e is None:
            return
        sembrar(e, 5)
        e.su.execute("INSERT INTO periodo (clave, clinica_id, area_id) VALUES (%s, %s, %s)", (SEMANA, e.cl["A"], e.ar["A"]))
        cid = e.colab["A"]
        for dia, turno in ((5, "NC"), (6, "M")):  # noche y mañana siguiente, fijas: rompen el descanso de 12 h
            e.su.execute("INSERT INTO asignacion VALUES (%s, 'cambios', %s, %s, %s, 'manual', 1, %s, %s)",
                         (SEMANA, cid, date(2026, 10, dia).isoformat(), turno, e.cl["A"], e.ar["A"]))
        e.su.commit()
        tid = encolar(e, SEMANA, modo="respetar", tiempo=10)
        assert Trabajador(e.pool).correr_uno()
        f = fila(e, tid)
        assert f["estado"] == "fallido" and "fijas" in f["error"], (f["estado"], f["error"])
        encolar(e, SEMANA)  # la clínica quedó libre: el índice único no lo rechaza


def test_matar_el_proceso_deja_fallido_al_reiniciar():
    with entorno() as e:
        if e is None:
            return
        sembrar(e, 13)
        tid = encolar(e, tiempo=120)
        esquema = e.su.execute("SELECT current_schema()").fetchone()[0]
        env = {**os.environ, "AN_PG_URL": f"{URL}{'&' if '?' in URL else '?'}options=-csearch_path%3D{esquema}", "AN_ROL": "an_app",
               "AN_TRABAJADOR_LATIDO_CADA": "0.5", "AN_TRABAJADOR_LATIDO_MAX": "60"}
        procesos = []
        try:
            with tempfile.TemporaryFile() as log:
                p = subprocess.Popen([sys.executable, "-m", "an.web.trabajador"], cwd=RAIZ, env=env, stdout=log, stderr=log)
                procesos.append(p)
                esperar(e, tid, {"corriendo"}, 60)
                p.kill()
                p.wait()
                assert fila(e, tid)["estado"] == "corriendo"
                time.sleep(3)  # el latido del proceso muerto queda más viejo que los 2 s del segundo arranque
                p2 = subprocess.Popen([sys.executable, "-m", "an.web.trabajador"], cwd=RAIZ, env={**env, "AN_TRABAJADOR_LATIDO_MAX": "2"},
                                      stdout=log, stderr=log)
                procesos.append(p2)
                f = esperar(e, tid, {"fallido"}, 60)
                assert "interrumpi" in f["error"] and f["terminado"] is not None
        finally:
            for p in procesos:
                if p.poll() is None:
                    p.kill()
                    p.wait()


if __name__ == "__main__":
    print("OK: correr con pytest")
