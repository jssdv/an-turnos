import type { ReactNode } from "react";
import { Table } from "@/components/application/table/table";

interface Props {
  columnas: string[];
  filas: ReactNode[][];
  vacio: string;
  descripcion: string;
  /** Mientras llegan los datos: evita mostrar «Aún no hay…» como si la lista estuviera vacía. */
  cargando?: boolean;
}

/** Tabla de Untitled UI armada desde columnas y filas, con estados de carga y vacío (Untitled no los trae). La grilla del cuadro es `Planilla`. */
export function Tabla({ columnas, filas, vacio, descripcion, cargando }: Props) {
  if (cargando) return <p className="p-6 text-center text-tertiary" aria-busy="true">Cargando…</p>;
  if (!filas.length) return <p className="p-6 text-center text-tertiary">{vacio}</p>;
  return (
    <div className="-mx-5 overflow-x-auto">
      <Table aria-label={descripcion} size="sm">
        <Table.Header>
          {columnas.map((c, i) => <Table.Head key={i} id={`c${i}`} label={c} isRowHeader={i === 0} />)}
        </Table.Header>
        <Table.Body>
          {filas.map((f, i) => (
            <Table.Row key={i} id={i}>
              {f.map((c, j) => <Table.Cell key={j}>{c}</Table.Cell>)}
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </div>
  );
}
