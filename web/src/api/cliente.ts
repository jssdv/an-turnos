/** Cliente HTTP mínimo: cookie de sesión, errores `{"detalle": …}` y `If-Match` en escrituras de un periodo. */
export class ErrorApi extends Error {
  /** `detalle` = el cuerpo de `detalle` tal cual lo envía la API (p. ej. la revisión vigente en un 409). */
  constructor(public estado: number, mensaje: string, public campos?: string[], public detalle?: unknown) {
    super(mensaje);
  }
}

let alVencer: (() => void) | null = null;
/** La sesión se registra aquí para enterarse de un 401 en cualquier petición. */
export function alVencerSesion(f: (() => void) | null) {
  alVencer = f;
}

export async function pedir<T>(
  metodo: "GET" | "POST",
  ruta: string,
  opciones: { cuerpo?: unknown; revision?: number; sinAviso401?: boolean } = {},
): Promise<T> {
  const cabeceras: Record<string, string> = {};
  if (opciones.cuerpo !== undefined) cabeceras["Content-Type"] = "application/json";
  if (opciones.revision !== undefined) cabeceras["If-Match"] = String(opciones.revision);
  let r: Response;
  try {
    r = await fetch(ruta, {
      method: metodo,
      headers: cabeceras,
      body: opciones.cuerpo === undefined ? undefined : JSON.stringify(opciones.cuerpo),
    });
  } catch {
    throw new ErrorApi(0, "No hay conexión con el servidor. Revisa la red e inténtalo de nuevo.");
  }
  const datos = await r.json().catch(() => null);
  if (!r.ok) {
    if (r.status === 401 && !opciones.sinAviso401) alVencer?.();
    const d = datos?.detalle;
    const texto = typeof d === "string" ? d : typeof d?.mensaje === "string" ? d.mensaje : "";  // 409 de revisión: {mensaje, revision}
    throw new ErrorApi(r.status, texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : "No se pudo completar la operación", datos?.campos, d);
  }
  return datos as T;
}

export const leer = <T>(ruta: string) => pedir<T>("GET", ruta);
