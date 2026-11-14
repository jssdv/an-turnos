import { useEffect, useState } from "react";
import { leer, pedir } from "../api/cliente";
import { mensaje } from "../api/catalogos";
import type { RespuestaCambio, Turno } from "../api/tipos";
import { fechaCorta } from "./fechas";
import { Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";

interface Candidato { colab_id: number; nombre: string; avisos: string[]; turnos_iguales: number; minutos: number }

const FRANJAS: [string, string][] = [["mañana", "M"], ["tarde", "T"], ["noche", "N"]];

/** Turno que se propone primero: el primero que cubre la franja que nombra la alerta («faltan 1 en mañana»). */
export const turnoParaAlerta = (texto: string, turnos: Turno[]) => {
  const franja = FRANJAS.find(([nombre]) => texto.includes(` en ${nombre}`))?.[1];
  return (turnos.find((t) => t.activo && franja && t.cubre.includes(franja)) ?? turnos.find((t) => t.activo))?.codigo ?? "";
};

/** ¿Quién cubre?: personas libres ese día que pueden hacer el turno sin romper reglas. Asignar registra un cambio de servicio. */
export function QuienCubre({ area, periodo, revision, fecha, turnoInicial, ausente, turnos, puedeAsignar, alCerrar, alAsignar }: {
  area: number; periodo: number; revision: number; fecha: string | null; turnoInicial: string; turnos: Turno[]; puedeAsignar: boolean;
  /** Quien tenía el turno y quedó con una novedad: al asignar, su celda pasa a libre en el mismo cambio. */
  ausente?: { id: number; nombre: string };
  alCerrar: () => void; alAsignar: (texto: string, alertas: string[]) => void;
}) {
  const [turno, setTurno] = useState(turnoInicial);
  const [lista, setLista] = useState<Candidato[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  useEffect(() => setTurno(turnoInicial), [turnoInicial, fecha]);
  useEffect(() => {
    if (!fecha || !turno) return;
    let vivo = true;
    setLista(null);
    setError(null);
    leer<Candidato[]>(`/api/areas/${area}/periodos/${periodo}/cubrir?fecha=${fecha}&turno=${encodeURIComponent(turno)}`)
      .then((x) => vivo && setLista(x))
      .catch((x) => vivo && setError(mensaje(x)));
    return () => { vivo = false; };
  }, [area, periodo, fecha, turno]);

  const asignar = async (c: Candidato) => {
    if (!fecha) return;
    setEnviando(true);
    try {
      const r = await pedir<RespuestaCambio>("POST", `/api/areas/${area}/periodos/${periodo}/cambios`, {
        revision, cuerpo: {
          tipo: "servicio", excepcion: false,
          celdas: [...(ausente ? [{ colab_id: ausente.id, fecha, turno: "L" }] : []), { colab_id: c.colab_id, fecha, turno }],
          motivo: ausente ? `Cubre a ${ausente.nombre} el ${fechaCorta(fecha)}` : `Cubre faltante del ${fechaCorta(fecha)}`,
        },
      });
      alAsignar(`${c.nombre} cubre ${turno} el ${fechaCorta(fecha)}.`, r.alertas_nuevas);
    } catch (x) {
      setError(mensaje(x));
    } finally {
      setEnviando(false);
    }
  };

  const horas = (m: number) => `${Math.round((m / 60) * 10) / 10} h`;
  return (
    <Ventana abierto={!!fecha} alCambiar={(a) => !a && alCerrar()} titulo="¿Quién cubre?" bloqueado={enviando}
      descripcion={fecha ? `${ausente ? `Reemplazo de ${ausente.nombre}. ` : ""}Personas libres el ${fechaCorta(fecha)} que pueden hacer el turno sin romper reglas, de menos a más carga.` : undefined}>
      <NativeSelect size="sm" className="w-48" label="Turno" value={turno} onChange={(x) => setTurno(x.target.value)}>
        {turnos.filter((t) => t.activo).map((t) => <option key={t.codigo} value={t.codigo}>{t.codigo} · {t.nombre}</option>)}
      </NativeSelect>
      {error && <p role="alert" className="text-sm text-error-primary">{error}</p>}
      {!lista && !error && <p className="text-sm text-tertiary">Buscando…</p>}
      {lista && lista.length === 0 && <p className="text-sm text-tertiary">Nadie libre puede hacer este turno ese día sin romper una regla.</p>}
      {lista && lista.length > 0 && (
        <ul>
          {lista.map((c) => (
            <li key={c.colab_id} className="flex items-center gap-3 border-t border-secondary py-2 first:border-t-0">
              <div className="flex-1">
                <p className="font-medium text-primary">{c.nombre}</p>
                <p className="text-sm text-tertiary">{horas(c.minutos)} en el periodo · {c.turnos_iguales} {turno} ya asignados</p>
                {c.avisos.map((a) => <p key={a} className="text-sm text-warning-primary">{a}</p>)}
              </div>
              {puedeAsignar && <Button color="secondary" size="sm" isDisabled={enviando} onPress={() => asignar(c)}>Asignar</Button>}
            </li>
          ))}
        </ul>
      )}
    </Ventana>
  );
}
