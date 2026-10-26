#!/usr/bin/env bash
# Levanta la web en local con datos de demo: base, migraciones, datos, API, trabajador y front. Ctrl+C lo apaga todo.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
SU=postgresql://an:an_dev@127.0.0.1:5433/an
docker compose up -d --wait db
AN_PG_URL=$SU $PY -m an.web.esquema
AN_PG_URL=$SU PYTHONPATH=. $PY web/sembrar_demo.py > /dev/null
export AN_PG_URL="$SU?options=-csearch_path%3Df4_demo" AN_ROL=an_app AN_ORIGEN=http://localhost:5173
trap 'kill 0' EXIT
.venv/bin/uvicorn an.web.app:crear_app --factory &
$PY -m an.web.trabajador &
cd web && { [ -d node_modules ] || npm ci; } && echo "Abre http://localhost:5173  ·  editor@demo.co / clave-larga-1" && npm run dev
