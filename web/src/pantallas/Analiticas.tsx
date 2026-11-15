import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { Download01, Printer } from "@untitledui/icons";
import { usar } from "../api/catalogos";
import { exportes } from "../api/exportes";
import type { Area } from "../api/tipos";
import { Barras, Linea, Mapa } from "../componentes/Graficos";
import { Tabla } from "../componentes/Tabla";
import { Indicador, Indicadores, Pagina, Seccion } from "./comun";
import { fechaCorta, nombrePeriodo, num } from "./fechas";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";

interface Datos {
  ausentismo: { pct: number; por_tipo: Record<string, number>; por_persona: Record<string, Record<string, number>>; por_mes: Record<string, Record<string, number>> };
  cobertura_tramos: { horas_requeridas: number; horas_faltantes: number; horas_sobrantes: number; cobertura_pct: number | null; eficiencia_pct: number | null; mapa: (number | null)[][];
    por_periodo: { periodo: string; horas_requeridas: number; horas_faltantes: number; horas_sobrantes: number }[] };
  cobertura: { periodo: string; dias_deficit: number; dias_exceso: number; puestos_sin_cubrir: number }[];
  simultaneos: { serie: [string, number][]; maximo: number; fecha_maximo: string | null; dias_riesgo: string[] };
  cambios: Record<string, { permuta: number; servicio: number; ajuste: number; excepciones: number }>;
  horas_extra: { periodo: string; ventana: number; mes: { diurna: number; nocturna: number }; semanas: { diurna: number; nocturna: number } }[];
  recargos: Record<string, { festivo: number; nocturna: number; equivalentes: number }>;
  equidad: { por_persona: Record<string, { noches: number; domingos: number; festivos: number }>; dispersion: { noches: number; domingos: number; festivos: number } };
  banco: { saldos: Record<string, number>; serie: [string, number, number][] };
  fatiga: Record<string, { max_dias_seguidos: number; rachas_largas: number; max_noches_seguidas: number; descansos_cortos: number; fines_trabajados: number; horas_4_sem_max: number; senales: number }>;
  patrones: { por_dia_semana: number[]; tras_festivo: number; bradford: { desde: string; equipo: Record<string, number>; por_persona: Record<string, { rachas: number; dias: number; puntaje: number }> } };
  estabilidad: { periodos: { periodo: string; celdas_cambiadas: number; celdas_total: number; pct: number; aviso_corto: number; dias_anticipacion: number }[]; cubre_mas: Record<string, number> };
}
const VACIO: Pick<Datos, "estabilidad" | "fatiga" | "patrones" | "cobertura_tramos"> = {
  cobertura_tramos: { horas_requeridas: 0, horas_faltantes: 0, horas_sobrantes: 0, cobertura_pct: null, eficiencia_pct: null, mapa: Array.from({ length: 7 }, () => Array(48).fill(null)), por_periodo: [] },
  estabilidad: { periodos: [], cubre_mas: {} }, fatiga: {},
  patrones: { por_dia_semana: [0, 0, 0, 0, 0, 0, 0], tras_festivo: 0, bradford: { desde: "", equipo: {}, por_persona: {} } },
};
const SEMANA = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
const TIPOS = ["Vacaciones", "Incapacidad", "Licencia", "Libre solicitado"];
const hoy = new Date();
const mes = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
/** Meses "AAAA-MM" de `a` a `b`, ambos incluidos (los meses sin ausencias no vienen en `por_mes`). */
const meses = (a: string, b: string) => {
  const out: string[] = [];
  for (let [y, n] = a.split("-").map(Number); `${y}-${String(n).padStart(2, "0")}` <= b; n === 12 ? (y++, n = 1) : n++) out.push(`${y}-${String(n).padStart(2, "0")}`);
  return out;
};
// Enlace normal, no de React Aria: su RouterProvider llevaría /api/... por react-router (igual que en Reportes).
const bajar = (href: string) => Object.assign(document.createElement("a"), { href, download: "" }).click();
const mesCorto = (m: string) => `${m.slice(5)}/${m.slice(2, 4)}`;
const ultimoDia = (m: string) => { const [y, n] = m.split("-").map(Number); return `${m}-${String(new Date(y, n, 0).getDate()).padStart(2, "0")}`; };

