import type { FC } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { Calendar, CalendarMinus01, ChevronRight, FileDownload02, Inbox01 } from "@untitledui/icons";
import { Link } from "react-aria-components";
import { usar } from "../api/catalogos";
import type { Alerta, Area, Colaborador, Cuadro, EstadoSolicitud, Novedad, Periodo } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { useSesion } from "../Sesion";
import { agrupar, Indicador, Indicadores, Pagina, Pasos, Seccion } from "./comun";
import { fechaCorta, isoHoy, nombrePeriodo, vigente } from "./fechas";
import { Badge } from "@/components/base/badges/badges";
import { Button } from "@/components/base/buttons/button";

interface Resumen {
  cobertura: { dias_deficit: number; puestos_sin_cubrir: number }[];
  horas_extra: { ventana: number; semanas: { diurna: number; nocturna: number } }[];
}
const COLOR_AUSENCIA: Record<string, "warning" | "error" | "gray"> = { Vacaciones: "warning", Incapacidad: "error" };

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
    <Pagina titulo="Inicio" sub={`Hola, ${usuario?.nombre?.split(" ")[0] ?? ""}${p ? ` · periodo ${nombrePeriodo(p.clave)}` : ""}`}
      filtros={<Button color="primary" size="sm" iconLeading={Calendar} onPress={alCuadro}>Ir al cuadro</Button>} error={periodos.error}>
      {periodos.datos && !p && <Seccion><p className="text-tertiary">Esta área aún no tiene periodos. Créalo desde «Cuadro de turnos» con «Nuevo periodo».</p></Seccion>}
      {p && cuadro.datos && alertas.datos && (
        <Pasos hay={cuadro.datos.celdas.length > 0} alertas={alertas.datos} publicado={!!p.publicado_en} alGenerar={alCuadro} alVerAlertas={alCuadro} alPublicar={alCuadro} />
      )}
      {p && (
        <Indicadores etiqueta="Indicadores del periodo">
          <Indicador titulo="Por corregir" tono={errores ? "error" : undefined} valor={alertas.datos ? String(errores) : "…"} nota={errores ? "Alertas rojas en el cuadro" : "Sin errores en el cuadro"} />
          <Indicador titulo="Solicitudes" tono={noCumplidas ? "aviso" : undefined} valor={solicitudes.datos ? `${noCumplidas} / ${solicitudes.datos.length}` : "…"} nota="no cumplidas este periodo" />
          <Indicador titulo="Cobertura" tono={cob && (cob.dias_deficit || cob.puestos_sin_cubrir) ? "aviso" : undefined} valor={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `${cob.dias_deficit} días` : "100 %") : "…"}
            nota={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `Con falta de personal · ${cob.puestos_sin_cubrir} puestos sin cubrir` : "Todos los puestos cubiertos") : "Calculando"} />
          <Indicador titulo="Horas extra" valor={horasExtra === null ? "…" : `${horasExtra} h`} nota={extra ? `Sobre el promedio de ${extra.ventana} semanas` : "Calculando"} />
        </Indicadores>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Seccion titulo="Ausentes hoy">
          <Tabla descripcion="Personas ausentes hoy" cargando={!novedades.datos && !novedades.error} vacio="Nadie está ausente hoy." columnas={["Persona", "Ausencia", "Hasta"]}
            filas={ausentes.map((n) => [nombre.get(n.colab_id) ?? `#${n.colab_id}`, <Badge size="sm" color={COLOR_AUSENCIA[n.tipo] ?? "gray"}>{n.tipo}</Badge>, fechaCorta(n.hasta)])} />
        </Seccion>
        <Seccion titulo="Accesos rápidos">
          <ul className="-my-2 divide-y divide-secondary">
            {accesos.map(([t, ruta, Icono]) => (
              <li key={t}>
                <Link href={`${r}/${ruta}`} className="flex h-11 items-center gap-3 px-1 text-sm font-medium text-primary outline-focus-ring hover:text-brand-secondary focus-visible:outline-2">
                  <Icono aria-hidden="true" className="size-4.5 text-fg-quaternary" />{t}<ChevronRight aria-hidden="true" className="ml-auto size-4 text-fg-quaternary" />
                </Link>
              </li>
            ))}
          </ul>
        </Seccion>
      </div>
    </Pagina>
  );
}
