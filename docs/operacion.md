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

**Qué hace:** `pg_dump -Fc` de toda la base, cifrado con `age` para la(s) clave(s) pública(s) de un archivo; deja `an-AAAAMMDD-HHMMSS.dump.age` y su `.cifras` (filas y hash por tabla). Conserva `AN_RESPALDO_DIAS` días. Si la base cambia mientras respalda, repite (hasta 3 veces) y avisa. Sale con error ≠ 0 ante cualquier fallo.

**Preparar (una vez, 👤):** genera el par de claves en un equipo de confianza (no el servidor):

```bash
docker run --rm $(docker build -q deploy/respaldo) age-keygen > an-respaldo.key   # la PRIVADA: guárdala fuera del servidor y fuera de Git
```

Copia al servidor solo la línea `Public key: age1…` (sin el prefijo) a `deploy/respaldo.recipients` (el archivo debe existir antes de la primera corrida, o Docker crea una carpeta con ese nombre). Guarda `an-respaldo.key` en dos lugares (gestor de contraseñas de la clínica y copia cifrada): sin ella los respaldos no se abren.

**Nocturno (cron del servidor, 👤):**

```cron
15 2 * * * cd /opt/an && docker compose -f docker-compose.prod.yml --env-file .env --profile herramientas run --rm -T respaldo >> /var/log/an-respaldo.log 2>&1
```

**Fuera del servidor (👤):** copia `AN_RESPALDO_DESTINO` a otro lugar de la misma región (rsync/rclone a un bucket). Un respaldo que solo vive en el mismo disco no sirve ante la pérdida del servidor.

**Probar la restauración** (en cualquier máquina con Docker; no toca la base real):

```bash
deploy/restaurar.sh respaldos/an-AAAAMMDD-HHMMSS.dump.age an-respaldo.key
# → "Restauración correcta: N tablas con las mismas cifras."  (sale ≠ 0 si algo difiere)
```

Hacerlo una vez al configurar y después cada mes. **Prueba automática con datos sintéticos** (siembra, respalda, restaura, compara y verifica que un respaldo manipulado o unas cifras alteradas fallan): `PYTHON=… checks/probar_respaldo.sh` — última corrida 26/10/2026: `OK` (27 tablas con cifras iguales).

**Recuperar el servidor real** (la base actual se reemplaza):

```bash
dc stop caddy api trabajador
age -d -i an-respaldo.key an-….dump.age | dc exec -T db pg_restore -U an_admin -d an --clean --if-exists --exit-on-error
dc up -d       # migrar vuelve a fijar la clave de an_app y aplica migraciones nuevas
```

Verifica con `deploy/cifras.sql` (`dc exec -T db psql -U an_admin -d an -At -v esquema=public -f - < deploy/cifras.sql | diff - an-….cifras`).

## 5. Logs y diagnóstico

```bash
dc logs --since 1h api trabajador      # errores con su id de petición (X-Request-Id)
dc logs caddy | tail                   # accesos y certificados
dc ps
```

Los logs rotan (10 MB × 5 por contenedor). Un 500 muestra al usuario un id: se busca en `dc logs api`. Auditoría de uso en la tabla `auditoria` (usuario, ruta, código, IP, evento).

**Subida de archivos de Radiología (tope de 10 MB).** La API acepta como máximo 10 MB (más 1 KB de holgura) en la subida del cuadro mensual y responde 413 «El archivo pasa de 10 MB.» si lo supera; el resto de las peticiones tienen tope de 1 MB. El `Caddyfile` no fija `request_body max_size`, así que Caddy deja pasar cualquier tamaño y el límite lo pone solo la API. Si algún día se agrega un límite en Caddy, debe ser ≥ 11 MB para la ruta de subida (`/api/areas/*/archivos`) o el usuario verá un 413 sin el mensaje de la aplicación. Un proxy o firewall corporativo con tope menor también cortaría la subida: probarla desde un PC de la clínica (§8). La API exige `Content-Length` en las escrituras (rechaza `chunked`): no usar herramientas que suban en trozos.

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
- [ ] 👤 Generar el par `age`, instalar la pública, guardar la privada fuera del servidor (§4).
- [ ] 👤 Programar el cron del respaldo, copiarlo fuera del servidor y probar una restauración con el respaldo real.
- [ ] 👤 Firmar el acuerdo de tratamiento (`docs/ACUERDO_TRATAMIENTO.md`) con la región y la transferencia escritas.
- [ ] 👤 Probar el acceso desde un PC de la clínica (red, certificado, bloqueo por proxy o firewall corporativo).
- [ ] 👤 Instalar los escáneres de seguridad (Gitleaks, Semgrep, OSV-Scanner) y repetir la auditoría; aceptar por escrito los hallazgos no corregidos (`docs/seguridad-hallazgos.md`).
- [ ] 👤 Capacitación del personal y 2–4 semanas en paralelo con el proceso actual; publicar un mes real desde la web.
- [ ] 👤 Decidir el retiro de Qt y la etiqueta `qt-final` (decisión 3 de §10 del plan).
