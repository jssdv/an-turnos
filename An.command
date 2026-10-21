#!/bin/bash
# An~: abre la app en el Mac (doble clic). La primera vez prepara su entorno de Python (.venv).
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "Preparando la app por primera vez (2-3 minutos)…"
  python3 -m venv .venv && .venv/bin/pip install -q PySide6-Essentials openpyxl ortools || { read -p "Error al preparar. Enter para salir."; exit 1; }
fi
exec .venv/bin/python app.py
