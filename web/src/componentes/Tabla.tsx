import type { ReactNode } from "react";
import e from "./Tabla.module.css";

interface Props {
  columnas: string[];
  filas: ReactNode[][];
  vacio: string;
  descripcion: string;
  /** Mientras llegan los datos: evita mostrar «Aún no hay…» como si la lista estuviera vacía. */
  cargando?: boolean;
}

/** Tabla simple de datos con estado vacío y de carga. La grilla del cuadro es `Planilla`. */
export function Tabla({ columnas, filas, vacio, descripcion, cargando }: Props) {
  if (cargando) return <p className={e.vacio} aria-busy="true">Cargando…</p>;
  if (!filas.length) return <p className={e.vacio}>{vacio}</p>;
  return (
    <div className={e.marco}>
      <table className={e.tabla} aria-label={descripcion}>
        <thead>
          <tr>{columnas.map((c) => <th key={c} scope="col">{c}</th>)}</tr>
        </thead>
        <tbody>
          {filas.map((f, i) => <tr key={i}>{f.map((c, j) => <td key={j}>{c}</td>)}</tr>)}
        </tbody>
      </table>
    </div>
  );
}
