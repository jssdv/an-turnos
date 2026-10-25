import type { HTMLAttributes, ReactNode } from "react";
import e from "./Tarjeta.module.css";

interface Props extends HTMLAttributes<HTMLElement> {
  titulo?: ReactNode;
  acciones?: ReactNode;
}

export function Tarjeta({ titulo, acciones, children, className, ...r }: Props) {
  return (
    <section className={`${e.tarjeta} ${className ?? ""}`} {...r}>
      {(titulo || acciones) && (
        <header className={e.cabeza}>
          <h2 className={e.titulo}>{titulo}</h2>
          {acciones}
        </header>
      )}
      {children}
    </section>
  );
}
