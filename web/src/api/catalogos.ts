/** Escrituras de catálogos y usuarios; lecturas con un hook que se vuelve a pedir tras guardar. */
import { useCallback, useEffect, useState } from "react";
import { ErrorApi, leer, pedir } from "./cliente";

export const enviar = <T = unknown>(metodo: "POST" | "PUT" | "DELETE", ruta: string, cuerpo?: unknown) =>
  pedir<T>(metodo, ruta, { cuerpo: cuerpo ?? {} });

export const mensaje = (x: unknown, defecto = "No se pudo completar la operación") => (x instanceof ErrorApi ? x.message : defecto);

/** Lee una lista de la API; `recargar()` la pide de nuevo. Una ruta `null` no pide nada. */
export function usar<T>(ruta: string | null) {
  const [datos, setDatos] = useState<T | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [n, setN] = useState(0);
  useEffect(() => {
    if (!ruta) return;
    let vivo = true;
    leer<T>(ruta).then((d) => { if (vivo) { setDatos(d); setError(null); } }).catch((x) => vivo && setError(mensaje(x)));
    return () => { vivo = false; };
  }, [ruta, n]);
  return { datos, error, recargar: useCallback(() => setN((k) => k + 1), []) };
}

export const aHHMM = (m: number) => `${String(Math.floor(m / 60) % 24).padStart(2, "0")}:${String(m % 60).padStart(2, "0")}`;
export const aMinutos = (t: string) => { const [h, m] = t.split(":").map(Number); return h * 60 + m; };
