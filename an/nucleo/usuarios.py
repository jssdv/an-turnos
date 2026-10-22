"""Usuarios locales de An: cada uno entra a una sola área. Sin contraseña por ahora (ver docs/NUCLEO.md)."""
import json

from . import RAIZ

RUTA = RAIZ / "usuarios.json"
POR_DEFECTO = {"Radiología": "radiologia", "Esterilización": "esterilizacion"}


class ErrorUsuarios(Exception):
    """El archivo de usuarios no se puede usar; el mensaje se muestra tal cual."""


def cargar(areas, ruta=RUTA):
    """{nombre: clave de área}. Si el archivo no existe se crea con un usuario por área."""
    if not ruta.exists():
        ruta.write_text(json.dumps(POR_DEFECTO, ensure_ascii=False, indent=2), encoding="utf-8")
    try:
        usuarios = json.loads(ruta.read_text(encoding="utf-8"))
    except ValueError as e:
        raise ErrorUsuarios(f"No se pudo leer «{ruta.name}»: {e}") from e
    if not isinstance(usuarios, dict) or not usuarios:
        raise ErrorUsuarios(f"«{ruta.name}» debe ser un objeto {{\"usuario\": \"área\"}} con al menos un usuario.")
    malos = sorted(n for n, a in usuarios.items() if a not in areas)
    if malos:
        raise ErrorUsuarios(f"«{ruta.name}»: área desconocida para {', '.join(malos)}. Áreas válidas: {', '.join(areas)}.")
    return usuarios
