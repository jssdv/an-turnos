import type { ReactNode } from "react";
import e from "./Aviso.module.css";

interface Props {
  nivel?: "info" | "ok" | "aviso" | "error";
  children: ReactNode;
  accion?: ReactNode;
}

/** Banner en línea. `error` y `aviso` se anuncian de inmediato a lectores de pantalla; el resto, con calma. */
export function Aviso({ nivel = "info", children, accion }: Props) {
  return (
    <div className={`${e.caja} ${e[nivel === "aviso" ? "alerta" : nivel]}`} role={nivel === "error" ? "alert" : "status"}>
      <span>{children}</span>
      {accion}
    </div>
  );
}
