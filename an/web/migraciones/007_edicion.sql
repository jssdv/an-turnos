-- Quién y cuándo cambió un periodo por última vez (lo muestra el 409 de revisión). Lo escribe la API de edición.
ALTER TABLE periodo ADD COLUMN modificado_por text, ADD COLUMN modificado_en timestamptz;
