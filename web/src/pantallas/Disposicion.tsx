import { useEffect, useState } from "react";
import { Navigate, Outlet, useNavigate, useParams } from "react-router";
import { leer } from "../api/cliente";
import type { Area } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { SECCIONES } from "./Radiologia";
import { Lateral } from "../componentes/Lateral";
import { useSesion } from "../Sesion";
import e from "./Disposicion.module.css";

/** Marco con el menú lateral. `/areas` elige la primera área disponible. */
export function Disposicion() {
  const { usuario, salir } = useSesion();
  const { area } = useParams();
  const ir = useNavigate();
  const [areas, setAreas] = useState<Area[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leer<Area[]>("/api/areas").then(setAreas).catch((x) => setError(x.message));
  }, []);

  if (error) return <main className={e.principal}><Aviso nivel="error">{error}</Aviso></main>;
  if (!areas) return <main className={e.principal} aria-busy="true"><p className={e.vacio}>Cargando…</p></main>;
  const inicio = (a: Area) => `/areas/${a.id}/${a.tipo === "radiologia" ? "radiologia/resumen" : "cuadro"}`;
  if (!area) {
    const primera = areas.find((a) => a.tipo === "turnos") ?? areas[0];
    return primera ? <Navigate to={inicio(primera)} replace /> : <main className={e.principal}><Aviso>No tienes áreas asignadas. Pide acceso a quien administra tu clínica.</Aviso></main>;
  }
  const actual = areas.find((a) => a.id === Number(area));
  if (!actual) return <main className={e.principal}><Aviso nivel="error">No encontramos esa área.</Aviso></main>;

  return (
    <div className={e.marco}>
      <a className="saltar" href="#contenido">Saltar al contenido</a>
      <Lateral
        area={actual.nombre}
        entradas={actual.tipo === "radiologia" ? SECCIONES.map(([titulo, ruta]) => ({ titulo, a: `/areas/${actual.id}/radiologia/${ruta}` })) : [
          ...[["Cuadro", "cuadro"], ["Solicitudes", "solicitudes"], ["Personal", "personal"], ["Novedades", "novedades"], ["Puestos", "puestos"], ["Parámetros", "parametros"], ["Analíticas", "analiticas"],
            ...(usuario?.es_admin ? [["Usuarios", "usuarios"]] : [])].map(([titulo, ruta]) => ({ titulo, a: `/areas/${actual.id}/${ruta}` })),
        ]}
        usuario={usuario?.nombre ?? ""}
        pie={
          <>
            {areas.length > 1 && (
              <select aria-label="Cambiar de área" value={actual.id} onChange={(x) => ir(inicio(areas.find((a) => a.id === Number(x.target.value))!))}>
                {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
              </select>
            )}
            <Boton className={e["boton-lateral"]} onClick={salir}>Salir</Boton>
          </>
        }
      />
      <main className={e.principal} id="contenido" tabIndex={-1}>
        <Outlet context={actual} />
      </main>
    </div>
  );
}
