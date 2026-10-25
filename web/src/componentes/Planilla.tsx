import { useEffect, useRef, useState, type KeyboardEvent, type ReactNode } from "react";
import { Ficha, type FichaProps } from "./Ficha";
import e from "./Planilla.module.css";

export interface Dia {
  fecha: string;
  n: number;
  letra: string;
  nombre: string;
  gris: boolean; // domingo o festivo
}
export interface Fila {
  id: number;
  nombre: string;
  extra?: ReactNode;
  extraAlto?: boolean;
}
export interface Pie {
  titulo: string;
  valor: (fecha: string) => ReactNode;
  alerta?: (fecha: string) => boolean;
}
export interface Foco {
  fila: number | null; // null = primera fila
  fecha: string;
  marca: number; // cambia en cada petición para repetir el mismo destino
}
interface Props {
  descripcion: string;
  dias: Dia[];
  filas: Fila[];
  celda: (fila: number, fecha: string) => FichaProps & { etiqueta: string };
  columnaExtra?: string;
  pie?: Pie[];
  foco?: Foco | null;
}

/** Grilla persona × día con `Ficha`. Una sola celda entra en el orden de tabulación; las flechas, Inicio y Fin se mueven dentro. */
export function Planilla({ descripcion, dias, filas, celda, columnaExtra, pie = [], foco }: Props) {
  const [activa, setActiva] = useState<[number, number]>([0, 0]);
  const cuerpo = useRef<HTMLTableSectionElement>(null);

  const enfocar = (r: number, c: number) => {
    const rr = Math.max(0, Math.min(filas.length - 1, r));
    const cc = Math.max(0, Math.min(dias.length - 1, c));
    setActiva([rr, cc]);
    cuerpo.current?.querySelector<HTMLElement>(`[data-r="${rr}"][data-c="${cc}"]`)?.focus();
  };

  useEffect(() => {
    if (!foco) return;
    const c = dias.findIndex((d) => d.fecha === foco.fecha);
    const r = foco.fila === null ? 0 : filas.findIndex((f) => f.id === foco.fila);
    if (c >= 0 && r >= 0) enfocar(r, c);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [foco?.marca]);

  const tecla = (ev: KeyboardEvent<HTMLTableSectionElement>) => {
    const td = (ev.target as HTMLElement).closest<HTMLElement>("td[data-r]");
    if (!td) return;
    const r = Number(td.dataset.r), c = Number(td.dataset.c);
    const mov: Record<string, [number, number]> = {
      ArrowUp: [r - 1, c], ArrowDown: [r + 1, c], ArrowLeft: [r, c - 1], ArrowRight: [r, c + 1],
      Home: [r, 0], End: [r, dias.length - 1], PageUp: [r - 10, c], PageDown: [r + 10, c],
    };
    const d = mov[ev.key];
    if (d) { ev.preventDefault(); enfocar(d[0], d[1]); }
  };

  return (
    <div className={e.contenedor}>
      <table className={e.planilla} role="grid" aria-label={descripcion} aria-rowcount={filas.length + 1} aria-colcount={dias.length + 2}>
        <thead>
          <tr>
            <th scope="col" className={e.persona}>Persona</th>
            {dias.map((d) => (
              <th key={d.fecha} scope="col" className={`${e.dia} ${d.gris ? e.gris : ""}`} aria-label={`${d.nombre} ${d.n}`}>
                <span className={e.letra}>{d.letra}</span>
                <span>{d.n}</span>
              </th>
            ))}
            {columnaExtra && <th scope="col" className={e.extra}>{columnaExtra}</th>}
          </tr>
        </thead>
        <tbody ref={cuerpo} onKeyDown={tecla}>
          {filas.map((f, r) => (
            <tr key={f.id}>
              <th scope="row" className={e.persona}>{f.nombre}</th>
              {dias.map((d, c) => {
                const { etiqueta, ...ficha } = celda(f.id, d.fecha);
                return (
                  <td
                    key={d.fecha}
                    role="gridcell"
                    data-r={r}
                    data-c={c}
                    tabIndex={activa[0] === r && activa[1] === c ? 0 : -1}
                    aria-label={`${f.nombre}, ${d.nombre} ${d.n}: ${etiqueta}`}
                    className={`${e.celda} ${d.gris ? e.gris : ""}`}
                    onFocus={() => setActiva([r, c])}
                    onClick={() => setActiva([r, c])}
                  >
                    <Ficha {...ficha} />
                  </td>
                );
              })}
              {columnaExtra && <td className={`${e.extra} ${f.extraAlto ? e.alto : ""}`}>{f.extra}</td>}
            </tr>
          ))}
        </tbody>
        {pie.length > 0 && (
          <tfoot>
            {pie.map((p) => (
              <tr key={p.titulo}>
                <th scope="row" className={e.persona}>{p.titulo}</th>
                {dias.map((d) => (
                  <td key={d.fecha} className={`${e.resumen} ${d.gris ? e.gris : ""} ${p.alerta?.(d.fecha) ? e.malo : ""}`}>{p.valor(d.fecha)}</td>
                ))}
                {columnaExtra && <td />}
              </tr>
            ))}
          </tfoot>
        )}
      </table>
    </div>
  );
}
