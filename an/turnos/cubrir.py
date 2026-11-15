"""¿Quién cubre?: para un turno sin cubrir, las personas libres ese día que pueden hacerlo sin romper reglas, de menos a más carga."""
import copy
from datetime import timedelta

from . import reglas


def candidatos(ctx, cuadro, fechas, fecha, codigo, fijos=(), previo=None, limite=5):
    """[{colab_id, nombre, avisos, turnos_iguales, minutos, semana_min, semana_tope}] de quienes pueden hacer `codigo` el día `fecha`.
    Se descarta a quien quedaría con un error nuevo de `reglas.validar`; los avisos nuevos se muestran y pesan en el orden.
    `semana_min` son sus minutos de esa semana (lunes a domingo, dentro del periodo) ya con el turno; `semana_tope`, lo contratado.
    Orden: menos avisos, sin pasar lo contratado de la semana (el costo de horas extra antes que quién responde primero),
    menos minutos en el periodo, menos veces ese turno, nombre."""
    turno = ctx.turnos.get(codigo)
    if turno is None:
        raise ValueError(f"«{codigo}» no es un turno")
    lunes = fecha - timedelta(fecha.weekday())
    semana = [f for f in fechas if lunes <= f < lunes + timedelta(7)]
    out = []
    for p in ctx.colabs:
        if not p.en_solver or cuadro.get((p.id, fecha), "L") != "L" or ctx.bloqueo(p, turno, fecha):
            continue
        # ponytail: valida el periodo entero de cada candidato (O(personas × días)); con >60 personas, validar ±3 días.
        solo = copy.copy(ctx)
        solo.colabs = [p]
        suyo = {k: v for k, v in cuadro.items() if k[0] == p.id}
        mias = lambda c: {(a.nivel, a.texto) for a in reglas.validar(solo, c, fechas, fijos, previo) if a.colab_id == p.id}
        nuevas = mias({**suyo, (p.id, fecha): codigo}) - mias(suyo)
        if any(nivel == "error" for nivel, _ in nuevas):
            continue
        dias = [cuadro.get((p.id, f), "L") for f in fechas]
        sem = turno.duracion + sum(ctx.turnos[c].duracion for f in semana if (c := cuadro.get((p.id, f), "L")) in ctx.turnos)
        out.append({"colab_id": p.id, "nombre": p.nombre, "avisos": sorted(t for _, t in nuevas),
                    "turnos_iguales": dias.count(codigo), "minutos": sum(ctx.turnos[c].duracion for c in dias if c in ctx.turnos),
                    "semana_min": sem, "semana_tope": round(p.horas_sem * p.pct * 60)})
    out.sort(key=lambda c: (len(c["avisos"]), c["semana_min"] > c["semana_tope"], c["minutos"], c["turnos_iguales"], c["nombre"]))
    return out[:limite]
