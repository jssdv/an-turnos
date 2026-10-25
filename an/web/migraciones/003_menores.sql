-- Purga de sesiones vencidas e intentos viejos, y la aplicación no toca esquema_version.
DO $$
DECLARE sp text := format('SET search_path = %I, pg_temp', current_schema());
BEGIN
  EXECUTE 'CREATE FUNCTION app_purgar() RETURNS void LANGUAGE sql SECURITY DEFINER ' || sp || ' AS $f$
             DELETE FROM sesion WHERE ultima < now() - interval ''35 minutes'' OR creada < now() - interval ''12 hours'';
             DELETE FROM intento_login WHERE fecha < now() - interval ''1 day'' $f$';
  EXECUTE format('REVOKE ALL ON FUNCTION app_purgar() FROM PUBLIC');
  EXECUTE format('GRANT EXECUTE ON FUNCTION app_purgar() TO an_app');
  EXECUTE format('REVOKE ALL ON esquema_version FROM an_app');
END $$;
