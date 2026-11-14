import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { usar } from "../api/catalogos";
import type { Area } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Indicador, Indicadores, Pagina, Seccion } from "./comun";
import { fechaCorta, nombrePeriodo } from "./fechas";
import { Input } from "@/components/base/input/input";

interface Datos {
  ausentismo: { pct: number; por_tipo: Record<string, number>; por_persona: Record<string, Record<string, number>> };
  cobertura: { periodo: string; dias_deficit: number; dias_exceso: number; puestos_sin_cubrir: number }[];
  simultaneos: { maximo: number; fecha_maximo: string | null; dias_riesgo: string[] };
  cambios: Record<string, { permuta: number; servicio: number; ajuste: number; excepciones: number }>;
  horas_extra: { periodo: string; ventana: number; mes: { diurna: number; nocturna: number }; semanas: { diurna: number; nocturna: number } }[];
  recargos: Record<string, { festivo: number; nocturna: number; equivalentes: number }>;
  equidad: { por_persona: Record<string, { noches: number; domingos: number; festivos: number }>; dispersion: { noches: number; domingos: number; festivos: number } };
  banco: { saldos: Record<string, number> };
}
const TIPOS = ["Vacaciones", "Incapacidad", "Licencia", "Libre solicitado"];
const hoy = new Date();
const mes = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
const ultimoDia = (m: string) => { const [y, n] = m.split("-").map(Number); return `${m}-${String(new Date(y, n, 0).getDate()).padStart(2, "0")}`; };

/** Barras horizontales por persona (la más alta = 100 %), ordenadas de mayor a menor. */
function Barras({ titulo, unidad, datos }: { titulo: string; unidad: string; datos: [string, number][] }) {
  const max = Math.max(1, ...datos.map(([, v]) => v));
  return (
    <Seccion titulo={titulo}>
      {datos.length === 0 ? <p className="text-tertiary">Sin datos en el rango.</p> : (
        <ul className="flex flex-col gap-2.5" aria-label={titulo}>
          {[...datos].sort((a, b) => b[1] - a[1]).slice(0, 10).map(([p, v]) => (
            <li key={p} className="grid grid-cols-[minmax(0,9rem)_1fr_auto] items-center gap-3 text-xs">
              <span className="truncate font-medium text-secondary">{p}</span>
              <span className="h-2.5 rounded-xs bg-secondary"><span className="block h-full rounded-xs bg-brand-600" style={{ width: `${(v / max) * 100}%` }} /></span>
              <span className="text-tertiary tabular-nums">{v} {unidad}</span>
            </li>
          ))}
        </ul>
      )}
      {datos.length > 10 && <p className="mt-3 text-xs text-tertiary">Las 10 más altas de {datos.length}; el detalle completo está en las tablas de abajo.</p>}
    </Seccion>
  );
}

