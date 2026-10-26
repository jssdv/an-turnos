import { useEffect, useState, type FC } from "react";
import { Navigate, Outlet, useLocation, useNavigate, useParams } from "react-router";
import { BarChart03, Building02, Calendar, CalendarMinus01, Inbox01, LogOut01, Settings01, UserCheck01, Users01 } from "@untitledui/icons";
import { Alert } from "@/components/application/alerts/alert";
import { MobileNavigationHeader } from "@/components/application/app-navigation/base-components/mobile-header";
import { NavList } from "@/components/application/app-navigation/base-components/nav-list";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { AnLogo } from "@/components/foundations/logo/an-logo";
import { leer } from "../api/cliente";
import type { Area } from "../api/tipos";
import { useSesion } from "../Sesion";
import { SECCIONES } from "./Radiologia";

const TURNOS: [string, string, FC<{ className?: string }>][] = [
  ["Cuadro", "cuadro", Calendar], ["Solicitudes", "solicitudes", Inbox01], ["Personal", "personal", Users01], ["Ausencias", "novedades", CalendarMinus01],
  ["Puestos", "puestos", Building02], ["Reglas y turnos", "parametros", Settings01], ["Analíticas", "analiticas", BarChart03],
];

/** Marco con la navegación lateral de Untitled UI. `/areas` elige la primera área disponible. */
export function Disposicion() {
  const { usuario, salir } = useSesion();
  const { area } = useParams();
  const { pathname } = useLocation();
  const ir = useNavigate();
  const [areas, setAreas] = useState<Area[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    leer<Area[]>("/api/areas").then((x) => setAreas(x.filter((a) => a.tipo === "turnos"))).catch((x) => setError(x.message));
  }, []);

  if (error) return <main className="p-6"><Alert color="error">{error}</Alert></main>;
  if (!areas) return <main className="p-6 text-tertiary" aria-busy="true">Cargando…</main>;
  const inicio = (a: Area) => `/areas/${a.id}/${a.tipo === "radiologia" ? "radiologia/resumen" : "cuadro"}`;
  if (!area) {
    const primera = areas.find((a) => a.tipo === "turnos") ?? areas[0];
    return primera ? <Navigate to={inicio(primera)} replace /> : <main className="p-6"><Alert>No tienes áreas asignadas. Pide acceso a quien administra tu clínica.</Alert></main>;
  }
  const actual = areas.find((a) => a.id === Number(area));
  if (!actual) return <main className="p-6"><Alert color="error">No encontramos esa área, o aún no está disponible en la web.</Alert></main>;

  const base = `/areas/${actual.id}`;
  const items = actual.tipo === "radiologia"
    ? SECCIONES.map(([label, ruta]) => ({ label, href: `${base}/radiologia/${ruta}` }))
    : [...TURNOS, ...(usuario?.es_admin ? [["Usuarios", "usuarios", UserCheck01] as const] : [])].map(([label, ruta, icon]) => ({ label, href: `${base}/${ruta}`, icon }));
  const activo = items.find((x) => pathname.startsWith(x.href))?.href;

  const lateral = (
    <aside aria-label="Secciones" className="flex h-full w-full flex-col overflow-auto border-secondary bg-primary pt-5 lg:w-70 lg:border-r">
      <AnLogo area={actual.nombre} className="px-5" />
      <NavList activeUrl={activo} items={items} />
      <div className="mt-auto flex flex-col gap-3 border-t border-secondary px-5 py-5">
        {areas.length > 1 && (
          <NativeSelect size="sm" aria-label="Cambiar de área" value={actual.id} onChange={(x) => ir(inicio(areas.find((a) => a.id === Number(x.target.value))!))}>
            {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
          </NativeSelect>
        )}
        <div className="flex items-center justify-between gap-3">
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold text-primary">{usuario?.nombre}</p>
            <p className="text-sm text-tertiary">{actual.permiso === "editar" ? "Puede editar" : "Solo consulta"}</p>
          </div>
          <Button color="tertiary" size="sm" iconLeading={LogOut01} onPress={salir} aria-label="Salir">Salir</Button>
        </div>
      </div>
    </aside>
  );

  return (
    <div className="flex h-full flex-col lg:flex-row">
      <a className="saltar" href="#contenido">Saltar al contenido</a>
      <MobileNavigationHeader key={pathname}>{lateral}</MobileNavigationHeader>{/* key: al navegar, el menú móvil se cierra */}
      <div className="hidden lg:flex" data-no-imprimir>{lateral}</div>
      <main className="min-w-0 flex-1 overflow-auto bg-secondary px-4 py-6 outline-none lg:px-8" id="contenido" tabIndex={-1}>
        {actual.permiso !== "editar" && (
          <div className="mb-4" data-no-imprimir>
            <Alert>Modo consulta: puedes ver y exportar, pero no cambiar nada. Si necesitas editar, pídeselo a quien administra la clínica.</Alert>
          </div>
        )}
        <Outlet context={actual} />
      </main>
    </div>
  );
}
