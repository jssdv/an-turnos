"""Reglas del código del servidor (docs/REGLAS_AUTOMATICAS.md): toda ruta declara permiso de área, nada de SQL armado con f-strings
y subprocess solo en el trabajador (an/web; la interfaz Qt puede abrir carpetas). Un SQL con partes constantes se marca con `# sql-ok: motivo` en su línea.
Uso: python checks/reglas.py [--raiz DIR]. Sale 1 si algo falla."""
import ast
import re
import sys
from pathlib import Path

PERMISOS = {"contexto_area", "usuario_actual", "usuario_permitido_cambiar"}
SIN_PERMISO = {"entrar"}  # el ingreso no tiene sesión todavía
VERBOS = {"get", "post", "put", "patch", "delete"}
SQL = re.compile(r"\b(SELECT\s.+\sFROM|INSERT\s+INTO|UPDATE\s.+\sSET|DELETE\s+FROM)\b", re.I | re.S)


def _es_ruta(f):
    return any(isinstance(d, ast.Call) and isinstance(d.func, ast.Attribute) and d.func.attr in VERBOS
               and getattr(d.func.value, "id", "") == "router" for d in f.decorator_list)


def _depende(f):
    por_defecto = f.args.defaults + [d for d in f.args.kw_defaults if d]
    return any(isinstance(d, ast.Call) and getattr(d.func, "id", "") == "Depends" and d.args and getattr(d.args[0], "id", "") in PERMISOS
               for d in por_defecto)


def _texto_sql(n):
    """¿Es una cadena armada (f-string, % o .format) con una sentencia SQL?"""
    if isinstance(n, ast.JoinedStr):
        constantes = "".join(v.value for v in n.values if isinstance(v, ast.Constant) and isinstance(v.value, str))
        return any(isinstance(v, ast.FormattedValue) for v in n.values) and bool(SQL.search(constantes))
    if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Mod) and isinstance(n.left, ast.Constant) and isinstance(n.left.value, str):
        return bool(SQL.search(n.left.value))
    if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "format" and isinstance(n.func.value, ast.Constant) \
            and isinstance(n.func.value.value, str):
        return bool(SQL.search(n.func.value.value))
    return False


def revisar(raiz):
    malas = []
    for ruta in sorted((raiz / "an").rglob("*.py")):
        rel = ruta.relative_to(raiz)
        texto = ruta.read_text(encoding="utf-8")
        lineas = texto.splitlines()
        arbol = ast.parse(texto)
        for n in ast.walk(arbol):
            if rel.parent.as_posix() == "an/web" and rel.name.startswith("rutas_") and isinstance(n, ast.FunctionDef) and _es_ruta(n):
                if n.name not in SIN_PERMISO and not _depende(n):
                    malas.append(f"{rel}:{n.lineno}: la ruta «{n.name}» no declara permiso de área (Depends de contexto_area o usuario_actual)")
            if rel.parts[1] in ("web", "turnos") and _texto_sql(n) and "sql-ok" not in lineas[n.lineno - 1]:
                malas.append(f"{rel}:{n.lineno}: SQL armado con f-string, % o format; usa parámetros (o marca «# sql-ok: motivo»)")
            if isinstance(n, (ast.Import, ast.ImportFrom)) and rel.parts[1] == "web" and rel.as_posix() != "an/web/trabajador.py":
                nombres = [a.name for a in n.names] + ([n.module] if isinstance(n, ast.ImportFrom) and n.module else [])
                if any(x.split(".")[0] == "subprocess" for x in nombres):
                    malas.append(f"{rel}:{n.lineno}: subprocess solo se permite en an/web/trabajador.py")
    return malas


def main(argv):
    raiz = Path(argv[argv.index("--raiz") + 1]) if "--raiz" in argv else Path(__file__).resolve().parents[1]
    malas = revisar(raiz)
    for m in malas:
        print(m, file=sys.stderr)
    return 1 if malas else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
