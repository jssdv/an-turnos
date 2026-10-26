-- Cierra las sesiones de un usuario de la clínica del alcance (el administrador desactiva o restablece la clave de otro usuario).
-- `sesion` no se toca directamente desde la aplicación: solo por funciones SECURITY DEFINER.
DO $$
DECLARE sp text := format('SET search_path = %I, pg_temp', current_schema());
BEGIN
  EXECUTE 'CREATE FUNCTION app_cerrar_sesiones(p_usuario bigint) RETURNS void LANGUAGE sql SECURITY DEFINER ' || sp || ' AS $f$
             DELETE FROM sesion WHERE usuario_id = p_usuario
               AND usuario_id IN (SELECT id FROM usuario WHERE clinica_id = current_setting(''app.clinica'')::bigint) $f$';
  EXECUTE format('REVOKE ALL ON FUNCTION app_cerrar_sesiones(bigint) FROM PUBLIC');
  EXECUTE format('GRANT EXECUTE ON FUNCTION app_cerrar_sesiones(bigint) TO an_app');
END $$;
