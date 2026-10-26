"""Registro de cambios de turno: permutas entre compañeros, cambios por necesidad del servicio y ajustes. Sin GUI.
Cada función escribe las celdas de `cambios` y deja una fila en `cambio_turno` (que solo crece) y una línea en `cambios.log`."""
import json
from datetime import date, datetime
from pathlib import Path


class ErrorCambio(Exception):
    pass


class LimiteExcedido(ErrorCambio):
    def __init__(self, ids):
        super().__init__("Límite de permutas superado")
        self.ids = ids


class EditadoDespues(ErrorCambio):
    """No se puede anular: alguna celda del cambio se editó después. `celdas` = [(colab_id, fecha)]."""
    def __init__(self, celdas):
        super().__init__("Una celda de este cambio se editó después; anula primero los cambios posteriores.")
        self.celdas = celdas


def limite(bd):
    return int(bd.param("limite_permutas", 2))


def cupo(bd, periodo, colab):
    """(permutas usadas en el periodo, límite). Las anuladas no cuentan."""
    n = bd.c.execute("SELECT count(*) FROM cambio_turno WHERE periodo=? AND tipo='permuta' AND anulado_en IS NULL "
                     "AND (colab_a=? OR colab_b=?)", (periodo, colab, colab)).fetchone()[0]
    return n, limite(bd)


def excedidos(bd, periodo, colabs):
    """Los colaboradores que ya gastaron todo su cupo de permutas en el periodo."""
    return [c for c in colabs if cupo(bd, periodo, c)[0] >= limite(bd)]


def _log(bd, linea):
    if bd.ruta in (None, ":memory:"):
        return
    try:
        with open(Path(bd.ruta).with_name("cambios.log"), "a", encoding="utf-8") as f:
            f.write(linea + "\n")
    except OSError:  # el registro en la base ya quedó; el archivo es una copia de respaldo
        pass


def puesto_de(bd, periodo, cid, fecha):
    """Puesto de la celda: el fijado a mano o, si no, donde pasa más tiempo según el reparto (0 = apoyo / sin puesto)."""
    if q := bd.puestos_fijos(periodo).get((cid, fecha)):
        return q
    tiempo = {}
    for a in bd.asignacion_puesto(periodo):
        if (a.colab_id, a.fecha) == (cid, fecha) and a.puesto_id:
            tiempo[a.puesto_id] = tiempo.get(a.puesto_id, 0) + a.hasta - a.desde
    return max(tiempo, key=tiempo.get) if tiempo else 0


def _registrar(bd, periodo, tipo, usuario, nuevas, motivo, colab_a, colab_b=None, excepcion=False):
    """nuevas = [(colab_id, fecha, código nuevo[, puesto])]; puesto None = no tocarlo, 0 = soltarlo, id = fijarlo.
    Escribe las celdas y la fila; devuelve su id."""
    if bd.periodo_cerrado(periodo):
        raise ErrorCambio("El periodo está cerrado.")
    usuario = usuario or "—"
    actual = bd.asignaciones(periodo)
    fijos = bd.puestos_fijos(periodo)
    celdas = []
    for cid, f, cod, *q in nuevas:
        pa = fijos.get((cid, f), 0)
        celdas.append((cid, f, actual.get((cid, f), "L"), cod, pa, pa if not q or q[0] is None else q[0]))
    for cid, f, _, cod, pa, pd in celdas:
        bd.set_celda(periodo, cid, f, cod)
        if pa != pd:
            bd.fijar_puesto(periodo, cid, f, pd)
    ahora = datetime.now().isoformat(timespec="seconds")
    js = json.dumps([[c, f.isoformat(), a, d, pa, pd] for c, f, a, d, pa, pd in celdas])
    id_ = bd._insertar("INSERT INTO cambio_turno (periodo, tipo, registrado_en, usuario, colab_a, colab_b, celdas, motivo, excepcion) "
                       "VALUES (?,?,?,?,?,?,?,?,?)",
                       (periodo, tipo, ahora, usuario, colab_a, colab_b, js, motivo, int(excepcion)))
    bd.c.commit()
    _log(bd, f"{ahora}\t{usuario}\t{tipo}\t{periodo}\t{motivo}\t{js}")
    return id_


