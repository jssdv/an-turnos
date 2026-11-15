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
import { Alert } from "@/components/application/alerts/alert";
import { Button } from "@/components/base/buttons/button";

interface Resumen {
  cobertura: { dias_deficit: number; puestos_sin_cubrir: number }[];
  horas_extra: { ventana: number; semanas: { diurna: number; nocturna: number } }[];
  fatiga: Record<string, { senales: number }>;
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
  const editar = area.permiso === "editar";  // quien solo consulta no registra ni genera: sin pasos ni accesos de edición, como en el cuadro
  const nombre = new Map((personas.datos ?? []).map((c) => [c.id, c.nombre]));
  const ausentes = (novedades.datos ?? []).filter((n) => n.desde <= hoy && hoy <= n.hasta);
  // Libres hoy: activas, sin turno ni ausencia. Es a quién llamar primero si alguien falta (¿Quién cubre? afina con las reglas).
  const enCuadroHoy = !!cuadro.datos?.celdas.length && !!p && desde <= hoy && hoy <= hasta;
  const turnoHoy = new Map((cuadro.datos?.celdas ?? []).filter((c) => c.fecha === hoy).map((c) => [c.colab_id, c.turno]));
  const libres = enCuadroHoy ? (personas.datos ?? []).filter((c) => c.activo && (turnoHoy.get(c.id) ?? "L") === "L" && !ausentes.some((n) => n.colab_id === c.id)) : [];
  // Publicar con tiempo: el periodo siguiente debería estar publicado (o al menos creado) dos semanas antes de empezar.
  const dias = (a: string, b: string) => Math.round((Date.parse(a) - Date.parse(b)) / 86_400_000);
  const cuando = (fecha: string) => { const n = dias(fecha, hoy); return n === 0 ? "hoy" : n === 1 ? "mañana" : `en ${n} días`; };
  const siguiente = (periodos.datos ?? []).filter((x) => x.clave.split("/")[0] > hoy).sort((x, y) => x.clave.localeCompare(y.clave))[0];
  const recordatorio = !editar || !periodos.datos ? null
    : siguiente ? (!siguiente.publicado_en && dias(siguiente.clave.split("/")[0], hoy) <= 14
      ? `${nombrePeriodo(siguiente.clave)} empieza ${cuando(siguiente.clave.split("/")[0])} y aún no está publicado. Publicarlo con dos semanas deja tiempo para cambios y permutas.` : null)
    : p && hasta >= hoy && dias(hasta, hoy) <= 14 ? `El periodo actual termina ${cuando(hasta)} y no hay uno siguiente. Créalo y publícalo con tiempo desde «Cuadro de turnos».` : null;
  const errores = agrupar((alertas.datos ?? []).filter((a) => a.nivel === "error")).length;
  const noCumplidas = (solicitudes.datos ?? []).filter((s) => s.estado === "no cumplida").length;
  const cob = resumen.datos?.cobertura[0], extra = resumen.datos?.horas_extra[0];
  const cansados = resumen.datos ? Object.values(resumen.datos.fatiga).filter((f) => f.senales > 0).length : null;
  const horasExtra = extra ? Math.round(extra.semanas.diurna + extra.semanas.nocturna) : null;
  const alCuadro = () => ir(`${r}/cuadro${p ? `/${p.id}` : ""}`);
  const accesos = ([["Registrar ausencia", "novedades?nueva", CalendarMinus01], ["Nueva solicitud", "solicitudes?nueva", Inbox01], ["Descargar reportes", "reportes", FileDownload02]] as [string, string, FC<{ className?: string }>][])
    .filter(([, ruta]) => editar || !ruta.endsWith("?nueva"));

