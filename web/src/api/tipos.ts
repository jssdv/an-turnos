/** Respuestas de lectura de la API. FastAPI no declara `response_model`, así que `esquema.d.ts` las deja como `unknown`:
 *  se describen aquí a mano, según los `asdict` del núcleo (an/turnos/dominio.py, reglas.py) y an/web/rutas_*.py. */
export interface Usuario {
  id: number;
  clinica_id: number;
  correo: string;
  nombre: string;
  es_admin: boolean;
  debe_cambiar: boolean;
}
export interface Area {
  id: number;
  nombre: string;
  tipo: string;
  permiso: "ver" | "editar";
}
export interface Periodo {
  id: number;
  clave: string; // «AAAA-MM-DD/AAAA-MM-DD»
  revision: number;
  publicado_en: string | null;
  cerrado_en: string | null;
  /** Ids de otros periodos del área que comparten fechas con este. */
  solapa_con?: number[];
}
export interface Celda {
  colab_id: number;
  fecha: string; // ISO
  turno: string;
  /** Editada a mano. */
  fijo?: boolean;
}
export interface Cuadro {
  clave: string;
  version: string;
  revision?: number;
  celdas: Celda[];
}
export interface Colaborador {
  id: number;
  nombre: string;
  tipo: string;
  activo: boolean;
}
export interface Turno {
  codigo: string;
  nombre: string;
  color: string; // «RRGGBB» sin «#»
  cubre: string[];
  inicio: number;
  fin: number;
  activo: boolean;
}
export interface Novedad {
  colab_id: number;
  tipo: string;
  desde: string;
  hasta: string;
}
export interface Alerta {
  nivel: "error" | "aviso";
  fecha: string | null;
  colab_id: number | null;
  texto: string;
}
export interface Horas {
  colab_id: number;
  contratadas: number;
  trabajadas: number;
}
export interface CoberturaPeriodo {
  periodo: string;
  dias_deficit: number;
  dias_exceso: number;
  puestos_sin_cubrir: number;
}
export interface Analiticas {
  cobertura: CoberturaPeriodo[];
}

/** Contrato de la Fase 3 (an/web/rutas_trabajos.py, trabajador.py). */
export type EstadoTrabajo = "en_cola" | "corriendo" | "listo" | "fallido" | "cancelado" | "conflicto";
export interface Resultado {
  estado: string;
  objetivo: number | null;
  solicitudes: { id: number; estado: string; motivo: string }[]; // parciales y no cumplidas
  faltan: [string, number, number][]; // [fecha, tramo 0–47, personas que faltan]
}
export interface Trabajo {
  id: number;
  estado: EstadoTrabajo;
  progreso: { segundos: number; limite: number; soluciones: number; objetivo: number | null; cota?: number | null } | null;
  resultado: Resultado | null;
  error: string | null;
}
export interface PedidoGenerar {
  modo: "cero" | "respetar" | "semana";
  lunes?: string;
  tiempo?: number; // segundos del solver (1–300)
}

/** Edición del cuadro (an/web/rutas_edicion.py). */
export type TipoCambio = "permuta" | "servicio" | "ajuste";
export interface CuerpoCambio {
  tipo: TipoCambio;
  celdas: { colab_id: number; fecha: string; turno: string }[];
  motivo: string;
  excepcion: boolean;
}
export interface RespuestaCambio {
  revision: number;
  ids?: number[];
  anulado?: boolean;
  alertas_nuevas: string[];
}
export interface CambioRegistrado {
  id: number;
  tipo: TipoCambio;
  registrado_en: string;
  usuario: string;
  colab_a: number;
  colab_b: number | null;
  motivo: string;
  excepcion: boolean;
  anulado_en: string | null;
  anulado_por: string | null;
  celdas: { colab_id: number; fecha: string; antes: string; despues: string }[];
}
export interface Cupo {
  colab_id: number;
  usadas: number;
  limite: number;
}
