import { useEffect, useState } from "react";
import { cambios } from "../api/cambios";
import { ErrorApi } from "../api/cliente";
import type { CambioRegistrado } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { NOMBRE_TIPO } from "./RegistrarCambio";
import { fechaCorta } from "./fechas";

interface Props {
  area: number;
  periodo: number;
  revision: number;
  nombres: Map<number, string>;
  /** Puede anular quien edita y mientras el periodo esté abierto. */
  puedeAnular: boolean;
  alAnular: (alertas: string[]) => void;
  alConflicto: () => void;
}

/** Registro de cambios del periodo (solo crece) con «Anular». Se vuelve a leer cada vez que cambia la revisión. */
export function Cambios({ area, periodo, revision, nombres, puedeAnular, alAnular, alConflicto }: Props) {
  const [lista, setLista] = useState<CambioRegistrado[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [ocupado, setOcupado] = useState<number | null>(null);

  useEffect(() => {
    let vivo = true;
    cambios.listar(area, periodo).then((l) => vivo && setLista(l)).catch((x) => vivo && setError(x.message));
    return () => { vivo = false; };
  }, [area, periodo, revision]);

  const anular = async (id: number) => {
    setOcupado(id);
    setError(null);
    try {
      alAnular((await cambios.anular(area, periodo, revision, id)).alertas_nuevas);
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo anular");
      if (x instanceof ErrorApi && x.estado === 409) alConflicto();
    } finally {
      setOcupado(null);
    }
  };

  const quien = (c: number) => nombres.get(c) ?? `#${c}`;
  return (
    <Tarjeta titulo="Cambios del periodo">
      {error && <Aviso nivel="error">{error}</Aviso>}
      {!lista ? <p aria-busy="true">Cargando…</p> : (
        <Tabla
          descripcion="Cambios registrados en el periodo"
          vacio="Aún no hay cambios registrados en este periodo."
          columnas={["Cuándo", "Quién", "Clase", "Celdas", "Motivo", ""]}
          filas={lista.map((c) => [
            c.registrado_en.replace("T", " ").slice(0, 16),
            c.usuario,
            <>{NOMBRE_TIPO[c.tipo]}{c.excepcion && " (excepción)"}</>,
            c.celdas.map((x) => `${quien(x.colab_id)} ${fechaCorta(x.fecha)}: ${x.antes}→${x.despues}`).join("; "),
            c.motivo,
            c.anulado_en ? <span>Anulado por {c.anulado_por}</span>
              : puedeAnular ? <Boton variante="texto" disabled={ocupado !== null} onClick={() => anular(c.id)}>{ocupado === c.id ? "Anulando…" : "Anular"}</Boton> : null,
          ])}
        />
      )}
    </Tarjeta>
  );
}
