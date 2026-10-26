/** Escrituras de un periodo (an/web/rutas_edicion.py). Todas envían la revisión vista (`If-Match`). */
import { leer, pedir } from "./cliente";
import type { CambioRegistrado, CuerpoCambio, Cupo, RespuestaCambio } from "./tipos";

const base = (area: number, periodo: number) => `/api/areas/${area}/periodos/${periodo}`;

export const cambios = {
  registrar: (area: number, periodo: number, revision: number, cuerpo: CuerpoCambio) =>
    pedir<RespuestaCambio>("POST", `${base(area, periodo)}/cambios`, { cuerpo, revision }),
  anular: (area: number, periodo: number, revision: number, cambio: number) =>
    pedir<RespuestaCambio>("POST", `${base(area, periodo)}/cambios/${cambio}/anular`, { cuerpo: {}, revision }),
  listar: (area: number, periodo: number) => leer<CambioRegistrado[]>(`${base(area, periodo)}/cambios`),
  cupos: (area: number, periodo: number) => leer<Cupo[]>(`${base(area, periodo)}/cupos`),
  accion: (area: number, periodo: number, revision: number, nombre: "publicar" | "restaurar" | "cerrar" | "reabrir") =>
    pedir<{ revision: number }>("POST", `${base(area, periodo)}/${nombre}`, { cuerpo: {}, revision }),
  crearPeriodo: (area: number, inicio: string, fin: string) =>
    pedir<{ id: number; clave: string }>("POST", `/api/areas/${area}/periodos`, { cuerpo: { inicio, fin } }),
};

/** Cambio a medio escribir. Se guarda antes de enviarlo: si la sesión vence (401) se recupera al ingresar de nuevo. */
export interface Borrador {
  area: number;
  periodo: number;
  modo: "intercambio" | "asignar";
  celdas: { colab_id: number; fecha: string }[];
  turno: string;
  tipo: "permuta" | "servicio" | "ajuste";
  motivo: string;
  excepcion: boolean;
}
const LLAVE = "an/pendiente";
export const borrador = {
  guardar(b: Borrador) { try { sessionStorage.setItem(LLAVE, JSON.stringify(b)); } catch { /* sin almacenamiento: se pierde solo en un 401 */ } },
  leer(area: number): Borrador | null {
    try {
      const b = JSON.parse(sessionStorage.getItem(LLAVE) ?? "null") as Borrador | null;
      return b && b.area === area ? b : null;
    } catch { return null; }
  },
  borrar() { try { sessionStorage.removeItem(LLAVE); } catch { /* nada */ } },
};