  return (
    <Pagina titulo="Inicio" sub={`Hola, ${usuario?.nombre?.split(" ")[0] ?? ""}${p ? ` · periodo ${nombrePeriodo(p.clave)}` : ""}`}
      filtros={<Button color="primary" size="sm" iconLeading={Calendar} onPress={alCuadro}>Ir al cuadro</Button>} error={periodos.error}>
      {periodos.datos && !p && <Seccion><p className="text-tertiary">Esta área aún no tiene periodos. Créalo desde «Cuadro de turnos» con «Nuevo periodo».</p></Seccion>}
      {recordatorio && <Alert color="warning" action={<Button color="secondary" size="sm" onPress={() => ir(`${r}/cuadro${siguiente ? `/${siguiente.id}` : ""}`)}>Ir al cuadro</Button>}>{recordatorio}</Alert>}
      {editar && p && cuadro.datos && alertas.datos && (
        <Pasos hay={cuadro.datos.celdas.length > 0} alertas={alertas.datos} publicado={!!p.publicado_en} alGenerar={alCuadro} alVerAlertas={() => ir(`${r}/cuadro/${p.id}?alertas`)} alPublicar={alCuadro} />
      )}
      {p && (
        <Indicadores etiqueta="Indicadores del periodo">
          <Indicador titulo="Por corregir" tono={errores ? "error" : undefined} valor={alertas.datos ? String(errores) : "…"} nota={errores ? "Alertas rojas en el cuadro" : "Sin errores en el cuadro"} />
          <Indicador titulo="Solicitudes" tono={noCumplidas ? "aviso" : undefined} valor={solicitudes.datos ? (solicitudes.datos.length ? `${noCumplidas} / ${solicitudes.datos.length}` : "0") : "…"} nota={solicitudes.datos?.length === 0 ? "Sin solicitudes este periodo" : "no cumplidas este periodo"} />
          <Indicador titulo="Cobertura" tono={cob && (cob.dias_deficit || cob.puestos_sin_cubrir) ? "aviso" : undefined} valor={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `${cob.dias_deficit} días` : "100 %") : "…"}
            nota={cob ? (cob.dias_deficit || cob.puestos_sin_cubrir ? `Con falta de personal · ${cob.puestos_sin_cubrir} puestos sin cubrir` : "Todos los puestos cubiertos") : "Calculando"} />
          <Indicador titulo="Horas extra" valor={horasExtra === null ? "…" : `${horasExtra} h`} nota={extra ? `Sobre el promedio de ${extra.ventana} semanas` : "Calculando"} />
          <Indicador titulo="Fatiga" tono={cansados ? "aviso" : undefined} valor={cansados === null ? "…" : String(cansados)}
            nota={cansados === null ? "Calculando" : cansados ? "personas con señales este periodo (ver Analíticas)" : "Sin señales este periodo"} />
        </Indicadores>
      )}
      <div className="grid gap-4 lg:grid-cols-2">
        <Seccion titulo="Ausentes hoy">
          {novedades.datos && !ausentes.length ? <p className="text-sm text-tertiary">Nadie está ausente hoy.</p> : (
          <Tabla descripcion="Personas ausentes hoy" cargando={!novedades.datos && !novedades.error} vacio="Nadie está ausente hoy." columnas={["Persona", "Ausencia", "Hasta"]}
            filas={ausentes.map((n) => [nombre.get(n.colab_id) ?? `#${n.colab_id}`, <Badge size="sm" color={COLOR_AUSENCIA[n.tipo] ?? "gray"}>{n.tipo}</Badge>, fechaCorta(n.hasta)])} />
          )}
        </Seccion>
        {enCuadroHoy && (
          <Seccion titulo={`Libres hoy (${libres.length})`}>
            <p className="mb-3 text-sm text-tertiary">Sin turno ni ausencia: a quién llamar primero si alguien falta.</p>
            {libres.length ? (
              <ul className="flex flex-wrap gap-2" aria-label="Personas libres hoy">
                {libres.map((c) => <li key={c.id}><Badge size="sm" color="gray">{c.nombre}</Badge></li>)}
              </ul>
            ) : <p className="text-sm text-tertiary">Hoy todo el personal activo tiene turno o ausencia.</p>}
          </Seccion>
        )}
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
