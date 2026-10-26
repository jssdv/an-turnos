"""Escribe el /openapi.json de la API en stdout sin base de datos (entrada de `npm run tipos` en web/)."""
import json

from an.web.app import crear_app

print(json.dumps(crear_app(pool=object()).openapi(), indent=2, ensure_ascii=False))
