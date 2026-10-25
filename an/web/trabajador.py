"""Trabajador del solver: toma trabajos de la tabla `trabajo` (uno por clínica a la vez), corre `solver.generar` con progreso y
cancelación y guarda el cuadro solo si el periodo no cambió. Arranque: python -m an.web.trabajador
Variables: AN_PG_URL y AN_ROL (como la API); opcionales AN_TRABAJADOR_PROGRESO_CADA (1 s), AN_TRABAJADOR_LATIDO_CADA (5 s),
AN_TRABAJADOR_LATIDO_MAX (60 s) y AN_SOLVER_WORKERS (hilos de CP-SAT)."""
import logging
import os
import signal
import threading
import time
from datetime import date

from psycopg.types.json import Jsonb

from an.turnos import flujo, solicitudes, solver
from an.turnos.db import BD

from . import conexion

log = logging.getLogger("an.web.trabajador")
MSG_CONFLICTO = "El periodo cambió mientras se generaba; vuelve a generar."


class _Monitor(threading.Thread):
    """Mientras corre el solver: escribe el progreso (a lo sumo una vez por `progreso_cada`), el latido cada `latido_cada` y lee
    `cancelar`; si está activo, activa `detener`."""

    def __init__(self, trab, t, detener):
        super().__init__(daemon=True)
        self.trab, self.t, self.detener = trab, t, detener
        self.avance, self.escrito = None, None  # último progreso del solver / el último que se escribió
        self.fin = threading.Event()

    def run(self):
        tr = self.trab
        paso, t_prog, t_lat = min(tr.progreso_cada, tr.latido_cada), 0.0, 0.0
        while True:  # la primera vuelta es inmediata: un `cancelar` previo al arranque se atiende sin esperar un paso
            ahora, avance = time.monotonic(), self.avance
            try:
                with conexion.transaccion(tr.pool, self.t["clinica_id"], self.t["area_id"]) as c:
                    cancelar = c.execute("SELECT cancelar FROM trabajo WHERE id = ?", (self.t["id"],)).fetchone()[0]
                    if avance is not self.escrito and ahora - t_prog >= tr.progreso_cada:
                        c.execute("UPDATE trabajo SET progreso = ?, latido = now() WHERE id = ? AND estado = 'corriendo'",
                                  (Jsonb(avance), self.t["id"]))
                        self.escrito, t_prog, t_lat = avance, ahora, ahora
                    elif ahora - t_lat >= tr.latido_cada:
                        c.execute("UPDATE trabajo SET latido = now() WHERE id = ? AND estado = 'corriendo'", (self.t["id"],))
                        t_lat = ahora
            except Exception:
                log.exception("monitor del trabajo %s", self.t["id"])
                cancelar = False
            if cancelar:
                self.detener.set()
            if self.fin.wait(paso):
                return

    def parar(self):
        self.fin.set()
        self.join()


