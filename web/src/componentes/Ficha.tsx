import { memo } from "react";
import { cx } from "@/utils/cx";

export interface FichaProps {
  codigo: string; // «L» = libre
  /** Color del turno (RRGGBB) cuando el código no tiene token propio. */
  color?: string;
  cambiada?: boolean;
  novedad?: string | null;
  faltante?: boolean;
  /** Nombre corto del puesto, bajo el código (interruptor «Ver puestos»). */
  puesto?: string;
}

const CON_TOKEN = new Set(["M", "T", "C", "NC"]);

/** Celda de turno: letra en el color del turno (la noche, NC, es la única con relleno); «·» si libre; novedad (V/I/…) con borde punteado;
 *  esquina marcada si se editó a mano y borde rojo si falta cobertura. Códigos sin token propio llevan su color de fondo. */
export const Ficha = memo(function Ficha({ codigo, color, cambiada, novedad, faltante, puesto }: FichaProps) {
  const libre = codigo === "L";
  const propio = !libre && !CON_TOKEN.has(codigo) && color ? { background: `#${color}` } : undefined;
  return (
    <span
      className={cx("relative inline-flex h-[22px] min-w-7 items-center justify-center rounded-sm px-[3px] font-mono text-xs font-semibold text-primary",
        "data-[turno=M]:text-turno-M data-[turno=T]:text-turno-T data-[turno=C]:text-turno-C data-[turno=NC]:bg-turno-NC data-[turno=NC]:text-white",
        libre && "font-normal text-quaternary", novedad && "font-medium text-quaternary outline-1 -outline-offset-1 outline-dashed outline-fg-quaternary", faltante && "ring-2 ring-error")}
      data-turno={CON_TOKEN.has(codigo) ? codigo : undefined}
      style={propio}
    >
      {novedad ?? (libre ? "·" : codigo)}
      {puesto && <sup className="ml-px text-xs font-semibold">{puesto}</sup>}
      {cambiada && <span className="absolute top-0 right-0 size-0 rounded-tr-md border-t-[7px] border-l-[7px] border-t-fg-primary border-l-transparent" aria-hidden="true" />}
    </span>
  );
});
