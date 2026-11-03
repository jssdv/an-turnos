-- Eliminar un periodo abierto: la API borra su cola de trabajos (trabajo) y su cuadro. Antes solo tenía SELECT, INSERT y UPDATE.
DO $$
BEGIN
  EXECUTE 'GRANT DELETE ON trabajo TO an_app';
END $$;
