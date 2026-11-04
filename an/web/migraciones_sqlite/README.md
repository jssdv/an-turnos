# Migraciones SQLite (entregable)

- La base de esta carpeta es `../esquema_sqlite.sql`, que equivale a la versión 12; la 013 agrega `puesto_fijo_mitad`.
- Cada migración es `NNN_nombre.sql` con NNN = 013, 014… en orden. Se aplica una sola vez.
- El archivo es SQL de SQLite, sin `BEGIN`/`COMMIT`: el código lo envuelve en una transacción y
  agrega `PRAGMA user_version = NNN`. Si una sentencia falla, no queda nada a medias.
- Una migración publicada no se edita: se agrega otra.
- Antes de aplicar cualquier migración, la base se copia a `Documents/An-respaldos` (ver `../entregable.py`).
- Las migraciones de PostgreSQL (`../migraciones/`) son otra cadena: no se traducen una a una.
