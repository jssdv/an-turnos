-- Una línea `tabla|filas|md5` por tabla del esquema :esquema (psql -v esquema=public -At -f cifras.sql). Debe correr como el rol dueño
-- (las tablas tienen RLS forzada: sin BYPASSRLS contaría cero filas). Sirve para comprobar que un respaldo restaurado trae los mismos datos.
SELECT t.tablename || '|' ||
       (xpath('/row/n/text()', query_to_xml(format('SELECT count(*) AS n FROM %I.%I', t.schemaname, t.tablename), false, true, '')))[1]::text || '|' ||
       (xpath('/row/h/text()', query_to_xml(format('SELECT coalesce(md5(string_agg(x::text, '''' ORDER BY x::text COLLATE "C")), ''-'') AS h FROM %I.%I x', t.schemaname, t.tablename), false, true, '')))[1]::text
FROM pg_tables t
WHERE t.schemaname = :'esquema'
ORDER BY t.tablename;
