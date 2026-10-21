#!/bin/bash
# Arma la carpeta portátil para Windows (sin instalar nada en el PC destino).
#   ./empaquetar.sh          -> dist/An.zip   (la app completa)
#   ./empaquetar.sh prueba   -> dist/PruebaPC.zip               (prueba que OR-Tools y Qt corren en el PC corporativo)
# Se corre en el Mac: baja el Python "embeddable" oficial y las librerías ya compiladas para Windows.
set -euo pipefail
cd "$(dirname "$0")"

PY_VER=3.13.16
PY_TAG=313
CACHE=.build_cache
MODO=${1:-app}
NOMBRE=$([ "$MODO" = prueba ] && echo PruebaPC || echo An)
DEST=dist/$NOMBRE

mkdir -p "$CACHE/wheels"
ZIP="$CACHE/python-$PY_VER-embed-amd64.zip"
[ -f "$ZIP" ] || curl -fL -o "$ZIP" "https://www.python.org/ftp/python/$PY_VER/python-$PY_VER-embed-amd64.zip"
python3 -m pip download -q --dest "$CACHE/wheels" --only-binary=:all: \
  --platform win_amd64 --python-version $PY_TAG --implementation cp \
  PySide6-Essentials openpyxl ortools

rm -rf "$DEST" "dist/$NOMBRE.zip"
mkdir -p "$DEST/python/Lib/site-packages" "$DEST/app"
unzip -q "$ZIP" -d "$DEST/python"
for w in "$CACHE"/wheels/*.whl; do unzip -q -o "$w" -d "$DEST/python/Lib/site-packages"; done
# El Python embeddable ignora PYTHONPATH: las rutas se declaran en el ._pth
printf 'python%s.zip\r\n.\r\nLib\\site-packages\r\n..\\app\r\nimport site\r\n' "$PY_TAG" > "$DEST/python/python$PY_TAG._pth"

if [ "$MODO" = prueba ]; then
  cat > "$DEST/app/app.py" <<'EOF'
import sys, platform, traceback
from PySide6.QtWidgets import QApplication, QLabel, QVBoxLayout, QWidget
app = QApplication(sys.argv)
try:
    import openpyxl
    from ortools.sat.python import cp_model
    m = cp_model.CpModel(); x = m.NewBoolVar("x"); m.Add(x == 1); s = cp_model.CpSolver()
    ok = s.Solve(m) == cp_model.OPTIMAL
    texto = f"Funciona. OR-Tools resolvió un modelo de prueba: {ok}\nPython {platform.python_version()}"
except Exception:
    texto = "Falló:\n" + traceback.format_exc()
w = QWidget(); w.setWindowTitle("Prueba PC"); w.resize(520, 220)
QVBoxLayout(w).addWidget(QLabel(texto))
w.show(); sys.exit(app.exec())
EOF
else
  cp app.py dominio.py db.py reglas.py recargos.py solver.py puestos.py capacitacion.py exportar.py flujo.py "$DEST/app/"
fi
printf '@echo off\r\nstart "" "%%~dp0python\\pythonw.exe" "%%~dp0app\\app.py"\r\n' > "$DEST/$( [ "$MODO" = prueba ] && echo 'Probar' || echo 'An').bat"

(cd dist && zip -qr "$NOMBRE.zip" "$NOMBRE")
du -sh "$DEST" "dist/$NOMBRE.zip"