def permuta(bd, periodo, a, fa, b, fb, motivo, usuario, excepcion=False):
    if a == b:
        raise ErrorCambio("Una permuta es entre dos personas distintas.")
    if (ex := excedidos(bd, periodo, [a, b])) and not excepcion:
        raise LimiteExcedido(ex)
    actual = bd.asignaciones(periodo)
    x, y = actual.get((a, fa), "L"), actual.get((b, fb), "L")
    pa = pb = None
    if bd.usa_puestos():  # la permuta mueve también el puesto de cada celda, si la otra persona puede ocuparlo
        perm = {p.id: p.puestos_permitidos for p in bd.colaboradores()}
        qa, qb = puesto_de(bd, periodo, a, fa), puesto_de(bd, periodo, b, fb)
        pa = qb if y != "L" and (perm.get(a) is None or qb in perm[a]) else 0
        pb = qa if x != "L" and (perm.get(b) is None or qa in perm[b]) else 0
    return [_registrar(bd, periodo, "permuta", usuario, [(a, fa, y, pa), (b, fb, x, pb)], motivo, a, b, bool(ex))]


def servicio(bd, periodo, celdas, motivo, usuario):
    """Cambio por necesidad del servicio: una fila por persona afectada. No gasta cupo."""
    if not motivo.strip():
        raise ErrorCambio("Un cambio de servicio necesita motivo.")
    porcolab = {}
    for c in celdas:
        porcolab.setdefault(c[0], []).append(c)
    return [_registrar(bd, periodo, "servicio", usuario, cs, motivo, cid) for cid, cs in porcolab.items()]


def ajuste(bd, periodo, celdas, motivo, usuario):
    """Edición sin más: una sola fila para todas las celdas (un lote es una operación)."""
    return [_registrar(bd, periodo, "ajuste", usuario, celdas, motivo, celdas[0][0])]


def restaurar_celdas(bd, periodo, antes):
    """antes = [(colab_id, fecha, código anterior, puesto fijado anterior)]: devuelve esas celdas de `cambios` a ese valor."""
    orig = bd.asignaciones(periodo, "original")
    for cid, f, cod, q in antes:
        bd.fijar_puesto(periodo, cid, f, q)
        if orig.get((cid, f), "L") == cod:
            bd.restaurar(periodo, {cid}, {f})
        else:
            bd.set_celda(periodo, cid, f, cod)


def _celdas(r):
    """[(colab_id, fecha, antes, después, puesto fijo antes, puesto fijo después)]; las filas viejas (4 campos) no tocaban el puesto."""
    return [(c, date.fromisoformat(f), a, n, *(q or (0, 0))) for c, f, a, n, *q in json.loads(r["celdas"])]


def anular(bd, id_, usuario):
    """Deshace un cambio registrado y deja la fila marcada. False si ya estaba anulado."""
    r = bd.c.execute("SELECT * FROM cambio_turno WHERE id=?", (id_,)).fetchone()
    if r["anulado_en"]:
        return False
    if bd.periodo_cerrado(r["periodo"]):
        raise ErrorCambio("El periodo está cerrado.")
    celdas = _celdas(r)
    actual, fijos = bd.asignaciones(r["periodo"]), bd.puestos_fijos(r["periodo"])
    if cambiadas := [(c, f) for c, f, _, n, _, q in celdas if actual.get((c, f), "L") != n or fijos.get((c, f), 0) != q]:  # todo o nada, sin dejar una permuta a medias
        raise EditadoDespues(cambiadas)
    restaurar_celdas(bd, r["periodo"], [(c, f, a, qa) for c, f, a, _, qa, _ in celdas])
    ahora = datetime.now().isoformat(timespec="seconds")
    bd.c.execute("UPDATE cambio_turno SET anulado_en=?, anulado_por=? WHERE id=?", (ahora, usuario or "—", id_))
    bd.c.commit()
    _log(bd, f"{ahora}\t{usuario or '—'}\tanulado\t{r['periodo']}\t#{id_}")
    return True


def listar(bd, periodo):
    """Filas del periodo, las más recientes primero, con `celdas` como [(colab_id, fecha, antes, después, puesto antes, puesto después)]."""
    out = []
    for r in bd.c.execute("SELECT * FROM cambio_turno WHERE periodo=? ORDER BY id DESC", (periodo,)):
        d = dict(r)
        d["celdas"] = _celdas(r)
        out.append(d)
    return out
