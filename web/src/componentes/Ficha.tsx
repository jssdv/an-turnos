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

/** Celda de turno: color del turno, esquina marcada si se editó a mano, novedad (V/I/…) y borde si falta cobertura. */
export const Ficha = memo(function Ficha({ codigo, color, cambiada, novedad, faltante, puesto }: FichaProps) {
  const libre = codigo === "L";
  const propio = !libre && !CON_TOKEN.has(codigo) && color ? { background: `#${color}` } : undefined;
  return (
    <span
      className={cx("relative inline-flex h-[22px] min-w-[22px] items-center justify-center rounded-sm bg-secondary px-[3px] text-[11px] font-bold text-primary",
        "data-[turno=M]:bg-(--turno-M) data-[turno=T]:bg-(--turno-T) data-[turno=C]:bg-(--turno-C) data-[turno=NC]:bg-(--turno-NC)",
        libre && "bg-transparent font-medium text-tertiary", novedad && "bg-utility-yellow-50 font-semibold text-utility-yellow-700", faltante && "ring-2 ring-error")}
      data-turno={CON_TOKEN.has(codigo) ? codigo : undefined}
      style={propio}
    >
      {novedad ?? codigo}
      {puesto && <sup className="ml-px text-[11px] font-semibold">{puesto}</sup>}
      {cambiada && <span className="absolute top-0 right-0 size-0 rounded-tr-sm border-t-[7px] border-l-[7px] border-t-fg-primary border-l-transparent" aria-hidden="true" />}
    </span>
  );
});
