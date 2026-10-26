import type { Borrador } from "../api/cambios";
import type { Cupo, Turno } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Dialogo } from "../componentes/Dialogo";
import { fechaCorta } from "./fechas";
import e from "./Generar.module.css";

interface Props {
  borrador: Borrador | null;
  alCambiar: (b: Borrador | null) => void;
  nombres: Map<number, string>;
  turnos: Turno[];
  /** Código actual de una celda. */
  actual: (colab: number, fecha: string) => string;
  cupos: Cupo[] | null;
  error: string | null;
  enviando: boolean;
  alEnviar: () => void;
}

export const NOMBRE_TIPO = { permuta: "Permuta", servicio: "Cambio de servicio", ajuste: "Solo ajuste" } as const;

/** Colaboradores que ya gastaron su cupo de permutas, entre los de las celdas. */
export function sinCupo(b: Borrador, cupos: Cupo[] | null) {
  return b.modo === "intercambio" && b.celdas.length === 2 && b.celdas[0].colab_id !== b.celdas[1].colab_id
    ? (cupos ?? []).filter((c) => b.celdas.some((x) => x.colab_id === c.colab_id) && c.usadas >= c.limite)
    : [];
}

/** Diálogo «Registrar cambio»: qué se cambia y de qué clase es (permuta, cambio de servicio o ajuste). Lo escrito vive en `borrador`. */
export function RegistrarCambio({ borrador: b, alCambiar, nombres, turnos, actual, cupos, error, enviando, alEnviar }: Props) {
  if (!b) return <Dialogo abierto={false} alCambiar={() => undefined} titulo="Registrar cambio">{null}</Dialogo>;
  const set = (p: Partial<Borrador>) => alCambiar({ ...b, ...p });
  const entre = b.modo === "intercambio" && b.celdas.length === 2 && b.celdas[0].colab_id !== b.celdas[1].colab_id;
  const tipos = (entre ? ["permuta", "servicio", "ajuste"] : ["servicio", "ajuste"]) as Borrador["tipo"][];
  const tipo = tipos.includes(b.tipo) ? b.tipo : tipos[0];
  const agotados = tipo === "permuta" ? sinCupo(b, cupos) : [];
  const cel = (x: Borrador["celdas"][number]) => `${nombres.get(x.colab_id) ?? x.colab_id} · ${fechaCorta(x.fecha)} (${actual(x.colab_id, x.fecha)})`;
  const resumen = b.modo === "intercambio" && b.celdas.length === 2 ? `${cel(b.celdas[0])} ⇄ ${cel(b.celdas[1])}`
    : b.celdas.length === 1 ? cel(b.celdas[0]) : `${b.celdas.length} celdas`;
  const sinMotivo = tipo === "servicio" && !b.motivo.trim();
  return (
    <Dialogo abierto alCambiar={(a) => { if (!a) alCambiar(null); }} titulo="Registrar cambio" descripcion={resumen}>
      {error && <Aviso nivel="error">{error}</Aviso>}
      <div className={e.form}>
        {b.celdas.length === 2 && (
          <Seleccion etiqueta="Qué hacer" value={b.modo} onChange={(x) => set({ modo: x.target.value as Borrador["modo"] })}>
            <option value="intercambio">Intercambiar las dos celdas</option>
            <option value="asignar">Poner un turno en las dos celdas</option>
          </Seleccion>
        )}
        {b.modo === "asignar" && (
          <Seleccion etiqueta="Turno" value={b.turno} onChange={(x) => set({ turno: x.target.value })}>
            <option value="L">L · libre</option>
            {turnos.filter((t) => t.activo).map((t) => <option key={t.codigo} value={t.codigo}>{t.codigo} · {t.nombre}</option>)}
          </Seleccion>
        )}
        <Seleccion etiqueta="Clase de cambio" value={tipo} onChange={(x) => set({ tipo: x.target.value as Borrador["tipo"] })}>
          {tipos.map((t) => <option key={t} value={t}>{NOMBRE_TIPO[t]}</option>)}
        </Seleccion>
        {agotados.length > 0 && (
          <Aviso nivel="aviso">
            Ya agotó su cupo de permutas en este periodo: {agotados.map((c) => `${nombres.get(c.colab_id) ?? c.colab_id} ${c.usadas}/${c.limite}`).join(", ")}. Puedes aprobar esta permuta como excepción.
          </Aviso>
        )}
        <Campo etiqueta="Motivo" value={b.motivo} maxLength={500} onChange={(x) => set({ motivo: x.target.value })}
          ayuda={tipo === "servicio" ? "Obligatorio en un cambio de servicio" : undefined} />
      </div>
      <div className={e.fila}>
        <Boton onClick={() => alCambiar(null)}>Cancelar</Boton>
        <Boton variante="primario" onClick={alEnviar} disabled={enviando || sinMotivo}>
          {enviando ? "Guardando…" : agotados.length ? "Aprobar como excepción" : "Registrar"}
        </Boton>
      </div>
    </Dialogo>
  );
}
