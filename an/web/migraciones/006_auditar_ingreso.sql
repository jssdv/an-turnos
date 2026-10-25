-- Auditoría de ingresos fallidos/bloqueados de usuarios que existen (la clínica sale del usuario; un correo inexistente no se audita:
-- ya queda en intento_login). Nunca recibe la contraseña ni el cuerpo.
DO $$
DECLARE sp text := format('SET search_path = %I, pg_temp', current_schema());
BEGIN
  EXECUTE 'CREATE FUNCTION app_auditar_ingreso(p_correo text, p_ip text, p_evento text, p_codigo int) RETURNS void LANGUAGE sql SECURITY DEFINER ' || sp || ' AS $f$
             INSERT INTO auditoria (usuario_id, correo, metodo, ruta, codigo, ip, evento, clinica_id)
             SELECT u.id, u.correo, ''POST'', ''/api/auth/entrar'', p_codigo, p_ip, p_evento, u.clinica_id FROM usuario u WHERE u.correo = lower(p_correo) $f$';
  EXECUTE format('REVOKE ALL ON FUNCTION app_auditar_ingreso(text, text, text, int) FROM PUBLIC');
  EXECUTE format('GRANT EXECUTE ON FUNCTION app_auditar_ingreso(text, text, text, int) TO an_app');
END $$;
