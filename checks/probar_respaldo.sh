#!/bin/sh
# Prueba de punta a punta del respaldo con datos sintéticos (web/sembrar_demo.py), todo en contenedores desechables:
# siembra → respaldar.sh (firma) → restaurar.sh (verifica la firma y coincide) → un respaldo manipulado, sin firma, con cifras alteradas o firmado con otra clave deben FALLAR.
# Necesita ssh-keygen en el equipo (el de OpenSSH).
# Uso: PYTHON=/ruta/al/python checks/probar_respaldo.sh   (necesita Docker; no toca ninguna base real)
set -eu
PYTHON=${PYTHON:-python3}
raiz=$(cd "$(dirname "$0")/.." && pwd)
tmp=$(mktemp -d)
red=an_prb_red_$$
pg=an_prb_pg_$$
limpiar() { docker rm -f "$pg" > /dev/null 2>&1 || true; docker network rm "$red" > /dev/null 2>&1 || true; rm -rf "$tmp"; }
trap limpiar EXIT
docker build -q -t an-respaldo:local "$raiz/deploy/respaldo" > /dev/null
docker network create "$red" > /dev/null
docker run -d --name "$pg" --network "$red" -e POSTGRES_USER=an_admin -e POSTGRES_PASSWORD=prueba -e POSTGRES_DB=an -p 127.0.0.1::5432 postgres:16 > /dev/null
puerto=$(docker port "$pg" 5432/tcp | head -1 | sed 's/.*://')
i=0; until docker exec "$pg" pg_isready -q -h 127.0.0.1 -U an_admin -d an; do i=$((i + 1)); [ $i -lt 60 ] || exit 1; sleep 1; done
AN_PG_URL="postgresql://an_admin:prueba@127.0.0.1:$puerto/an" "$PYTHON" "$raiz/web/sembrar_demo.py" prb_demo > /dev/null 2>&1
mkdir "$tmp/respaldos"
docker run --rm an-respaldo:local age-keygen > "$tmp/id.key" 2> "$tmp/pub.txt"
ssh-keygen -q -t ed25519 -N '' -C an-respaldo -f "$tmp/firma.key"; ssh-keygen -q -t ed25519 -N '' -C otra -f "$tmp/otra.key"
sed -n 's/^Public key: //p' "$tmp/pub.txt" > "$tmp/recipients"; grep -q '^age1' "$tmp/recipients"
docker run --rm --network "$red" -e PGHOST="$pg" -e PGUSER=an_admin -e PGPASSWORD=prueba -e PGDATABASE=an -e AN_ESQUEMA=prb_demo \
  -v "$tmp/respaldos:/respaldos" -v "$tmp/recipients:/recipients:ro" -v "$raiz/deploy/cifras.sql:/cifras.sql:ro" -v "$raiz/deploy/respaldar.sh:/respaldar.sh:ro" -v "$tmp/firma.key:/firma.key:ro" \
  an-respaldo:local sh /respaldar.sh
archivo=$(ls "$tmp"/respaldos/an-*.dump.age)
echo "--- restauración (debe coincidir)"
AN_ESQUEMA=prb_demo "$raiz/deploy/restaurar.sh" "$archivo" "$tmp/id.key" "$tmp/firma.key.pub"
echo "--- el respaldo no queda en claro"
! grep -aq "Persona 01" "$archivo"
base=${archivo%.dump.age}
# copia el respaldo firmado a $tmp/m/ y corre restaurar.sh con la pública dada: debe salir ≠ 0
rechaza() {  # $1 = descripción, $2 = pública de firma
  if AN_ESQUEMA=prb_demo "$raiz/deploy/restaurar.sh" "$tmp/m/$(basename "$archivo")" "$tmp/id.key" "$2" > /dev/null 2>&1; then echo "FALLO: $1"; exit 1; fi
}
copia() { rm -rf "$tmp/m"; mkdir "$tmp/m"; cp "$base".* "$tmp/m/"; }
echo "--- respaldo manipulado (debe fallar)"
copia; printf 'X' | dd of="$tmp/m/$(basename "$archivo")" bs=1 seek=200 conv=notrunc 2> /dev/null
rechaza "aceptó un respaldo manipulado" "$tmp/firma.key.pub"
echo "--- respaldo sin firma (debe fallar)"
copia; rm "$tmp/m/"*.firmas "$tmp/m/"*.firmas.sig
rechaza "aceptó un respaldo sin firma" "$tmp/firma.key.pub"
echo "--- cifras alteradas (debe fallar)"
copia; sed -i.bak '1s/|[^|]*$/|0000/' "$tmp/m/$(basename "$base").cifras"; rm "$tmp/m/"*.bak
rechaza "no notó las cifras distintas" "$tmp/firma.key.pub"
echo "--- firmas reescritas y firmadas con otra clave (debe fallar)"
copia; rm "$tmp/m/"*.firmas.sig; ssh-keygen -q -Y sign -f "$tmp/otra.key" -n an-respaldo "$tmp/m/$(basename "$base").firmas"
rechaza "aceptó una firma de otra clave" "$tmp/firma.key.pub"
echo "--- sin clave de firma al respaldar (debe fallar)"
if docker run --rm --network "$red" -e PGHOST="$pg" -e PGUSER=an_admin -e PGPASSWORD=prueba -e PGDATABASE=an -e AN_ESQUEMA=prb_demo \
  -v "$tmp/respaldos:/respaldos" -v "$tmp/recipients:/recipients:ro" -v "$raiz/deploy/cifras.sql:/cifras.sql:ro" -v "$raiz/deploy/respaldar.sh:/respaldar.sh:ro" \
  an-respaldo:local sh /respaldar.sh > /dev/null 2>&1; then echo "FALLO: respaldó sin clave de firma"; exit 1; fi
echo "--- sin clave pública (debe fallar)"
if docker run --rm --network "$red" -e PGHOST="$pg" -e PGUSER=an_admin -e PGPASSWORD=prueba -e PGDATABASE=an -e AN_ESQUEMA=prb_demo \
  -v "$tmp/respaldos:/respaldos" -v "$tmp/id.key:/recipients:ro" -v "$raiz/deploy/cifras.sql:/cifras.sql:ro" -v "$raiz/deploy/respaldar.sh:/respaldar.sh:ro" -v "$tmp/firma.key:/firma.key:ro" \
  an-respaldo:local sh /respaldar.sh > /dev/null 2>&1; then echo "FALLO: respaldó sin clave pública"; exit 1; fi
echo "OK"
