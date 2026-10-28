-- Los exportes ya no se guardan: uno nuevo borra los anteriores del periodo y cada descarga borra el archivo.
DO $$
BEGIN
  EXECUTE 'GRANT DELETE ON exporte TO an_app';
END $$;
