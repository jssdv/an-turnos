import { memo } from "react";
import e from "./Ficha.module.css";

export interface FichaProps {
  codigo: string; // «L» = libre
  /** Color del turno (RRGGBB) cuando el código no tiene token propio. */
  color?: string;
  cambiada?: boolean;
  novedad?: string | null;
  faltante?: boolean;
}

const CON_TOKEN = new Set(["M", "T", "C", "NC"]);

/** Celda de turno: color del turno, esquina marcada si se editó a mano, novedad (V/I/…) y borde si falta cobertura. */
export const Ficha = memo(function Ficha({ codigo, color, cambiada, novedad, faltante }: FichaProps) {
  const libre = codigo === "L";
  const propio = !libre && !CON_TOKEN.has(codigo) && color ? { background: `#${color}` } : undefined;
  return (
    <span
      className={`${e.ficha} ${libre ? e.libre : ""} ${novedad ? e.novedad : ""} ${faltante ? e.faltante : ""}`}
      data-turno={CON_TOKEN.has(codigo) ? codigo : undefined}
      style={propio}
    >
      {novedad ?? codigo}
      {cambiada && <span className={e.marca} aria-hidden="true" />}
    </span>
  );
});
