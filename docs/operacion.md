# Operación de An en producción

Servidor único con Docker Compose (`docker-compose.prod.yml`): **caddy** (HTTPS y front) → **api**; **trabajador** (solver); **db** (PostgreSQL 16, sin puerto público); **migrar** (una vez por arranque). Seguridad: `docs/seguridad.md`. Plan y estado: `docs/superpowers/plans/2026-10-28-web-fase-8.md`.

En los comandos, `dc` es:

```bash
alias dc='docker compose -f docker-compose.prod.yml --env-file .env'
```

## 1. Puesta en marcha (servidor nuevo)

Requisitos: un servidor Linux con Docker y Compose v2, el dominio apuntando a su IP (registro A) y los puertos 80 y 443 abiertos (el 80 lo necesita Caddy para el certificado). Postgres no se abre al exterior.

```bash
git clone https://github.com/jssdv/an-turnos.git /opt/an && cd /opt/an
cp .env.example .env && chmod 600 .env     # edita: AN_DOMINIO y cada CAMBIAR_… (openssl rand -hex 24)
dc up -d --build                           # construye, crea roles, migra y arranca
dc ps                                      # todo "Up"/"healthy"; migrar "Exited (0)"
```

Primer uso (desde el servidor; los comandos muestran la clave temporal una sola vez):

```bash
dc --profile herramientas run --rm admin crear-clinica "Nombre de la clínica"
dc --profile herramientas run --rm admin crear-area --clinica 1 --nombre "Esterilización"
dc --profile herramientas run --rm admin crear-usuario --clinica 1 --correo coordinadora@clinica.co --nombre "Nombre" --admin
dc --profile herramientas run --rm admin dar-permiso --usuario 1 --area 1 --permiso editar
```

Después, el administrador de la clínica crea al resto desde la pantalla Usuarios. Migrar un `turnos.db` existente: `dc --profile herramientas run --rm --entrypoint python -v $PWD/turnos.db:/turnos.db admin -m an.web.migrar /turnos.db --clinica 1 --area 1` (compara cifras y revierte si no coinciden).

## 2. Variables (`.env`)

| Variable | Para qué |
|---|---|
| `AN_DOMINIO` | Dominio público; Caddy pide y renueva el certificado. `localhost` usa su CA interna (pruebas). |
| `AN_PUERTO_HTTP`, `AN_PUERTO_HTTPS` | Puertos publicados (80/443). Solo cambian en pruebas locales. |
| `AN_ORIGEN_PUERTO` | Solo pruebas con un puerto HTTPS distinto de 443 (`:18443`): la API compara el `Origin`. Vacío en producción. |
| `AN_ADMIN_CLAVE` | Rol dueño `an_admin` (migra, administra, respalda). |
| `AN_APP_CLAVE` | Rol `an_app` de la API y el trabajador. Solo letras y números. |
| `AN_SOLVER_WORKERS` | Hilos del solver; igual a los vCPU del servidor. |
| `AN_RESPALDO_DESTINO`, `AN_RESPALDO_RECIPIENTS`, `AN_RESPALDO_DIAS` | Ver §4. |

Roles: `migrar` crea/actualiza `an_app` con `AN_APP_CLAVE` (`python -m an.web.roles`) y aplica las migraciones (`python -m an.web.esquema`) como `an_admin` en cada `up`; la API y el trabajador esperan a que termine bien. Una migración publicada no se edita: se agrega otra.

## 3. Actualizar

```bash
cd /opt/an && git pull && dc up -d --build && dc ps
```

Hacer un respaldo (§4) antes de cada actualización que traiga migraciones. Si algo falla: `git checkout <versión anterior> && dc up -d --build`; las migraciones no se deshacen, por eso el respaldo previo. Las imágenes base (`python:3.13-slim`, `postgres:16`, `caddy:2`) se actualizan al reconstruir con `dc build --pull`.

## 4. Respaldo y restauración

**Qué hace:** `pg_dump -Fc` de toda la base, cifrado con `age` para la(s) clave(s) pública(s) de un archivo; deja `an-AAAAMMDD-HHMMSS.dump.age`, su `.cifras` (filas y hash por tabla) y `.firmas` + `.firmas.sig` (sha256 de ambos, firmado con `ssh-keygen -Y sign`, clave de firma distinta de la de cifrado; sin clave de firma no hay respaldo). Conserva `AN_RESPALDO_DIAS` días. **Riesgo:** el `.cifras` queda **en claro** junto al respaldo y revela cuántas filas y qué hash tiene cada tabla (p. ej. cuántos usuarios o cambios hay); trátalo como información interna: mismos permisos y mismo destino que el `.dump.age`, y no lo publiques aparte. Cifrarlo exigiría cambiar `respaldar.sh`, `restaurar.sh` y `probar_respaldo.sh` a la vez; queda pendiente. Si la base cambia mientras respalda, repite (hasta 3 veces) y avisa. Sale con error ≠ 0 ante cualquier fallo.

**Preparar (una vez, 👤):** genera el par de claves en un equipo de confianza (no el servidor):

