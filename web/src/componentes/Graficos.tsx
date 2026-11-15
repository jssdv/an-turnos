import { Seccion } from "../pantallas/comun";
import { num } from "../pantallas/fechas";
import { trazo } from "./trazo";

/** Barras horizontales por persona (la más alta = 100 %), ordenadas de mayor a menor. */
export function Barras({ titulo, unidad, datos }: { titulo: string; unidad: string; datos: [string, number][] }) {
  const max = Math.max(1, ...datos.map(([, v]) => v));
  return (
    <Seccion titulo={titulo}>
      {datos.length === 0 ? <p className="text-tertiary">Sin datos en el rango.</p> : (
        <ul className="flex flex-col gap-2.5" aria-label={titulo}>
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
      {!etiquetas.length || !series.length ? <p className="text-tertiary">Sin datos en el rango.</p> : (
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
