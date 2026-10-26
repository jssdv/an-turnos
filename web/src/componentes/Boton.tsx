import type { ButtonHTMLAttributes } from "react";
import e from "./Boton.module.css";

interface Props extends ButtonHTMLAttributes<HTMLButtonElement> {
  variante?: "primario" | "secundario" | "peligro" | "texto";
}

export function Boton({ variante = "secundario", className, type = "button", ...r }: Props) {
  return <button type={type} className={`${e.boton} ${e[variante]} ${className ?? ""}`} {...r} />;
}
