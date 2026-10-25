"""Contraseñas (scrypt), sesiones y bloqueo por intentos. El ingreso usa funciones SECURITY DEFINER de la migración 002."""
import base64
import hashlib
import hmac
import secrets
from dataclasses import dataclass

N, R, P = 2 ** 14, 8, 1
MIN_CLAVE = 10
MAX_FALLOS = 5


class ErrorAuth(Exception):
    pass


@dataclass
class Usuario:
    id: int
    clinica_id: int
    correo: str
    nombre: str
    es_admin: bool
    debe_cambiar: bool


def _scrypt(clave, sal, n=N, r=R, p=P):
    return hashlib.scrypt(clave.encode(), salt=sal, n=n, r=r, p=p, dklen=32)


def hash_clave(clave):
    sal = secrets.token_bytes(16)
    b64 = lambda b: base64.b64encode(b).decode()
    return f"scrypt${N}${R}${P}${b64(sal)}${b64(_scrypt(clave, sal))}"


def verificar_clave(clave, guardado):
    try:
        _, n, r, p, sal, esperado = guardado.split("$")
        calculado = _scrypt(clave, base64.b64decode(sal), int(n), int(r), int(p))
        return hmac.compare_digest(calculado, base64.b64decode(esperado))
    except (ValueError, TypeError):
        return False


_FALSO = None  # hash de relleno: verificar también cuando el correo no existe, para no delatarlo por el tiempo de respuesta


def _hash_token(token):
    return hashlib.sha256(token.encode()).hexdigest()


def _contar_intento(c, clave, ip):
    """Registra el intento ANTES de verificar y dice si ya pasó el límite: así las peticiones en paralelo no se cuelan antes del bloqueo."""
    c.execute("SELECT app_registrar_intento(?, ?)", (clave, ip))
    c.commit()
    return c.execute("SELECT app_intentos(?, ?)", (clave, ip)).fetchone()[0] > MAX_FALLOS


def iniciar_sesion(c, correo, clave, ip):
    """(token en claro, Usuario). Lanza ErrorAuth("credenciales inválidas") o ErrorAuth("bloqueado")."""
    global _FALSO
    correo = correo.strip().lower()
    if _contar_intento(c, correo, ip):
        raise ErrorAuth("bloqueado: demasiados intentos; espera 15 minutos")
    u = c.execute("SELECT * FROM app_buscar_usuario(?)", (correo,)).fetchone()
    if u is None and _FALSO is None:
        _FALSO = hash_clave(secrets.token_hex(8))
    if not verificar_clave(clave, u["hash_clave"] if u else _FALSO) or u is None or not u["activo"]:
        raise ErrorAuth("credenciales inválidas")
    token = secrets.token_urlsafe(32)
    c.execute("SELECT app_limpiar_intentos(?, ?)", (correo, ip))
    c.execute("SELECT app_crear_sesion(?, ?)", (_hash_token(token), u["id"]))
    c.execute("SELECT app_purgar()")
    c.commit()
    return token, Usuario(u["id"], u["clinica_id"], correo, u["nombre"], u["es_admin"], u["debe_cambiar"])


def usuario_de_token(c, token):
    """El usuario de la sesión, o None si no existe, se cerró o venció (35 min sin uso / 12 h desde que se creó; hora del servidor)."""
    u = c.execute("SELECT * FROM app_sesion(?)", (_hash_token(token),)).fetchone()
    c.commit()
    return Usuario(u["id"], u["clinica_id"], u["correo"], u["nombre"], u["es_admin"], u["debe_cambiar"]) if u else None


def cerrar_sesion(c, token):
    c.execute("SELECT app_cerrar_sesion(?)", (_hash_token(token),))
    c.commit()


def cambiar_clave(c, usuario, actual, nueva, token=None, ip="?"):
    """Cambia la clave de `usuario` (un Usuario) y cierra sus demás sesiones (se conserva la de `token`). Las pruebas fallidas de la
    clave actual cuentan como intentos (mismo bloqueo que el ingreso). El alcance se fija a su clínica: las funciones SQL lo exigen."""
    clave_intento = f"clave:{usuario.id}"
    if _contar_intento(c, clave_intento, ip):
        raise ErrorAuth("bloqueado: demasiados intentos; espera 15 minutos")
    c.execute("SELECT set_config('app.clinica', ?, true)", (str(usuario.clinica_id),))
    if not verificar_clave(actual, c.execute("SELECT app_hash_clave(?)", (usuario.id,)).fetchone()[0] or ""):
        c.commit()
        raise ErrorAuth("la contraseña actual no coincide")
    if len(nueva) < MIN_CLAVE:
        raise ErrorAuth(f"la contraseña nueva debe tener al menos {MIN_CLAVE} caracteres")
    c.execute("SELECT app_limpiar_intentos(?, ?)", (clave_intento, ip))
    c.execute("SELECT app_poner_clave(?, ?, ?)", (usuario.id, hash_clave(nueva), _hash_token(token) if token else None))
    c.commit()