```bash
docker run --rm $(docker build -q deploy/respaldo) age-keygen > an-respaldo.key   # la PRIVADA: guárdala fuera del servidor y fuera de Git
```

**Clave de firma (una vez, 👤):** `ssh-keygen -t ed25519 -N '' -C an-respaldo -f respaldo.firma.key`. La privada (`chmod 600`) va en el servidor en `deploy/respaldo.firma.key` (o `AN_RESPALDO_FIRMA`): solo permite firmar, no abrir respaldos. La pública (`respaldo.firma.key.pub`) se guarda en el equipo de confianza. Quien robe la clave de firma puede firmar un respaldo falso, no leer los reales; por eso la restauración exige además la verificación en el equipo de confianza.

Copia al servidor solo la línea `Public key: age1…` (sin el prefijo) a `deploy/respaldo.recipients` (el archivo debe existir antes de la primera corrida, o Docker crea una carpeta con ese nombre). Guarda `an-respaldo.key` en dos lugares (gestor de contraseñas de la clínica y copia cifrada): sin ella los respaldos no se abren.

**Nocturno (cron del servidor, 👤):**

```cron
15 2 * * * cd /opt/an && docker compose -f docker-compose.prod.yml --env-file .env --profile herramientas run --rm -T respaldo >> /var/log/an-respaldo.log 2>&1
```

**Fuera del servidor (👤):** copia `AN_RESPALDO_DESTINO` a otro lugar de la misma región (rsync/rclone a un bucket). Un respaldo que solo vive en el mismo disco no sirve ante la pérdida del servidor.

**Probar la restauración** (en un equipo de confianza con Docker y `ssh-keygen`, nunca en el servidor; no toca la base real). `restaurar.sh` verifica primero la firma y los sha256; sin firma válida no descifra:

```bash
deploy/restaurar.sh respaldos/an-AAAAMMDD-HHMMSS.dump.age an-respaldo.key respaldo.firma.key.pub
# → "Restauración correcta: N tablas con las mismas cifras."  (sale ≠ 0 si algo difiere)
```

Hacerlo una vez al configurar y después cada mes. **Prueba automática con datos sintéticos** (siembra, respalda, restaura, compara y verifica que un respaldo manipulado, sin firma, con cifras alteradas o firmado con otra clave fallan): `PYTHON=… checks/probar_respaldo.sh` — con firma: `OK` (corrida local 26/10/2026).

**Recuperar el servidor real** (la base actual se reemplaza). La clave privada `age` nunca va al servidor. En el equipo de confianza: corre `deploy/restaurar.sh` con el respaldo (verifica firma y cifras y prueba la restauración), y solo entonces descifra y copia el volcado al servidor por canal seguro:

```bash
# equipo de confianza (tras un restaurar.sh correcto):
age -d -i an-respaldo.key an-….dump.age > an.dump && scp an.dump servidor:/opt/an/
# servidor:
dc stop caddy api trabajador
dc exec -T db pg_restore -U an_admin -d an --clean --if-exists --exit-on-error < an.dump && shred -u an.dump
dc up -d       # migrar vuelve a fijar la clave de an_app y aplica migraciones nuevas
```

Verifica con `deploy/cifras.sql` (`dc exec -T db psql -U an_admin -d an -At -v esquema=public -f - < deploy/cifras.sql | diff - an-….cifras`).

## 5. Logs y diagnóstico

```bash
dc logs --since 1h api trabajador      # errores con su id de petición (X-Request-Id)
dc logs caddy | tail                   # accesos y certificados
dc ps
```

**Qué queda en los registros y por cuánto.** Los registros de Docker (`json-file`) rotan por tamaño: 10 MB × 5 por contenedor, y se pierden al recrear el contenedor. Uvicorn corre con `--no-access-log` (la API no escribe cada URL); Caddy sí registra cada petición en `dc logs caddy`. Ninguna URL lleva nombres de personas ni de archivos: el nombre del cuadro subido viaja en la cabecera `X-Nombre-Archivo` y la agenda de un médico se pide por su posición (`/agenda/3.ics`). La auditoría (tabla `auditoria`) sí guarda el nombre del archivo subido (evento `archivo_subido id=… nombre=…`); no se purga sola. No envíes los registros de Caddy fuera del servidor sin revisarlos.

Los logs rotan (10 MB × 5 por contenedor). Un 500 muestra al usuario un id: se busca en `dc logs api`. Auditoría de uso en la tabla `auditoria` (usuario, ruta, código, IP, evento).

**Subida de archivos de Radiología (tope de 10 MB).** La API acepta como máximo 10 MB (más 1 KB de holgura) en la subida del cuadro mensual y responde 413 «El archivo pasa de 10 MB.» si lo supera; el resto de las peticiones tienen tope de 1 MB. El `Caddyfile` no fija `request_body max_size`, así que Caddy deja pasar cualquier tamaño y el límite lo pone solo la API. Si algún día se agrega un límite en Caddy, debe ser ≥ 11 MB para la ruta de subida (`/api/areas/*/archivos`) o el usuario verá un 413 sin el mensaje de la aplicación. Un proxy o firewall corporativo con tope menor también cortaría la subida: probarla desde un PC de la clínica (§8). La API exige `Content-Length` en las escrituras (rechaza `chunked`): no usar herramientas que suban en trozos.

