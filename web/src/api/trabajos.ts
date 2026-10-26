/** Generar un periodo: contrato de la Fase 3 (POST …/generar con If-Match, GET /api/trabajos/{id}, POST …/cancelar).
 *  Son las rutas reales; con VITE_TRABAJOS_SIMULADOS=1 se usa una simulación en memoria (para probar la pantalla sin trabajador). */
import { pedir } from "./cliente";
import type { PedidoGenerar, Trabajo } from "./tipos";

export interface Trabajos {
  iniciar(area: number, periodo: number, revision: number, pedido: PedidoGenerar): Promise<{ id: number }>;
  consultar(id: number): Promise<Trabajo>;
  cancelar(id: number): Promise<Trabajo>;
}

const real: Trabajos = {
  iniciar: (area, periodo, revision, pedido) =>
    pedir("POST", `/api/areas/${area}/periodos/${periodo}/generar`, { cuerpo: pedido, revision }),
  consultar: (id) => pedir("GET", `/api/trabajos/${id}`),
  cancelar: (id) => pedir("POST", `/api/trabajos/${id}/cancelar`, { cuerpo: {} }),
};

const LIMITE_S = 12;
const simulados = new Map<number, { t0: number; cancelado: boolean }>();
let siguiente = 1;

function estadoSimulado(id: number): Trabajo {
  const s = simulados.get(id);
  if (!s) return { id, estado: "fallido", progreso: null, resultado: null, error: "Trabajo desconocido" };
  const seg = Math.min(LIMITE_S, (Date.now() - s.t0) / 1000);
  const base = { id, resultado: null, error: null };
  if (s.cancelado) return { ...base, estado: "cancelado", progreso: null };
  const progreso = { segundos: Math.round(seg * 10) / 10, limite: LIMITE_S, soluciones: Math.floor(seg / 2) + (seg > 1 ? 1 : 0), objetivo: seg > 1 ? Math.round(9000 - seg * 500) : null };
  if (seg >= LIMITE_S) return { ...base, estado: "listo", progreso, resultado: { estado: "OPTIMAL", objetivo: progreso.objetivo, solicitudes: [], faltan: [] } };
  return { ...base, estado: seg < 0.8 ? "en_cola" : "corriendo", progreso };
}

const simulado: Trabajos = {
  iniciar: async () => {
    const id = siguiente++;
    simulados.set(id, { t0: Date.now(), cancelado: false });
    return { id };
  },
  consultar: async (id) => estadoSimulado(id),
  cancelar: async (id) => {
    const s = simulados.get(id);
    if (s) s.cancelado = true;
    return estadoSimulado(id);
  },
};

export const trabajos: Trabajos = import.meta.env.VITE_TRABAJOS_SIMULADOS === "1" ? simulado : real;
export const trabajosSimulados = import.meta.env.VITE_TRABAJOS_SIMULADOS === "1";
