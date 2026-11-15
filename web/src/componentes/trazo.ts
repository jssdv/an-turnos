/** Trazo SVG de una serie: x repartida de 0 a `ancho`, y de `alto` (valor 0) a 0 (valor `max`). Sin máximo, todo abajo. */
export function trazo(valores: number[], ancho: number, alto: number, max: number): string {
  const paso = valores.length > 1 ? ancho / (valores.length - 1) : 0;
  const y = (v: number) => (max > 0 ? alto - (v / max) * alto : alto);
  return valores.map((v, i) => `${i ? "L" : "M"}${+(i * paso).toFixed(1)},${+y(v).toFixed(1)}`).join(" ");
}
