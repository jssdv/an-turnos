#!/usr/bin/env bash
# Arranca An (versión SQLite) en macOS con doble clic: prepara el entorno la primera vez y abre la ventana.
# Datos: ~/Library/Application Support/AnTurnos/an.db · respaldos al cerrar: ~/Documents/An-respaldos
set -e
cd "$(dirname "$0")/.."
VENV="${VENV:-.venv}"
if [ ! -x "$VENV/bin/python" ]; then
  echo "Primera vez: creando el entorno (unos minutos)…"
  python3 -m venv "$VENV"
  "$VENV/bin/pip" install -q -r requirements.txt -r requirements-web.txt
fi
if [ ! -f web/dist/index.html ]; then
  echo "Primera vez: construyendo la interfaz…"
  (cd web && npm ci --silent && npm run build --silent)
fi
export AN_DATOS="${AN_DATOS:-$HOME/Library/Application Support/AnTurnos}"
echo "Datos en: $AN_DATOS"
exec "$VENV/bin/python" -m an.web.entregable
