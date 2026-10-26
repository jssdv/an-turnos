#!/bin/sh
# Respaldo cifrado de la base: pg_dump -Fc | age -R <claves públicas>  →  an-AAAAMMDD-HHMMSS.dump.age + .cifras en /respaldos.
# Corre en el contenedor `respaldo` (docker-compose.prod.yml, perfil herramientas). La clave PRIVADA no está aquí: sin ella no se restaura.
# Si el contenido cambia mientras se respalda (escrituras), reintenta; sale ≠ 0 en cualquier fallo y nunca deja un respaldo a medias.
set -eu
set -o pipefail
DEST=${AN_RESPALDO_DESTINO_DIR:-/respaldos}
REC=${AN_RESPALDO_RECIPIENTS_ARCHIVO:-/recipients}
ESQUEMA=${AN_ESQUEMA:-public}
CIFRAS=${AN_CIFRAS_SQL:-/cifras.sql}
[ -s "$REC" ] || { echo "Error: no hay claves públicas age en $REC" >&2; exit 1; }
grep -q '^age1' "$REC" || { echo "Error: $REC no tiene una clave pública age (age1…)" >&2; exit 1; }
base="$DEST/an-$(date -u +%Y%m%d-%H%M%S)"
trap 'rm -f "$base".*.tmp' EXIT
for intento in 1 2 3; do
  psql -At -v ON_ERROR_STOP=1 -v esquema="$ESQUEMA" -f "$CIFRAS" > "$base.cifras.tmp"
  pg_dump -Fc | age -R "$REC" -o "$base.dump.age.tmp"
  psql -At -v ON_ERROR_STOP=1 -v esquema="$ESQUEMA" -f "$CIFRAS" > "$base.despues.tmp"
  if cmp -s "$base.cifras.tmp" "$base.despues.tmp"; then
    [ -s "$base.cifras.tmp" ] || { echo "Error: la base no tiene tablas en el esquema $ESQUEMA" >&2; exit 1; }
    mv "$base.dump.age.tmp" "$base.dump.age"
    mv "$base.cifras.tmp" "$base.cifras"
    find "$DEST" -maxdepth 1 -name 'an-*' -mtime +"${AN_RESPALDO_DIAS:-30}" -delete
    echo "respaldo listo: $(basename "$base").dump.age"
    exit 0
  fi
  echo "aviso: hubo escrituras durante el respaldo (intento $intento); se repite" >&2
  sleep 5
done
echo "Error: la base no dejó de cambiar durante el respaldo" >&2
exit 1
