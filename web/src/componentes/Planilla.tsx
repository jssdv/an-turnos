import { useEffect, useRef, useState, type KeyboardEvent, type MouseEvent, type ReactNode } from "react";
import { Ficha, type FichaProps } from "./Ficha";
import { cx } from "@/utils/cx";

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
export interface Sel {
  fila: number;
  fecha: string;
}
interface Props {
  descripcion: string;
  dias: Dia[];
  filas: Fila[];
  celda: (fila: number, fecha: string) => FichaProps & { etiqueta: string };
  columnaExtra?: string;
  pie?: Pie[];
  foco?: Foco | null;
  /** Celdas que se pueden seleccionar y arrastrar. Sin esto la grilla es de solo lectura. */
  editable?: (fila: number, fecha: string) => boolean;
  /** Enter, F2 o doble clic sobre la selección. */
  alAccionar?: (celdas: Sel[]) => void;
  /** Se soltó la celda `origen` sobre `destino`. */
  alSoltar?: (origen: Sel, destino: Sel) => void;
}

/** Grilla persona × día con `Ficha`. Una sola celda entra en el orden de tabulación; las flechas, Inicio y Fin se mueven dentro. */
export function Planilla({ descripcion, dias, filas, celda, columnaExtra, pie = [], foco, editable, alAccionar, alSoltar }: Props) {
  const [activa, setActiva] = useState<[number, number]>([0, 0]);
  const cuerpo = useRef<HTMLTableSectionElement>(null);
  const [sel, setSel] = useState<Map<string, Sel>>(new Map());
  const ancla = useRef<[number, number]>([0, 0]);
  const arrastrada = useRef<Sel | null>(null);

  const celdaDe = (r: number, c: number): Sel => ({ fila: filas[r].id, fecha: dias[c].fecha });
  const clave = (x: Sel) => `${x.fila}|${x.fecha}`;
  const puede = (r: number, c: number) => !!editable && editable(filas[r].id, dias[c].fecha);
  /** Clic: simple reemplaza; Ctrl/Cmd suma o quita; Mayús toma el rectángulo desde el ancla. */
  const elegir = (r: number, c: number, ev: { shiftKey: boolean; ctrlKey: boolean; metaKey: boolean }) => {
    if (!puede(r, c)) return;
    const nuevo = new Map(ev.ctrlKey || ev.metaKey ? sel : []);
    if (ev.shiftKey) {
      const [r0, c0] = ancla.current;
      for (let i = Math.min(r0, r); i <= Math.max(r0, r); i++) for (let j = Math.min(c0, c); j <= Math.max(c0, c); j++) if (puede(i, j)) nuevo.set(clave(celdaDe(i, j)), celdaDe(i, j));
    } else {
      const x = celdaDe(r, c);
      if ((ev.ctrlKey || ev.metaKey) && nuevo.has(clave(x))) nuevo.delete(clave(x)); else nuevo.set(clave(x), x);
      ancla.current = [r, c];
    }
    setSel(nuevo);
  };
  const accionar = (r: number, c: number) => {
    if (!alAccionar || !puede(r, c)) return;
    const lista = sel.has(clave(celdaDe(r, c))) ? [...sel.values()] : [celdaDe(r, c)];
    alAccionar(lista);
  };

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
    if (d) {
      ev.preventDefault();
      enfocar(d[0], d[1]);
      if (ev.shiftKey) elegir(Math.max(0, Math.min(filas.length - 1, d[0])), Math.max(0, Math.min(dias.length - 1, d[1])), ev);
    } else if (ev.key === "Enter" || ev.key === "F2") { ev.preventDefault(); accionar(r, c); }
    else if (ev.key === " ") { ev.preventDefault(); elegir(r, c, { shiftKey: false, ctrlKey: true, metaKey: false }); }
    else if (ev.key === "Escape") setSel(new Map());
  };

  return (
    <div className="max-w-full overflow-auto">
      <table className="w-max min-w-full border-separate border-spacing-0 text-sm [&_td]:px-0.5 [&_td]:py-[3px] [&_td]:text-center [&_th]:px-0.5 [&_th]:py-[3px] [&_th]:text-center [&_thead_th]:bg-secondary [&_thead_th]:py-1.5 [&_thead_th]:text-[11px] [&_thead_th]:font-semibold [&_thead_th]:text-tertiary [&_tfoot_td]:border-t [&_tfoot_td]:border-secondary [&_tfoot_td]:text-[11px] [&_tfoot_td]:text-tertiary [&_tfoot_th]:border-t [&_tfoot_th]:border-secondary [&_tfoot_th]:text-[11px] [&_tfoot_th]:font-semibold [&_tfoot_th]:text-tertiary" role="grid" aria-label={descripcion} aria-rowcount={filas.length + 1} aria-colcount={dias.length + 2}>
        <thead>
          <tr>
            <th scope="col" className="sticky left-0 z-[1] min-w-40 bg-primary pr-4! pl-3! text-left! font-medium whitespace-nowrap">Persona</th>
            {dias.map((d) => (
              <th key={d.fecha} scope="col" className={cx("min-w-7", d.gris && "bg-tertiary! text-primary!")} aria-label={`${d.nombre} ${d.n}`}>
                <span className="block text-[11px]">{d.letra}</span>
                <span>{d.n}</span>
              </th>
            ))}
            {columnaExtra && <th scope="col" className="min-w-14">{columnaExtra}</th>}
          </tr>
        </thead>
        <tbody ref={cuerpo} onKeyDown={tecla}>
          {filas.map((f, r) => (
            <tr key={f.id}>
              <th scope="row" className="sticky left-0 z-[1] min-w-40 bg-primary pr-4! pl-3! text-left! font-medium whitespace-nowrap">{f.nombre}</th>
              {dias.map((d, c) => {
                const { etiqueta, ...ficha } = celda(f.id, d.fecha);
                const ed = puede(r, c), elegida = sel.has(`${f.id}|${d.fecha}`);
                return (
                  <td
                    key={d.fecha}
                    role="gridcell"
                    data-r={r}
                    data-c={c}
                    tabIndex={activa[0] === r && activa[1] === c ? 0 : -1}
                    aria-label={`${f.nombre}, ${d.nombre} ${d.n}: ${etiqueta}`}
                    aria-selected={ed ? elegida : undefined}
                    className={cx("h-[30px] focus-visible:rounded-sm focus-visible:outline-2 focus-visible:-outline-offset-2 focus-visible:outline-brand", d.gris && "bg-secondary", ed && "cursor-pointer", elegida && "rounded-sm bg-brand-primary outline-2 -outline-offset-2 outline-brand")}
                    onFocus={() => setActiva([r, c])}
                    onClick={(ev: MouseEvent) => { setActiva([r, c]); elegir(r, c, ev); }}
                    onDoubleClick={() => accionar(r, c)}
                    draggable={ed && !!alSoltar}
                    onDragStart={ed ? (ev) => { arrastrada.current = celdaDe(r, c); ev.dataTransfer.effectAllowed = "move"; ev.dataTransfer.setData("text/plain", clave(celdaDe(r, c))); } : undefined}
                    onDragOver={ed && alSoltar ? (ev) => ev.preventDefault() : undefined}
                    onDrop={ed && alSoltar ? (ev) => {
                      ev.preventDefault();
                      const o = arrastrada.current;
                      arrastrada.current = null;
                      if (o && clave(o) !== clave(celdaDe(r, c))) alSoltar(o, celdaDe(r, c));
                    } : undefined}
                  >
                    <Ficha {...ficha} />
                  </td>
                );
              })}
              {columnaExtra && <td className={cx("min-w-14 font-semibold text-primary", f.extraAlto && "text-utility-yellow-700")}>{f.extra}</td>}
            </tr>
          ))}
        </tbody>
        {pie.length > 0 && (
          <tfoot>
            {pie.map((p) => (
              <tr key={p.titulo}>
                <th scope="row" className="sticky left-0 z-[1] min-w-40 bg-primary pr-4! pl-3! text-left! font-medium whitespace-nowrap">{p.titulo}</th>
                {dias.map((d) => (
                  <td key={d.fecha} className={cx("tabular-nums", d.gris && "bg-secondary", p.alerta?.(d.fecha) && "bg-utility-red-50 font-bold text-utility-red-700")}>{p.valor(d.fecha)}</td>
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
