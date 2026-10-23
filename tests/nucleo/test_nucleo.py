"""Usuarios locales y shell: el usuario decide el área; archivo de usuarios inválido se explica. Imprime OK."""
import os, sys, tempfile
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QLabel, QPushButton

QSettings.setDefaultFormat(QSettings.IniFormat)  # no tocar los ajustes reales del usuario
QSettings.setPath(QSettings.IniFormat, QSettings.UserScope, tempfile.mkdtemp())

from an.__main__ import AREAS
from an.nucleo import usuarios as u
from an.nucleo.shell import Ventana
from an.nucleo.tema import preparar_app

tmp = Path(tempfile.mkdtemp())
# primer arranque: se crea el archivo con un usuario por área
por_defecto = u.cargar(AREAS, tmp / "usuarios.json")
assert (tmp / "usuarios.json").exists() and set(por_defecto.values()) == set(AREAS), por_defecto
# los usuarios del repositorio y los de ejemplo apuntan a áreas que existen
assert u.POR_DEFECTO.keys() == por_defecto.keys()
# archivo editado a mano: se respeta
(tmp / "u2.json").write_text('{"Ana": "radiologia"}', encoding="utf-8")
assert u.cargar(AREAS, tmp / "u2.json") == {"Ana": "radiologia"}
# errores con mensaje para el coordinador
for texto, parte in (("{", "No se pudo leer"), ("[]", "al menos un usuario"), ('{"Ana": "cocina"}', "área desconocida")):
    (tmp / "mal.json").write_text(texto, encoding="utf-8")
    try:
        u.cargar(AREAS, tmp / "mal.json")
        raise AssertionError(texto)
    except u.ErrorUsuarios as e:
        assert parte in str(e), (texto, str(e))

# la ventana muestra usuario y área, y «Cambiar usuario» pide volver a elegir
app = preparar_app([])
for clave, Area in AREAS.items():
    v = Ventana(Area, "Ana")
    assert v.windowTitle() == f"An · {Area.NOMBRE}" and not v.cambiar_usuario
    textos = {l.text() for l in v.findChildren(QLabel)}
    assert {Area.NOMBRE, "Ana"} <= textos, textos
    next(b for b in v.findChildren(QPushButton) if b.text() == "Cambiar usuario").click()
    assert v.cambiar_usuario
print("OK")
