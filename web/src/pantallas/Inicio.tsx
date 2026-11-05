import type { FC } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { AlertTriangle, Calendar, CalendarMinus01, CheckCircle, ChevronRight, FileDownload02, Home02, Inbox01, LineChartUp01 } from "@untitledui/icons";
import { Link } from "react-aria-components";
import { usar } from "../api/catalogos";
import type { Alerta, Area, Colaborador, Cuadro, EstadoSolicitud, Novedad, Periodo } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { useSesion } from "../Sesion";
import { agrupar, Pagina, Pasos, Seccion } from "./comun";
import { fechaCorta, isoHoy, nombrePeriodo, vigente } from "./fechas";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";

interface Resumen {
  cobertura: { dias_deficit: number; puestos_sin_cubrir: number }[];
  horas_extra: { ventana: number; semanas: { diurna: number; nocturna: number } }[];
}
const COLOR_AUSENCIA: Record<string, "warning" | "error" | "gray"> = { Vacaciones: "warning", Incapacidad: "error" };

function Indicador({ icono: Icono, titulo, valor, nota }: { icono: FC<{ className?: string }>; titulo: string; valor: string; nota: string }) {
  return (
    <div className="tarjeta flex flex-col gap-3 p-5" role="listitem">
      <span className="flex items-center gap-2.5 text-sm font-medium text-tertiary">
        <span className="grid size-9 place-items-center rounded-lg bg-brand-50 text-brand-600" aria-hidden="true"><Icono className="size-4.5" /></span>{titulo}
      </span>
      <strong className="text-display-xs font-semibold text-primary">{valor}</strong>
      <span className="text-xs text-tertiary">{nota}</span>
    </div>
  );
}

/** Resumen del periodo vigente: pasos, indicadores, ausentes de hoy y accesos rápidos. Solo lee lo que ya existe. */
export function Inicio() {
  const area = useOutletContext<Area>();
  const { usuario } = useSesion();
  const ir = useNavigate();
  const b = `/api/areas/${area.id}`, r = `/areas/${area.id}`;
  const periodos = usar<Periodo[]>(`${b}/periodos`);
  const p = periodos.datos ? vigente(periodos.datos) : null;
  const [desde, hasta] = p?.clave.split("/") ?? [];
  const cuadro = usar<Cuadro>(p ? `${b}/periodos/${p.id}/cuadro?version=cambios` : null);
  const alertas = usar<Alerta[]>(p ? `${b}/periodos/${p.id}/alertas` : null);
  const solicitudes = usar<EstadoSolicitud[]>(p ? `${b}/periodos/${p.id}/solicitudes` : null);
  const resumen = usar<Resumen>(p ? `${b}/analiticas?desde=${desde}&hasta=${hasta}` : null);
  const novedades = usar<Novedad[]>(`${b}/novedades`);
  const personas = usar<Colaborador[]>(`${b}/colaboradores`);
  const hoy = isoHoy();
  const nombre = new Map((personas.datos ?? []).map((c) => [c.id, c.nombre]));
  const ausentes = (novedades.datos ?? []).filter((n) => n.desde <= hoy && hoy <= n.hasta);
  const errores = agrupar((alertas.datos ?? []).filter((a) => a.nivel === "error")).length;
  const noCumplidas = (solicitudes.datos ?? []).filter((s) => s.estado === "no cumplida").length;
  const cob = resumen.datos?.cobertura[0], extra = resumen.datos?.horas_extra[0];
  const horasExtra = extra ? Math.round(extra.semanas.diurna + extra.semanas.nocturna) : null;
  const alCuadro = () => ir(`${r}/cuadro${p ? `/${p.id}` : ""}`);
  const accesos: [string, string, FC<{ className?: string }>][] = [["Ver el cuadro", `cuadro${p ? `/${p.id}` : ""}`, Calendar], ["Registrar ausencia", "novedades", CalendarMinus01], ["Nueva solicitud", "solicitudes", Inbox01], ["Descargar reportes", "reportes", FileDownload02]];

  return (
    <Pagina titulo="Inicio" icono={Home02} sub={`Hola, ${usuario?.nombre?.split(" ")[0] ?? ""}${p ? ` · periodo ${nombrePeriodo(p.clave)}` : ""}`}
      filtros={<Button color="primary" size="sm" iconLeading={Calendar} onPress={alCuadro}>Ir al cuadro</Button>} error={periodos.error}>
      {periodos.datos && !p && <Seccion><p className="text-tertiary">Esta área aún no tiene periodos. Créalo desde «Cuadro de turnos» con «Nuevo periodo».</p></Seccion>}
      {p && cuadro.datos && alertas.datos && (
        <Pasos hay={cuadro.datos.celdas.length > 0} alertas={alertas.datos} publicado={!!p.publicado_en} alGenerar={alCuadro} alVerAlertas={alCuadro} alPublicar={alCuadro} />
      )}
      {p && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-4" role="list" aria-label="Indicadores del periodo">
          <Indicador icono={AlertTriangle} titulo="Por corregir" valor={alertas.datos ? String(errores) : "…"} nota={errores ? "Alertas rojas en el cuadro" : "Sin errores en el cuadro"} />
          <Indicador icono={Inbox01} titulo="Solicitudes no cumplidas" valor={solicitudes.datos ? String(noCumplidas) : "…"} nota={`De ${solicitudes.datos?.length ?? 0} evaluadas este periodo`} />
          <Indicador icono={CheckCircle} titulo="Cobertura" valor={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `${cob.dias_deficit} días` : "100 %") : "…"}
            nota={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `Con falta de personal · ${cob.puestos_sin_cubrir} puestos sin cubrir` : "Todos los puestos cubiertos") : "Calculando"} />
          <Indicador icono={LineChartUp01} titulo="Horas extra" valor={horasExtra === null ? "…" : `${horasExtra} h`} nota={extra ? `Sobre el promedio de ${extra.ventana} semanas` : "Calculando"} />
        </div>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Seccion titulo="Ausentes hoy">
          <Tabla descripcion="Personas ausentes hoy" cargando={!novedades.datos && !novedades.error} vacio="Nadie está ausente hoy." columnas={["Persona", "Ausencia", "Hasta"]}
            filas={ausentes.map((n) => [nombre.get(n.colab_id) ?? `#${n.colab_id}`, <Badge size="sm" color={COLOR_AUSENCIA[n.tipo] ?? "gray"}>{n.tipo}</Badge>, fechaCorta(n.hasta)])} />
        </Seccion>
        <Seccion titulo="Accesos rápidos">
          <div className="grid gap-3 sm:grid-cols-2">
            {accesos.map(([t, ruta, Icono]) => (
              <Link key={t} href={`${r}/${ruta}`} className="flex h-16 items-center gap-3 rounded-2xl bg-brand-25 px-4 text-sm font-semibold text-secondary ring-1 ring-brand-100 outline-focus-ring ring-inset hover:bg-brand-50 focus-visible:outline-2">
                <Icono aria-hidden="true" className="size-5 text-brand-600" />{t}<ChevronRight aria-hidden="true" className="ml-auto size-4.5 text-fg-quaternary" />
              </Link>
            ))}
          </div>
        </Seccion>
      </div>
    </Pagina>
  );
}
