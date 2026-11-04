import type { Borrador } from "../api/cambios";
import type { Cupo, Puesto, Turno } from "../api/tipos";
import { fechaCorta } from "./fechas";
import { Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert } from "@/components/application/alerts/alert";

interface Props {
  borrador: Borrador | null;
  alCambiar: (b: Borrador | null) => void;
  nombres: Map<number, string>;
  turnos: Turno[];
  /** Código actual de una celda. */
  actual: (colab: number, fecha: string) => string;
  /** Puestos activos del área, o null si no trabaja por puestos. */
  puestos: Puesto[] | null;
  /** Nombre del puesto actual de una celda ("" si no tiene). */
  puestoDe: (colab: number, fecha: string) => string;
  /** Ids de los puestos de una celda en orden horario (dos = C partida). */
  puestosDe: (colab: number, fecha: string) => number[];
  cupos: Cupo[] | null;
  error: string | null;
  enviando: boolean;
  alEnviar: () => void;
}

/** Turno corrido: 10 h o más y sin noche (como `demanda.es_corrido`). Solo estos se pueden fijar por mitad. */
export function esCorrido(t?: Turno) {
  if (!t) return false;
  const min = (t.fin - t.inicio + 1440) % 1440 || 1440;
  return min >= 600 && !t.cubre.includes("N");
}

export const NOMBRE_TIPO = { permuta: "Permuta", servicio: "Cambio de servicio", ajuste: "Solo ajuste" } as const;

/** Colaboradores que ya gastaron su cupo de permutas, entre los de las celdas. */
export function sinCupo(b: Borrador, cupos: Cupo[] | null) {
  return b.modo === "intercambio" && b.celdas.length === 2 && b.celdas[0].colab_id !== b.celdas[1].colab_id
    ? (cupos ?? []).filter((c) => b.celdas.some((x) => x.colab_id === c.colab_id) && c.usadas >= c.limite)
    : [];
}

