import { useMemo, useState, type ReactNode } from "react";
import { usar } from "../api/catalogos";
import { base, rutaSemana, type Alertas as TAlertas, type Archivo, type Equidad as TEquidad, type EquidadMeses, type Hoja, type Semana } from "../api/radiologia";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Tarjeta } from "../componentes/Tarjeta";
import r from "./Radiologia.module.css";

const num = (v: number | null | undefined) => (v ?? "");

function Cuadro({ columnas, filas, vacio, clases }: { columnas: string[]; filas: ReactNode[][]; vacio: string; clases?: (f: number, c: number) => string | undefined }) {
  if (!filas.length) return <p className={r.vacio}>{vacio}</p>;
  return (
    <table className={r.tabla}>
      <thead><tr>{columnas.map((c) => <th key={c} scope="col">{c}</th>)}</tr></thead>
      <tbody>{filas.map((f, i) => <tr key={i}>{f.map((x, j) => <td key={j} className={clases?.(i, j)}>{x}</td>)}</tr>)}</tbody>
    </table>
  );
}

export function Resumen({ datos }: { datos: Semana["resumen"] }) {
  return (
    <>
      <h2 className={r.cifra}>{datos.semana}</h2>
      {datos.aviso && <Aviso nivel="aviso">{datos.aviso}</Aviso>}
      <div className={r.tarjetas}>
        {datos.tarjetas.map((t) => (
          <Tarjeta key={t.titulo} titulo={t.titulo}>
            <div className={`${r.cifra} ${r[t.nivel]}`}>{t.valor}</div>
            <div className={r.detalle}>{t.detalle}</div>
          </Tarjeta>
        ))}
      </div>
      <Tarjeta titulo="Cobertura de la semana">
        <p className={r.detalle}>Médicos asignados por servicio y día. En amarillo, los días con franjas sin médico (pasa el mouse para ver cuáles).</p>
        <table className={r.tabla}>
          <thead><tr><th scope="col">Servicio</th>{datos.dias.map((d) => <th key={d} scope="col" className={r.centro}>{d}</th>)}</tr></thead>
          <tbody>
            {datos.cobertura.map((f) => (
              <tr key={f.servicio}>
                <th scope="row">{f.servicio}</th>
                {f.dias.map((d, k) => <td key={k} className={`${r.centro} ${d.faltan.length ? r.amarillo : ""}`} title={d.faltan.length ? `Sin médico: ${d.faltan.join(", ")}` : undefined}>{d.n || ""}</td>)}
              </tr>
            ))}
          </tbody>
        </table>
      </Tarjeta>
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
  if (hojas.error) return <Aviso nivel="error">{hojas.error}</Aviso>;
  if (!hoja) return <p className={r.vacio} aria-busy="true">Cargando…</p>;
  return (
    <Tarjeta titulo="Vista previa" acciones={<Boton onClick={() => window.print()}>Imprimir</Boton>}>
      <div className={r.pestanas} role="tablist">
        {hojas.datos!.map((h, i) => <button key={h.hoja} role="tab" aria-selected={i === sel} className={r.pestana} onClick={() => setSel(i)}>{h.titulo}</button>)}
      </div>
      <div className={r.hoja}>
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
    </Tarjeta>
  );
}

export function Alertas({ datos }: { datos: TAlertas }) {
  return (
    <>
      <p className={r.detalle}>Revisa esto antes de publicar. Los problemas se corrigen en el cuadro mensual de Excel; al subirlo de nuevo, la página se actualiza.</p>
      <Tarjeta titulo="PROBLEMAS EN EL CUADRO MENSUAL">
        <Cuadro columnas={["Fecha", "Médico", "Problema"]} filas={datos.revision.map((a) => [a.corta, a.medico, a.problema])} vacio="Sin problemas en el cuadro." />
      </Tarjeta>
      <Tarjeta titulo="REGLAS DE DESCANSO">
        <Cuadro columnas={["Fecha", "Médico", "Regla"]} filas={datos.descanso.map((a) => [a.corta, a.medico, a.regla])} vacio="Se cumplen las reglas de descanso." />
      </Tarjeta>
      <Tarjeta titulo="FRANJAS SIN MÉDICO">
        <Cuadro columnas={["Fecha", "Servicio", "Franja", "Qué falta"]} filas={datos.pendientes.map((a) => [a.corta, a.servicio, a.franja, a.que])} vacio="Todas las franjas tienen médico." />
      </Tarjeta>
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
      <p className={r.detalle}>Carga de cada radiólogo. Pasa el mouse sobre un encabezado para ver qué significa.</p>
      <div className={r.fila}>
        <label><input type="radio" name="modo" checked={!acumulado} onChange={() => setAcumulado(false)} /> Este mes</label>
        <label><input type="radio" name="modo" checked={acumulado} onChange={() => setAcumulado(true)} /> Varios meses (acumulado)</label>
      </div>
      {acumulado && (
        <fieldset className={r.marcas}>
          <legend className={r.detalle}>Suma los cuadros mensuales que elijas</legend>
          {archivos.filter((a) => a.id !== actual).map((a) => (
            <label key={a.id}><input type="checkbox" checked={otros.includes(a.id)} onChange={(ev) => setOtros(ev.target.checked ? [...otros, a.id] : otros.filter((x) => x !== a.id))} /> {a.nombre}</label>
          ))}
        </fieldset>
      )}
      {!acumulado ? (
        <Tarjeta>
          <table className={r.tabla}>
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
                  <td className={e.jornada && e.semana > e.jornada ? r.rojo : undefined}>{e.semana}</td>
                  <td>{num(e.jornada)}</td><td>{num(e.mes)}</td><td>{num(e.meta)}</td>
                  <td className={e.pendiente ? (e.pendiente > 0 ? r.amarillo : r.azul) : undefined}>{num(e.pendiente)}</td>
                  <td>{num(e.noches)}</td><td>{num(e.domingos)}</td><td>{num(e.festivos)}</td><td>{num(e.findes_libres)}</td><td>{num(e.disponibilidades)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </Tarjeta>
      ) : meses.error ? <Aviso nivel="error">{meses.error}</Aviso> : meses.datos && (
        <Tarjeta>
          <p className={r.detalle}>Meses: {meses.datos.meses.join(", ")}{meses.datos.fallidos.length ? `  ·  No se pudieron leer: ${meses.datos.fallidos.join(", ")}` : ""}</p>
          <Cuadro
            columnas={["Médico", "Meses", "Horas", "Meta", "Pendiente", "Noches URG", "Domingos", "Festivos", "Finde libres", "Disponibilidades"]}
            filas={meses.datos.filas.map((f) => [f.medico, f.meses.length, num(f.mes), num(f.meta), num(f.pendiente), num(f.noches), num(f.domingos), num(f.festivos), num(f.findes_libres), num(f.disponibilidades)])}
            vacio="Sin datos." clases={(i, j) => (j === 4 && meses.datos!.filas[i].pendiente ? (meses.datos!.filas[i].pendiente! > 0 ? r.amarillo : r.azul) : undefined)}
          />
        </Tarjeta>
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
      <p className={r.detalle}>Turnos de cada médico para enviar por WhatsApp o correo. «Exportar agendas» baja un .zip con un .ics por médico para Outlook.</p>
      {copiado && <Aviso nivel="ok">{copiado}</Aviso>}
      <div className={r.dos}>
        <Tarjeta>
          <input type="search" aria-label="Buscar médico" placeholder="Buscar médico…" value={buscar} onChange={(ev) => setBuscar(ev.target.value)} />
          <ul className={r.medicos}>
            {nombres.map((n) => <li key={n}><button aria-current={n === actual} onClick={() => setElegido(n)}>{n}</button></li>)}
          </ul>
        </Tarjeta>
        <Tarjeta>
          {actual ? <pre className={r.texto}>{agendas[actual]}</pre> : <p className={r.vacio}>Nadie tiene turnos esta semana.</p>}
          <div className={r.fila}>
            <Boton onClick={() => location.assign(`${ruta}/agendas.zip`)}>Exportar agendas</Boton>
            {actual && <Boton onClick={() => location.assign(`${ruta}/agenda.ics?medico=${encodeURIComponent(actual)}`)}>Descargar .ics</Boton>}
            <Boton onClick={() => copiar(Object.values(agendas).join("\n\n"), `${Object.keys(agendas).length} agendas copiadas.`)}>Copiar todas</Boton>
            {actual && <Boton onClick={() => copiar(agendas[actual], "Agenda copiada.")}>Copiar esta agenda</Boton>}
          </div>
        </Tarjeta>
      </div>
    </>
  );
}

export function Cambios({ datos }: { datos: Semana["cambios"] }) {
  const estado = !datos.version_anterior ? "Aún no se ha guardado ninguna versión de esta semana."
    : !datos.lista.length ? `Sin cambios respecto a «${datos.version_anterior}».` : `${datos.lista.length} cambio(s) respecto a «${datos.version_anterior}».`;
  return (
    <>
      <p className={r.detalle}>Diferencias con la última planilla guardada de esta semana. Al generar, quedan marcadas en amarillo y en la hoja «Cambios».</p>
      <Tarjeta titulo="Cambios">
        <p>{estado}</p>
        {datos.lista.length > 0 && <pre className={r.texto}>{datos.lista.join("\n")}</pre>}
      </Tarjeta>
    </>
  );
}
