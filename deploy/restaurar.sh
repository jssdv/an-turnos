#!/bin/sh
# Restaura un respaldo en un PostgreSQL 16 DESECHABLE (contenedor local) y compara las cifras con las del respaldo.
# Uso: deploy/restaurar.sh <an-….dump.age> <archivo con la clave privada age> [--conservar]
#   AN_ESQUEMA (por defecto public) = esquema cuyas cifras se comparan. Sale 0 solo si todas coinciden.
# No toca la base real: sirve igual para probar el respaldo en cualquier máquina con Docker. --conservar deja el contenedor para inspeccionarlo.
set -eu
[ $# -ge 2 ] || { echo "Uso: $0 <archivo.dump.age> <identidad.key> [--conservar]" >&2; exit 2; }
archivo=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
clave=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
cifras="${archivo%.dump.age}.cifras"
raiz=$(cd "$(dirname "$0")" && pwd)
[ -f "$archivo" ] && [ -f "$cifras" ] && [ -f "$clave" ] || { echo "Error: faltan el respaldo, su .cifras o la clave" >&2; exit 2; }
docker build -q -t an-respaldo:local "$raiz/respaldo" > /dev/null
nombre="an_restaurar_$$"
[ "${3:-}" = "--conservar" ] || trap 'docker rm -f "$nombre" > /dev/null 2>&1 || true' EXIT
docker run -d --name "$nombre" -e POSTGRES_USER=an_admin -e POSTGRES_PASSWORD=desechable -e POSTGRES_DB=an \
  -v "$archivo:/in/respaldo.dump.age:ro" -v "$clave:/in/identidad.key:ro" -v "$raiz/cifras.sql:/cifras.sql:ro" an-respaldo:local > /dev/null
i=0
until docker exec "$nombre" pg_isready -q -h 127.0.0.1 -U an_admin -d an; do
  i=$((i + 1)); [ $i -lt 60 ] || { echo "Error: el PostgreSQL desechable no arrancó" >&2; exit 1; }
  sleep 1
done
docker exec "$nombre" psql -U an_admin -d an -q -c "CREATE ROLE an_app"  # las migraciones dan permisos a este rol; debe existir
docker exec "$nombre" sh -c 'age -d -i /in/identidad.key /in/respaldo.dump.age | pg_restore -U an_admin -d an --exit-on-error'
docker exec "$nombre" psql -U an_admin -d an -At -v ON_ERROR_STOP=1 -v esquema="${AN_ESQUEMA:-public}" -f /cifras.sql > "${TMPDIR:-/tmp}/an_cifras_$$.txt"
if diff "$cifras" "${TMPDIR:-/tmp}/an_cifras_$$.txt" > /dev/null; then
  echo "Restauración correcta: $(wc -l < "$cifras" | tr -d ' ') tablas con las mismas cifras."
  rm -f "${TMPDIR:-/tmp}/an_cifras_$$.txt"
else
  echo "Error: las cifras de la restauración difieren del respaldo:" >&2
  diff "$cifras" "${TMPDIR:-/tmp}/an_cifras_$$.txt" >&2 || true
  rm -f "${TMPDIR:-/tmp}/an_cifras_$$.txt"
  exit 1
fi
