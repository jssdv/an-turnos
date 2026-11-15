import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { usar } from "../api/catalogos";
import type { Area } from "../api/tipos";
import { Barras, Linea } from "../componentes/Graficos";
import { Tabla } from "../componentes/Tabla";
import { Indicador, Indicadores, Pagina, Seccion } from "./comun";
import { fechaCorta, nombrePeriodo, num } from "./fechas";
import { Input } from "@/components/base/input/input";

interface Datos {
  ausentismo: { pct: number; por_tipo: Record<string, number>; por_persona: Record<string, Record<string, number>>; por_mes: Record<string, Record<string, number>> };
  cobertura: { periodo: string; dias_deficit: number; dias_exceso: number; puestos_sin_cubrir: number }[];
  simultaneos: { serie: [string, number][]; maximo: number; fecha_maximo: string | null; dias_riesgo: string[] };
  cambios: Record<string, { permuta: number; servicio: number; ajuste: number; excepciones: number }>;
  horas_extra: { periodo: string; ventana: number; mes: { diurna: number; nocturna: number }; semanas: { diurna: number; nocturna: number } }[];
  recargos: Record<string, { festivo: number; nocturna: number; equivalentes: number }>;
  equidad: { por_persona: Record<string, { noches: number; domingos: number; festivos: number }>; dispersion: { noches: number; domingos: number; festivos: number } };
  banco: { saldos: Record<string, number>; serie: [string, number, number][] };
}
const TIPOS = ["Vacaciones", "Incapacidad", "Licencia", "Libre solicitado"];
const hoy = new Date();
const mes = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
/** Meses "AAAA-MM" de `a` a `b`, ambos incluidos (los meses sin ausencias no vienen en `por_mes`). */
const meses = (a: string, b: string) => {
  const out: string[] = [];
  for (let [y, n] = a.split("-").map(Number); `${y}-${String(n).padStart(2, "0")}` <= b; n === 12 ? (y++, n = 1) : n++) out.push(`${y}-${String(n).padStart(2, "0")}`);
  return out;
};
const mesCorto = (m: string) => `${m.slice(5)}/${m.slice(2, 4)}`;
const ultimoDia = (m: string) => { const [y, n] = m.split("-").map(Number); return `${m}-${String(new Date(y, n, 0).getDate()).padStart(2, "0")}`; };

/** Solo lectura: ausentismo, cobertura, cambios, horas extra, recargos, equidad y banco de horas de un rango de meses. «Costo» = horas equivalentes. */
export function Analiticas() {
  const area = useOutletContext<Area>();
  const [desde, setDesde] = useState(mes(new Date(hoy.getFullYear(), hoy.getMonth() - 5, 1)));
  const [hasta, setHasta] = useState(mes(hoy));
  const ok = desde && hasta && desde <= hasta;
  const r = usar<Datos>(ok ? `/api/areas/${area.id}/analiticas?desde=${desde}-01&hasta=${ultimoDia(hasta)}` : null);
  const d = r.datos;
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
            <Indicador titulo="Ausentismo" valor={`${num(d.ausentismo.pct)} %`} nota={`${total.ausencias} días de ausencia`} />
            <Indicador titulo="Ausentes a la vez (máximo)" valor={String(d.simultaneos.maximo)} nota={d.simultaneos.fecha_maximo ? `El ${fechaCorta(d.simultaneos.fecha_maximo)}` : "Sin ausencias simultáneas"} />
            <Indicador titulo="Días con déficit" valor={String(total.deficit)} nota={`${d.simultaneos.dias_riesgo.length} con ausentes en riesgo`} />
            <Indicador titulo="Cambios de turno" valor={String(total.cambios)} nota={`${total.excepciones} con excepción`} />
          </Indicadores>
          <div className="grid gap-4 lg:grid-cols-2">
            <Barras titulo="Equidad de domingos y festivos" unidad="días" datos={Object.entries(d.equidad.por_persona).map(([p, o]) => [p, o.domingos + o.festivos])} />
            <Barras titulo="Recargos por persona" unidad="h equivalentes" datos={Object.entries(d.recargos).map(([p, r2]) => [p, r2.equivalentes])} />
          </div>
          <div className="grid gap-4 lg:grid-cols-2">
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
        </>
      )}
    </Pagina>
  );
}
