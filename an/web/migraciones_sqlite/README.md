# Migraciones SQLite (entregable)

- La base de esta carpeta es `../esquema_sqlite.sql`, que equivale a la versión 12; la 013 agrega `puesto_fijo_mitad`; la 014 saca las tablas de área
  a `area_<id>.db` (antes del SQL, `esquema._separar_areas` copia las filas de cada área a su archivo) y deja `trabajo` sin clave foránea a `periodo`.
- Los archivos de área tienen su propia cadena: `../esquema_area_sqlite.sql` (versión 1) y `../migraciones_area/NNN_nombre.sql` desde 002,
  con las mismas reglas; `esquema.aplicar_sqlite` las aplica a todos los `area_*.db` de la carpeta.
- Cada migración es `NNN_nombre.sql` con NNN = 013, 014… en orden. Se aplica una sola vez.
- El archivo es SQL de SQLite, sin `BEGIN`/`COMMIT`: el código lo envuelve en una transacción y
  agrega `PRAGMA user_version = NNN`. Si una sentencia falla, no queda nada a medias.
- Una migración publicada no se edita: se agrega otra.
- Antes de aplicar cualquier migración, la base se copia a `Documents/An-respaldos` (ver `../entregable.py`).
- Las migraciones de PostgreSQL (`../migraciones/`) son otra cadena: no se traducen una a una.
