/** Trazo SVG de una serie: x repartida de 0 a `ancho`, y de `alto` (valor 0) a 0 (valor `max`). Sin máximo, todo abajo. */
export function trazo(valores: number[], ancho: number, alto: number, max: number): string {
  const paso = valores.length > 1 ? ancho / (valores.length - 1) : 0;
  const y = (v: number) => (max > 0 ? alto - (v / max) * alto : alto);
  return valores.map((v, i) => `${i ? "L" : "M"}${+(i * paso).toFixed(1)},${+y(v).toFixed(1)}`).join(" ");
}

/** Color de una celda del mapa de cobertura: `v` = personas que faltan en promedio (≥ 0); intensidad relativa a `max` (el más alto). Menos de 0,05 cuenta como cubierto. */
export function tonoMapa(v: number | null, max: number): { tono: "falta" | "cubierto" | "vacio"; alfa: number } {
  if (v === null) return { tono: "vacio", alfa: 0 };
  if (v < 0.05) return { tono: "cubierto", alfa: 1 };
  return { tono: "falta", alfa: max > 0 ? Math.min(1, v / max) : 1 };
}
