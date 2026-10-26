#!/bin/sh
# Restaura un respaldo en un PostgreSQL 16 DESECHABLE (contenedor local) y compara las cifras con las del respaldo.
# Uso: deploy/restaurar.sh <an-….dump.age> <clave privada age> <firma.pub> [--conservar]   (correr en un equipo de confianza, nunca en el servidor)
#   Primero VERIFICA la firma (an-….firmas.sig con la clave pública de firma) y los sha256; sin firma válida no descifra ni restaura nada.
#   AN_ESQUEMA (por defecto public) = esquema cuyas cifras se comparan. Sale 0 solo si todas coinciden.
# No toca la base real: sirve igual para probar el respaldo en cualquier máquina con Docker. --conservar deja el contenedor para inspeccionarlo.
set -eu
[ $# -ge 3 ] || { echo "Uso: $0 <archivo.dump.age> <identidad.key> <firma.pub> [--conservar]" >&2; exit 2; }
archivo=$(cd "$(dirname "$1")" && pwd)/$(basename "$1")
clave=$(cd "$(dirname "$2")" && pwd)/$(basename "$2")
cifras="${archivo%.dump.age}.cifras"
firmas="${archivo%.dump.age}.firmas"
pub=$3
raiz=$(cd "$(dirname "$0")" && pwd)
[ -f "$archivo" ] && [ -f "$cifras" ] && [ -f "$clave" ] && [ -f "$pub" ] || { echo "Error: faltan el respaldo, su .cifras, la clave o la pública de firma" >&2; exit 2; }
[ -f "$firmas" ] && [ -f "$firmas.sig" ] || { echo "Error: respaldo sin firma (faltan $(basename "$firmas") y .sig); no se restaura" >&2; exit 1; }
signers=$(mktemp)
awk '{print "an-respaldo", $1, $2}' "$pub" > "$signers"
ssh-keygen -Y verify -f "$signers" -I an-respaldo -n an-respaldo -s "$firmas.sig" < "$firmas" > /dev/null 2>&1 \
  || { rm -f "$signers"; echo "Error: la firma del respaldo no es válida; no se restaura" >&2; exit 1; }
rm -f "$signers"
hash() { if command -v sha256sum > /dev/null; then sha256sum < "$1"; else shasum -a 256 < "$1"; fi | cut -d' ' -f1; }
[ "$(sed -n "s/  $(basename "$archivo")\$//p" "$firmas")" = "$(hash "$archivo")" ] && [ "$(sed -n "s/  $(basename "$cifras")\$//p" "$firmas")" = "$(hash "$cifras")" ] \
  || { echo "Error: el respaldo o su .cifras no coinciden con lo firmado; no se restaura" >&2; exit 1; }
docker build -q -t an-respaldo:local "$raiz/respaldo" > /dev/null
nombre="an_restaurar_$$"
[ "${4:-}" = "--conservar" ] || trap 'docker rm -f "$nombre" > /dev/null 2>&1 || true' EXIT
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
