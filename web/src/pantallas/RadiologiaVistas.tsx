import { useMemo, useState, type ReactNode } from "react";
import { usar } from "../api/catalogos";
import { base, rutaSemana, type Alertas as TAlertas, type Archivo, type Equidad as TEquidad, type EquidadMeses, type Hoja, type Semana } from "../api/radiologia";
import { Button } from "@/components/base/buttons/button";
import { Alert } from "@/components/application/alerts/alert";
import { Seccion } from "./comun";
import { cx } from "@/utils/cx";

const num = (v: number | null | undefined) => (v ?? "");

function Cuadro({ columnas, filas, vacio, clases }: { columnas: string[]; filas: ReactNode[][]; vacio: string; clases?: (f: number, c: number) => string | undefined }) {
  if (!filas.length) return <p className="p-4 text-center text-tertiary">{vacio}</p>;
  return (
    <table className="w-full border-collapse text-sm [&_td]:border-b [&_td]:border-secondary [&_td]:px-2 [&_td]:py-2 [&_th]:border-b [&_th]:border-secondary [&_th]:bg-secondary [&_th]:px-2 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-semibold [&_th]:text-tertiary">
      <thead><tr>{columnas.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
      <tbody>{filas.map((f, i) => <tr key={i}>{f.map((x, j) => <td key={j} className={clases?.(i, j)}>{x}</td>)}</tr>)}</tbody>
    </table>
  );
}

const NIVEL = { ok: "text-utility-green-700", warn: "text-utility-yellow-700", error: "text-utility-red-700", info: "text-utility-blue-700" };

export function Resumen({ datos }: { datos: Semana["resumen"] }) {
  return (
    <>
      <h2 className="text-display-sm font-semibold text-primary">{datos.semana}</h2>
      {datos.aviso && <Alert color="warning">{datos.aviso}</Alert>}
      <div className="grid grid-cols-[repeat(auto-fit,minmax(210px,1fr))] gap-3">
        {datos.tarjetas.map((t) => (
          <Seccion key={t.titulo} titulo={t.titulo}>
            <div className={cx("text-display-sm font-semibold text-primary", NIVEL[t.nivel as keyof typeof NIVEL])}>{t.valor}</div>
            <div className="text-xs text-tertiary">{t.detalle}</div>
          </Seccion>
        ))}
      </div>
      <Seccion titulo="Cobertura de la semana">
        <p className="text-xs text-tertiary">Médicos asignados por servicio y día. En amarillo, los días con franjas sin médico (pasa el mouse para ver cuáles).</p>
        <table className="w-full border-collapse text-sm [&_td]:border-b [&_td]:border-secondary [&_td]:px-2 [&_td]:py-2 [&_th]:border-b [&_th]:border-secondary [&_th]:bg-secondary [&_th]:px-2 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-semibold [&_th]:text-tertiary">
          <thead><tr><th scope="col">Servicio</th>{datos.dias.map((d) => <th key={d} scope="col" className="text-center">{d}</th>)}</tr></thead>
          <tbody>
            {datos.cobertura.map((f) => (
              <tr key={f.servicio}>
                <th scope="row">{f.servicio}</th>
                {f.dias.map((d, k) => <td key={k} className={`text-center ${d.faltan.length ? "bg-utility-yellow-100" : ""}`} title={d.faltan.length ? `Sin médico: ${d.faltan.join(", ")}` : undefined}>{d.n || ""}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </Seccion>
    </>
  );
}

export function Previa({ area, archivo, lunes }: { area: number; archivo: number; lunes: string }) {
  const hojas = usar<Hoja[]>(`${rutaSemana(area, archivo, lunes)}/previa`);
  const [sel, setSel] = useState(0);
  const hoja = hojas.datos?.[Math.min(sel, (hojas.datos?.length ?? 1) - 1)];
  const tapadas = useMemo(() => {
    const m = new Map<string, [number, number]>(), t = new Set<string>();
    hoja?.fusiones.forEach(([f, c, nf, nc]) => {
      m.set(`${f},${c}`, [nf, nc]);
      for (let a = f; a < f + nf; a++) for (let b = c; b < c + nc; b++) if (a !== f || b !== c) t.add(`${a},${b}`);
    });
    return { m, t };
  }, [hoja]);
  if (hojas.error) return <Alert color="error">{hojas.error}</Alert>;
  if (!hoja) return <p className="p-4 text-center text-tertiary" aria-busy="true">Cargando…</p>;
  return (
    <Seccion titulo="Vista previa" acciones={<Button color="secondary" size="sm" onPress={() => window.print()}>Imprimir</Button>}>
      <div className="mb-3 flex flex-wrap gap-1 border-b border-secondary print:hidden" role="tablist">
        {hojas.datos!.map((h, i) => <button key={h.hoja} role="tab" aria-selected={i === sel} className="cursor-pointer border-b-2 border-transparent px-3 py-2 text-sm font-semibold text-quaternary aria-selected:border-brand aria-selected:text-brand-secondary" onClick={() => setSel(i)}>{h.titulo}</button>)}
      </div>
      <div className="max-h-[70vh] overflow-auto print:max-h-none print:overflow-visible [&_table]:border-collapse [&_table]:text-xs [&_td]:min-w-[150px] [&_td]:px-2 [&_td]:py-1 [&_td]:align-middle">
        <table>
          <tbody>
            {hoja.filas.map((fila, i) => (
              <tr key={i}>
                {fila.map((cel, j) => {
                  if (tapadas.t.has(`${i},${j}`)) return null;
                  const [nf, nc] = tapadas.m.get(`${i},${j}`) ?? [1, 1];
                  return <td key={j} rowSpan={nf} colSpan={nc} style={{ background: cel.fondo ?? undefined, color: cel.color ?? undefined, fontWeight: cel.negrita ? 600 : undefined }}>{cel.texto}</td>;
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Seccion>
  );
}

export function Alertas({ datos }: { datos: TAlertas }) {
  return (
    <>
      <p className="text-xs text-tertiary">Revisa esto antes de publicar. Los problemas se corrigen en el cuadro mensual de Excel; al subirlo de nuevo, la página se actualiza.</p>
      <Seccion titulo="PROBLEMAS EN EL CUADRO MENSUAL">
        <Cuadro columnas={["Fecha", "Médico", "Problema"]} filas={datos.revision.map((a) => [a.corta, a.medico, a.problema])} vacio="Sin problemas en el cuadro." />
      </Seccion>
      <Seccion titulo="REGLAS DE DESCANSO">
        <Cuadro columnas={["Fecha", "Médico", "Regla"]} filas={datos.descanso.map((a) => [a.corta, a.medico, a.regla])} vacio="Se cumplen las reglas de descanso." />
      </Seccion>
      <Seccion titulo="FRANJAS SIN MÉDICO">
        <Cuadro columnas={["Fecha", "Servicio", "Franja", "Qué falta"]} filas={datos.pendientes.map((a) => [a.corta, a.servicio, a.franja, a.que])} vacio="Todas las franjas tienen médico." />
      </Seccion>
    </>
  );
}

export function Equidad({ area, archivos, actual, datos }: { area: number; archivos: Archivo[]; actual: number; datos: TEquidad[] }) {
  const [acumulado, setAcumulado] = useState(false);
  const [otros, setOtros] = useState<number[]>([]);
  const ids = [actual, ...otros.filter((x) => x !== actual)];
  const meses = usar<EquidadMeses>(acumulado ? `${base(area)}/equidad-meses?archivos=${ids.join(",")}` : null);
  return (
    <>
      <p className="text-xs text-tertiary">Carga de cada radiólogo. Pasa el mouse sobre un encabezado para ver qué significa.</p>
      <div className="flex flex-wrap items-center gap-2 print:hidden">
        <label><input type="radio" name="modo" checked={!acumulado} onChange={() => setAcumulado(false)} /> Este mes</label>
        <label><input type="radio" name="modo" checked={acumulado} onChange={() => setAcumulado(true)} /> Varios meses (acumulado)</label>
      </div>
      {acumulado && (
        <fieldset className="flex flex-wrap gap-3">
          <legend className="text-xs text-tertiary">Suma los cuadros mensuales que elijas</legend>
          {archivos.filter((a) => a.id !== actual).map((a) => (
            <label key={a.id}><input type="checkbox" checked={otros.includes(a.id)} onChange={(ev) => setOtros(ev.target.checked ? [...otros, a.id] : otros.filter((x) => x !== a.id))} /> {a.nombre}</label>
          ))}
        </fieldset>
      )}
      {!acumulado ? (
        <Seccion>
          <table className="w-full border-collapse text-sm [&_td]:border-b [&_td]:border-secondary [&_td]:px-2 [&_td]:py-2 [&_th]:border-b [&_th]:border-secondary [&_th]:bg-secondary [&_th]:px-2 [&_th]:py-2 [&_th]:text-left [&_th]:text-xs [&_th]:font-semibold [&_th]:text-tertiary">
            <thead>
              <tr>
                <th scope="col">Médico</th>
                <th scope="col" title="Horas de la semana elegida según la hoja Nom-Hrs (rojo: supera la jornada)">Horas semana</th>
                <th scope="col">Jornada sem.</th><th scope="col">Horas mes</th><th scope="col">Meta mes</th>
                <th scope="col" title="Meta del mes menos horas programadas (amarillo: le faltan horas; azul: tiene de más)">Pendiente</th>
                <th scope="col">Noches URG</th><th scope="col">Domingos</th><th scope="col">Festivos</th>
                <th scope="col" title="Fines de semana completos libres en el mes">Finde libres</th>
                <th scope="col" title="Días con disponibilidad en el mes">Disponibilidades</th>
              </tr>
            </thead>
            <tbody>
              {datos.map((e) => (
                <tr key={e.medico}>
                  <th scope="row">{e.medico}</th>
                  <td className={e.jornada && e.semana > e.jornada ? "bg-utility-red-50" : undefined}>{e.semana}</td>
                  <td>{num(e.jornada)}</td><td>{num(e.mes)}</td><td>{num(e.meta)}</td>
                  <td className={e.pendiente ? (e.pendiente > 0 ? "bg-utility-yellow-100" : "bg-utility-blue-50") : undefined}>{num(e.pendiente)}</td>
                  <td>{num(e.noches)}</td><td>{num(e.domingos)}</td><td>{num(e.festivos)}</td><td>{num(e.findes_libres)}</td><td>{num(e.disponibilidades)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Seccion>
      ) : meses.error ? <Alert color="error">{meses.error}</Alert> : meses.datos && (
        <Seccion>
          <p className="text-xs text-tertiary">Meses: {meses.datos.meses.join(", ")}{meses.datos.fallidos.length ? `  ·  No se pudieron leer: ${meses.datos.fallidos.join(", ")}` : ""}</p>
          <Cuadro
            columnas={["Médico", "Meses", "Horas", "Meta", "Pendiente", "Noches URG", "Domingos", "Festivos", "Finde libres", "Disponibilidades"]}
            filas={meses.datos.filas.map((f) => [f.medico, f.meses.length, num(f.mes), num(f.meta), num(f.pendiente), num(f.noches), num(f.domingos), num(f.festivos), num(f.findes_libres), num(f.disponibilidades)])}
            vacio="Sin datos." clases={(i, j) => (j === 4 && meses.datos!.filas[i].pendiente ? (meses.datos!.filas[i].pendiente! > 0 ? "bg-utility-yellow-100" : "bg-utility-blue-50") : undefined)}
          />
        </Seccion>
      )}
    </>
  );
}

export function Agendas({ area, archivo, lunes, agendas }: { area: number; archivo: number; lunes: string; agendas: Record<string, string> }) {
  const [buscar, setBuscar] = useState("");
  const [elegido, setElegido] = useState<string | null>(null);
  const [copiado, setCopiado] = useState("");
  const nombres = Object.keys(agendas).filter((n) => n.toLowerCase().includes(buscar.trim().toLowerCase()));
  const actual = elegido && elegido in agendas ? elegido : Object.keys(agendas)[0];
  const copiar = async (texto: string, msg: string) => {
    try { await navigator.clipboard.writeText(texto); setCopiado(msg); } catch { setCopiado("No se pudo copiar: selecciona el texto y cópialo a mano."); }
  };
  const ruta = rutaSemana(area, archivo, lunes);
  return (
    <>
      <p className="text-xs text-tertiary">Turnos de cada médico para enviar por WhatsApp o correo. «Exportar agendas» baja un .zip con un .ics por médico para Outlook.</p>
      {copiado && <Alert color="success">{copiado}</Alert>}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-[minmax(220px,300px)_1fr]">
        <Seccion>
          <input type="search" aria-label="Buscar médico" placeholder="Buscar médico…" value={buscar} onChange={(ev) => setBuscar(ev.target.value)} />
          <ul className="mt-2 max-h-[60vh] overflow-auto [&_button]:block [&_button]:w-full [&_button]:cursor-pointer [&_button]:rounded-md [&_button]:p-2 [&_button]:text-left [&_button]:text-secondary [&_button[aria-current=true]]:bg-brand-primary [&_button[aria-current=true]]:font-semibold [&_button[aria-current=true]]:text-brand-secondary">
            {nombres.map((n) => <li key={n}><button aria-current={n === actual} onClick={() => setElegido(n)}>{n}</button></li>)}
          </ul>
        </Seccion>
        <Seccion>
          {actual ? <pre className="mb-3 min-h-[200px] whitespace-pre-wrap rounded-md bg-secondary p-3 ring-1 ring-secondary ring-inset">{agendas[actual]}</pre> : <p className="p-4 text-center text-tertiary">Nadie tiene turnos esta semana.</p>}
          <div className="flex flex-wrap items-center gap-2 print:hidden">
            <Button color="secondary" size="sm" onPress={() => location.assign(`${ruta}/agendas.zip`)}>Exportar agendas</Button>
            {actual && <Button color="secondary" size="sm" onPress={() => location.assign(`${ruta}/agenda/${Object.keys(agendas).indexOf(actual)}.ics`)}>Descargar .ics</Button>}
            <Button color="secondary" size="sm" onPress={() => copiar(Object.values(agendas).join("\n\n"), `${Object.keys(agendas).length} agendas copiadas.`)}>Copiar todas</Button>
            {actual && <Button color="secondary" size="sm" onPress={() => copiar(agendas[actual], "Agenda copiada.")}>Copiar esta agenda</Button>}
          </div>
        </Seccion>
      </div>
    </>
  );
}

export function Cambios({ datos }: { datos: Semana["cambios"] }) {
  const estado = !datos.version_anterior ? "Aún no se ha guardado ninguna versión de esta semana."
    : !datos.lista.length ? `Sin cambios respecto a «${datos.version_anterior}».` : `${datos.lista.length} cambio(s) respecto a «${datos.version_anterior}».`;
  return (
    <>
      <p className="text-xs text-tertiary">Diferencias con la última planilla guardada de esta semana. Al generar, quedan marcadas en amarillo y en la hoja «Cambios».</p>
      <Seccion titulo="Cambios">
        <p>{estado}</p>
        {datos.lista.length > 0 && <pre className="mb-3 min-h-[200px] whitespace-pre-wrap rounded-md bg-secondary p-3 ring-1 ring-secondary ring-inset">{datos.lista.join("\n")}</pre>}
      </Seccion>
    </>
  );
}
