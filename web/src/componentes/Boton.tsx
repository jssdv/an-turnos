import type { ButtonHTMLAttributes } from "react";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: "primario" | "secundario" | "peligro" | "texto";
}

const BASE = "inline-flex items-center justify-center gap-2 min-h-9 rounded-md border border-transparent font-semibold text-sm cursor-pointer " +
  "disabled:cursor-not-allowed disabled:bg-superficie-sutil disabled:text-deshabilitado disabled:border-borde";
const VARIANTE = {
  primario: "px-4 bg-acento text-superficie enabled:hover:bg-acento-hover",
  secundario: "px-4 bg-superficie text-titulo border-borde-control enabled:hover:bg-superficie-sutil",
  peligro: "px-4 bg-error text-superficie enabled:hover:bg-error-texto",
  texto: "bg-transparent text-acento px-2 enabled:hover:bg-acento-suave",
};

export function Boton({ variante = "secundario", className, type = "button", ...r }: Props) {
  return <button type={type} className={`${BASE} ${VARIANTE[variante]} ${className ?? ""}`} {...r} />;
}
