#!/bin/sh
# Prueba de punta a punta del respaldo con datos sintéticos (web/sembrar_demo.py), todo en contenedores desechables:
# siembra → respaldar.sh → restaurar.sh (debe coincidir) → un respaldo manipulado y unas cifras alteradas deben FALLAR.
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
sed -n 's/^Public key: //p' "$tmp/pub.txt" > "$tmp/recipients"; grep -q '^age1' "$tmp/recipients"
docker run --rm --network "$red" -e PGHOST="$pg" -e PGUSER=an_admin -e PGPASSWORD=prueba -e PGDATABASE=an -e AN_ESQUEMA=prb_demo \
  -v "$tmp/respaldos:/respaldos" -v "$tmp/recipients:/recipients:ro" -v "$raiz/deploy/cifras.sql:/cifras.sql:ro" -v "$raiz/deploy/respaldar.sh:/respaldar.sh:ro" \
  an-respaldo:local sh /respaldar.sh
archivo=$(ls "$tmp"/respaldos/an-*.dump.age)
echo "--- restauración (debe coincidir)"
AN_ESQUEMA=prb_demo "$raiz/deploy/restaurar.sh" "$archivo" "$tmp/id.key"
echo "--- el respaldo no queda en claro"
! grep -aq "Persona 01" "$archivo"
echo "--- respaldo manipulado (debe fallar)"
cp "$archivo" "$tmp/malo.dump.age"; cp "${archivo%.dump.age}.cifras" "$tmp/malo.cifras"
printf 'X' | dd of="$tmp/malo.dump.age" bs=1 seek=200 conv=notrunc 2> /dev/null
if AN_ESQUEMA=prb_demo "$raiz/deploy/restaurar.sh" "$tmp/malo.dump.age" "$tmp/id.key" > /dev/null 2>&1; then echo "FALLO: aceptó un respaldo manipulado"; exit 1; fi
echo "--- cifras alteradas (debe fallar)"
sed -i.bak '1s/|[^|]*$/|0000/' "$tmp/malo.cifras"; cp "$archivo" "$tmp/malo.dump.age"
if AN_ESQUEMA=prb_demo "$raiz/deploy/restaurar.sh" "$tmp/malo.dump.age" "$tmp/id.key" > /dev/null 2>&1; then echo "FALLO: no notó las cifras distintas"; exit 1; fi
echo "--- sin clave pública (debe fallar)"
if docker run --rm --network "$red" -e PGHOST="$pg" -e PGUSER=an_admin -e PGPASSWORD=prueba -e PGDATABASE=an -e AN_ESQUEMA=prb_demo \
  -v "$tmp/respaldos:/respaldos" -v "$tmp/id.key:/recipients:ro" -v "$raiz/deploy/cifras.sql:/cifras.sql:ro" -v "$raiz/deploy/respaldar.sh:/respaldar.sh:ro" \
  an-respaldo:local sh /respaldar.sh > /dev/null 2>&1; then echo "FALLO: respaldó sin clave pública"; exit 1; fi
echo "OK"
