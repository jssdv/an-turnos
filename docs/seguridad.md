# Seguridad de An (servidor web)

Estado real del código (`an/web/`), no una intención. Auditoría y decisiones: `docs/seguridad-hallazgos.md`. Operación: `docs/operacion.md`. Acuerdo con la clínica: `docs/ACUERDO_TRATAMIENTO.md`.

## Qué se protege y de quién

Datos del personal de una clínica (nombres, turnos, ausencias, solicitudes; potencialmente datos sensibles como incapacidades). Amenazas consideradas:

| Amenaza | Defensa |
|---|---|
| Alguien de la clínica A ve o cambia datos de la B | RLS forzada en cada tabla por `clinica_id` (y `area_id`), alcance fijado por petición; la API entra como un rol sin `BYPASSRLS`. |
| Usuario sin permiso edita un área | `contexto_area`: `ver` para GET, `editar` para el resto; un solo editor por área (índice único). `checks/reglas.py` falla si una ruta no declara permiso. |
| Robo o adivinanza de contraseñas | scrypt con sal, mínimo 10 caracteres, bloqueo por (correo, IP) tras 5 fallos en 15 min, mismo mensaje para correo inexistente, hash de relleno para no delatar por tiempo. |
| Robo de sesión | Token aleatorio de 32 bytes; en base solo su SHA-256. Cookie `an_sid` `HttpOnly`, `Secure`, `SameSite=Lax`; vence a los 35 min sin uso y a las 12 h; se cierra al cambiar la clave, restablecerla o desactivar al usuario. |
| CSRF | `Origin` debe ser el propio (`AN_ORIGEN`) en POST/PUT/PATCH/DELETE; además `SameSite=Lax`. |
| Inyección SQL | Parámetros siempre; `checks/reglas.py` rechaza SQL armado con f-strings. |
| Cuerpos enormes | Tope de 1 MB por `Content-Length`; se rechaza `chunked` sin longitud. |
| Edición concurrente / pérdida de datos | `If-Match` con la revisión del periodo y bloqueo `FOR UPDATE`. |
| Pérdida del servidor | Respaldo nocturno cifrado fuera del servidor con restauración probada (`docs/operacion.md`). |
| Robo del respaldo | Cifrado con `age` (clave pública en el servidor, privada fuera). |
| Respaldo falsificado o manipulado | Cada respaldo se firma (`ssh-keygen -Y sign`, clave de firma propia); `restaurar.sh` verifica firma y sha256 antes de descifrar, en un equipo de confianza. |

## Cadena de una petición (`an/web/app.py`, middleware `cadena`)

1. `Content-Length` válido (400), `chunked` en escritura (411), tope 1 MB (413).
2. Escritura con `Origin` distinto del propio → 403 (si traía sesión válida se audita como `origen_rechazado`).
3. Se atiende la ruta. Un error inesperado devuelve `{"detalle": "Error interno", "id": …}` sin traza; el detalle va al log con ese id.
4. Cabeceras en toda respuesta: `Content-Security-Policy: default-src 'self'; frame-ancestors 'none'`, `X-Content-Type-Options: nosniff`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, `X-Request-Id`.
5. Si hay usuario en la petición, se escribe en `auditoria` (usuario, método, ruta, código, IP, evento). Nunca el cuerpo. Los ingresos fallidos o bloqueados se auditan con `app_auditar_ingreso`.

Dentro de la ruta: sesión (`usuario_permitido_cambiar` / `usuario_actual`: 401 sin sesión, 403 si `debe_cambiar`) → permiso de área → alcance RLS (`app.clinica`, `app.area` con `set_config(…, true)`: solo la transacción) → núcleo. Las validaciones de Pydantic responden 422 sin devolver el cuerpo (puede traer claves).

El front estático lo sirve Caddy con su propia CSP (`default-src 'self'`, `style-src` con `'unsafe-inline'`), HSTS, `nosniff` y sin cabecera `Server`. No hay `/docs`, `/redoc` ni `/openapi.json`.

## Base de datos y roles

- `an_admin` (superusuario del contenedor Postgres): aplica migraciones, es dueño de las tablas y de las funciones `SECURITY DEFINER`. Solo lo usan `migrar`, `admin` y `respaldo`.
- `an_app` (`LOGIN`, sin superusuario ni `BYPASSRLS`): API y trabajador. `conexion.abrir_pool` se niega a arrancar si el rol efectivo se salta RLS. Tiene permisos de tabla mínimos; `sesion`, `intento_login` y `esquema_version` no son tocables directamente.
- Funciones `SECURITY DEFINER` (`app_*`): `search_path` fijo, `REVOKE … FROM PUBLIC`, `GRANT EXECUTE` a `an_app`. Existen porque el ingreso ocurre antes de conocer la clínica, y para el trabajador (que toma trabajos de todas las clínicas).
- Postgres no publica puertos: solo la red interna de Compose lo alcanza.

## Red y contenedores

Solo Caddy publica puertos (80/443; HTTPS automático). API y trabajador: usuario sin privilegios (uid 10001), `cap_drop: ALL`, `no-new-privileges`. La IP del cliente: Caddy tiene IP fija en una red propia y uvicorn solo confía en `X-Forwarded-For` de esa IP (`--forwarded-allow-ips`), así el bloqueo por intentos y la auditoría ven la IP real y un encabezado falsificado se ignora (`tests/web/test_proxy.py`).

## Secretos

- Nada real en Git: `.env`, `*.key` y `respaldos/` están en `.gitignore`; `.env.example` solo trae marcadores. La clave de `an_app` y la del dueño entran por `.env` (permisos 600), y a los procesos por `PGPASSWORD`.
- Claves temporales de usuarios: `secrets.token_urlsafe(12)`, se muestran una sola vez y obligan a cambiarlas.
- La clave privada `age` del respaldo no vive en el servidor; en él solo está la clave de firma (firma, no abre). La restauración corre en un equipo de confianza y verifica la firma antes de tocar nada.
- Rotar: cambiar `AN_APP_CLAVE` en `.env` y `docker compose … up -d` (el servicio `migrar` ejecuta `an.web.roles` y la actualiza). Cambiar `AN_ADMIN_CLAVE` exige además `ALTER ROLE an_admin PASSWORD …` dentro del contenedor `db`.

## Lo que NO cubre

- **Escáneres automáticos:** la auditoría R1 no tuvo Semgrep/Gitleaks/OSV (no instalados); ver `docs/seguridad-hallazgos.md`.
- **Fuerza bruta distribuida, límite de tasa, WAF, detección de intrusos, doble factor:** no hay. El acceso por contraseña es el único factor.
- **El servidor anfitrión:** parches del sistema, SSH, firewall, cifrado de disco y accesos del proveedor son responsabilidad de quien opere el servidor (👤 en `docs/operacion.md`).
- **Datos en el navegador y los equipos de la clínica:** un PC comprometido o compartido sin cerrar sesión expone lo que el usuario ve.
- **Integridad frente a un administrador malicioso de la clínica:** el administrador crea usuarios y restablece claves; sus actos quedan en `auditoria`, no se previenen.
- **Retención y borrado de datos personales:** definidos en el acuerdo de tratamiento; el código no los automatiza.
- **Disponibilidad:** un solo servidor; sin alta disponibilidad. La recuperación es restaurar el respaldo (hasta ~24 h de datos perdidos si el servidor se pierde).
- **Radiología y exportes:** ramas aún no revisadas aquí.
