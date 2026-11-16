import type { ReactNode } from "react";
import { Table } from "@/components/application/table/table";
import { Vacio } from "../pantallas/comun";

interface Props {
  columnas: string[];
  filas: ReactNode[][];
  vacio: string;
  descripcion: string;
  /** Mientras llegan los datos: evita mostrar «Aún no hay…» como si la lista estuviera vacía. */
  cargando?: boolean;
}

/** Tabla de Untitled UI armada desde columnas y filas, con estados de carga y vacío (Untitled no los trae); la primera columna (el nombre) no se parte en dos líneas. La grilla del cuadro es `Planilla`. */
export function Tabla({ columnas, filas, vacio, descripcion, cargando }: Props) {
  if (cargando) return <Vacio aria-busy="true">Cargando…</Vacio>;
  if (!filas.length) return <Vacio>{vacio}</Vacio>;
  return (
    <div className="overflow-x-auto">
      <Table aria-label={descripcion} size="sm">
        <Table.Header bordered={false}>
          {columnas.map((c, i) => <Table.Head key={i} id={`c${i}`} label={c} isRowHeader={i === 0} />)}
        </Table.Header>
        <Table.Body>
          {filas.map((f, i) => (
            <Table.Row key={i} id={i}>
              {f.map((c, j) => <Table.Cell key={j} className={j === 0 ? "whitespace-nowrap" : undefined}>{c}</Table.Cell>)}
            </Table.Row>
          ))}
        </Table.Body>
      </Table>
    </div>
  );
}
