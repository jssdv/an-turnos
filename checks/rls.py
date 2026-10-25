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


def main(argv):
    esquema = argv[argv.index("--esquema") + 1] if "--esquema" in argv else "public"
    with psycopg.connect(os.environ["AN_PG_URL"]) as c:
        filas = c.execute(CONSULTA, (esquema,)).fetchall()
    malas = [f"{t}: sin RLS activado, forzado o política" for t, activo, forzado, politica in filas if not (activo and forzado and politica)]
    if not filas:
        malas.append(f"esquema {esquema}: no hay tablas con clinica_id (¿migraciones sin aplicar?)")
    for m in malas:
        print(m, file=sys.stderr)
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