/** Solo lectura: ausentismo, cobertura, cambios, horas extra, recargos, equidad y banco de horas de un rango de meses. «Costo» = horas equivalentes. */
export function Analiticas() {
  const area = useOutletContext<Area>();
  const [desde, setDesde] = useState(mes(new Date(hoy.getFullYear(), hoy.getMonth() - 5, 1)));
  const [hasta, setHasta] = useState(mes(hoy));
  const ok = desde && hasta && desde <= hasta;
  const r = usar<Datos>(ok ? `/api/areas/${area.id}/analiticas?desde=${desde}-01&hasta=${ultimoDia(hasta)}` : null);
  const d = useMemo(() => r.datos && { ...VACIO, ...r.datos }, [r.datos]);  // un servidor sin actualizar no trae los bloques nuevos: vacíos, no pantalla en blanco
  const total = useMemo(() => d && {
    deficit: d.cobertura.reduce((s, c) => s + c.dias_deficit, 0),
    cambios: Object.values(d.cambios).reduce((s, c) => s + c.permuta + c.servicio + c.ajuste, 0),
    excepciones: Object.values(d.cambios).reduce((s, c) => s + c.excepciones, 0),
    ausencias: Object.values(d.ausentismo.por_tipo).reduce((s, x) => s + x, 0),
    cambiadas: d.estabilidad.periodos.reduce((s, p) => s + p.celdas_cambiadas, 0),
    celdas: d.estabilidad.periodos.reduce((s, p) => s + p.celdas_total, 0),
    avisoCorto: d.estabilidad.periodos.reduce((s, p) => s + p.aviso_corto, 0),
  }, [d]);

  return (
    <Pagina titulo={<>Analíticas<span className="hidden print:inline"> · {mesCorto(desde)} a {mesCorto(hasta)}</span></>}
      acciones={ok && d && <>
        <Button color="secondary" size="sm" iconLeading={Printer} onPress={() => window.print()}>Imprimir</Button>
        <Button color="secondary" size="sm" iconLeading={Download01} onPress={() => bajar(exportes.urlAnaliticas(area.id, `${desde}-01`, ultimoDia(hasta)))}>Descargar Excel</Button>
      </>}
      filtros={<div className="flex flex-wrap items-start gap-3">
        <Input className="w-48 [&_label]:sr-only" value={String(desde)} label="Desde (mes)" type="month" onChange={(x) => setDesde(x)} />
        <Input className="w-48 [&_label]:sr-only" value={String(hasta)} hint={ok ? null : "El mes final es anterior al inicial"} isInvalid={!ok} label="Hasta (mes)" type="month" onChange={(x) => setHasta(x)} />
      </div>} sub="Cifras de lo ya registrado. Solo se consulta: aquí no se cambia nada." ayuda={<>Elige el rango de meses. Arriba ves el resumen: <strong>ausentismo</strong> (porcentaje de días perdidos por ausencias), cuántas personas faltaron <strong>a la vez</strong>, días con <strong>déficit</strong> (faltó gente en algún puesto) y cambios de turno. Las tablas de abajo muestran el detalle por persona y por periodo.</>} error={r.error}>
      {!d || !total ? <p aria-busy="true">Cargando…</p> : (
        <div className="flex flex-col gap-4 print:[&_section]:break-inside-avoid">
          <Indicadores etiqueta="Resumen">
            <Indicador titulo="Ausentismo" valor={`${num(d.ausentismo.pct)} %`} nota={`${total.ausencias} días de ausencia`} />
            <Indicador titulo="Ausentes a la vez (máximo)" valor={String(d.simultaneos.maximo)} nota={d.simultaneos.fecha_maximo ? `El ${fechaCorta(d.simultaneos.fecha_maximo)}` : "Sin ausencias simultáneas"} />
            <Indicador titulo="Días con déficit" valor={String(total.deficit)} nota={`${d.simultaneos.dias_riesgo.length} con ausentes en riesgo`} />
            <Indicador titulo="Cambios de turno" valor={String(total.cambios)} nota={`${total.excepciones} con excepción`} />
            <Indicador titulo="Cambios tras publicar" valor={total.celdas ? `${num(total.cambiadas / total.celdas * 100)} %` : "—"}
              nota={total.celdas ? `${total.avisoCorto} con poco aviso` : "Sin periodos publicados"} />
          </Indicadores>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
            <Barras titulo="Equidad de domingos y festivos" unidad="días" datos={Object.entries(d.equidad.por_persona).map(([p, o]) => [p, o.domingos + o.festivos])} />
            <Barras titulo="Recargos por persona" unidad="h equivalentes" datos={Object.entries(d.recargos).map(([p, r2]) => [p, r2.equivalentes])} />
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
            <Linea titulo="Ausencias por mes" unidad="días" etiquetas={meses(desde, hasta).map(mesCorto)}
              series={TIPOS.map((t) => ({ nombre: t, valores: meses(desde, hasta).map((m) => d.ausentismo.por_mes[m]?.[t] ?? 0) })).filter((s) => s.valores.some(Boolean))} />
            <Linea titulo="Ausentes a la vez" unidad="personas" etiquetas={d.simultaneos.serie.map(([f]) => fechaCorta(f))}
              series={[{ nombre: "Ausentes", valores: d.simultaneos.serie.map(([, n]) => n) }]} />
            <Linea titulo="Banco de horas" unidad="h" etiquetas={d.banco.serie.map(([m]) => m)}
              series={[{ nombre: "A favor", valores: d.banco.serie.map(([, f]) => f) }, { nombre: "En deuda", valores: d.banco.serie.map(([, , x]) => x) }]} />
          </div>
          <Seccion titulo="Ausentismo por persona (días)">
            <Tabla descripcion="Ausencias por persona" vacio="Sin ausencias en el rango." columnas={["Persona", "Total", ...TIPOS]}
              filas={Object.entries(d.ausentismo.por_persona).sort().map(([p, t]) => [p, Object.values(t).reduce((s, x) => s + x, 0), ...TIPOS.map((x) => t[x] ?? 0)])} />
          </Seccion>
          <Seccion titulo="Patrones de ausencia (no planeadas)">
            <p className="mb-4 text-sm text-tertiary">Solo incapacidades y licencias: vacaciones y libres solicitados se planean. {d.patrones.tras_festivo === 1 ? "1 ausencia empezó" : `${d.patrones.tras_festivo} ausencias empezaron`} el día después de un festivo.</p>
            <div className="grid grid-cols-[minmax(0,1fr)] gap-6 lg:grid-cols-2">
              <ul className="flex flex-col gap-2.5" aria-label="Ausencias por día de la semana">
                {d.patrones.por_dia_semana.map((v, w) => (
                  <li key={w} className="grid grid-cols-[2.5rem_1fr_4rem] items-center gap-3 text-xs">
                    <span className="font-medium text-secondary">{SEMANA[w]}</span>
                    <span className="h-2.5 rounded-xs bg-secondary"><span className="block h-full rounded-xs bg-brand-600" style={{ width: `${(v / Math.max(0.0001, ...d.patrones.por_dia_semana)) * 100}%` }} /></span>
                    <span className="text-right text-tertiary tabular-nums">{num(v, 1)} %</span>
                  </li>
                ))}
              </ul>
              <Tabla descripcion="Factor Bradford del equipo (últimos 12 meses)" vacio="Sin personal." columnas={["Factor Bradford (12 meses)", "Personas"]}
                filas={Object.entries(d.patrones.bradford.equipo).map(([k, n]) => [k, n])} />
            </div>
            <h3 className="mt-6 mb-1 text-sm font-semibold text-primary">Factor Bradford por persona{d.patrones.bradford.desde && ` · 12 meses desde el ${fechaCorta(d.patrones.bradford.desde)}`}</h3>
            <p className="mb-3 text-xs text-tertiary">Ausencias² × días: pesa más faltar seguido y por poco que una sola ausencia larga. Indicador de patrones; no usar para sanciones.</p>
            <Tabla descripcion="Factor Bradford por persona" vacio="Sin ausencias no planeadas en el rango." columnas={["Persona", "Ausencias", "Días", "Puntaje"]}
              filas={Object.entries(d.patrones.bradford.por_persona).sort(([a, x], [b, y]) => y.puntaje - x.puntaje || a.localeCompare(b)).map(([p, o]) => [p, o.rachas, o.dias, o.puntaje])} />
          </Seccion>
          <Indicadores etiqueta="Cobertura por tramo de 30 minutos">
            <Indicador titulo="Cobertura" valor={d.cobertura_tramos.cobertura_pct === null ? "—" : `${num(d.cobertura_tramos.cobertura_pct)} %`} nota="de las horas obligatorias, tramo a tramo" />
            <Indicador titulo="Horas faltantes" tono={d.cobertura_tramos.horas_faltantes ? "aviso" : undefined} valor={`${num(d.cobertura_tramos.horas_faltantes, 1)} h`} nota="personas × horas por debajo de lo obligatorio" />
            <Indicador titulo="Horas sobrantes" valor={`${num(d.cobertura_tramos.horas_sobrantes, 1)} h`} nota="por encima de obligatorio + deseable" />
            <Indicador titulo="Eficiencia" valor={d.cobertura_tramos.eficiencia_pct === null ? "—" : `${num(d.cobertura_tramos.eficiencia_pct)} %`} nota="descuenta lo que falta y lo que sobra" />
          </Indicadores>
          <Mapa titulo="Cobertura por día y hora (promedio)" mapa={d.cobertura_tramos.mapa} />
          <Seccion titulo="Cobertura por periodo">
            <Tabla descripcion="Cobertura por periodo" vacio="Sin periodos en el rango." columnas={["Periodo", "Días con déficit", "Días con exceso", "Puestos sin cubrir", "Horas faltantes", "Horas sobrantes"]}
              filas={d.cobertura.map((c) => { const t = d.cobertura_tramos.por_periodo.find((x) => x.periodo === c.periodo); return [nombrePeriodo(c.periodo), c.dias_deficit, c.dias_exceso, c.puestos_sin_cubrir, t ? num(t.horas_faltantes, 1) : "—", t ? num(t.horas_sobrantes, 1) : "—"]; })} />
          </Seccion>
          <Seccion titulo="Cambios de turno por periodo">
            <Tabla descripcion="Cambios por periodo" vacio="Sin cambios registrados." columnas={["Periodo", "Permutas", "Servicio", "Ajustes", "Excepciones"]}
              filas={Object.entries(d.cambios).map(([k, c]) => [nombrePeriodo(k), c.permuta, c.servicio, c.ajuste, c.excepciones])} />
          </Seccion>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-2">
            <Seccion titulo="Estabilidad del cuadro">
              <p className="mb-3 text-sm text-tertiary">Cuánto cambió cada periodo después de publicarlo. Publicar con 14 días o más y cambiar poco da horarios predecibles.</p>
              <Tabla descripcion="Estabilidad por periodo" vacio="Sin periodos publicados en el rango." columnas={["Periodo", "% cambiado", "Celdas cambiadas", "Con poco aviso", "Publicado con (días)"]}
                filas={d.estabilidad.periodos.map((p) => [nombrePeriodo(p.periodo), `${num(p.pct)} %`, p.celdas_cambiadas, p.aviso_corto, p.dias_anticipacion])} />
            </Seccion>
            <Barras titulo="Quién cubre más" unidad="turnos" datos={Object.entries(d.estabilidad.cubre_mas)} />
          </div>
          <div className="grid grid-cols-[minmax(0,1fr)] gap-4 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <Seccion titulo="Señales de fatiga">
              <p className="mb-3 text-sm text-tertiary">Rachas largas, noches seguidas, descansos cortos entre turnos y fines de semana trabajados en el rango. Los topes se cambian en Parámetros → Analíticas.</p>
              <Tabla descripcion="Señales de fatiga por persona" vacio="Sin personal." columnas={["Persona", "Señales", "Días seguidos (máx.)", "Noches seguidas (máx.)", "Descansos cortos", "Fines trabajados", "Horas en 4 semanas (máx.)"]}
                filas={Object.entries(d.fatiga).sort(([a, x], [b, y]) => y.senales - x.senales || a.localeCompare(b))
                  .map(([p, f]) => [p, f.senales, f.max_dias_seguidos, f.max_noches_seguidas, f.descansos_cortos, f.fines_trabajados, num(f.horas_4_sem_max, 1)])} />
            </Seccion>
            <Barras titulo="Fines de semana trabajados" unidad="fines" datos={Object.entries(d.fatiga).map(([p, f]) => [p, f.fines_trabajados])} />
          </div>
          <Seccion titulo="Horas extra por periodo">
            <Tabla descripcion="Horas extra" vacio="Sin periodos en el rango." columnas={["Periodo", "Ventana (sem.)", "Diurnas (mes)", "Nocturnas (mes)", "Diurnas (ventana)", "Nocturnas (ventana)"]}
              filas={d.horas_extra.map((h) => [nombrePeriodo(h.periodo), h.ventana, num(h.mes.diurna), num(h.mes.nocturna), num(h.semanas.diurna), num(h.semanas.nocturna)])} />
          </Seccion>
          <Seccion titulo="Recargos (horas)">
            <Tabla descripcion="Recargos por persona" vacio="Sin recargos en el rango." columnas={["Persona", "Dominical/festivo", "Nocturno", "Equivalentes"]}
              filas={Object.entries(d.recargos).sort().map(([p, r2]) => [p, num(r2.festivo), num(r2.nocturna), num(r2.equivalentes)])} />
          </Seccion>
          <Seccion titulo="Equidad">
            <p>Diferencia entre quien más y quien menos tiene: {d.equidad.dispersion.noches} noches, {d.equidad.dispersion.domingos} domingos, {d.equidad.dispersion.festivos} festivos.</p>
            <Tabla descripcion="Equidad por persona" vacio="Sin personal." columnas={["Persona", "Noches", "Domingos", "Festivos"]}
              filas={Object.entries(d.equidad.por_persona).sort().map(([p, o]) => [p, o.noches, o.domingos, o.festivos])} />
          </Seccion>
          <Seccion titulo="Banco de horas (saldo al final del rango)">
            <Tabla descripcion="Saldos del banco" vacio="Sin saldos." columnas={["Persona", "Saldo (h)"]}
              filas={Object.entries(d.banco.saldos).sort().map(([p, s]) => [p, num(s)])} />
          </Seccion>
        </div>
      )}
    </Pagina>
  );
}
