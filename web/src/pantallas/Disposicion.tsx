import { useEffect, useState, type FC } from "react";
import { Navigate, Outlet, useLocation, useNavigate, useParams } from "react-router";
import { BarChart03, Building02, Calendar, CalendarCheck01, CalendarMinus01, ChevronLeft, ChevronRight, FileDownload02, Headphones02, Home02, Inbox01, LineChartUp01, LogOut01, PlayCircle, Settings01, UserCheck01, Users01 } from "@untitledui/icons";
import { Alert } from "@/components/application/alerts/alert";
import { MobileNavigationHeader } from "@/components/application/app-navigation/base-components/mobile-header";
import { NavList } from "@/components/application/app-navigation/base-components/nav-list";
import { Avatar } from "@/components/base/avatar/avatar";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { AnLogo } from "@/components/foundations/logo/an-logo";
import { cx } from "@/utils/cx";
import { leer } from "../api/cliente";
import type { Area } from "../api/tipos";
import { ProveedorAvisos, useCargarAvisos } from "../componentes/Avisos";
import { Tutorial } from "../componentes/Tutorial";
import { useSesion } from "../Sesion";
import { SECCIONES } from "./Radiologia";

type Icono = FC<{ className?: string }>;
/** Menú de Turnos, en el orden del rediseño. El ícono de cada sección se repite en el encabezado de su pantalla. */
export const TURNOS: [string, string, Icono][] = [
  ["Inicio", "inicio", Home02], ["Cuadro de turnos", "cuadro", Calendar], ["Solicitudes", "solicitudes", Inbox01], ["Personal", "personal", Users01],
  ["Ausencias", "novedades", CalendarMinus01], ["Requerimiento", "puestos", Building02], ["Reportes", "reportes", FileDownload02],
  ["Parámetros", "parametros", Settings01], ["Analíticas", "analiticas", LineChartUp01],
];
const RADIOLOGIA: Record<string, Icono> = { resumen: Home02, previa: CalendarCheck01, alertas: BarChart03, equidad: LineChartUp01, agendas: Calendar, cambios: Inbox01 };
const iniciales = (n = "") => n.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
const recordar = (v?: boolean) => {
  try {
    if (v === undefined) return localStorage.getItem("menu") === "plegado";
    localStorage.setItem("menu", v ? "plegado" : "abierto");
  } catch { /* almacenamiento bloqueado: el menú arranca abierto */ }
  return false;
};

