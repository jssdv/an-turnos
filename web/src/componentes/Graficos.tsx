import { useId } from "react";
import { Seccion, Vacio } from "../pantallas/comun";
import { num } from "../pantallas/fechas";
import { aHHMM } from "../api/catalogos";
import { tonoMapa, trazo } from "./trazo";

/** Barras horizontales por persona (la más alta = 100 %), ordenadas de mayor a menor. */
export function Barras({ titulo, unidad, datos, nota }: { titulo: string; unidad: string; datos: [string, number][]; nota?: string }) {
  const max = Math.max(1, ...datos.map(([, v]) => v));
  return (
    <Seccion titulo={titulo} descripcion={nota}>
      {datos.length === 0 ? <Vacio>Sin datos en el rango.</Vacio> : (
        <ul className="flex flex-col gap-2" aria-label={titulo}>
          {[...datos].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([p, v]) => (
            <li key={p} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 text-xs">
              <span className="truncate font-medium text-secondary">{p}</span>
              <span className="h-2.5 rounded-xs bg-secondary"><span className="block h-full rounded-xs bg-brand-600" style={{ width: `${(v / max) * 100}%` }} /></span>
              <span className="text-tertiary tabular-nums">{num(v, 1)} {unidad}</span>
            </li>
          ))}
        </ul>
      )}
      {datos.length > 10 && <p className="mt-3 text-xs text-tertiary">Las 10 más altas de {datos.length}; el detalle completo está en las tablas de abajo.</p>}
    </Seccion>
  );
}

const COLORES = ["var(--color-brand-600)", "var(--color-utility-orange-500)", "var(--color-utility-blue-500)", "var(--color-utility-pink-500)"];
const W = 600, H = 160;

/** Líneas de una o más series sobre las mismas etiquetas (meses o días). El detalle exacto queda en las tablas. */
export function Linea({ titulo, unidad, etiquetas, series }: { titulo: string; unidad: string; etiquetas: string[]; series: { nombre: string; valores: number[] }[] }) {
  const max = Math.max(0, ...series.flatMap((s) => s.valores));
  const marcas = etiquetas.length > 2 ? [0, Math.floor((etiquetas.length - 1) / 2), etiquetas.length - 1] : etiquetas.map((_, i) => i);
  const x = (i: number) => (etiquetas.length > 1 ? (i / (etiquetas.length - 1)) * 100 : 0);
  return (
    <Seccion titulo={titulo}>
      {!etiquetas.length || !series.length ? <Vacio>Sin datos en el rango.</Vacio> : (
        <>
          <div className="grid grid-cols-[auto_1fr] gap-2 text-xs text-tertiary">
            <div className="flex flex-col justify-between text-right tabular-nums" aria-hidden="true"><span>{num(max, 0)} {unidad}</span><span>0</span></div>
            <svg role="img" aria-label={`${titulo}: ${series.map((s) => `${s.nombre}, máximo ${num(Math.max(0, ...s.valores), 1)} ${unidad}`).join("; ")}`}
              viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none" className="h-40 w-full overflow-visible border-b border-l border-secondary">
              {series.map((s, i) => (
                <path key={s.nombre} d={trazo(s.valores, W, H, max)} fill="none" stroke={COLORES[i % COLORES.length]} strokeWidth={2} vectorEffect="non-scaling-stroke" strokeLinejoin="round" />
              ))}
            </svg>
            <span />
            <div className="relative h-4" aria-hidden="true">
              {marcas.map((i) => (
                <span key={i} className="absolute whitespace-nowrap" style={{ left: `${x(i)}%`, transform: `translateX(-${x(i)}%)` }}>{etiquetas[i]}</span>
              ))}
            </div>
          </div>
          {series.length > 1 && (
            <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-secondary">
              {series.map((s, i) => (
                <li key={s.nombre} className="flex items-center gap-1.5"><span className="size-2.5 rounded-full" style={{ background: COLORES[i % COLORES.length] }} />{s.nombre}</li>
              ))}
            </ul>
          )}
        </>
      )}
    </Seccion>
  );
}

const DIAS_MAPA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const COLOR_MAPA = { falta: "var(--color-utility-red-500)", cubierto: "var(--color-utility-neutral-300)", vacio: "transparent" };
const fondo = (v: number | null, max: number) => {
  const { tono, alfa } = tonoMapa(v, max);
  return tono === "vacio" ? "transparent" : `color-mix(in srgb, ${COLOR_MAPA[tono]} ${Math.round(25 + 75 * alfa)}%, transparent)`;
};
const tramo = (t: number) => `${aHHMM(t * 30)}–${aHHMM(t * 30 + 30)}`;
const decir = (v: number) => (tonoMapa(v, 1).tono === "falta" ? `faltan ${num(v, 1)} en promedio` : "cubierto");

