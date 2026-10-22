"""Pruebas del núcleo de puestos, demanda por tramos y dotación. Imprime OK."""
from datetime import date

import demanda
from dominio import Contexto, Demanda, Puesto, Turno


def ctx_con(demandas):
    return Contexto({}, [], [], {}, {}, demandas=demandas)


def test_tramos_ventana():
    assert demanda.tramos_ventana(360, 720) == [(0, t) for t in range(12, 24)]
    noche = demanda.tramos_ventana(1080, 360)
    assert len(noche) == 24 and noche[0] == (0, 36) and noche[-1] == (1, 11)


def test_franjas_de():
    assert demanda.franjas_de(Turno("M7", "", 420, 780)) == ("M",)
    assert demanda.franjas_de(Turno("C", "", 360, 1080)) == ("M", "T")
    assert demanda.franjas_de(Turno("NC", "", 1080, 360)) == ("N",)
    assert demanda.franjas_de(Turno("MAD", "", 0, 360)) == ("N",)  # empieza a las 00:00


def test_demanda_cruza_medianoche_y_tipo_de_dia():
    """Review Focus 1: la madrugada del domingo viene del sábado de noche (tipo LS)."""
    guardia = [Demanda(1, "LS", 1080, 360, 2), Demanda(1, "DF", 1080, 360, 1)]
    ctx = ctx_con(guardia)
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 17))  # sábado
    assert len(obl) == 48 and obl[40] == 2 and obl[2] == 2  # la madrugada del sábado viene del viernes (LS)
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 18))  # domingo
    assert obl[2] == 2 and obl[40] == 1  # madrugada del domingo: del sábado (LS); noche del domingo: DF
    obl, _ = demanda.demanda_fecha(ctx, date(2026, 10, 19))  # lunes
    assert obl[2] == 1  # madrugada del lunes: del domingo (DF)


def test_deseables_van_aparte():
    ctx = ctx_con([Demanda(1, "LS", 480, 720, 1, obligatorio=False)])
    obl, des = demanda.demanda_fecha(ctx, date(2026, 10, 14))
    assert sum(obl) == 0 and des[16] == 1 and des[23] == 1 and des[24] == 0


def test_cobertura_derivada_a_mano():
    ds = [Demanda(1, "LS", 360, 1080, 2), Demanda(2, "LS", 480, 840, 1)]
    assert demanda.cobertura_derivada(ds) == {"LS": {"M": 3, "T": 3, "N": 0}, "DF": {"M": 0, "T": 0, "N": 0}}


def test_huecos_sin_turno():
    m, t, nc = Turno("M", "", 360, 720), Turno("T", "", 720, 1080), Turno("NC", "", 1080, 360)
    ds = [Demanda(1, "LS", 480, 840, 1)]
    assert demanda.huecos_sin_turno(ds, {"M": m, "T": t}) == []
    assert demanda.huecos_sin_turno(ds, {"NC": nc}) == [(480, 840)]
    sin_dom = Turno("M", "", 360, 720, dom_fest=False)
    assert demanda.huecos_sin_turno([Demanda(1, "DF", 480, 720, 1)], {"M": sin_dom}) == [(480, 720)]


def test_estimar_personas():
    ds = [Demanda(1, "LS", 360, 1080, 2), Demanda(1, "DF", 360, 720, 1), Demanda(2, "LS", 360, 1080, 1, obligatorio=False)]
    assert demanda.horas_persona_semana(ds) == 150
    e = demanda.estimar_personas(ds, 42, 0.10)
    assert e["horas_semana"] == 150 and e["personas"] == 4 and e["por_puesto"] == {1: 150}
    assert e["por_franja"]["M"] + e["por_franja"]["T"] + e["por_franja"]["N"] == 150
    assert demanda.estimar_personas(ds, 42, 0.10, incluir_deseables=True)["horas_semana"] == 150 + 72


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
