import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router";
import { leer } from "../api/cliente";
import type { Alerta, Analiticas, Area, Colaborador, Cuadro as CuadroApi, Horas, Novedad, Periodo, Turno } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Seleccion } from "../componentes/Campo";
import { Planilla, type Foco } from "../componentes/Planilla";
import { Tarjeta } from "../componentes/Tarjeta";
import e from "./Cuadro.module.css";
import { dias as diasDe, fechaCorta, mesDe, nombrePeriodo } from "./fechas";
import { Generar } from "./Generar";

interface Datos {
  cuadro: CuadroApi;
  alertas: Alerta[];
  horas: Horas[];
  colabs: Colaborador[];
  turnos: Turno[];
  novedades: Novedad[];
  analiticas: Analiticas;
}
const SIGLA_NOVEDAD: Record<string, string> = { Vacaciones: "V", Incapacidad: "I", Licencia: "Li", "Libre solicitado": "LS" };

export function Cuadro() {
  const area = useOutletContext<Area>();
  const { periodo } = useParams();
  const ir = useNavigate();
  const [periodos, setPeriodos] = useState<Periodo[] | null>(null);
  const [datos, setDatos] = useState<Datos | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [recarga, setRecarga] = useState(0);
  const [foco, setFoco] = useState<Foco | null>(null);

  useEffect(() => {
    setPeriodos(null);
    leer<Periodo[]>(`/api/areas/${area.id}/periodos`).then(setPeriodos).catch((x) => setError(x.message));
  }, [area.id, recarga]);

  const actual = useMemo(() => periodos?.find((p) => p.id === Number(periodo)) ?? periodos?.at(-1) ?? null, [periodos, periodo]);

  useEffect(() => {
    if (!actual) return;
    let vivo = true;
    const base = `/api/areas/${area.id}`;
    const [desde, hasta] = actual.clave.split("/");
    performance.mark("cuadro:pide");
    setError(null);
    Promise.all([
      leer<CuadroApi>(`${base}/periodos/${actual.id}/cuadro`),
      leer<Alerta[]>(`${base}/periodos/${actual.id}/alertas`),
      leer<Horas[]>(`${base}/periodos/${actual.id}/horas`),
      leer<Colaborador[]>(`${base}/colaboradores`),
      leer<Turno[]>(`${base}/turnos`),
      leer<Novedad[]>(`${base}/novedades`),
      leer<Analiticas>(`${base}/analiticas?desde=${desde}&hasta=${hasta}`),
    ])
      .then(([cuadro, alertas, horas, colabs, turnos, novedades, analiticas]) => {
        if (!vivo) return;
        performance.mark("cuadro:datos");
        setDatos({ cuadro, alertas, horas, colabs, turnos, novedades, analiticas });
      })
      .catch((x) => vivo && setError(x.message));
    return () => { vivo = false; };
  }, [area.id, actual?.id, recarga]); // eslint-disable-line react-hooks/exhaustive-deps

  // Pintado: de que llegan los datos a que el navegador dibuja la grilla (umbral de PLAN_WEB §8: 1 s).
  useEffect(() => {
    if (!datos) return;
    requestAnimationFrame(() => requestAnimationFrame(() => {
      performance.mark("cuadro:pintado");
      performance.measure("cuadro:pintado-ms", "cuadro:datos", "cuadro:pintado");
    }));
  }, [datos]);

  const dias = useMemo(() => (actual ? diasDe(actual.clave) : []), [actual]);
  const vista = useMemo(() => {
    if (!datos) return null;
    const celdas = new Map(datos.cuadro.celdas.map((c) => [`${c.colab_id}|${c.fecha}`, c]));
    const turnos = new Map(datos.turnos.map((t) => [t.codigo, t]));
    const horas = new Map(datos.horas.map((h) => [h.colab_id, h]));
    const faltan = new Set(datos.alertas.filter((a) => a.nivel === "error" && a.colab_id && a.fecha).map((a) => `${a.colab_id}|${a.fecha}`));
    const diaMalo = new Set(datos.alertas.filter((a) => a.nivel === "error" && !a.colab_id && a.fecha).map((a) => a.fecha!));
    const novedades = new Map<string, string>();
    for (const n of datos.novedades) for (const d of dias) if (d.fecha >= n.desde && d.fecha <= n.hasta) novedades.set(`${n.colab_id}|${d.fecha}`, n.tipo);
    const presentes = (fecha: string, franja: string) =>
      datos.colabs.reduce((s, c) => s + (turnos.get(celdas.get(`${c.id}|${fecha}`)?.turno ?? "")?.cubre.includes(franja) ? 1 : 0), 0);
    return { celdas, turnos, horas, faltan, diaMalo, novedades, presentes };
  }, [datos, dias]);

  if (error) return <div className={e.pagina}><Aviso nivel="error" accion={<Boton onClick={() => setRecarga((n) => n + 1)}>Reintentar</Boton>}>{error}</Aviso></div>;
  if (!periodos) return <p className={e.vacio} aria-busy="true">Cargando…</p>;
  if (!actual) return <p className={e.vacio}>Esta área aún no tiene periodos. Genera o migra un cuadro para verlo aquí.</p>;

  const deficit = datos?.analiticas.cobertura[0];
  const irA = (a: Alerta) => a.fecha && setFoco({ fila: a.colab_id, fecha: a.fecha, marca: Date.now() });

  return (
    <div className={e.pagina}>
      <div className={e.barra}>
        <div>
          <h1 className={e.titulo}>Cuadro de {mesDe(actual.clave)}</h1>
          <p className={e.sub}>
            {dias.length} días · revisión {actual.revision}
            {deficit && ` · ${deficit.dias_deficit} días con déficit, ${deficit.puestos_sin_cubrir} puestos sin cubrir`}
          </p>
        </div>
        <div className={e.acciones}>
          {actual.cerrado_en ? <span className={e.estado}>Cerrado</span> : actual.publicado_en && <span className={e.estado}>Publicado</span>}
          <Seleccion etiqueta="Periodo" value={actual.id} onChange={(x) => ir(`/areas/${area.id}/cuadro/${x.target.value}`)}>
            {periodos.map((p) => <option key={p.id} value={p.id}>{nombrePeriodo(p.clave)}</option>)}
          </Seleccion>
          {area.permiso === "editar" && <Generar area={area.id} periodo={actual} bloqueado={!!actual.cerrado_en} alTerminar={() => setRecarga((n) => n + 1)} />}
        </div>
      </div>

      <Tarjeta aria-busy={!datos}>
        {!datos || !vista ? (
          <p className={e.vacio}>Cargando el cuadro…</p>
        ) : datos.cuadro.celdas.length === 0 ? (
          <p className={e.vacio}>Este periodo no tiene cuadro todavía.</p>
        ) : (
          <>
            <Planilla
              descripcion={`Cuadro de turnos de ${nombrePeriodo(actual.clave)}`}
              dias={dias}
              filas={datos.colabs.filter((c) => c.activo).map((c) => {
                const h = vista.horas.get(c.id);
                return { id: c.id, nombre: c.nombre, extra: h ? h.trabajadas : "", extraAlto: !!h && h.trabajadas > h.contratadas };
              })}
              columnaExtra="Horas"
              foco={foco}
              celda={(id, fecha) => {
                const c = vista.celdas.get(`${id}|${fecha}`);
                const codigo = c?.turno ?? "L";
                const t = vista.turnos.get(codigo);
                const nov = codigo === "L" ? vista.novedades.get(`${id}|${fecha}`) : undefined;
                const falta = vista.faltan.has(`${id}|${fecha}`);
                return {
                  codigo, color: t?.color, cambiada: c?.fijo, novedad: nov ? (SIGLA_NOVEDAD[nov] ?? nov) : null, faltante: falta,
                  etiqueta: `${nov ?? t?.nombre ?? (codigo === "L" ? "Libre" : codigo)}${c?.fijo ? ", editada a mano" : ""}${falta ? ", con alerta" : ""}`,
                };
              }}
              pie={(["M", "T", "N"] as const).map((f) => ({
                titulo: { M: "Presentes mañana", T: "Presentes tarde", N: "Presentes noche" }[f],
                valor: (fecha) => vista.presentes(fecha, f),
                alerta: (fecha) => vista.diaMalo.has(fecha),
              }))}
            />
            <div className={e.leyenda}>
              {datos.turnos.filter((t) => t.activo).map((t) => <span key={t.codigo}>{t.codigo} {t.nombre}</span>)}
              <span>L Libre</span>
              <span>◥ editada a mano</span>
              <span>columnas grises: domingo</span>
            </div>
          </>
        )}
      </Tarjeta>

      {datos && (
        <Tarjeta titulo={<>Alertas {datos.alertas.length > 0 && <span className={e.cuenta}>{datos.alertas.length}</span>}</>}>
          {datos.alertas.length === 0 ? (
            <p className={e.vacio}>Sin alertas: el cuadro cumple las reglas.</p>
          ) : (
            <ul className={e.alertas}>
              {datos.alertas.map((a, i) => (
                <li key={i} className={e.alerta}>
                  <span className={`${e.chip} ${a.nivel === "error" ? e["chip-error"] : e["chip-aviso"]}`}>{a.nivel === "error" ? "Error" : "Aviso"}</span>
                  <span className={e.texto}>{a.texto}</span>
                  {a.fecha && (
                    <Boton variante="texto" onClick={() => irA(a)} aria-label={`${a.colab_id ? "Ir a la celda" : "Ir al día"}: ${a.texto}`}>
                      {a.colab_id ? "Ir a la celda" : `Ir al ${fechaCorta(a.fecha)}`}
                    </Boton>
                  )}
                </li>
              ))}
            </ul>
          )}
        </Tarjeta>
      )}
    </div>
  );
}
