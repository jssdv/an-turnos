/** Trazo SVG de una serie: x repartida de 0 a `ancho`, y de `alto` (valor 0) a 0 (valor `max`). Sin máximo, todo abajo. */
export function trazo(valores: number[], ancho: number, alto: number, max: number): string {
  const paso = valores.length > 1 ? ancho / (valores.length - 1) : 0;
  const y = (v: number) => (max > 0 ? alto - (v / max) * alto : alto);
  return valores.map((v, i) => `${i ? "L" : "M"}${+(i * paso).toFixed(1)},${+y(v).toFixed(1)}`).join(" ");
}

/** Color de una celda del mapa de cobertura: `v` = personas que faltan en promedio (≥ 0) y `s` = las que sobran por encima de
 *  obligatoria + deseable; intensidad relativa al más alto de cada uno. Menos de 0,05 personas cuenta como nada. Faltar pesa más que sobrar. */
export function tonoMapa(v: number | null, max: number, s = 0, maxS = 0): { tono: "falta" | "sobra" | "cubierto" | "vacio"; alfa: number } {
  if (v === null) return { tono: "vacio", alfa: 0 };
  if (v >= 0.05) return { tono: "falta", alfa: max > 0 ? Math.min(1, v / max) : 1 };
  if (s >= 0.05) return { tono: "sobra", alfa: maxS > 0 ? Math.min(1, s / maxS) : 1 };
  return { tono: "cubierto", alfa: 1 };
}

/** Meses «AAAA-MM» del rango anterior de igual largo: 2026-05..2026-10 → 2025-11..2026-04. */
export function rangoAnterior(desde: string, hasta: string): [string, string] {
  const n = (m: string) => { const [y, x] = m.split("-").map(Number); return y * 12 + x - 1; };
  const m = (k: number) => `${Math.floor(k / 12)}-${String((k % 12) + 1).padStart(2, "0")}`;
  const largo = n(hasta) - n(desde) + 1;
  return [m(n(desde) - largo), m(n(desde) - 1)];
}

/** «▲ 1,2 pp frente al rango anterior»: flecha y palabras (el color no dice si es bueno o malo). Sin dato de alguno, nada. */
export function variacion(ahora: number | null | undefined, antes: number | null | undefined, unidad: string): string | undefined {
  if (ahora == null || antes == null) return undefined;
  const d = ahora - antes;
  if (Math.abs(d) < 0.05) return "Igual que el rango anterior";
  const u = Math.abs(d) === 1 ? unidad.replace(/(?<=\p{L}{3})s$/u, "") : unidad;  // «1 persona», «1 día»; «pp» y «h» quedan
  return `${d > 0 ? "▲" : "▼"} ${Math.abs(d).toLocaleString("es-CO", { maximumFractionDigits: 1 })} ${u} frente al rango anterior`;
}
