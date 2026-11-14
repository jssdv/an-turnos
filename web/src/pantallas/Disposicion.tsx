import { useEffect, useState, type FC } from "react";
import { Button as AriaButton } from "react-aria-components";
import { Navigate, NavLink, Outlet, useLocation, useNavigate, useParams } from "react-router";
import { BarChart03, Building02, Calendar, CalendarCheck01, CalendarMinus01, ChevronDown, FileDownload02, HelpCircle, Home02, Inbox01, LineChartUp01, LogOut01, SearchLg, Settings01, UserCheck01, Users01 } from "@untitledui/icons";
import { Alert } from "@/components/application/alerts/alert";
import { MobileNavigationHeader } from "@/components/application/app-navigation/base-components/mobile-header";
import { NavList } from "@/components/application/app-navigation/base-components/nav-list";
import { Button } from "@/components/base/buttons/button";
import { Dropdown } from "@/components/base/dropdown/dropdown";
import { NativeSelect } from "@/components/base/select/select-native";
import { cx } from "@/utils/cx";
import { leer } from "../api/cliente";
import type { Area } from "../api/tipos";
import { Campana, ProveedorAvisos, useCargarAvisos } from "../componentes/Avisos";
import { Tutorial } from "../componentes/Tutorial";
import { useSesion } from "../Sesion";
import { Ventana } from "./comun";
import { SECCIONES } from "./Radiologia";

type Icono = FC<{ className?: string }>;
/** Menú de Turnos, en el orden del rediseño (barra superior). Parámetros va en «Ajustes» junto a lo de administración. */
export const TURNOS: [string, string, Icono][] = [
  ["Inicio", "inicio", Home02], ["Cuadro", "cuadro", Calendar], ["Solicitudes", "solicitudes", Inbox01], ["Personal", "personal", Users01],
  ["Ausencias", "novedades", CalendarMinus01], ["Requerimiento", "puestos", Building02], ["Reportes", "reportes", FileDownload02],
  ["Analíticas", "analiticas", LineChartUp01], ["Parámetros", "parametros", Settings01],
];
const RADIOLOGIA: Record<string, Icono> = { resumen: Home02, previa: CalendarCheck01, alertas: BarChart03, equidad: LineChartUp01, agendas: Calendar, cambios: Inbox01 };
const AJUSTES = new Set(["parametros", "usuarios", "areas"]);
const iniciales = (n = "") => n.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase();
/** Última área visitada, para volver a ella desde `/areas`. */
const ultimaArea = (id?: number) => {
  try {
    if (id === undefined) return Number(localStorage.getItem("area"));
    localStorage.setItem("area", String(id));
  } catch { /* almacenamiento bloqueado: se abre la primera área */ }
  return NaN;
};
const sinTildes = (s: string) => s.normalize("NFD").replace(/\p{M}/gu, "").toLowerCase();

interface Destino { label: string; href: string; ruta: string; icon: Icono; badge?: number }

/** «Ir a…» con ⌘K / Ctrl+K: filtra secciones y áreas por nombre; Enter abre la primera coincidencia. */
function Buscador({ destinos }: { destinos: { label: string; grupo: string; href: string }[] }) {
  const [abierto, setAbierto] = useState(false);
  const [q, setQ] = useState("");
  const ir = useNavigate();
  useEffect(() => {
    const f = (e: KeyboardEvent) => { if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); setQ(""); setAbierto(true); } };
    addEventListener("keydown", f);
    return () => removeEventListener("keydown", f);
  }, []);
  const lista = destinos.filter((d) => sinTildes(`${d.label} ${d.grupo}`).includes(sinTildes(q.trim())));
  const abrir = (href: string) => { setAbierto(false); ir(href); };
  return (
    <>
      <AriaButton onPress={() => { setQ(""); setAbierto(true); }} aria-keyshortcuts="Meta+K Control+K"
        className="flex h-8 w-56 cursor-pointer items-center gap-2 rounded-xl bg-secondary px-2.5 text-sm text-placeholder ring-1 ring-secondary outline-focus-ring ring-inset hover:text-tertiary focus-visible:outline-2 focus-visible:outline-offset-2">
        <SearchLg aria-hidden="true" className="size-4" />Ir a…<kbd className="ml-auto rounded-sm px-1 font-mono text-xs text-tertiary ring-1 ring-primary ring-inset">⌘K</kbd>
      </AriaButton>
      <Ventana abierto={abierto} alCambiar={setAbierto} titulo="Ir a">
        <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} aria-label="Buscar sección o área" placeholder="Cuadro, Personal, Radiología…"
          onKeyDown={(e) => { if (e.key === "Enter" && lista[0]) abrir(lista[0].href); }}
          className="h-10 w-full rounded-lg bg-primary px-3 text-md text-primary ring-1 ring-primary outline-focus-ring ring-inset placeholder:text-placeholder focus-visible:outline-2" />
        <ul className="-mx-2 max-h-80 overflow-y-auto">
          {lista.map((d, i) => (
            <li key={d.href}>
              <button type="button" onClick={() => abrir(d.href)} className={cx("flex w-full cursor-pointer items-center justify-between rounded-md px-2 py-2 text-left text-sm text-primary outline-focus-ring hover:bg-primary_hover focus-visible:outline-2", i === 0 && q && "bg-secondary")}>
                {d.label}<span className="text-xs text-tertiary">{d.grupo}</span>
              </button>
            </li>
          ))}
          {!lista.length && <li className="px-2 py-2 text-sm text-tertiary">Nada con «{q}».</li>}
        </ul>
      </Ventana>
    </>
  );
}