/** Mapa día de la semana × tramo de 30 min: personas que faltan en promedio frente a lo obligatorio (sin festivos). Rojo = falta. */
export function Mapa({ titulo, mapa }: { titulo: string; mapa: (number | null)[][] }) {
  const id = useId();
  const max = Math.max(0, ...mapa.flat().map((v) => v ?? 0));
  const peores = mapa.flatMap((fila, w) => fila.map((v, t) => ({ v, w, t }))).filter((c): c is { v: number; w: number; t: number } => c.v !== null && tonoMapa(c.v, max).tono === "falta")
    .sort((a, b) => b.v - a.v).slice(0, 3);
  const resumen = peores.length ? `Donde más falta: ${peores.map((c) => `${DIAS_MAPA[c.w]} ${tramo(c.t)} (${decir(c.v)})`).join("; ")}.` : "En promedio no falta gente en ningún tramo.";
  return (
    <Seccion titulo={titulo} descripcion={mapa.flat().every((v) => v === null) ? undefined : <span id={id}>{resumen}</span>}>
      {mapa.flat().every((v) => v === null) ? <Vacio>Sin datos en el rango.</Vacio> : (
        <>
          <div role="img" aria-label={titulo} aria-describedby={id} className="grid grid-cols-[2.25rem_minmax(0,1fr)] gap-x-2 gap-y-0.5 text-xs text-tertiary">
            {mapa.map((fila, w) => (
              <div key={w} className="contents">
                <span className="self-center">{DIAS_MAPA[w]}</span>
                <div className="grid h-4 grid-cols-[repeat(48,minmax(0,1fr))]">
                  {fila.map((v, t) => <span key={t} title={v === null ? undefined : `${DIAS_MAPA[w]} ${tramo(t)}: ${decir(v)}`} style={{ background: fondo(v, max) }} />)}
                </div>
              </div>
            ))}
            <span />
            <div className="flex justify-between" aria-hidden="true">{["00:00", "06:00", "12:00", "18:00", "24:00"].map((h) => <span key={h}>{h}</span>)}</div>
          </div>
          <ul className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-secondary" aria-hidden="true">
            <li className="flex items-center gap-1.5"><span className="size-2.5 rounded-xs" style={{ background: COLOR_MAPA.falta }} />Falta gente (más intenso, más falta)</li>
            <li className="flex items-center gap-1.5"><span className="size-2.5 rounded-xs" style={{ background: COLOR_MAPA.cubierto }} />Cubierto</li>
            <li>Sin color: sin demanda. Los festivos no entran.</li>
          </ul>
        </>
      )}
    </Seccion>
  );
}

/** Barras que salen del centro: a la derecha más que la media del equipo, a la izquierda menos. Las 6 más arriba y las 6 más abajo. */
export function Divergente({ titulo, unidad, datos }: { titulo: string; unidad: string; datos: [string, number][] }) {
  const orden = [...datos].filter(([, v]) => Math.abs(v) >= 0.05).sort((a, b) => b[1] - a[1]);
  const filas = [...orden.filter(([, v]) => v > 0).slice(0, 6), ...orden.filter(([, v]) => v < 0).slice(-6)];
  const max = Math.max(0.0001, ...filas.map(([, v]) => Math.abs(v)));
  return (
    <Seccion titulo={titulo}>
      {!filas.length ? <Vacio>{datos.length ? "Todos están en la media del equipo." : "Sin datos en el rango."}</Vacio> : (
        <ul className="flex flex-col gap-2" aria-label={titulo}>
          {filas.map(([p, v]) => (
            <li key={p} className="grid grid-cols-[minmax(0,9rem)_1fr_1fr_auto] items-center gap-x-1 text-xs">
              <span className="truncate pr-2 font-medium text-secondary">{p}</span>
              <span className="flex h-2.5 justify-end">{v < 0 && <span className="block h-full rounded-xs bg-utility-blue-500" style={{ width: `${(-v / max) * 100}%` }} />}</span>
              <span className="flex h-2.5 border-l border-secondary">{v > 0 && <span className="block h-full rounded-xs bg-utility-orange-500" style={{ width: `${(v / max) * 100}%` }} />}</span>
              <span className="pl-2 text-tertiary tabular-nums">{v > 0 ? "+" : ""}{num(v, 1)} {unidad}</span>
            </li>
          ))}
        </ul>
      )}
      <p className="mt-3 text-xs text-tertiary">Respecto de la media del equipo, a tiempo completo (dividido por la dedicación). Naranja: más de lo que le toca; azul: menos.</p>
    </Seccion>
  );
}
