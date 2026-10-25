import os, sys; sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
"""Pruebas de checks/reglas.py: permiso de área en rutas, SQL sin f-strings y subprocess solo en el trabajador. Imprime OK."""
import contextlib
import io
import tempfile
from pathlib import Path

from checks import reglas

RAIZ = Path(__file__).resolve().parents[2]


def correr(archivos):
    with tempfile.TemporaryDirectory() as d:
        for ruta, texto in archivos.items():
            p = Path(d, ruta)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(texto, encoding="utf-8")
        err = io.StringIO()
        with contextlib.redirect_stderr(err):
            rc = reglas.main(["--raiz", d])
        return rc, err.getvalue()


def test_ruta_sin_permiso():
    rc, err = correr({"an/web/rutas_x.py": "@router.get('/a')\ndef a():\n    return 1\n"})
    assert rc == 1 and "rutas_x.py" in err and "permiso" in err
    rc, _ = correr({"an/web/rutas_x.py": "@router.get('/a')\ndef a(ctx=Depends(contexto_area)):\n    return 1\n"})
    assert rc == 0


def test_sql_con_fstring_o_format():
    rc, err = correr({"an/turnos/q.py": "def f(t):\n    return f'SELECT * FROM {t}'\n"})
    assert rc == 1 and "q.py" in err and "SQL" in err
    assert correr({"an/turnos/q.py": "def f(t):\n    return 'DELETE FROM %s' % t\n"})[0] == 1
    assert correr({"an/turnos/q.py": "def f(t):\n    return 'UPDATE {} SET x=1'.format(t)\n"})[0] == 1
    assert correr({"an/turnos/q.py": "def f(t):\n    return f'SELECT * FROM {t}'  # sql-ok: nombre de constante\n"})[0] == 0
    assert correr({"an/turnos/q.py": "def f(t):\n    return f'hola {t}'\n"})[0] == 0


def test_subprocess_solo_en_el_trabajador():
    rc, err = correr({"an/web/otro.py": "import subprocess\n"})
    assert rc == 1 and "subprocess" in err
    assert correr({"an/web/trabajador.py": "import subprocess\n"})[0] == 0


def test_el_repositorio_cumple():
    assert reglas.main(["--raiz", str(RAIZ)]) == 0


if __name__ == "__main__":
    for nombre, fn in list(globals().items()):
        if nombre.startswith("test_"):
            fn()
    print("OK")
