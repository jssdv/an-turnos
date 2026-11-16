import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de las métricas del dashboard de analíticas (solo lectura). Imprime OK."""
from datetime import date, datetime, timedelta

from an.turnos import analitica, cambios, db
from an.turnos.dominio import Colaborador, Novedad

I, F = date(2026, 10, 1), date(2026, 10, 31)


def nuevo():
    bd = db.BD()
    for n, t in (("A", "regular"), ("B", "regular"), ("C", "regular"), ("R", "refuerzo")):
        bd.guardar_colaborador(Colaborador(None, n, t))
    ids = {p.nombre: p.id for p in bd.colaboradores()}
    return bd, ids


def test_ausentismo_recorta_y_no_duplica():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Vacaciones", date(2026, 9, 28), date(2026, 10, 3)))
    bd.guardar_novedad(Novedad(i["A"], "Licencia", date(2026, 10, 2), date(2026, 10, 5)))
    r = analitica.ausentismo(bd, I, F)
    assert r["por_persona"]["A"] == {"Vacaciones": 3, "Licencia": 2}, r
    assert r["por_tipo"] == {"Vacaciones": 3, "Licencia": 2}
    assert r["por_mes"]["2026-10"] == {"Vacaciones": 3, "Licencia": 2}
    assert abs(r["pct"] - 5 / (31 * 3) * 100) < 1e-6, r["pct"]


def test_ausentismo_ignora_refuerzo_e_inactivo():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["R"], "Vacaciones", I, F))
    c = next(p for p in bd.colaboradores() if p.nombre == "C")
    c.activo = False
    bd.guardar_colaborador(c)
    bd.guardar_novedad(Novedad(i["C"], "Licencia", I, F))
    assert analitica.ausentismo(bd, I, F)["por_tipo"] == {}


def test_ausentismo_vacio():
    bd, _ = nuevo()
    r = analitica.ausentismo(bd, I, F)
    assert r["por_tipo"] == {} and r["pct"] == 0
    assert analitica.ausentismo(db.BD(), I, F)["pct"] == 0  # sin personas


def test_simultaneos_maximo_y_riesgo():
    bd, i = nuevo()
    d5, d6 = date(2026, 10, 5), date(2026, 10, 6)
    bd.guardar_novedad(Novedad(i["A"], "Vacaciones", d5, d5))
    bd.guardar_novedad(Novedad(i["B"], "Incapacidad", d5, d5))
    r = analitica.simultaneos(bd, I, F)
    assert r["maximo"] == 2 and r["fecha_maximo"] == d5 and len(r["serie"]) == 31 and r["dias_riesgo"] == []
    bd.guardar_cuadro("2026-10-01/2026-10-31", {(i["C"], d5): "M", (i["C"], d6): "M"})  # casi nadie: hay déficit
    r = analitica.simultaneos(bd, I, F)
    assert d5 in r["dias_riesgo"] and d6 not in r["dias_riesgo"], r["dias_riesgo"]  # d6: déficit pero sin ausentes
    assert analitica.simultaneos(db.BD(), I, F)["fecha_maximo"] is None

K2 = "2026-10-05/2026-10-11"


def test_cobertura_deficit_y_exceso():
    bd, i = nuevo()
    d5 = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i["A"], d5): "M"})  # casi nadie: déficit
    r = analitica.cobertura(bd, I, F)
    assert len(r) == 1 and r[0]["periodo"] == K2 and r[0]["dias_deficit"] >= 1, r
    assert analitica.cobertura(bd, date(2026, 11, 1), date(2026, 11, 30)) == []  # fuera del rango


def test_cobertura_exceso():
    bd, i = nuevo()
    d = date(2026, 10, 6)
    for dm in bd.demandas():  # sin demanda alguna, cualquier turno es exceso
        bd.c.execute("DELETE FROM demanda WHERE id=?", (dm.id,))
    bd.guardar_cuadro(K2, {(i["A"], d): "M"})
    r = analitica.cobertura(bd, I, F)[0]
    assert r["dias_exceso"] == 1 and r["dias_deficit"] == 0, r


def test_cobertura_sin_cuadro():
    assert analitica.cobertura(nuevo()[0], I, F) == []


def test_cambios_resumen_excluye_anulados():
    bd, i = nuevo()
    d5, d6 = date(2026, 10, 5), date(2026, 10, 6)
    bd.guardar_cuadro(K2, {(i["A"], d5): "M", (i["B"], d5): "T", (i["A"], d6): "L"})
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "pedido", "u")
    [aj] = cambios.ajuste(bd, K2, [(i["A"], d6, "M")], "x", "u")
    cambios.anular(bd, aj, "u")
    r = analitica.cambios_resumen(bd, I, F)
    assert r == {K2: {"permuta": 1, "servicio": 0, "ajuste": 0, "excepciones": 0}}, r
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "otra", "u")
    cambios.permuta(bd, K2, i["A"], d5, i["B"], d5, "tercera", "u", excepcion=True)
    r = analitica.cambios_resumen(bd, I, F)[K2]
    assert r["permuta"] == 3 and r["excepciones"] == 1, r


def test_cambios_sin_filas():
    assert analitica.cambios_resumen(nuevo()[0], I, F) == {}


def _cuadro_octubre(bd, i):
    """A: corrido los primeros 14 días de octubre; B: noche corrida los días 5, 6, 11 y 12."""
    c = {(i["A"], date(2026, 10, d)): "C" for d in range(1, 15)}
    c.update({(i["B"], date(2026, 10, d)): "NC" for d in (5, 6, 11, 12)})
    bd.guardar_cuadro("2026-10-01/2026-10-31", c)


def test_horas_extra_mes_vs_semanas():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    [r] = analitica.horas_extra(bd, I, F)
    assert r["periodo"] == "2026-10-01/2026-10-31" and r["ventana"] == 3, r
    assert r["semanas"] == {"diurna": 42.0, "nocturna": 0.0}, r  # 168 h contra 126 contratadas en la 1.ª ventana
    assert r["mes"] == {"diurna": 0.0, "nocturna": 0.0}, r  # 168 h contra 186 del mes completo
    assert analitica.horas_extra(bd, date(2026, 12, 1), date(2026, 12, 31)) == []


def test_recargos_resumen():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    r = analitica.recargos_resumen(bd, I, F)
    assert r["A"]["festivo"] == 36.0 and r["A"]["nocturna"] == 0.0, r["A"]  # domingos 4 y 11 y festivo del 12
    assert r["B"]["nocturna"] == 44.0 and r["B"]["festivo"] > 0, r["B"]  # 4 noches de 11 h desde las 19:00
    assert r["A"]["equivalentes"] > 0 and set(r) == {"A", "B", "C"}


def test_equidad():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    r = analitica.equidad(bd, I, F)
    assert r["por_persona"]["A"] == {"noches": 0, "domingos": 2, "festivos": 1}, r
    assert r["por_persona"]["B"] == {"noches": 4, "domingos": 1, "festivos": 1}, r
    assert r["dispersion"] == {"noches": 4, "domingos": 2, "festivos": 1}, r
    assert analitica.equidad(bd, date(2026, 12, 1), date(2026, 12, 31))["dispersion"] == {"noches": 0, "domingos": 0, "festivos": 0}


def test_banco():
    bd, i = nuevo()
    bd.cerrar_periodo("2026-10-01/2026-10-31", [(i["A"], 100, 110), (i["B"], 100, 94)])
    bd.cerrar_periodo("2026-09-01/2026-09-30", [(i["A"], 100, 105)])  # anterior al rango: entra en el acumulado
    bd.agregar_movimiento(i["A"], date(2026, 11, 2), -4, "Pagado en nómina")
    r = analitica.banco(bd, I, date(2026, 11, 30))
    assert r["saldos"] == {"A": 11.0, "B": -6.0, "C": 0.0}, r["saldos"]
    assert r["serie"] == [("10/26", 15.0, 6.0), ("11/26", 11.0, 6.0)], r["serie"]
    assert analitica.banco(db.BD(), I, F)["serie"] == [("10/26", 0.0, 0.0)]


# --- estabilidad del cuadro ------------------------------------------------------------------------
def _semana_completa(bd, i):
    bd.guardar_cuadro(K2, {(i[n], date(2026, 10, d)): "M" for n in "ABC" for d in range(5, 12)})


def test_estabilidad_pct_y_sin_publicar():
    bd, i = nuevo()
    _semana_completa(bd, i)
    cambios.ajuste(bd, K2, [(i["A"], date(2026, 10, 5), "T"), (i["B"], date(2026, 10, 6), "L")], "x", "u")
    [p] = analitica.estabilidad(bd, I, F, {K2: datetime(2026, 9, 25, 9, 0)})["periodos"]
    assert p["celdas_total"] == 21 and p["celdas_cambiadas"] == 2, p
    assert abs(p["pct"] - 2 / 21 * 100) < 1e-6, p
    assert analitica.estabilidad(bd, I, F, {})["periodos"] == []  # sin publicar no cuenta


def test_estabilidad_aviso_corto():
    bd, i = nuevo()
    _semana_completa(bd, i)
    d = date(2026, 10, 8)
    [cid] = cambios.servicio(bd, K2, [(i["A"], d, "T")], "falta gente", "u")
    pub = {K2: datetime(2026, 9, 25)}
    bd.c.execute("UPDATE cambio_turno SET registrado_en=? WHERE id=?", ("2026-10-07T20:00:00", cid))
    assert analitica.estabilidad(bd, I, F, pub)["periodos"][0]["aviso_corto"] == 1
    bd.c.execute("UPDATE cambio_turno SET registrado_en=? WHERE id=?", ("2026-10-03T08:00:00", cid))
    assert analitica.estabilidad(bd, I, F, pub)["periodos"][0]["aviso_corto"] == 0
    bd.c.execute("UPDATE cambio_turno SET registrado_en=? WHERE id=?", ("2026-10-07T20:00:00", cid))
    cambios.anular(bd, cid, "u")
    assert analitica.estabilidad(bd, I, F, pub)["periodos"][0]["aviso_corto"] == 0  # anulado no cuenta


def test_estabilidad_dias_anticipacion():
    bd, i = nuevo()
    _semana_completa(bd, i)
    [p] = analitica.estabilidad(bd, I, F, {K2: datetime(2026, 9, 25, 18, 30)})["periodos"]
    assert p["dias_anticipacion"] == 10, p


def test_estabilidad_cubre_mas():
    bd, i = nuevo()
    d5 = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i["A"], d5): "M"})
    cambios.servicio(bd, K2, [(i["A"], d5, "L"), (i["B"], d5, "M")], "A enfermo", "u")
    assert analitica.estabilidad(bd, I, F, {K2: datetime(2026, 9, 25)})["cubre_mas"] == {"B": 1}


def test_estabilidad_vacio():
    assert analitica.estabilidad(db.BD(), I, F, {}) == {"periodos": [], "cubre_mas": {}}


# --- fatiga -----------------------------------------------------------------------------------------
KO = "2026-10-01/2026-10-31"


def test_fatiga_rachas_y_horas():
    bd, i = nuevo()
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, d)): "M" for d in range(1, 8)})
    a = analitica.fatiga(bd, I, F)["A"]
    assert a["max_dias_seguidos"] == 7 and a["rachas_largas"] == 1, a  # tope por defecto: 6
    assert a["horas_4_sem_max"] == 42, a
    assert a["senales"] >= 1, a
    bd.set_param("max_dias_seguidos", 7)
    assert analitica.fatiga(bd, I, F)["A"]["rachas_largas"] == 0


def test_fatiga_descanso_corto_cruza_medianoche():
    bd, i = nuevo()
    c = {(i["A"], date(2026, 10, 5)): "NC", (i["A"], date(2026, 10, 6)): "M",  # NC termina 06:00 y M empieza 06:00
         (i["A"], date(2026, 10, 12)): "NC",                                     # seguida de libre: nada
         (i["A"], date(2026, 10, 20)): "T", (i["A"], date(2026, 10, 21)): "M"}   # justo 12 h
    bd.guardar_cuadro(KO, c)
    assert analitica.fatiga(bd, I, F)["A"]["descansos_cortos"] == 1
    bd.set_param("descanso_corto_horas", 13)
    assert analitica.fatiga(bd, I, F)["A"]["descansos_cortos"] == 2


def test_fatiga_noches():
    bd, i = nuevo()
    bd.guardar_cuadro(KO, {(i["B"], date(2026, 10, d)): "NC" for d in (5, 7, 9)})  # N-L-N-L-N
    assert analitica.fatiga(bd, I, F)["B"]["max_noches_seguidas"] == 3


def test_fatiga_fines():
    bd, i = nuevo()
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, 3)): "M", (i["A"], date(2026, 10, 18)): "T"})  # sáb 3 y dom 18
    r = analitica.fatiga(bd, I, F)
    assert r["A"]["fines_trabajados"] == 2 and r["B"]["fines_trabajados"] == 0, r


def test_fatiga_vacio():
    assert analitica.fatiga(db.BD(), I, F) == {}


# --- patrones de ausencia y riesgo ----------------------------------------------------------------
def test_bradford():
    bd, i = nuevo()
    for d in (6, 13, 20):
        bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, d), date(2026, 10, d)))
    bd.guardar_novedad(Novedad(i["B"], "Incapacidad", date(2026, 10, 6), date(2026, 10, 8)))
    bd.guardar_novedad(Novedad(i["C"], "Vacaciones", date(2026, 10, 6), date(2026, 10, 20)))
    b = analitica.patrones_ausencia(bd, I, F)["bradford"]
    assert b["por_persona"] == {"A": {"rachas": 3, "dias": 3, "puntaje": 27}, "B": {"rachas": 1, "dias": 3, "puntaje": 3}}, b
    assert b["equipo"] == {"0-49": 3, "50-199": 0, "200-499": 0, "500+": 0}, b


def test_rachas_recorta_borde():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 9, 28), date(2026, 10, 3)))
    assert analitica._rachas_ausencia(bd, I, F) == [(i["A"], "Incapacidad", I, date(2026, 10, 3))]


def test_por_dia_semana_y_tras_festivo():
    bd, i = nuevo()
    for d in (5, 12, 19):  # lunes
        bd.guardar_novedad(Novedad(i["A"], "Licencia", date(2026, 10, d), date(2026, 10, d)))
    r = analitica.patrones_ausencia(bd, I, F)
    assert r["por_dia_semana"][0] == max(r["por_dia_semana"]) > 0 and r["por_dia_semana"][1] == 0, r
    assert abs(r["por_dia_semana"][0] - 3 / (4 * 3) * 100) < 1e-6, r  # 4 lunes en octubre, 3 personas
    assert r["tras_festivo"] == 0
    bd.guardar_novedad(Novedad(i["B"], "Incapacidad", date(2026, 10, 13), date(2026, 10, 14)))  # el 12/10 es festivo
    assert analitica.patrones_ausencia(bd, I, F)["tras_festivo"] == 1


def test_riesgo_proximo():
    bd, i = nuevo()
    for d in (5, 12, 19, 26):  # lunes con incapacidad: el lunes es el día flojo
        bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, d), date(2026, 10, d)))
    bd.guardar_cuadro("2026-11-02/2026-11-08", {(i["A"], date(2026, 11, 4)): "M"})  # casi nadie: margen negativo todos los días
    r = analitica.riesgo_proximo(bd, date(2026, 11, 2))
    assert [x["fecha"] for x in r] == [date(2026, 11, 2)], r
    assert r[0]["franjas"] and r[0]["tasa"] > r[0]["media"], r
    assert analitica.riesgo_proximo(bd, date(2026, 11, 10)) == []  # sin cuadro en los próximos 14 días


def test_patrones_vacio():
    r = analitica.patrones_ausencia(db.BD(), I, F)
    assert r["por_dia_semana"] == [0] * 7 and r["bradford"]["por_persona"] == {} and r["tras_festivo"] == 0, r
    assert analitica.riesgo_proximo(db.BD(), I) == []


# --- hallazgos de la revisión ----------------------------------------------------------------------
def test_fatiga_racha_que_viene_de_antes_del_rango():
    bd, i = nuevo()
    bd.guardar_cuadro("2026-09-01/2026-09-30", {(i["A"], date(2026, 9, d)): "M" for d in range(20, 31)})
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, d)): "M" for d in range(1, 6)})  # 16 días seguidos
    a = analitica.fatiga(bd, I, F)["A"]
    assert a["max_dias_seguidos"] == 16 and a["rachas_largas"] == 1 and a["senales"] >= 1, a


def test_fatiga_sin_tope_de_noches():
    bd, i = nuevo()
    bd.set_param("max_noches_seguidas", 0)  # 0 = sin límite, como en validar
    bd.guardar_cuadro(KO, {(i["B"], date(2026, 10, 5)): "NC"})
    assert analitica.fatiga(bd, I, F)["B"]["senales"] == 0


def test_estabilidad_no_se_borra_al_republicar():
    bd, i = nuevo()
    _semana_completa(bd, i)
    pub = {K2: datetime(2026, 9, 25)}
    [antes] = cambios.ajuste(bd, K2, [(i["C"], date(2026, 10, 9), "T")], "borrador", "u")
    bd.c.execute("UPDATE cambio_turno SET registrado_en='2026-09-20T10:00:00' WHERE id=?", (antes,))  # antes de publicar: no cuenta
    [a] = cambios.ajuste(bd, K2, [(i["A"], date(2026, 10, 5), "T")], "x", "u")
    [b] = cambios.ajuste(bd, K2, [(i["B"], date(2026, 10, 6), "L")], "y", "u")
    bd.c.execute("UPDATE cambio_turno SET registrado_en='2026-10-01T10:00:00' WHERE id=?", (a,))
    bd.c.execute("UPDATE cambio_turno SET registrado_en='2026-10-07T10:00:00' WHERE id=?", (b,))  # después del turno: corrección, no aviso
    bd.publicar(K2)  # publicar otra vez copia `cambios` en `original`
    [p] = analitica.estabilidad(bd, I, F, pub)["periodos"]
    assert p["celdas_cambiadas"] == 2 and p["aviso_corto"] == 0, p


# --- pendientes menores de la revisión -------------------------------------------------------------
def test_tras_festivo_en_rango_largo():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, 13), date(2026, 10, 13)))  # el 12/10/2026 es festivo
    assert analitica.patrones_ausencia(bd, date(2022, 1, 1), date(2026, 12, 31))["tras_festivo"] == 1


def test_tras_festivo_no_cuenta_racha_recortada():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, 12), date(2026, 10, 14)))  # empezó el festivo mismo
    assert analitica.patrones_ausencia(bd, date(2026, 10, 13), F)["tras_festivo"] == 0


def test_bradford_mira_los_ultimos_12_meses():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2025, 1, 10), date(2025, 1, 10)))  # más de un año antes del fin
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, 6), date(2026, 10, 6)))
    r = analitica.patrones_ausencia(bd, date(2024, 1, 1), F)
    assert r["bradford"]["por_persona"]["A"] == {"rachas": 1, "dias": 1, "puntaje": 1}, r["bradford"]
    assert r["bradford"]["desde"] == date(2025, 11, 1), r["bradford"]


def test_riesgo_pide_historial_minimo():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Incapacidad", date(2026, 10, 26), date(2026, 10, 26)))  # un solo lunes
    bd.guardar_cuadro("2026-11-02/2026-11-08", {(i["A"], date(2026, 11, 4)): "M"})
    assert analitica.riesgo_proximo(bd, date(2026, 11, 2)) == []


# --- v3: cobertura por tramo -------------------------------------------------------------------------
def _una_demanda(bd):
    """Lunes a sábado de 06:00 a 12:00: 2 obligatorias y 1 deseable; domingo nada."""
    bd.c.execute("DELETE FROM demanda")
    bd.c.execute("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (1, 'LS', 360, 720, 2, 1)")
    bd.c.execute("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (1, 'LS', 360, 720, 1, 0)")
    bd.c.commit()


def test_cobertura_tramos_horas_y_porcentajes():
    bd, i = nuevo()
    _una_demanda(bd)
    lunes = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i["A"], lunes): "M", (i["C"], lunes): "M", (i["B"], lunes): "T"})  # lunes justo; B sobra en la tarde
    r = analitica.cobertura_tramos(bd, I, F)
    assert (r["horas_requeridas"], r["horas_faltantes"], r["horas_sobrantes"]) == (72, 60, 6), r
    assert abs(r["cobertura_pct"] - (1 - 60 / 72) * 100) < 1e-6 and abs(r["eficiencia_pct"] - (1 - 66 / 72) * 100) < 1e-6, r
    assert r["mapa"][0][12] == 0 and r["mapa"][1][12] == 2 and r["mapa"][0][24] is None, (r["mapa"][0][12], r["mapa"][1][12], r["mapa"][0][24])
    assert r["mapa"][6][12] is None  # domingo sin demanda ni gente
    assert r["por_periodo"] == [{"periodo": K2, "horas_requeridas": 72, "horas_faltantes": 60, "horas_sobrantes": 6,
                                 "cobertura_pct": (1 - 60 / 72) * 100, "eficiencia_pct": (1 - 66 / 72) * 100}], r["por_periodo"]


def test_cobertura_tramos_eficiencia_no_baja_de_cero():
    bd, i = nuevo()
    _una_demanda(bd)
    lunes = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i[n], lunes + timedelta(days=d)): "C" for n in "ABC" for d in range(6)})  # 3 personas 12 h para 6 h de 2
    r = analitica.cobertura_tramos(bd, I, F)
    assert r["horas_sobrantes"] > r["horas_requeridas"] and r["eficiencia_pct"] == 0, r


def test_cobertura_puestos_no_tapa_un_puesto_con_otro():
    from an.turnos.dominio import AsignacionPuesto
    bd, i = nuevo()
    bd.c.execute("DELETE FROM demanda")
    bd.c.execute("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (1, 'LS', 360, 720, 2, 1)")
    bd.c.execute("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (2, 'LS', 360, 720, 1, 1)")
    bd.c.commit()
    lunes = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i[n], lunes): "M" for n in "ABC"})  # 3 personas para 3 obligatorias: el área queda justa
    bd.guardar_asignacion_puesto(K2, [AsignacionPuesto(lunes, i["A"], 1, 360, 720, 1),  # Lavado pide 2 y tiene 1
                                      AsignacionPuesto(lunes, i["B"], 2, 360, 720, 1),  # Autoclave pide 1 y tiene 2
                                      AsignacionPuesto(lunes, i["C"], 2, 360, 720, 1)])
    area = analitica.cobertura_tramos(bd, lunes, lunes)
    assert (area["horas_faltantes"], area["horas_sobrantes"]) == (0, 0), area  # sumado, una cosa tapa la otra
    r = {p["puesto"]: p for p in analitica.cobertura_puestos(bd, lunes, lunes)}
    assert (r["Lavado"]["horas_requeridas"], r["Lavado"]["horas_faltantes"], r["Lavado"]["horas_sobrantes"]) == (12, 6, 0), r
    assert (r["Autoclave"]["horas_requeridas"], r["Autoclave"]["horas_faltantes"], r["Autoclave"]["horas_sobrantes"]) == (6, 0, 6), r
    assert r["Lavado"]["cobertura_pct"] == 50 and list(r) == ["Lavado", "Autoclave"], r
    bd.set_param("usa_puestos", "0")
    assert analitica.cobertura_puestos(bd, lunes, lunes) is None  # sin puestos no hay reparto que mirar


def test_cobertura_tramos_vacio():
    r = analitica.cobertura_tramos(db.BD(), I, F)
    assert r["horas_requeridas"] == 0 and r["cobertura_pct"] is None and r["por_periodo"] == [], r
    assert all(v is None for fila in r["mapa"] for v in fila)


# --- v3: equidad, concentración de horas extra y solicitudes ---------------------------------------
def test_equidad_desviacion_y_mad():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)  # noches: A 0, B 4, C 0
    r = analitica.equidad(bd, I, F)
    e = r["estadisticas"]["noches"]
    assert abs(e["media"] - 4 / 3) < 1e-6 and abs(e["mad"] - 16 / 9) < 1e-6, e
    assert abs(r["desviacion"]["B"]["noches"] - 8 / 3) < 1e-6 and abs(r["desviacion"]["A"]["noches"] + 4 / 3) < 1e-6, r["desviacion"]


def test_equidad_ajusta_por_dedicacion():
    bd, i = nuevo()
    c = next(p for p in bd.colaboradores() if p.nombre == "C")
    c.pct = 0.5
    bd.guardar_colaborador(c)
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, 5)): "NC", (i["A"], date(2026, 10, 7)): "NC", (i["C"], date(2026, 10, 5)): "NC"})
    d = analitica.equidad(bd, I, F)["desviacion"]
    assert abs(d["A"]["noches"] - d["C"]["noches"]) < 1e-6, d  # 2 noches a tiempo completo = 1 a medio tiempo


def test_concentracion_extra():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    r = analitica.concentracion_extra(bd, I, F)
    assert r["top_n"] == 1 and r["por_persona"]["A"] == 42 and r["top_pct"] == 100, r
    assert analitica.concentracion_extra(db.BD(), I, F) == {"por_persona": {}, "top_n": 0, "top_pct": None}


def test_solicitudes_resumen():
    from an.turnos.dominio import Solicitud
    bd, i = nuevo()
    _cuadro_octubre(bd, i)  # A trabaja C del 1 al 14
    for s in (Solicitud(i["A"], "libre", date(2026, 10, 5), date(2026, 10, 5)),
              Solicitud(i["A"], "evitar", date(2026, 10, 1), date(2026, 10, 2), "C"),
              Solicitud(i["B"], "libre", date(2026, 10, 7), date(2026, 10, 7)),
              Solicitud(i["C"], "quiero", date(2026, 10, 20), date(2026, 10, 20), "M"),
              Solicitud(i["C"], "libre", date(2026, 12, 1), date(2026, 12, 1))):  # fuera del rango
        bd.guardar_solicitud(s)
    r = analitica.solicitudes_resumen(bd, I, F)
    assert r["por_persona"]["A"] == {"pedidas": 2, "cumplidas": 0, "parciales": 0, "no_cumplidas": 2, "tasa": 0}, r
    assert r["por_persona"]["B"]["tasa"] == 100 and r["tasa"] == 50, r
    assert r["por_tipo"] == {"libre": {"pedidas": 2, "cumplidas": 1}, "evitar": {"pedidas": 1, "cumplidas": 0}, "quiero": {"pedidas": 1, "cumplidas": 1}}, r
    assert analitica.solicitudes_resumen(db.BD(), I, F) == {"por_persona": {}, "por_tipo": {}, "rango_tasa": None, "tasa": None}


# --- v3: planificación ----------------------------------------------------------------------------
def test_pronostico_ausencias():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["A"], "Vacaciones", date(2025, 11, 1), date(2025, 11, 10)))  # mismo mes del año pasado: 10
    for mes, n in ((8, 3), (9, 6), (10, 9)):                                                   # últimos 3 meses: media 6
        bd.guardar_novedad(Novedad(i["B"], "Incapacidad", date(2026, mes, 1), date(2026, mes, n)))
    r = analitica.pronostico_ausencias(bd, F)
    assert len(r["serie"]) == 12 and r["serie"][-1] == ("2026-10", 9) and r["serie"][0] == ("2025-11", 10), r["serie"]
    assert (r["siguiente"], r["mismo_mes_anterior"], r["media_3"], r["estimado"]) == ("2026-11", 10, 6, 8), r


def test_corridas():
    def f(h):
        return datetime(2026, 10, 1, 8, 0) + timedelta(seconds=h)
    filas = [{"periodo": K2, "estado": "fallido", "creado": f(0), "terminado": f(5), "resultado": None},
             {"periodo": K2, "estado": "listo", "creado": f(10), "terminado": f(40), "resultado": {"faltan": [["2026-10-05", "06:00", 1]], "solicitudes": [{"id": 1}]}},
             {"periodo": K2, "estado": "listo", "creado": f(50), "terminado": f(60), "resultado": {"faltan": [], "solicitudes": [{"id": 1}, {"id": 2}]}},
             {"periodo": K2, "estado": "corriendo", "creado": f(70), "terminado": None, "resultado": None},
             {"periodo": K2, "estado": "cancelado", "creado": f(75), "terminado": f(900), "resultado": None}]  # ni en la mediana ni en el %
    assert analitica.corridas(filas) == [{"periodo": K2, "corridas": 5, "terminadas_bien": 2, "pct_bien": 66.7, "mediana_seg": 10.0,
                                          "faltan_ultima": 0, "solicitudes_ultima": 2}]
    assert analitica.corridas([]) == []


def test_proximo_recargo():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    fest = sum(r["festivo"] for r in analitica.recargos_resumen(bd, I, F).values())
    r = analitica.proximo_recargo(bd, date(2026, 11, 15), I, F)
    assert (r["desde"], r["actual"], r["nuevo"]) == (date(2027, 7, 1), 90, 100), r
    assert abs(r["horas_mes"] - round(fest / (31 / 30.44) * 0.10, 2)) < 1e-6 and fest > 0, (r, fest)  # octubre: 31 días
    assert analitica.proximo_recargo(bd, date(2028, 1, 1), I, F) is None  # sin cambios por delante


# --- revisión de v3 --------------------------------------------------------------------------------
def test_proximo_recargo_promedia_sobre_los_dias_con_cuadro():
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    todo = (date(2026, 1, 1), date(2026, 12, 31))  # solo octubre tiene cuadro: no dividir por 12
    fest = sum(r["festivo"] for r in analitica.recargos_resumen(bd, *todo).values())
    r = analitica.proximo_recargo(bd, date(2026, 11, 15), *todo)
    assert abs(r["horas_mes"] - round(fest / (31 / 30.44) * 0.10, 2)) < 1e-6, (r, fest)


def test_pronostico_sin_historial_usa_media_3():
    bd, i = nuevo()
    for mes in (8, 9, 10):
        bd.guardar_novedad(Novedad(i["B"], "Incapacidad", date(2026, mes, 1), date(2026, mes, 6)))
    r = analitica.pronostico_ausencias(bd, F)
    assert r["estimado"] == 6 and r["base"] == "media_3", r


def test_pronostico_no_usa_el_mes_en_curso():
    bd, _ = nuevo()
    r = analitica.pronostico_ausencias(bd, F, hoy=date(2026, 10, 15))
    assert r["serie"][-1][0] == "2026-09" and r["siguiente"] == "2026-10", r


def test_equidad_descuenta_dias_ausente():
    bd, i = nuevo()
    bd.guardar_novedad(Novedad(i["C"], "Incapacidad", date(2026, 10, 16), date(2026, 10, 30)))  # la mitad de 30 días
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, 5)): "NC", (i["A"], date(2026, 10, 20)): "NC", (i["C"], date(2026, 10, 5)): "NC"})
    d = analitica.equidad(bd, I, date(2026, 10, 30))["desviacion"]
    assert abs(d["A"]["noches"] - d["C"]["noches"]) < 1e-6, d  # 2 noches en 30 días = 1 en 15 disponibles


def test_mapa_sobra_cuenta_lo_que_pasa_de_obligatoria_mas_deseable():
    bd, i = nuevo()
    bd.c.execute("DELETE FROM demanda")
    bd.c.execute("INSERT INTO demanda (puesto_id, tipo_dia, inicio, fin, personas, obligatorio) VALUES (1, 'LS', 360, 720, 2, 1)")
    bd.c.commit()
    lunes = date(2026, 10, 5)
    bd.guardar_cuadro(K2, {(i["A"], lunes): "M", (i["B"], lunes): "M", (i["C"], lunes): "M"})  # 3 donde piden 2
    r = analitica.cobertura_tramos(bd, I, F)
    assert r["mapa_sobra"][0][12] == 1 and r["mapa"][0][12] == 0, (r["mapa_sobra"][0][12], r["mapa"][0][12])
    assert r["mapa_sobra"][1][12] == 0 and r["mapa_sobra"][0][24] is None  # martes sin gente: falta, no sobra; sin demanda: nada


def test_mapa_promedia_faltantes_sin_festivos():
    bd, i = nuevo()
    _una_demanda(bd)
    c = {(i["A"], date(2026, 10, 5)): "M"}                                          # lunes 5: falta 1
    c.update({(i[n], date(2026, 10, 12)): "M" for n in "ABC"})                      # lunes 12 festivo: no entra
    c.update({(i[n], date(2026, 10, d)): "M" for n in "AC" for d in (19, 26)})       # lunes 19 y 26: justo
    bd.guardar_cuadro(KO, c)
    assert analitica.cobertura_tramos(bd, I, F)["mapa"][0][12] == round(1 / 3, 2)


def test_cobertura_recorta_al_rango():
    bd, i = nuevo()
    _una_demanda(bd)
    bd.guardar_cuadro(K2, {(i["A"], date(2026, 10, 7)): "M"})  # lunes a sábado con déficit
    assert analitica.cobertura(bd, date(2026, 10, 5), date(2026, 10, 6))[0]["dias_deficit"] == 2


def test_solicitudes_rango_de_tasas():
    from an.turnos.dominio import Solicitud
    bd, i = nuevo()
    _cuadro_octubre(bd, i)
    bd.guardar_solicitud(Solicitud(i["A"], "libre", date(2026, 10, 5), date(2026, 10, 5)))
    bd.guardar_solicitud(Solicitud(i["B"], "libre", date(2026, 10, 7), date(2026, 10, 7)))
    assert analitica.solicitudes_resumen(bd, I, F)["rango_tasa"] == 100


def test_equidad_festivos_en_rango_largo():
    bd, i = nuevo()
    bd.guardar_cuadro(KO, {(i["A"], date(2026, 10, 12)): "M"})  # festivo de 2026 con un rango que empieza en 2022
    assert analitica.equidad(bd, date(2022, 1, 1), F)["por_persona"]["A"]["festivos"] == 1


# --- aviso de ausencias y reemplazos ---------------------------------------------------------------
def test_novedad_guarda_cuando_se_registra():
    bd, i = nuevo()
    n = Novedad(i["A"], "Incapacidad", date(2026, 10, 6), date(2026, 10, 6))
    bd.guardar_novedad(n)
    [x] = bd.novedades()
    assert abs((x.registrado_en - datetime.now()).total_seconds()) < 60, x
    primera = x.registrado_en
    x.nota = "editada"
    bd.guardar_novedad(x)
    assert bd.novedades()[0].registrado_en == primera  # editar no cambia cuándo se avisó


def test_avisos_ausencia_y_reemplazos():
    bd, i = nuevo()
    d6, d7, d9 = date(2026, 10, 6), date(2026, 10, 7), date(2026, 10, 9)
    bd.guardar_cuadro(K2, {(i["A"], d6): "M", (i["B"], d7): "M"})
    casos = [(i["A"], "Incapacidad", d6, "2026-10-06T07:00:00"),   # ya había empezado el turno de las 06:00: tarde
             (i["B"], "Incapacidad", d7, "2026-10-06T20:00:00"),   # 10 h antes del turno
             (i["C"], "Licencia", d9, "2026-10-07T08:00:00"),      # sin turno ese día: 40 h antes de las 00:00
             (i["A"], "Vacaciones", d9, "2026-09-01T08:00:00"),    # planeada: no cuenta
             (i["A"], "Incapacidad", date(2026, 10, 20), None)]    # registrada antes de existir el dato
    for cid, tipo, d, reg in casos:
        n = Novedad(cid, tipo, d, d)
        bd.guardar_novedad(n)
        bd.c.execute("UPDATE novedad SET registrado_en=? WHERE id=?", (reg, n.id))
    for cid in cambios.servicio(bd, K2, [(i["A"], d6, "L"), (i["C"], d6, "M")], "A enferma", "u"):  # una fila por persona
        bd.c.execute("UPDATE cambio_turno SET registrado_en='2026-10-06T08:00:00' WHERE id=?", (cid,))
    r = analitica.avisos_ausencia(bd, I, F)
    assert r["avisos"] == {"tarde": 1, "menos_24h": 1, "24_72h": 1, "mas_72h": 0} and r["sin_dato"] == 1, r
    assert (r["dias_con_turno"], r["cubiertos"], r["pct_cubiertos"], r["mediana_horas"]) == (2, 1, 50.0, 1.0), r
    vacio = analitica.avisos_ausencia(db.BD(), I, F)
    assert vacio["sin_dato"] == 0 and vacio["pct_cubiertos"] is None and vacio["mediana_horas"] is None, vacio


for t in [v for k, v in dict(globals()).items() if k.startswith("test_")]:
    t()
print("OK")
