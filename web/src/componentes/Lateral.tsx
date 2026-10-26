import type { ReactNode } from "react";
import { NavLink } from "react-router";
import e from "./Lateral.module.css";

export interface Entrada {
  titulo: string;
  a: string;
  insignia?: number;
}
interface Props {
  area: string;
  entradas: Entrada[];
  usuario: string;
  rol?: string;
  pie?: ReactNode;
}

/** Menú del área: marca, secciones con insignias y usuario. Todas las áreas lo usan tal cual. */
export function Lateral({ area, entradas, usuario, rol, pie }: Props) {
  return (
    <aside className={e.lateral}>
      <div className={e.marca}>
        <span className={e.logo} aria-hidden="true">An</span>
        <div>
          <div className={e.nombre}>An</div>
          <div className={e.area}>{area}</div>
        </div>
      </div>
      <nav aria-label="Secciones">
        <div className={e.campo}>SECCIONES</div>
        <ul className={e.lista}>
          {entradas.map((x) => (
            <li key={x.a}>
              <NavLink to={x.a} className={({ isActive }) => `${e.enlace} ${isActive ? e.activo : ""}`}>
                {x.titulo}
                {!!x.insignia && <span className={e.insignia}>{x.insignia}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>
      <div className={e.usuario}>
        <div><div className={e.usuarioNombre}>{usuario}</div>{rol && <div className={e.rol}>{rol}</div>}</div>
        {pie}
      </div>
    </aside>
  );
}
