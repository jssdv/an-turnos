"""Mide el solver sobre un mes completo (13 personas, octubre 2026): segundos hasta la primera solución, hasta la última mejora y objetivo final.
Uso: python checks/medir_solver.py [workers ...] [--tiempo 60]. No corre en la CI (sirve para fijar AN_SOLVER_WORKERS en el servidor)."""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from an.turnos import db, flujo, solver  # noqa: E402
from an.turnos.dominio import Colaborador  # noqa: E402


def medir(workers, tiempo):
    bd = db.BD()
    for i in range(13):
        bd.guardar_colaborador(Colaborador(0, f"P{i}"))
    ctx, dias, kw = flujo.preparar(bd, *flujo.periodo_mes(2026, 10), tiempo=tiempo)
    marcas = []
    t0 = time.monotonic()
    _, info = solver.generar(ctx, dias, **kw, workers=workers, al_avance=lambda d: marcas.append((time.monotonic() - t0, d["objetivo"])))
    total = time.monotonic() - t0
    print(f"workers={workers}: primera solución {marcas[0][0]:.1f} s (objetivo {marcas[0][1]:.0f}); última mejora {marcas[-1][0]:.1f} s; "
          f"final {info['objetivo']:.0f} {info['estado']}, faltan {len(info['faltan'])}; total {total:.1f} s; soluciones {len(marcas)}", flush=True)


if __name__ == "__main__":
    args = sys.argv[1:]
    tiempo = int(args[args.index("--tiempo") + 1]) if "--tiempo" in args else 60
    for w in [int(a) for a in args if a.isdigit() and args[args.index(a) - 1] != "--tiempo"] or [8]:
        medir(w, tiempo)
