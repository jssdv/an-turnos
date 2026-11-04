"""Versión portable: la capa web sobre SQLite (login, áreas, periodo, positional INSERT con defaults), arranque y migraciones.
Corre como script: imprime OK."""
import sqlite3
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from an.web import admin, conexion, entregable, esquema, sqlite_pg
from an.web.app import crear_app

O = "https://testserver"


def _carpeta():
    return Path(tempfile.mkdtemp())


def _version(ruta):
    con = sqlite3.connect(ruta)
    try:
        return con.execute("PRAGMA user_version").fetchone()[0]
    finally:
        con.close()


def test_flujo_basico():
    d = _carpeta()
    ruta = str(d / "an.db")
    primer = entregable.preparar_base(ruta, d / "respaldos")
    assert "Clave temporal" in primer and entregable.preparar_base(ruta, d / "respaldos") is None  # la segunda vez no recrea nada
    clave = primer.split("Clave temporal: ")[1].split("\n")[0]
    con = sqlite_pg.abrir(ruta)
    con.execute("UPDATE usuario SET debe_cambiar = 0")
    con.commit()
    con.close()
    cli = TestClient(crear_app(conexion.abrir_pool("sqlite:" + ruta)), base_url=O)
    H = {"Origin": O}
    assert cli.get("/api/areas").status_code == 401
    assert cli.post("/api/auth/entrar", json={"correo": entregable.CORREO, "clave": clave}, headers=H).status_code == 200
    assert cli.get("/api/areas").json()[0]["nombre"] == "Turnos"
    assert len(cli.get("/api/areas/1/turnos").json()) > 3  # sembrado con INSERT … VALUES posicional
    assert cli.post("/api/areas/1/colaboradores", json={"nombre": "Ana"}, headers=H).status_code == 201
    p = cli.post("/api/areas/1/periodos", json={"inicio": "2026-11-01", "fin": "2026-11-30"}, headers=H)
    assert p.status_code == 201, p.text


def test_base_nueva_queda_en_la_ultima_version():
    ruta = str(_carpeta() / "an.db")
    entregable.preparar_base(ruta, _carpeta())
    assert _version(ruta) == esquema.ultima_sqlite() == 12


def test_migracion_de_prueba_sube_desde_12():
    d = _carpeta()
    migraciones = d / "migraciones"
    migraciones.mkdir()
    (migraciones / "013_prueba.sql").write_text("CREATE TABLE prueba (id INTEGER PRIMARY KEY);", encoding="utf-8")
    (migraciones / "014_rota.sql").write_text("CREATE TABLE rota (id INTEGER); SELECT no_existe();", encoding="utf-8")
    ruta = str(d / "an.db")
    con = sqlite_pg.abrir(ruta)
    assert esquema.aplicar_sqlite(con) == 12  # base nueva: sin migraciones en la carpeta real
    con.close()
    con = sqlite_pg.abrir(ruta)
    try:
        esquema.aplicar_sqlite(con, migraciones)  # 013 sube, 014 falla y se revierte entera
        raise AssertionError("la migración 014 debía fallar")
    except sqlite3.Error:
        pass
    finally:
        con.close()
    assert _version(ruta) == 13
    raw = sqlite3.connect(ruta)
    tablas = {r[0] for r in raw.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
    raw.close()
    assert "prueba" in tablas and "rota" not in tablas
    (migraciones / "014_rota.sql").write_text("CREATE TABLE ok (id INTEGER);", encoding="utf-8")
    con = sqlite_pg.abrir(ruta)
    assert esquema.aplicar_sqlite(con, migraciones) == 14
    con.close()


def test_base_del_formato_anterior_se_marca_12():
    d = _carpeta()
    ruta = str(d / "an.db")
    raw = sqlite3.connect(ruta)
    raw.executescript(esquema.BASE_SQLITE.read_text(encoding="utf-8"))  # como la creaba el código anterior: sin user_version
    raw.close()
    entregable.preparar_base(ruta, d / "respaldos")
    assert _version(ruta) == 12


def test_base_del_formato_anterior_con_tabla_que_falta_se_rechaza():
    d = _carpeta()
    ruta = str(d / "an.db")
    raw = sqlite3.connect(ruta)
    raw.executescript(esquema.BASE_SQLITE.read_text(encoding="utf-8"))
    raw.execute("DROP TABLE exporte")
    raw.commit()
    raw.close()
    antes = Path(ruta).read_bytes()
    try:
        entregable.preparar_base(ruta, d / "respaldos")
        raise AssertionError("debía rechazar la base")
    except esquema.BaseNoUsable as e:
        assert "exporte" in str(e) and "no la modificó" in str(e)
    assert Path(ruta).read_bytes() == antes


def test_version_mas_nueva_se_rechaza_sin_tocarla():
    d = _carpeta()
    ruta = str(d / "an.db")
    entregable.preparar_base(ruta, d / "respaldos")
    raw = sqlite3.connect(ruta)
    raw.execute("PRAGMA user_version = 99")
    raw.close()
    antes = Path(ruta).read_bytes()
    try:
        entregable.preparar_base(ruta, d / "respaldos")
        raise AssertionError("debía rechazar la base")
    except esquema.BaseNoUsable as e:
        assert "más nueva" in str(e)
    assert Path(ruta).read_bytes() == antes


def test_base_danada_no_se_toca_y_ofrece_el_respaldo():
    d = _carpeta()
    ruta = d / "an.db"
    respaldos = d / "respaldos"
    entregable.preparar_base(str(ruta), respaldos)
    entregable.respaldar(ruta, respaldos)
    ruta.write_bytes(b"esto no es una base de datos " * 200)
    antes = ruta.read_bytes()
    try:
        entregable.preparar_base(str(ruta), respaldos)
        raise AssertionError("debía avisar de la base dañada")
    except esquema.BaseNoUsable as e:
        assert "dañada" in str(e) and str(entregable.ultimo_respaldo(respaldos)) in str(e)
    assert ruta.read_bytes() == antes


def test_cero_bytes_es_base_nueva():
    d = _carpeta()
    ruta = d / "an.db"
    ruta.touch()
    primer = entregable.preparar_base(str(ruta), d / "respaldos")
    assert "Clave temporal" in primer
    assert not (d / "respaldos").exists()  # nada que respaldar


def test_respaldo_al_abrir_con_poda():
    d = _carpeta()
    ruta = str(d / "an.db")
    respaldos = d / "respaldos"
    entregable.preparar_base(ruta, respaldos)
    entregable.preparar_base(ruta, respaldos)
    assert len(list(respaldos.glob("an_*.db"))) == 1  # la segunda apertura dejó su copia
    for i in range(entregable.RESPALDOS_MAX + 2):  # copias viejas: la poda deja las últimas RESPALDOS_MAX
        (respaldos / f"an_1999{i:04d}.db").write_bytes(b"x")
    entregable.respaldar(Path(ruta), respaldos)
    assert len(list(respaldos.glob("an_*.db"))) == entregable.RESPALDOS_MAX


if __name__ == "__main__":
    for prueba in [test_flujo_basico, test_base_nueva_queda_en_la_ultima_version, test_migracion_de_prueba_sube_desde_12,
                   test_base_del_formato_anterior_se_marca_12, test_base_del_formato_anterior_con_tabla_que_falta_se_rechaza,
                   test_version_mas_nueva_se_rechaza_sin_tocarla, test_base_danada_no_se_toca_y_ofrece_el_respaldo,
                   test_cero_bytes_es_base_nueva, test_respaldo_al_abrir_con_poda]:
        prueba()
    print("OK")
