import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas del registro de cambios de turno (permutas, cambios de servicio, ajustes). Imprime OK."""
import tempfile
from contextlib import contextmanager
from datetime import date
from pathlib import Path

from an.turnos import cambios, db
from an.turnos.cambios import EditadoDespues, ErrorCambio, LimiteExcedido

K = "2026-10-01/2026-10-31"
d1, d2 = date(2026, 10, 5), date(2026, 10, 6)
u = "coord"


@contextmanager
def raises(exc):
    try:
        yield
    except exc as e:
        raises.visto = e
    else:
        raise AssertionError(f"no lanzó {exc.__name__}")


def nuevo(ruta=":memory:"):
    bd = db.BD(ruta)
    bd.guardar_cuadro(K, {(1, d1): "M", (2, d1): "T", (1, d2): "L"})
    return bd


def test_esquema_v6():
    bd = db.BD()
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 7
    cols = [r["name"] for r in bd.c.execute("PRAGMA table_info(cambio_turno)")]
    assert cols == ["id", "periodo", "servicio", "tipo", "registrado_en", "usuario", "colab_a", "colab_b",
                    "celdas", "motivo", "excepcion", "anulado_en", "anulado_por"]


def test_migra_v5_a_v6():
    ruta = tempfile.mkdtemp() + "/t.db"
    bd = db.BD(ruta)
    bd.c.execute("DROP TABLE cambio_turno")
    bd.c.execute("PRAGMA user_version = 5")
    bd.guardar_cuadro("2026-10-01/2026-10-31", {(1, date(2026, 10, 5)): "M"})
    bd.c.commit()
    bd.c.close()
    bd = db.BD(ruta)
    assert bd.c.execute("PRAGMA user_version").fetchone()[0] == 7
    assert bd.asignaciones("2026-10-01/2026-10-31") == {(1, date(2026, 10, 5)): "M"}
    assert bd.c.execute("SELECT count(*) FROM cambio_turno").fetchone()[0] == 0
    assert bd.ruta == ruta


def test_permuta_intercambia_registra_y_gasta_cupo():
    bd = nuevo()
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "pedido", u)
    c = bd.asignaciones(K)
    assert c[(1, d1)] == "T" and c[(2, d1)] == "M"
    assert cambios.cupo(bd, K, 1) == (1, 2) and cambios.cupo(bd, K, 2) == (1, 2)
    fila = cambios.listar(bd, K)[0]
    assert fila["id"] == i and fila["tipo"] == "permuta" and fila["usuario"] == u and fila["motivo"] == "pedido"
    assert fila["servicio"] == "esterilizacion"
    assert fila["celdas"] == [(1, d1, "M", "T"), (2, d1, "T", "M")]


def test_permuta_sobre_limite_exige_excepcion():
    bd = nuevo()
    bd.set_param("limite_permutas", 1)
    cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.excedidos(bd, K, [1, 2, 3]) == [1, 2]
    with raises(LimiteExcedido):
        cambios.permuta(bd, K, 1, d2, 2, d2, "", u)
    assert raises.visto.ids == [1, 2]
    assert len(cambios.listar(bd, K)) == 1  # no escribió
    cambios.permuta(bd, K, 1, d2, 2, d2, "", u, excepcion=True)
    assert [f["excepcion"] for f in cambios.listar(bd, K)] == [1, 0]  # la excepción es la más reciente


def test_limite_cero_y_otro_periodo_no_cuenta():
    bd = nuevo()
    bd.set_param("limite_permutas", 0)
    assert cambios.excedidos(bd, K, [1]) == [1]
    bd.set_param("limite_permutas", 1)
    cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.cupo(bd, "2026-11-01/2026-11-30", 1) == (0, 1)


def test_servicio_y_ajuste_no_gastan_cupo():
    bd = nuevo()
    ids = cambios.servicio(bd, K, [(1, d1, "L"), (2, d1, "L")], "falta personal", u)
    assert len(ids) == 2
    cambios.ajuste(bd, K, [(1, d2, "M"), (2, d2, "M")], "Lote: 2 celdas → M", u)
    assert cambios.cupo(bd, K, 1) == (0, 2) and len(cambios.listar(bd, K)) == 3  # el lote es una sola fila


def test_servicio_sin_motivo_se_rechaza():
    bd = nuevo()
    for m in ("", "   "):
        with raises(ErrorCambio):
            cambios.servicio(bd, K, [(1, d1, "L")], m, u)
    assert bd.asignaciones(K)[(1, d1)] == "M" and cambios.listar(bd, K) == []


def test_permuta_consigo_misma_se_rechaza():
    bd = nuevo()
    with raises(ErrorCambio):
        cambios.permuta(bd, K, 1, d1, 1, d2, "", u)
    with raises(ErrorCambio):
        cambios.permuta(bd, K, 1, d1, 1, d1, "", u)
    assert cambios.listar(bd, K) == []


def test_anular_restaura_conserva_fila_y_es_idempotente():
    bd = nuevo()
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    assert cambios.anular(bd, i, u) is True and bd.asignaciones(K)[(1, d1)] == "M"
    assert cambios.cupo(bd, K, 1) == (0, 2)
    fila = cambios.listar(bd, K)[0]
    assert fila["anulado_por"] == u and fila["anulado_en"]
    assert cambios.anular(bd, i, u) is False


def test_periodo_cerrado_rechaza():
    bd = nuevo()
    bd.cerrar_periodo(K, [])
    with raises(ErrorCambio):
        cambios.ajuste(bd, K, [(1, d1, "L")], "", u)
    assert bd.asignaciones(K)[(1, d1)] == "M"


def test_log_en_archivo_y_tolera_fallo():
    ruta = tempfile.mkdtemp() + "/t.db"
    b = nuevo(ruta)
    cambios.ajuste(b, K, [(1, d1, "L")], "x", u)
    assert "ajuste" in Path(ruta).with_name("cambios.log").read_text(encoding="utf-8")
    b.ruta = "/no/existe/t.db"
    cambios.ajuste(b, K, [(1, d2, "M")], "y", u)  # no lanza
    assert len(cambios.listar(b, K)) == 2


def test_anular_rechaza_si_se_edito_despues():
    bd = nuevo()
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    bd.set_celda(K, 1, d1, "L")  # edición posterior a la permuta
    with raises(EditadoDespues):
        cambios.anular(bd, i, u)
    assert raises.visto.celdas == [(1, d1)]
    c = bd.asignaciones(K)
    assert c[(1, d1)] == "L" and c[(2, d1)] == "M"  # no restauró ni la otra mitad de la permuta
    assert cambios.listar(bd, K)[0]["anulado_en"] is None


def test_anular_en_orden_inverso_funciona():
    bd = nuevo()
    [i] = cambios.permuta(bd, K, 1, d1, 2, d1, "", u)
    [j] = cambios.ajuste(bd, K, [(1, d1, "L")], "", u)
    with raises(EditadoDespues):
        cambios.anular(bd, i, u)
    assert cambios.anular(bd, j, u) is True and cambios.anular(bd, i, u) is True
    c = bd.asignaciones(K)
    assert c[(1, d1)] == "M" and c[(2, d1)] == "T"


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
