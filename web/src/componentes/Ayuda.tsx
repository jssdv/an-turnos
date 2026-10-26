import { useState, type ReactNode } from "react";
import e from "./Ayuda.module.css";

const recordar = (clave: string, abierta?: boolean) => {
  try {
    if (abierta === undefined) return localStorage.getItem(clave) !== "cerrada";
    localStorage.setItem(clave, abierta ? "abierta" : "cerrada");
  } catch { /* almacenamiento bloqueado: se muestra abierta */ }
  return true;
};

/** Recuadro «¿Cómo se usa?» de cada pantalla. Abierto la primera vez; si se cierra, este navegador lo recuerda. */
export function Ayuda({ titulo, clave, children }: { titulo: string; clave: string; children: ReactNode }) {
  const [abierta] = useState(() => recordar(`ayuda/${clave}`));
  return (
    <details className={e.ayuda} open={abierta} onToggle={(x) => recordar(`ayuda/${clave}`, x.currentTarget.open)}>
      <summary className={e.titulo}><span className={e.icono} aria-hidden="true">?</span>{titulo}</summary>
      <div className={e.cuerpo}>{children}</div>
    </details>
  );
}
