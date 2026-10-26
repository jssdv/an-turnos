/** Fechas ISO sin zona horaria: todo se calcula en UTC para que el huso del navegador no mueva un día. */
const LETRAS = ["D", "L", "M", "M", "J", "V", "S"];
const NOMBRES = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];

export interface DiaCuadro {
  fecha: string;
  n: number;
  letra: string;
  nombre: string;
  gris: boolean;
}

const aUTC = (iso: string) => new Date(`${iso}T00:00:00Z`);
const aISO = (d: Date) => d.toISOString().slice(0, 10);

export function dias(clave: string): DiaCuadro[] {
  const [ini, fin] = clave.split("/");
  const out: DiaCuadro[] = [];
  for (let d = aUTC(ini); aISO(d) <= fin; d = new Date(d.getTime() + 86_400_000)) {
    const s = d.getUTCDay();
    out.push({ fecha: aISO(d), n: d.getUTCDate(), letra: LETRAS[s], nombre: NOMBRES[s], gris: s === 0 });
  }
  return out;
}

const fmt = (iso: string, o: Intl.DateTimeFormatOptions) => new Intl.DateTimeFormat("es-CO", { timeZone: "UTC", ...o }).format(aUTC(iso));
const cap = (s: string) => s.charAt(0).toUpperCase() + s.slice(1);

/** «Octubre 2026» si el periodo es un mes calendario; si no, «5 oct – 4 nov 2026». */
export function nombrePeriodo(clave: string) {
  const [ini, fin] = clave.split("/");
  const finMes = aISO(new Date(Date.UTC(+ini.slice(0, 4), +ini.slice(5, 7), 0)));
  if (ini.endsWith("-01") && fin === finMes) return cap(fmt(ini, { month: "long", year: "numeric" }));
  return `${fmt(ini, { day: "numeric", month: "short" })} – ${fmt(fin, { day: "numeric", month: "short", year: "numeric" })}`;
}

export const mesDe = (clave: string) => fmt(clave.split("/")[0], { month: "long" });
export const fechaCorta = (iso: string) => fmt(iso, { weekday: "short", day: "numeric", month: "short" });