/** Marco: barra superior (marca y área, secciones, Ir a…, avisos, ayuda, usuario); en móvil, cabecera con menú lateral.
 *  `/areas` vuelve a la última área visitada o elige la primera. */
export function Disposicion() {
  const { usuario, salir } = useSesion();
  const { area } = useParams();
  const { pathname } = useLocation();
  const ir = useNavigate();
  const [areas, setAreas] = useState<Area[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [tutorial, setTutorial] = useState(false);
  const actual = areas?.find((a) => a.id === Number(area));
  const avisos = useCargarAvisos(actual, pathname);

  useEffect(() => {
    leer<Area[]>("/api/areas").then(setAreas).catch((x) => setError(x.message));
  }, []);
  useEffect(() => { if (actual) ultimaArea(actual.id); }, [actual]);

  if (error) return <main className="p-6"><Alert color="error">{error}</Alert></main>;
  if (!areas) return <main className="p-6 text-tertiary" aria-busy="true">Cargando…</main>;
  const inicio = (a: Area) => `/areas/${a.id}/${a.tipo === "radiologia" ? "radiologia/resumen" : "inicio"}`;
  if (!area) {
    const ultima = ultimaArea();
    const primera = areas.find((a) => a.id === ultima) ?? areas.find((a) => a.tipo === "turnos") ?? areas[0];
    return primera ? <Navigate to={inicio(primera)} replace /> : <main className="p-6"><Alert>No tienes áreas asignadas. Pide acceso a quien administra tu clínica.</Alert></main>;
  }
  if (!actual) return <main className="p-6"><Alert color="error">No encontramos esa área, o aún no está disponible en la web.</Alert></main>;

  const base = `/areas/${actual.id}`;
  const admin: [string, string, Icono][] = usuario?.es_admin ? [["Usuarios", "usuarios", UserCheck01], ["Áreas", "areas", Building02]] : [];
  const todos: Destino[] = (actual.tipo === "radiologia"
    ? [...SECCIONES.map(([label, ruta]) => [label, `radiologia/${ruta}`, RADIOLOGIA[ruta]] as [string, string, Icono]), ...admin]
    : [...TURNOS, ...admin]
  ).map(([label, ruta, icon]) => ({ label, ruta, href: `${base}/${ruta}`, icon, badge: ruta === "solicitudes" && avisos.noCumplidas ? avisos.noCumplidas : undefined }));
  const principales = todos.filter((d) => !AJUSTES.has(d.ruta)), ajustes = todos.filter((d) => AJUSTES.has(d.ruta));
  const enAjustes = ajustes.some((d) => pathname.startsWith(d.href));
  const rol = usuario?.es_admin ? "Administrador" : actual.permiso === "editar" ? "Puede editar" : "Solo consulta";
  const cambiarArea = (id: string) => ir(inicio(areas.find((a) => a.id === Number(id))!));
  const pestana = (activa: boolean) => cx("flex shrink-0 items-center gap-1.5 border-b-2 text-sm font-medium whitespace-nowrap outline-focus-ring focus-visible:outline-2 focus-visible:-outline-offset-2",
    activa ? "border-fg-primary text-primary" : "border-transparent text-tertiary hover:text-primary");

  const movil = (
    <aside aria-label="Secciones" className="flex h-full w-full flex-col overflow-y-auto bg-primary p-3.5">
      <p className="px-2 pb-4 text-md font-semibold text-primary">An <span className="font-normal text-tertiary">· {actual.nombre}</span></p>
      <NavList activeUrl={todos.find((x) => pathname.startsWith(x.href))?.href}
        items={todos.map((d) => ({ label: d.label, href: d.href, icon: d.icon, badge: d.badge ? <span className="ml-3 font-mono text-xs font-semibold text-brand-secondary" aria-label={`${d.badge} no cumplidas`}>{d.badge}</span> : undefined }))}
        className="gap-1 px-0 pt-0" />
      <div className="mt-auto flex flex-col gap-3 pt-5">
        {areas.length > 1 && (
          <NativeSelect size="sm" aria-label="Cambiar de área" value={actual.id} onChange={(x) => cambiarArea(x.target.value)}>
            {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
          </NativeSelect>
        )}
        <Button color="secondary" size="sm" iconLeading={HelpCircle} onPress={() => setTutorial(true)}>Ayuda y tutorial</Button>
        <div className="flex items-center gap-3 border-t border-secondary px-1 pt-3">
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-semibold text-primary">{usuario?.nombre}</p>
            <p className="text-xs text-tertiary">{rol}</p>
          </div>
          <Button color="tertiary" size="sm" iconLeading={LogOut01} onPress={salir} aria-label="Salir" />
        </div>
      </div>
    </aside>
  );

  return (
    <ProveedorAvisos value={avisos}>
      <div className="flex h-full flex-col">
        <a className="saltar" href="#contenido">Saltar al contenido</a>
        <MobileNavigationHeader key={pathname} extra={<Campana />}>{movil}</MobileNavigationHeader>{/* key: al navegar, el menú móvil se cierra */}
        <header className="hidden h-12 shrink-0 items-stretch gap-6 border-b border-secondary bg-primary px-6 lg:flex" data-no-imprimir>
          <div className="flex shrink-0 items-center gap-2.5">
            <span className="text-md font-semibold text-primary">An</span>
            {areas.length > 1
              ? <select aria-label="Cambiar de área" value={actual.id} onChange={(x) => cambiarArea(x.target.value)}
                  className="cursor-pointer rounded-md border-l border-secondary bg-transparent py-1 pr-1 pl-2.5 text-sm text-tertiary outline-focus-ring hover:text-primary focus-visible:outline-2">
                  {areas.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
                </select>
              : <span className="border-l border-secondary pl-2.5 text-sm text-tertiary">{actual.nombre}</span>}
          </div>
          <nav aria-label="Secciones" className="flex min-w-0 items-stretch gap-5 overflow-x-auto">
            {principales.map((d) => (
              <NavLink key={d.href} to={d.href} className={({ isActive }) => pestana(isActive)}>
                {d.label}{d.badge && <span className="font-mono text-xs font-semibold text-brand-secondary" aria-label={`, ${d.badge} no cumplidas`}>{d.badge}</span>}
              </NavLink>
            ))}
            {ajustes.length > 0 && (
              <Dropdown.Root>
                <AriaButton className={cx(pestana(enAjustes), "cursor-pointer")}>Ajustes<ChevronDown aria-hidden="true" className="size-4" /></AriaButton>
                <Dropdown.Popover placement="bottom start" className="w-52">
                  <Dropdown.Menu>{ajustes.map((d) => <Dropdown.Item key={d.href} href={d.href} label={d.label} icon={d.icon} />)}</Dropdown.Menu>
                </Dropdown.Popover>
              </Dropdown.Root>
            )}
          </nav>
          <div className="ml-auto flex shrink-0 items-center gap-2">
            <Buscador destinos={[...todos.map((d) => ({ label: d.label, grupo: actual.nombre, href: d.href })), ...areas.filter((a) => a.id !== actual.id).map((a) => ({ label: a.nombre, grupo: "Área", href: inicio(a) }))]} />
            <Campana />
            <Button color="tertiary" size="sm" iconLeading={HelpCircle} aria-label="Ayuda y tutorial" onPress={() => setTutorial(true)} />
            <Dropdown.Root>
              <AriaButton aria-label={`Cuenta: ${usuario?.nombre ?? ""}`} className="grid size-8 cursor-pointer place-items-center rounded-full text-xs font-semibold text-tertiary ring-1 ring-primary outline-focus-ring ring-inset hover:text-primary focus-visible:outline-2 focus-visible:outline-offset-2">
                {iniciales(usuario?.nombre)}
              </AriaButton>
              <Dropdown.Popover placement="bottom end" className="w-60">
                <div className="border-b border-secondary px-4 py-3"><p className="truncate text-sm font-semibold text-primary">{usuario?.nombre}</p><p className="text-xs text-tertiary">{rol}</p></div>
                <Dropdown.Menu>
                  <Dropdown.Item href="/cambiar-clave" label="Cambiar contraseña" />
                  <Dropdown.Item onAction={salir} label="Salir" icon={LogOut01} />
                </Dropdown.Menu>
              </Dropdown.Popover>
            </Dropdown.Root>
          </div>
        </header>
        <main className="min-w-0 flex-1 overflow-auto px-4 pt-4 pb-6 outline-none lg:px-6 lg:pt-5 lg:pb-10" id="contenido" tabIndex={-1}>
          {actual.permiso !== "editar" && (
            <div className="mb-4" data-no-imprimir>
              <Alert>Modo consulta: puedes ver y exportar, pero no cambiar nada. Si necesitas editar, pídeselo a quien administra la clínica.</Alert>
            </div>
          )}
          <Outlet context={actual} />
        </main>
        <Tutorial abierto={tutorial} alCambiar={setTutorial} />
      </div>
    </ProveedorAvisos>
  );
}