/** Diálogo «Registrar cambio»: qué se cambia y de qué clase es (permuta, cambio de servicio o ajuste). Lo escrito vive en `borrador`. */
export function RegistrarCambio({ borrador: b, alCambiar, nombres, turnos, actual, puestos, puestoDe, puestosDe, cupos, error, enviando, alEnviar }: Props) {
  if (!b) return <Ventana abierto={false} alCambiar={() => undefined} titulo="Registrar cambio">{null}</Ventana>;
  const set = (p: Partial<Borrador>) => alCambiar({ ...b, ...p });
  const entre = b.modo === "intercambio" && b.celdas.length === 2 && b.celdas[0].colab_id !== b.celdas[1].colab_id;
  const tipos = (entre ? ["permuta", "servicio", "ajuste"] : ["servicio", "ajuste"]) as Borrador["tipo"][];
  const tipo = tipos.includes(b.tipo) ? b.tipo : tipos[0];
  const agotados = tipo === "permuta" ? sinCupo(b, cupos) : [];
  const cel = (x: Borrador["celdas"][number]) => `${nombres.get(x.colab_id) ?? x.colab_id} · ${fechaCorta(x.fecha)} (${actual(x.colab_id, x.fecha)}${puestoDe(x.colab_id, x.fecha) ? ` · ${puestoDe(x.colab_id, x.fecha)}` : ""})`;
  const resumen = b.modo === "intercambio" && b.celdas.length === 2 ? `${cel(b.celdas[0])} ⇄ ${cel(b.celdas[1])}`
    : b.celdas.length === 1 ? cel(b.celdas[0]) : `${b.celdas.length} celdas`;
  const sinMotivo = tipo === "servicio" && !b.motivo.trim();
  const partido = !!puestos && b.modo === "asignar" && esCorrido(turnos.find((t) => t.codigo === b.turno));
  const [m0, t0] = (() => { const p = puestosDe(b.celdas[0].colab_id, b.celdas[0].fecha); return [p[0] ?? 0, p[1] ?? p[0] ?? 0]; })();
  const mitad = (lado: "puesto" | "puestoTarde", actual: number) => b[lado] ?? String(actual);
  return (
    <Ventana abierto alCambiar={(a) => { if (!a) alCambiar(null); }} titulo="Registrar cambio" descripcion={resumen}>
      {error && <Alert color="error">{error}</Alert>}
      <div className="flex flex-col gap-4">
        {b.celdas.length === 2 && (
          <NativeSelect size="sm" label="Qué hacer" value={b.modo} onChange={(x) => set({ modo: x.target.value as Borrador["modo"] })}>
            <option value="intercambio">Intercambiar</option>
            <option value="asignar">Poner el mismo turno</option>
          </NativeSelect>
        )}
        {b.modo === "asignar" && (
          <NativeSelect size="sm" label="Turno" value={b.turno} onChange={(x) => set({ turno: x.target.value })}>
            <option value="L">L · libre</option>
            {turnos.filter((t) => t.activo).map((t) => <option key={t.codigo} value={t.codigo}>{t.codigo} · {t.nombre}</option>)}
          </NativeSelect>
        )}
        {puestos && b.modo === "asignar" && !partido && (
          <NativeSelect size="sm" label="Puesto" value={b.puesto ?? ""} onChange={(x) => set({ puesto: x.target.value })}
            hint="Sin cambio = conserva el puesto.">
            <option value="">Sin cambio</option>
            <option value="0">Automático</option>
            {puestos.map((q) => <option key={q.id} value={q.id}>{q.numero} · {q.nombre}</option>)}
          </NativeSelect>
        )}
        {puestos && partido && (["puesto", "puestoTarde"] as const).map((lado) => (
          <NativeSelect key={lado} size="sm" label={lado === "puesto" ? "Puesto de la mañana" : "Puesto de la tarde"} value={mitad(lado, lado === "puesto" ? m0 : t0)}
            hint={lado === "puestoTarde" ? "Al cambiar uno se fijan los dos." : undefined}
            onChange={(x) => set({ puesto: lado === "puesto" ? x.target.value : mitad("puesto", m0), puestoTarde: lado === "puestoTarde" ? x.target.value : mitad("puestoTarde", t0) })}>
            <option value="0">Automático</option>
            {puestos.map((q) => <option key={q.id} value={q.id}>{q.numero} · {q.nombre}</option>)}
          </NativeSelect>
        ))}
        {puestos && b.modo === "intercambio" && <p className="text-sm text-tertiary">Cada quien toma el turno y el puesto del otro.</p>}
        <NativeSelect size="sm" label="Clase de cambio" value={tipo} onChange={(x) => set({ tipo: x.target.value as Borrador["tipo"] })}
          hint="Permuta: entre dos personas. Servicio: por necesidad. Ajuste: corrección.">
          {tipos.map((t) => <option key={t} value={t}>{NOMBRE_TIPO[t]}</option>)}
        </NativeSelect>
        {agotados.length > 0 && (
          <Alert color="warning">
            {agotados.map((c) => `${nombres.get(c.colab_id) ?? c.colab_id} (${c.usadas}/${c.limite})`).join(", ")}: sin permutas disponibles. Se registrará como excepción.
          </Alert>
        )}
        <Input value={String(b.motivo)} label="Motivo" maxLength={500} onChange={(x) => set({ motivo: x })}
          hint={tipo === "servicio" ? "Obligatorio" : undefined} />
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <Button color="secondary" size="sm" onPress={() => alCambiar(null)}>Cancelar</Button>
        <Button color="primary" size="sm" onPress={alEnviar} isDisabled={enviando || sinMotivo}>
          {enviando ? "Guardando…" : agotados.length ? "Aprobar como excepción" : "Registrar"}
        </Button>
      </div>
    </Ventana>
  );
}