/** Marco: barra lateral flotante (menú, tutorial, usuario), campana y ayuda flotante. `/areas` elige la primera área disponible. */
export function Disposicion() {
  const { usuario, salir } = useSesion();
  const { area } = useParams();
  const { pathname } = useLocation();
  const ir = useNavigate();
  const [areas, setAreas] = useState<Area[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [plegada, setPlegada] = useState(() => recordar());
  const [tutorial, setTutorial] = useState(false);
  const actual = areas?.find((a) => a.id === Number(area));
  const avisos = useCargarAvisos(actual, pathname);

  useEffect(() => {
    leer<Area[]>("/api/areas").then((x) => setAreas(x.filter((a) => a.tipo === "turnos"))).catch((x) => setError(x.message));
  }, []);

  if (error) return <main className="p-6"><Alert color="error">{error}</Alert></main>;
  if (!areas) return <main className="p-6 text-tertiary" aria-busy="true">Cargando…</main>;
  const inicio = (a: Area) => `/areas/${a.id}/${a.tipo === "radiologia" ? "radiologia/resumen" : "inicio"}`;
  if (!area) {
    const primera = areas.find((a) => a.tipo === "turnos") ?? areas[0];
    return primera ? <Navigate to={inicio(primera)} replace /> : <main className="p-6"><Alert>No tienes áreas asignadas. Pide acceso a quien administra tu clínica.</Alert></main>;
  }
  if (!actual) return <main className="p-6"><Alert color="error">No encontramos esa área, o aún no está disponible en la web.</Alert></main>;

  const base = `/areas/${actual.id}`;
  const items = actual.tipo === "radiologia"
    ? SECCIONES.map(([label, ruta]) => ({ label, href: `${base}/radiologia/${ruta}`, icon: RADIOLOGIA[ruta] }))
    : [...TURNOS, ...(usuario?.es_admin ? [["Usuarios", "usuarios", UserCheck01] as const] : [])].map(([label, ruta, icon]) => ({
      label, href: `${base}/${ruta}`, icon, badge: ruta === "solicitudes" && avisos.noCumplidas ? <span data-texto className="ml-3 rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white" aria-label={`${avisos.noCumplidas} no cumplidas`}>{avisos.noCumplidas}</span> : undefined,
    }));
  const activo = items.find((x) => pathname.startsWith(x.href))?.href;
  const plegar = (v: boolean) => { setPlegada(v); recordar(v); };

  const lateral = (movil: boolean) => {
    const p = plegada && !movil;
    return (
      <aside aria-label="Secciones" className={cx("tarjeta flex h-full flex-col overflow-y-auto p-3.5", p ? "w-20 [&_[data-texto]]:sr-only" : "w-full lg:w-66", movil && "rounded-none")}>
        <div className={cx("flex items-center gap-2 px-1 pb-5", p && "flex-col")}>
          <AnLogo area={actual.nombre} plegado={p} />
          {!movil && <Button color="tertiary" size="sm" className="ml-auto" aria-label={p ? "Mostrar el menú completo" : "Plegar el menú"} iconLeading={p ? ChevronRight : ChevronLeft} onPress={() => plegar(!p)} />}
        </div>
        <NavList activeUrl={activo} items={items} className="gap-1 px-0 pt-0" />
        <div className="mt-auto flex flex-col gap-3 pt-5">
          {!p && (
            <div className="flex flex-col items-center gap-2.5 rounded-2xl bg-linear-to-b from-brand-50 to-primary p-4 text-center ring-1 ring-brand-100 ring-inset">
              <span className="grid size-12 place-items-center rounded-2xl bg-primary text-brand-600 shadow-sm" aria-hidden="true"><CalendarCheck01 className="size-6" /></span>
              <p className="text-sm font-medium text-secondary">Tu equipo, siempre en el mejor turno</p>
              <Button color="secondary" size="sm" iconLeading={PlayCircle} onPress={() => setTutorial(true)}>Ver tutorial</Button>
            </div>
          )}
          {areas.length > 1 && !p && (
            <NativeSelect size="sm" aria-label="Cambiar de área" value={actual.id} onChange={(x) => ir(inicio(areas.find((a) => a.id === Number(x.target.value))!))}>
              {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </NativeSelect>
          )}
          <div className={cx("flex items-center gap-3 border-t border-secondary px-1 pt-3", p && "flex-col")}>
            <Avatar size="md" initials={iniciales(usuario?.nombre)} contentClassName="bg-brand-100 text-brand-700" />
            <div className={cx("min-w-0 flex-1", p && "sr-only")}>
              <p className="truncate text-sm font-semibold text-primary">{usuario?.nombre}</p>
              <p className="text-xs text-tertiary">{usuario?.es_admin ? "Administrador" : actual.permiso === "editar" ? "Puede editar" : "Solo consulta"}</p>
            </div>
            <Button color="tertiary" size="sm" iconLeading={LogOut01} onPress={salir} aria-label="Salir" />
          </div>
        </div>
      </aside>
    );
  };

  return (
    <ProveedorAvisos value={avisos}>
      <div className="flex h-full flex-col lg:flex-row lg:gap-5 lg:p-5">
        <a className="saltar" href="#contenido">Saltar al contenido</a>
        <MobileNavigationHeader key={pathname}>{lateral(true)}</MobileNavigationHeader>{/* key: al navegar, el menú móvil se cierra */}
        <div className="hidden lg:flex" data-no-imprimir>{lateral(false)}</div>
        <main className="min-w-0 flex-1 overflow-auto px-4 py-4 outline-none lg:px-0 lg:py-0" id="contenido" tabIndex={-1}>
          {actual.permiso !== "editar" && (
            <div className="mb-4" data-no-imprimir>
              <Alert>Modo consulta: puedes ver y exportar, pero no cambiar nada. Si necesitas editar, pídeselo a quien administra la clínica.</Alert>
            </div>
          )}
          <Outlet context={actual} />
        </main>
        <Button color="primary" size="sm" iconLeading={Headphones02} aria-label="Ayuda y tutorial" onPress={() => setTutorial(true)}
          className="fixed right-5 bottom-5 z-30 size-13 rounded-full shadow-lg" data-no-imprimir />
        <Tutorial abierto={tutorial} alCambiar={setTutorial} />
      </div>
    </ProveedorAvisos>
  );
}
