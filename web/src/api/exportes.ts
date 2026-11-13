/** Exportes en Excel de un periodo (an/web/rutas_exportes.py). La descarga es un enlace normal: la cookie de sesión viaja sola. */
import { leer, pedir } from "./cliente";
import type { Exporte, TipoExporte } from "./tipos";

const base = (area: number, periodo: number) => `/api/areas/${area}/periodos/${periodo}/exportes`;

export const exportes = {
  crear: (area: number, periodo: number, tipo: TipoExporte) => pedir<Exporte>("POST", base(area, periodo), { cuerpo: { tipo } }),
  listar: (area: number, periodo: number) => leer<Exporte[]>(base(area, periodo)),
  /** Descargas directas (se arman al pedirlas, no se guardan). */
  urlBanco: (area: number, periodo: number) => `/api/areas/${area}/periodos/${periodo}/banco.xlsx`,
  urlDescarga: (area: number, periodo: number, id: number) => `${base(area, periodo)}/${id}/descargar`,
};
