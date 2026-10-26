# Hallazgos de la auditoría de seguridad — Fase 8 (ronda R1)

Registro de la auditoría con la skill `security-audit` (alcance: este repositorio, rama `claude/web-fase-8-f3665b`, 26/10/2026). Sin secretos ni datos del personal. Cobertura **reducida**: ningún escáner de código abierto estaba instalado (Gitleaks, Semgrep, OSV-Scanner, Checkov, zizmor, pip-audit, Bandit) y no se instalaron sin permiso de la persona dueña. Lo que sí corrió: `npm audit` (0 vulnerabilidades, 26/10/2026), revisión manual guiada por la lista de la skill (cadena de seguridad, autenticación, RLS, rutas de usuarios y trabajos, migraciones, Docker/Compose/Caddy, front) y búsqueda de secretos por `git grep`. 👤 Antes de operar con datos reales: instalar los escáneres y repetir la ronda (`security-verify`); los hallazgos de abajo no sustituyen esa pasada.

**Resultado: 0 hallazgos Altos o Críticos en lo revisado.** Medios: 3 (aceptados con motivo). Bajos/Info: 9 (5 corregidos).

| ID | Sev. | Hallazgo | Decisión | Estado |
|---|---|---|---|---|
| SEC-001 | Media | Contraseñas con scrypt N=2^14 (por debajo de la recomendación actual de OWASP, N=2^17). `auth.py` guarda los parámetros en el hash, así que se puede subir sin romper claves viejas. | **Aceptar** hasta tener rehash al ingresar: subir el costo sin tope de concurrencia convierte `/entrar` en una vía de agotar memoria (64–128 MiB por intento), y el bloqueo por intentos limita la fuerza bruta en línea. Revisar en la Fase 8b. | Aceptado |
| SEC-002 | Media | El bloqueo de ingreso cuenta por (correo, IP): un atacante con muchas IPs puede probar claves contra una cuenta sin tope global. | **Aceptar** con mitigación: clave mínima de 10 caracteres, auditoría de `ingreso_fallido` (revisión semanal, `docs/operacion.md`). Un tope global por correo permitiría a un tercero bloquear a cualquier usuario (negación de servicio). | Aceptado |
| SEC-003 | Media | Sin límite de tasa en Caddy para `/api/auth/entrar`; cada intento escribe una fila (`intento_login`). | **Aceptar** para el piloto (una clínica, acceso conocido); añadir límite de tasa (módulo de Caddy o el firewall del proveedor) si aparece abuso. | Aceptado |
| SEC-004 | Baja | `/openapi.json` se servía sin sesión (mapa de la API). Detrás de Caddy no se alcanza (solo `/api/*` va a la API), pero era una exposición evitable. | **Corregir** (prueba primero: `tests/web/test_superficie.py`). `openapi_url=None` en `an/web/app.py`; `checks/openapi.py` sigue funcionando. | Corregido |
| SEC-005 | Baja | `ortools` y `openpyxl` sin versión fija; imágenes base por etiqueta, no por huella. | **Corregir** lo primero (`requirements-servidor.txt` fija las versiones probadas); las etiquetas de imagen quedan: se actualizan al reconstruir (`docs/operacion.md`). | Corregido / aceptado |
| SEC-006 | Baja | La imagen del servidor incluía `web/sembrar_demo.py` (borra y recrea esquemas). Inalcanzable desde la API, pero sobra en producción. | **Corregir**: se quitó del `Dockerfile`. | Corregido |
| SEC-007 | Info | API y trabajador con todas las capacidades de Linux y sin `no-new-privileges`. | **Corregir**: `cap_drop: [ALL]`, `no-new-privileges` y rotación de logs en `docker-compose.prod.yml`. | Corregido |
| SEC-008 | Baja | El rol dueño `an_admin` es superusuario del contenedor Postgres (las funciones `SECURITY DEFINER` necesitan un dueño que se salte RLS). Solo lo usan `migrar`, `admin` y `respaldo`; la API y el trabajador entran como `an_app` (sin `BYPASSRLS`, y `abrir_pool` se niega a arrancar si lo tuvieran). | **Aceptar**: un dueño `BYPASSRLS` no superusuario sería más estrecho; se evalúa si la clínica lo exige. | Aceptado |
| SEC-009 | Baja | CSP del front estático con `style-src 'unsafe-inline'` (el front usa atributos `style`). Sin `unsafe-inline` en scripts. | **Aceptar** mientras el front use estilos en línea. | Aceptado |
| SEC-010 | Baja | El borrador de un cambio (celdas y turnos) se guarda en `sessionStorage` para sobrevivir a un 401. Se borra al cerrar la pestaña. | **Aceptar**: sin nombres ni credenciales; el equipo de la clínica es compartido solo por la persona que edita. | Aceptado |
| SEC-011 | Baja | `intento_login` solo se purga al iniciar sesión alguien; con muchos intentos sobre correos inexistentes crece hasta el siguiente ingreso. | **Aceptar** (índice y volumen bajos); `docs/operacion.md` incluye revisar su tamaño. | Aceptado |
| SEC-012 | Info | Los secretos viajan por variables de entorno de los contenedores (visibles para quien administre Docker en el servidor). | **Aceptar**: inherente a Compose sin gestor de secretos; el archivo `.env` va con permisos 600 y fuera de Git. | Aceptado |