class Trabajador:
    def __init__(self, pool, sondeo=1.0, progreso_cada=1.0, latido_cada=5.0, latido_max=60.0, revisar_cada=60.0):
        self.pool, self.sondeo, self.progreso_cada = pool, sondeo, progreso_cada
        self.latido_cada, self.latido_max, self.revisar_cada = latido_cada, latido_max, revisar_cada

    def marcar_huerfanos(self):
        """Pasa a `fallido` lo `corriendo` cuyo latido pasó de `latido_max` s (el proceso que lo corría murió)."""
        with self.pool.connection() as conn:
            n = conn.execute("SELECT app_marcar_fallidos(%s)", (self.latido_max,)).fetchone()[0]
        if n:
            log.warning("%s trabajo(s) interrumpido(s) marcados como fallidos", n)
        return n

    def correr_uno(self):
        """Toma el trabajo más antiguo y lo ejecuta de punta a punta. False si no había ninguno."""
        with self.pool.connection() as conn:
            t = conn.execute("SELECT * FROM app_tomar_trabajo()").fetchone()
        if t is None:
            return False
        detener = threading.Event()
        monitor = _Monitor(self, t, detener)
        monitor.start()
        generado, error = None, None
        try:
            generado = self._generar(t, detener, monitor)
        except solver.ErrorSolver as e:
            error = str(e)
        except Exception:
            log.exception("trabajo %s", t["id"])
            error = "Error interno al generar el cuadro."
        finally:
            monitor.parar()
        try:
            if detener.is_set() or self._cancelado(t):  # cancelar manda aunque ya hubiera solución: no se escribe nada
                self._cerrar(t, "cancelado")
            elif generado is None:
                self._cerrar(t, "fallido", error=error)
            else:
                self._guardar(t, *generado)
        except Exception:
            log.exception("trabajo %s al cerrar", t["id"])
            self._cerrar(t, "fallido", error="Error interno al guardar el cuadro.")
        return True

    def _generar(self, t, detener, monitor):
        p = t["params"]
        with conexion.transaccion(self.pool, t["clinica_id"], t["area_id"]) as c:
            clave = c.execute("SELECT clave FROM periodo WHERE id = ?", (t["periodo_id"],)).fetchone()[0]
            inicio, fin = flujo.desde_clave(clave)
            lunes = date.fromisoformat(p["lunes"]) if p.get("lunes") else None
            ctx, dias, kw = flujo.preparar(BD.postgres(c), inicio, fin, p.get("modo", "cero"), lunes, p.get("tiempo", 20))
        al_avance = lambda d: setattr(monitor, "avance", {**d, "estado": "buscando"})
        cuadro, info = solver.generar(ctx, dias, **kw, semilla=p.get("semilla", 0), al_avance=al_avance, detener=detener)
        return inicio, fin, ctx, dias, cuadro, info, kw["fijos"]

    def _cancelado(self, t):
        with conexion.transaccion(self.pool, t["clinica_id"], t["area_id"]) as c:
            return c.execute("SELECT cancelar FROM trabajo WHERE id = ?", (t["id"],)).fetchone()[0]

    def _cerrar(self, t, estado, error=None, resultado=None, c=None):
        sql = "UPDATE trabajo SET estado = ?, error = ?, resultado = ?, terminado = now() WHERE id = ? AND estado = 'corriendo'"
        params = (estado, error, Jsonb(resultado) if resultado is not None else None, t["id"])
        if c is not None:
            c.execute(sql, params)
        else:
            with conexion.transaccion(self.pool, t["clinica_id"], t["area_id"]) as c:
                c.execute(sql, params)

    def _guardar(self, t, inicio, fin, ctx, dias, cuadro, info, fijos):
        """Una transacción: si el periodo conserva la revisión base se escribe el cuadro y sube la revisión; si no, `conflicto`."""
        with conexion.transaccion(self.pool, t["clinica_id"], t["area_id"]) as c:
            rev = c.execute("SELECT revision FROM periodo WHERE id = ? FOR UPDATE", (t["periodo_id"],)).fetchone()[0]
            if rev != t["revision_base"]:
                return self._cerrar(t, "conflicto", error=MSG_CONFLICTO, c=c)
            flujo.terminar(BD.postgres(c), inicio, fin, ctx, dias, cuadro, t["params"].get("modo", "cero"))
            c.execute("UPDATE periodo SET revision = revision + 1 WHERE id = ?", (t["periodo_id"],))
            sol = [{"id": r.solicitud.id, "estado": r.estado, "motivo": r.motivo} for r in solicitudes.evaluar(ctx, cuadro, dias, fijos)
                   if r.estado in ("parcial", "no cumplida")]
            self._cerrar(t, "listo", c=c, resultado={
                "estado": info["estado"], "objetivo": info["objetivo"], "solicitudes": sol,
                "faltan": [[f.isoformat(), tramo, n] for f, tramo, n in info["faltan"]]})

    def servir(self, parar):
        """Bucle del proceso: marca huérfanos al arrancar y cada `revisar_cada` s; corre trabajos; duerme `sondeo` s si no hay."""
        self.marcar_huerfanos()
        ultimo = time.monotonic()
        while not parar.is_set():
            if time.monotonic() - ultimo >= self.revisar_cada:
                self.marcar_huerfanos()
                ultimo = time.monotonic()
            try:
                hubo = self.correr_uno()
            except Exception:
                log.exception("no se pudo tomar un trabajo")
                hubo = False
            if not hubo:
                parar.wait(self.sondeo)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    env = lambda k, d: float(os.environ.get(k, d))
    pool = conexion.abrir_pool()
    parar = threading.Event()
    for senal in (signal.SIGTERM, signal.SIGINT):  # termina el trabajo en curso y sale; si lo matan, el latido lo marca fallido
        signal.signal(senal, lambda *_: parar.set())
    log.info("trabajador listo")
    try:
        Trabajador(pool, progreso_cada=env("AN_TRABAJADOR_PROGRESO_CADA", 1), latido_cada=env("AN_TRABAJADOR_LATIDO_CADA", 5),
                   latido_max=env("AN_TRABAJADOR_LATIDO_MAX", 60)).servir(parar)
    finally:
        pool.close()


if __name__ == "__main__":
    main()
