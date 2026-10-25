"""Comprueba que toda tabla con clinica_id tenga RLS activado y forzado, y al menos una política. Sale 1 si alguna falla.
Uso: AN_PG_URL=… python checks/rls.py [--esquema public]"""
import os
import sys

import psycopg

CONSULTA = """
select c.relname, c.relrowsecurity, c.relforcerowsecurity, exists (select 1 from pg_policy p where p.polrelid = c.oid)
from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = %s and c.relkind = 'r' and exists
  (select 1 from pg_attribute a where a.attrelid = c.oid and a.attname = 'clinica_id' and not a.attisdropped)
order by 1"""


SIN_CLINICA = {"clinica", "esquema_version", "sesion", "intento_login"}  # tablas que no son de una clínica o que solo tocan funciones
CONSULTA_SIN_CLINICA = """
select c.relname from pg_class c join pg_namespace n on n.oid = c.relnamespace
where n.nspname = %s and c.relkind = 'r' and not exists
  (select 1 from pg_attribute a where a.attrelid = c.oid and a.attname = 'clinica_id' and not a.attisdropped)"""
CONSULTA_POLITICAS = """
select p.polname from pg_policy p join pg_class c on c.oid = p.polrelid join pg_namespace n on n.oid = c.relnamespace
where n.nspname = %s and lower(coalesce(pg_get_expr(p.polqual, p.polrelid), 'true')) in ('true', '(true)')"""
CONSULTA_FUNCIONES = """
select p.proname from pg_proc p join pg_namespace n on n.oid = p.pronamespace
where n.nspname = %s and p.prosecdef and (p.proacl is null or exists
  (select 1 from aclexplode(p.proacl) a where a.grantee = 0 and a.privilege_type = 'EXECUTE'))"""


def main(argv):
    esquema = argv[argv.index("--esquema") + 1] if "--esquema" in argv else "public"
    with psycopg.connect(os.environ["AN_PG_URL"]) as c:
        filas = c.execute(CONSULTA, (esquema,)).fetchall()
        sin_clinica = [r[0] for r in c.execute(CONSULTA_SIN_CLINICA, (esquema,)) if r[0] not in SIN_CLINICA]
        abiertas = [r[0] for r in c.execute(CONSULTA_POLITICAS, (esquema,))]
        publicas = [r[0] for r in c.execute(CONSULTA_FUNCIONES, (esquema,))]
    malas = [f"{t}: sin RLS activado, forzado o política" for t, activo, forzado, politica in filas if not (activo and forzado and politica)]
    malas += [f"{t}: tabla sin clinica_id (si no es de una clínica, agrégala a SIN_CLINICA)" for t in sin_clinica]
    malas += [f"política {p}: USING (true) deja ver todo" for p in abiertas]
    malas += [f"función {f}: SECURITY DEFINER ejecutable por PUBLIC (falta REVOKE … FROM PUBLIC)" for f in publicas]
    if not filas:
        malas.append(f"esquema {esquema}: no hay tablas con clinica_id (¿migraciones sin aplicar?)")
    for m in malas:
        print(m, file=sys.stderr)
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
