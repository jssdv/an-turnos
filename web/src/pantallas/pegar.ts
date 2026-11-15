/** Lee personal pegado desde Excel (o texto): una persona por línea; columnas separadas por tabulador o punto y coma:
 * nombre, horas por semana (opcional, 42) y dedicación (opcional: 100, «50 %» o 0,5). Sin dependencias: lo prueba `pruebas/pegar.test.ts`. */
export interface PersonaPegada { nombre: string; horas_sem: number; pct: number }
export interface Lectura { personas: PersonaPegada[]; repetidas: string[]; errores: string[] }

const numero = (s: string) => Number(s.replace("%", "").trim().replace(",", "."));
const clave = (s: string) => s.normalize("NFD").replace(/\p{Diacritic}/gu, "").toLowerCase().replace(/\s+/g, " ").trim();

export function leerLista(texto: string, existentes: string[] = []): Lectura {
  const ya = new Set(existentes.map(clave));
  const out: Lectura = { personas: [], repetidas: [], errores: [] };
  texto.split(/\r?\n/).forEach((linea, i) => {
    const [nombre = "", h = "", p = ""] = linea.split(/\t|;/).map((x) => x.trim());
    if (!nombre) return;
    if (i === 0 && /^nombres?$/i.test(nombre)) return; // encabezado copiado con la tabla
    const horas = h ? numero(h) : 42;
    let pct = p ? numero(p) : 100;
    if (p && pct > 0 && pct <= 1 && !p.includes("%")) pct *= 100; // 0,5 = media jornada
    if (!(horas > 0 && horas <= 84)) return void out.errores.push(`Línea ${i + 1} (${nombre}): horas por semana «${h}» debe ir de 1 a 84.`);
    if (!(pct > 0 && pct <= 100)) return void out.errores.push(`Línea ${i + 1} (${nombre}): dedicación «${p}» debe ir de 1 a 100 %.`);
    if (nombre.length > 120) return void out.errores.push(`Línea ${i + 1}: el nombre pasa de 120 caracteres.`);
    if (ya.has(clave(nombre))) return void out.repetidas.push(nombre);
    ya.add(clave(nombre));
    out.personas.push({ nombre: nombre.replace(/\s+/g, " "), horas_sem: horas, pct: Math.round(pct) / 100 });
  });
  return out;
}
