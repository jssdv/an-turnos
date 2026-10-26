import { useId, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes } from "react";
import e from "./Campo.module.css";

interface Comun {
  etiqueta: string;
  error?: string | null;
  ayuda?: ReactNode;
}

/** Texto, número, fecha o contraseña según `type`. */
export function Campo({ etiqueta, error, ayuda, ...r }: Comun & InputHTMLAttributes<HTMLInputElement>) {
  const id = useId();
  return (
    <div className={e.campo}>
      <label htmlFor={id} className={e.etiqueta}>{etiqueta}</label>
      <input id={id} className={e.control} aria-invalid={!!error} aria-describedby={`${id}-d`} {...r} />
      <span id={`${id}-d`} className={error ? e.error : e.ayuda}>{error ?? ayuda}</span>
    </div>
  );
}

export function Seleccion({ etiqueta, error, ayuda, children, ...r }: Comun & SelectHTMLAttributes<HTMLSelectElement>) {
  const id = useId();
  return (
    <div className={e.campo}>
      <label htmlFor={id} className={e.etiqueta}>{etiqueta}</label>
      <select id={id} className={e.control} aria-invalid={!!error} aria-describedby={`${id}-d`} {...r}>{children}</select>
      <span id={`${id}-d`} className={error ? e.error : e.ayuda}>{error ?? ayuda}</span>
    </div>
  );
}
