/** Radiología: cuadro mensual subido y análisis de una semana (an/web/rutas_radiologia.py). */
import { ErrorApi } from "./cliente";

export interface Archivo { id: number; nombre: string; tamano: number; subido: string; subido_por: string | null }
export interface Semanas { hoja: string; semanas: { lunes: string; etiqueta: string }[]; defecto: string }
export interface Tarjeta { titulo: string; valor: number | string; nivel: "ok" | "warn" | "error" | "info"; detalle: string }
export interface Cobertura { servicio: string; dias: { n: number; faltan: string[] }[] }
export interface Resumen { semana: string; tarjetas: Tarjeta[]; cobertura: Cobertura[]; dias: string[]; aviso: string; festivos: string[] }
export interface Alertas {
  revision: { fecha: string | null; corta: string; medico: string; problema: string }[];
  descanso: { fecha: string; corta: string; medico: string; regla: string }[];
  pendientes: { fecha: string; corta: string; servicio: string; franja: string; que: string }[];
}
export interface Equidad {
  medico: string; semana: number; jornada: number | null; mes: number | null; meta: number | null; pendiente: number | null;
  noches: number | null; domingos: number | null; festivos: number | null; findes_libres: number | null; disponibilidades: number;
}
export interface Semana { resumen: Resumen; alertas: Alertas; equidad: Equidad[]; agendas: Record<string, string>; cambios: { version_anterior: string | null; lista: string[] } }
export interface CeldaHoja { texto: string; fondo: string | null; negrita: boolean; color: string | null }
export interface Hoja { hoja: string; titulo: string; filas: CeldaHoja[][]; fusiones: [number, number, number, number][] }
export interface EquidadMeses {
  meses: string[]; fallidos: string[];
  filas: { medico: string; meses: string[]; mes: number | null; meta: number | null; pendiente: number | null; noches: number | null; domingos: number | null; festivos: number | null; findes_libres: number | null; disponibilidades: number | null }[];
}

export const base = (area: number) => `/api/areas/${area}`;
export const rutaSemana = (area: number, archivo: number, lunes: string) => `${base(area)}/archivos/${archivo}/semanas/${lunes}`;

/** El cuerpo va crudo (sin multipart): el nombre viaja en la consulta. Los errores traen el mensaje en español de la API. */
export async function subirCuadro(area: number, archivo: File): Promise<Archivo> {
  let r: Response;
  try {
    r = await fetch(`${base(area)}/archivos?nombre=${encodeURIComponent(archivo.name)}`, {
      method: "POST", headers: { "Content-Type": "application/octet-stream" }, body: archivo,
    });
  } catch {
    throw new ErrorApi(0, "No hay conexión con el servidor. Revisa la red e inténtalo de nuevo.");
  }
  const datos = await r.json().catch(() => null);
  if (!r.ok) throw new ErrorApi(r.status, typeof datos?.detalle === "string" ? datos.detalle : "No se pudo subir el archivo");
  return datos as Archivo;
}