## Notas

- **Pendiente conocido «IP real detrás de Caddy»: cerrado.** Caddy tiene IP fija; uvicorn confía en `X-Forwarded-For` solo de esa IP (`--proxy-headers --forwarded-allow-ips`). Pruebas: `tests/web/test_proxy.py` y, en la pila local, un `X-Forwarded-For` falsificado desde fuera no cambia la IP auditada.
- **Sin hallazgos de aislamiento entre clínicas** en la revisión de rutas (`rutas_usuarios`, `rutas_trabajos`, `deps.contexto_area`) ni de las funciones `SECURITY DEFINER` (todas con `search_path` fijo, `REVOKE … FROM PUBLIC`). `checks/rls.py` y `checks/reglas.py` siguen en verde.
- **No revisado a fondo:** `rutas_catalogos.py`/`rutas_edicion.py` línea por línea (las cubre `checks/reglas.py`: permiso de área y sin SQL armado), la migración de datos, y Radiología (ramas aún sin fusionar).


# Ronda R2 — revisión independiente (solo lectura) y su corrección

Un revisor externo encontró 1 hallazgo importante y 9 menores. Se corrigen en `docs/superpowers/plans/2026-10-29-seguridad-fix.md` (cada uno con una prueba que falló primero).

| ID | Sev. | Hallazgo | Corrección | Estado |
|---|---|---|---|---|
| I-1 | Importante | Un `.xlsx` de 5 KB con una celda en `E1048576` hacía recorrer un millón de filas (cientos de MB por petición) y quedaba guardado. | `cargar_mensual` rechaza hojas con > 500 filas o > 80 columnas (422 al subir y al leer los ya guardados); `MAX_DESCOMPRIMIDO` 10 MB; `mem_limit` y `pids_limit` en API y trabajador. | Corregido |
| M-1 | Media | Nombres que empiezan por `= + - @` se publicaban como fórmula en los Excel. | `an/nucleo/xlsx.poner_texto` fuerza tipo texto en las salidas de Radiología y Esterilización. | Corregido |
| M-2 | Media | Un usuario `ver` escribía en `exporte` y `periodo` (Radiología) y sin tope (ambas áreas). | Exportar en Radiología exige `editar`; en Esterilización `ver` puede, con tope de 20 por periodo en 24 h (429). | Corregido |
| M-3 | Media | Nombres de médicos y de archivos en la URL, y por tanto en los registros. | Cabecera `X-Nombre-Archivo`; agenda por posición; `--no-access-log`; retención documentada. | Corregido |
| M-4 | Media | Respaldos sin firma; la restauración corre como superusuario; la clave privada puede estar en el servidor. | **Pendiente, a decidir.** Requiere elegir esquema de firma y procedimiento. Propuesta: firmar cada `.dump.age` con `minisign` o `ssh-keygen -Y sign` desde el servidor (clave de firma distinta de la de cifrado), verificar la firma antes de restaurar y descifrar/restaurar solo en un equipo de confianza, nunca en el servidor. | Pendiente |
| M-5 | Media | Caddy sin `cap_drop`/`no-new-privileges`; red `interna` con salida. | Caddy con `cap_drop: [ALL]` + `NET_BIND_SERVICE` y `no-new-privileges`; red `publica` (Caddy) y `interna` con `internal: true`. | Corregido |
| M-6 | Media | Con IPv6 sin activar en Docker, las conexiones llegan con la IP de la puerta de enlace y el bloqueo por intentos cuenta a todos como una IP. | Documentado en `docs/operacion.md`: no publicar AAAA salvo con IPv6 en Docker y `userland-proxy: false`. | Documentado |
| M-7 | Media | El correo único global revela correos de otras clínicas al crear un usuario. | **Pendiente, decisión de producto.** Opciones: mensaje genérico, o unicidad por `(clinica_id, correo)` con cambios en `app_buscar_usuario`. | Pendiente |
| M-8 | Media | El borrador del cambio en `sessionStorage` no estaba ligado al usuario ni se borraba al salir (el `motivo` puede llevar datos de salud). | Se guarda con el id de usuario, se descarta si es otro y se borra al salir. | Corregido |
| M-9 | Baja | (a) claves `CAMBIAR_…` aceptadas; (b) subida y borrado de archivos sin evento de auditoría; (c) `.cifras` en claro junto al respaldo. | (a) `roles.py` las rechaza; (b) eventos `archivo_subido` / `archivo_borrado`; (c) riesgo documentado, cifrado pendiente (toca tres scripts). | Corregido / documentado |