/** Solo lectura: ausentismo, cobertura, cambios, horas extra, recargos, equidad y banco de horas de un rango de meses. «Costo» = horas equivalentes. */
export function Analiticas() {
  const area = useOutletContext<Area>();
  const [desde, setDesde] = useState(mes(new Date(hoy.getFullYear(), hoy.getMonth() - 5, 1)));
  const [hasta, setHasta] = useState(mes(hoy));
  const ok = desde && hasta && desde <= hasta;
  const r = usar<Datos>(ok ? `/api/areas/${area.id}/analiticas?desde=${desde}-01&hasta=${ultimoDia(hasta)}` : null);
  const d = r.datos;
  const n = (x: number) => (Math.round(x * 100) / 100).toString();
  const total = useMemo(() => d && {
    deficit: d.cobertura.reduce((s, c) => s + c.dias_deficit, 0),
    cambios: Object.values(d.cambios).reduce((s, c) => s + c.permuta + c.servicio + c.ajuste, 0),
    excepciones: Object.values(d.cambios).reduce((s, c) => s + c.excepciones, 0),
    ausencias: Object.values(d.ausentismo.por_tipo).reduce((s, x) => s + x, 0),
  }, [d]);

  return (
    <Pagina titulo="Analíticas"
      filtros={<div className="flex flex-wrap items-start gap-3">
        <Input className="w-48 [&_label]:sr-only" value={String(desde)} label="Desde (mes)" type="month" onChange={(x) => setDesde(x)} />
        <Input className="w-48 [&_label]:sr-only" value={String(hasta)} hint={ok ? null : "El mes final es anterior al inicial"} isInvalid={!ok} label="Hasta (mes)" type="month" onChange={(x) => setHasta(x)} />
      </div>} sub="Cifras de lo ya registrado. Solo se consulta: aquí no se cambia nada." ayuda={<>Elige el rango de meses. Arriba ves el resumen: <strong>ausentismo</strong> (porcentaje de días perdidos por ausencias), cuántas personas faltaron <strong>a la vez</strong>, días con <strong>déficit</strong> (faltó gente en algún puesto) y cambios de turno. Las tablas de abajo muestran el detalle por persona y por periodo.</>} error={r.error}>
      {!d || !total ? <p aria-busy="true">Cargando…</p> : (
        <>
          <Indicadores etiqueta="Resumen">
            <Indicador titulo="Ausentismo" valor={`${n(d.ausentismo.pct)} %`} nota={`${total.ausencias} días de ausencia`} />
            <Indicador titulo="Ausentes a la vez (máximo)" valor={String(d.simultaneos.maximo)} nota={d.simultaneos.fecha_maximo ? `El ${fechaCorta(d.simultaneos.fecha_maximo)}` : "Sin ausencias simultáneas"} />
            <Indicador titulo="Días con déficit" valor={String(total.deficit)} nota={`${d.simultaneos.dias_riesgo.length} con ausentes en riesgo`} />
            <Indicador titulo="Cambios de turno" valor={String(total.cambios)} nota={`${total.excepciones} con excepción`} />
          </Indicadores>
          <div className="grid gap-4 lg:grid-cols-2">
            <Barras titulo="Equidad de domingos y festivos" unidad="días" datos={Object.entries(d.equidad.por_persona).map(([p, o]) => [p, o.domingos + o.festivos])} />
            <Barras titulo="Recargos por persona" unidad="h equivalentes" datos={Object.entries(d.recargos).map(([p, r2]) => [p, Math.round(r2.equivalentes * 10) / 10])} />
          </div>
          <Seccion titulo="Ausentismo por persona (días)">
            <Tabla descripcion="Ausencias por persona" vacio="Sin ausencias en el rango." columnas={["Persona", "Total", ...TIPOS]}
              filas={Object.entries(d.ausentismo.por_persona).sort().map(([p, t]) => [p, Object.values(t).reduce((s, x) => s + x, 0), ...TIPOS.map((x) => t[x] ?? 0)])} />
          </Seccion>
          <Seccion titulo="Cobertura por periodo">
            <Tabla descripcion="Cobertura por periodo" vacio="Sin periodos en el rango." columnas={["Periodo", "Días con déficit", "Días con exceso", "Puestos sin cubrir"]}
              filas={d.cobertura.map((c) => [nombrePeriodo(c.periodo), c.dias_deficit, c.dias_exceso, c.puestos_sin_cubrir])} />
          </Seccion>
          <Seccion titulo="Cambios de turno por periodo">
            <Tabla descripcion="Cambios por periodo" vacio="Sin cambios registrados." columnas={["Periodo", "Permutas", "Servicio", "Ajustes", "Excepciones"]}
              filas={Object.entries(d.cambios).map(([k, c]) => [nombrePeriodo(k), c.permuta, c.servicio, c.ajuste, c.excepciones])} />
          </Seccion>
          <Seccion titulo="Horas extra por periodo">
            <Tabla descripcion="Horas extra" vacio="Sin periodos en el rango." columnas={["Periodo", "Ventana (sem.)", "Diurnas (mes)", "Nocturnas (mes)", "Diurnas (ventana)", "Nocturnas (ventana)"]}
              filas={d.horas_extra.map((h) => [nombrePeriodo(h.periodo), h.ventana, n(h.mes.diurna), n(h.mes.nocturna), n(h.semanas.diurna), n(h.semanas.nocturna)])} />
          </Seccion>
          <Seccion titulo="Recargos (horas)">
            <Tabla descripcion="Recargos por persona" vacio="Sin recargos en el rango." columnas={["Persona", "Dominical/festivo", "Nocturno", "Equivalentes"]}
              filas={Object.entries(d.recargos).sort().map(([p, r2]) => [p, n(r2.festivo), n(r2.nocturna), n(r2.equivalentes)])} />
          </Seccion>
          <Seccion titulo="Equidad">
            <p>Diferencia entre quien más y quien menos tiene: {d.equidad.dispersion.noches} noches, {d.equidad.dispersion.domingos} domingos, {d.equidad.dispersion.festivos} festivos.</p>
            <Tabla descripcion="Equidad por persona" vacio="Sin personal." columnas={["Persona", "Noches", "Domingos", "Festivos"]}
              filas={Object.entries(d.equidad.por_persona).sort().map(([p, o]) => [p, o.noches, o.domingos, o.festivos])} />
          </Seccion>
          <Seccion titulo="Banco de horas (saldo al final del rango)">
            <Tabla descripcion="Saldos del banco" vacio="Sin saldos." columnas={["Persona", "Saldo (h)"]}
              filas={Object.entries(d.banco.saldos).sort().map(([p, s]) => [p, n(s)])} />
          </Seccion>
        </>
      )}
    </Pagina>
  );
}