**Límites de recursos.** La API y el trabajador corren con `mem_limit` (2 GB; `AN_MEM_SERVIDOR` en `.env` para cambiarlo) y `pids_limit: 256`, para que un archivo hostil no tumbe el servidor entero. El cuadro mensual de Radiología se rechaza si su hoja usa más de 500 filas u 80 columnas, o si descomprime a más de 10 MB; los ya guardados que lo superen responden 422 con el motivo. El trabajador resuelve con `AN_SOLVER_WORKERS` hilos: con 2 GB no subas la cuenta sin subir también el límite.

**Redes.** Caddy es el único en la red `publica` y el único con puertos publicados; API, trabajador, base y respaldo viven en `interna` (`internal: true`: sin salida a internet). Caddy corre sin capacidades salvo `NET_BIND_SERVICE` y con `no-new-privileges`.

**IPv6.** No publiques un registro DNS AAAA para el dominio salvo que actives IPv6 en Docker con `"userland-proxy": false` en `/etc/docker/daemon.json`. Con IPv6 sin activar, las conexiones que llegan por `docker-proxy` aparecen con la IP de la puerta de enlace: el bloqueo de ingreso por intentos (correo, IP) y la auditoría contarían a todos los usuarios como una sola IP.

## 6. Qué revisar cada semana

- `dc ps`: todo arriba; sin reinicios repetidos.
- Respaldo: el archivo de anoche existe, pesa parecido al anterior y llegó fuera del servidor; `tail /var/log/an-respaldo.log` sin errores.
- Seguridad: eventos `ingreso_fallido`, `bloqueado`, `origen_rechazado` y accesos fuera de horario:
  ```bash
  dc exec -T db psql -U an_admin -d an -c "SELECT evento, count(*) FROM auditoria WHERE fecha > now() - interval '7 days' AND evento IS NOT NULL GROUP BY 1"
  ```
- Espacio en disco (`df -h`, volumen de Docker) y tamaño de `intento_login`.
- Actualizaciones del sistema operativo y de las imágenes (`dc build --pull`) al menos una vez al mes.
- Usuarios: personas que ya no trabajan deben estar desactivadas (pantalla Usuarios).

## 7. Prueba local de la pila (sin dominio)

```bash
cp .env.example .env   # AN_DOMINIO=localhost; AN_PUERTO_HTTP=18080; AN_PUERTO_HTTPS=18443; AN_ORIGEN_PUERTO=:18443; claves de prueba
docker compose -p an_prod_local -f docker-compose.prod.yml --env-file .env up -d --build
# https://localhost:18443 (certificado interno de Caddy: el navegador lo marca como no confiable)
docker compose -p an_prod_local -f docker-compose.prod.yml --env-file .env down -v    # y borra los datos
```

Verificado el 26/10/2026 en local: construcción de ambas imágenes; arranque con `migrar` → `api` (healthy) → `caddy`; ingreso, cambio de clave, `GET /api/areas`, creación de periodo y cuadro por `curl`; un trabajo `generar` tomado y terminado por el contenedor `trabajador`; la IP auditada es la del cliente y un `X-Forwarded-For` falso se ignora; Postgres sin puertos publicados.

## 8. Pasos manuales (👤)

Nada de esto lo puede hacer el repositorio:

- [ ] 👤 Elegir región y proveedor del servidor (≥ 4 vCPU recomendado para el solver; respaldos en la misma región) y contratar el VPS.
- [ ] 👤 Registrar el dominio y apuntar el DNS (A) al servidor; firewall con solo 80/443 y SSH por llave; actualizaciones automáticas de seguridad del sistema.
- [ ] 👤 Instalar Docker, clonar el repositorio, crear `.env` con claves generadas (`openssl rand -hex 24`) y levantar la pila (§1).
- [ ] 👤 Generar el par `age` y la clave de firma, instalar la pública `age` y la privada de firma, guardar la privada `age` y la pública de firma fuera del servidor (§4).
- [ ] 👤 Programar el cron del respaldo, copiarlo fuera del servidor y probar una restauración con el respaldo real.
- [ ] 👤 Firmar el acuerdo de tratamiento (`docs/ACUERDO_TRATAMIENTO.md`) con la región y la transferencia escritas.
- [ ] 👤 Probar el acceso desde un PC de la clínica (red, certificado, bloqueo por proxy o firewall corporativo).
- [ ] 👤 Instalar los escáneres de seguridad (Gitleaks, Semgrep, OSV-Scanner) y repetir la auditoría; aceptar por escrito los hallazgos no corregidos (`docs/seguridad-hallazgos.md`).
- [ ] 👤 Capacitación del personal y 2–4 semanas en paralelo con el proceso actual; publicar un mes real desde la web.
- [ ] 👤 Decidir el retiro de Qt y la etiqueta `qt-final` (decisión 3 de §10 del plan).
