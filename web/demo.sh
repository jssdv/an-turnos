#!/usr/bin/env bash
# Levanta la web en local con datos de demo (base SQLite en web/.demo): datos, API con su trabajador y front. Ctrl+C lo apaga todo.
set -e
cd "$(dirname "$0")/.."
PY=.venv/bin/python
export AN_BASE=$(PYTHONPATH=. $PY web/sembrar_demo.py) AN_ORIGEN=http://localhost:5173
trap 'kill 0' EXIT
PYTHONPATH=. $PY - <<'PY' &
import threading, uvicorn
from an.web import conexion
from an.web.app import crear_app
from an.web.trabajador import Trabajador
pool = conexion.abrir_pool()
threading.Thread(target=Trabajador(pool).servir, args=(threading.Event(),), daemon=True).start()
uvicorn.run(crear_app(pool), host="127.0.0.1", port=8000, log_level="warning")
PY
cd web && { [ -d node_modules ] || npm ci; } && echo "Abre http://localhost:5173  ·  editor@demo.co / clave-larga-1" && npm run dev
