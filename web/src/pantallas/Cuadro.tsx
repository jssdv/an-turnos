import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router";
import { borrador as guardado, cambios, type Borrador } from "../api/cambios";
import { ErrorApi, leer } from "../api/cliente";
import { useSesion } from "../Sesion";
import type { Alerta, Analiticas, Area, Colaborador, Cuadro as CuadroApi, Cupo, CuerpoCambio, Horas, Novedad, Periodo, Turno } from "../api/tipos";
import { Ayuda } from "../componentes/Ayuda";
import { Planilla, type Foco, type Sel } from "../componentes/Planilla";
import { Tarjeta } from "../componentes/Tarjeta";
import { AccionesPeriodo } from "./AccionesPeriodo";
import { Cambios } from "./Cambios";
import e from "./Cuadro.module.css";
import { dias as diasDe, fechaCorta, mesDe, nombrePeriodo } from "./fechas";
import { Exportar } from "./Exportar";
import { Generar } from "./Generar";
import { RegistrarCambio, sinCupo } from "./RegistrarCambio";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";

interface Datos {
  cuadro: CuadroApi;
  alertas: Alerta[];
  horas: Horas[];
  colabs: Colaborador[];
  turnos: Turno[];
  novedades: Novedad[];
  analiticas: Analiticas;
}
/** Junta alertas de texto idéntico (p. ej. el mismo turno prohibido en dos celdas) para no repetir la misma línea. */
function agrupar(alertas: Alerta[]) {
  const g = new Map<string, { alerta: Alerta; veces: number }>();
  for (const a of alertas) {
    const x = g.get(a.texto);
    if (x) x.veces++; else g.set(a.texto, { alerta: a, veces: 1 });
  }
  return [...g.values()];
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
  const uid = useSesion().usuario?.id ?? 0;
  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [cupos, setCupos] = useState<Cupo[] | null>(null);
  const [errorCambio, setErrorCambio] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<{ nivel: "ok" | "aviso"; texto: string } | null>(null);
  const [pendiente, setPendiente] = useState<Borrador | null>(() => guardado.leer(area.id, uid));

  // Al recargar (p. ej. tras generar) se conserva lo que hay en pantalla: vaciarlo desmontaría el diálogo de Generar.
  useEffect(() => { setPeriodos(null); setDatos(null); }, [area.id]);
  useEffect(() => {
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

  // Pintado: de que llegan los datos a que la grilla está maquetada (umbral de PLAN_WEB §8: 1 s). Leer offsetHeight fuerza la maquetación
  // sin depender de requestAnimationFrame, que un navegador en segundo plano retrasa; el pintado en sí se mide aparte.
  useEffect(() => {
    if (!datos) return;
    void document.body.offsetHeight;
    performance.mark("cuadro:maquetado");
    performance.measure("cuadro:maquetado-ms", "cuadro:datos", "cuadro:maquetado");
    requestAnimationFrame(() => {
      performance.mark("cuadro:pintado");
      performance.measure("cuadro:pintado-ms", "cuadro:datos", "cuadro:pintado");
    });
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

  const nombres = useMemo(() => new Map((datos?.colabs ?? []).map((c) => [c.id, c.nombre])), [datos]);
  const puedeEditar = area.permiso === "editar" && !!actual && !actual.cerrado_en;
  const codigoDe = (id: number, fecha: string) => vista?.celdas.get(`${id}|${fecha}`)?.turno ?? "L";
  /** Como `_editable` de Qt: persona del cuadro, y no una celda libre cubierta por novedad. */
  const editable = (id: number, fecha: string) => {
    if (!puedeEditar || !vista) return false;
    const nov = vista.novedades.has(`${id}|${fecha}`);
    return !(nov && codigoDe(id, fecha) === "L");
  };

  const abrirCambio = (b: Borrador) => {
    setErrorCambio(null);
    setResultado(null);
    setBorrador(b);
    if (b.modo === "intercambio" || b.celdas.length === 2) cambios.cupos(area.id, b.periodo).then(setCupos).catch(() => setCupos(null));
  };
  const nuevoBorrador = (celdas: Sel[], modo: Borrador["modo"]): Borrador => ({
    area: area.id, periodo: actual!.id, modo, celdas: celdas.map((c) => ({ colab_id: c.fila, fecha: c.fecha })),
    turno: codigoDe(celdas[0].fila, celdas[0].fecha), tipo: celdas.length === 2 && celdas[0].fila !== celdas[1].fila ? "permuta" : "ajuste", motivo: "", excepcion: false,
  });
  const accionar = (celdas: Sel[]) => abrirCambio(nuevoBorrador(celdas, celdas.length === 2 ? "intercambio" : "asignar"));
  const soltar = (o: Sel, d: Sel) => abrirCambio(nuevoBorrador([o, d], "intercambio"));

  const enviar = async () => {
    if (!borrador || !actual) return;
    const b = borrador;
    const entre = b.modo === "intercambio" && b.celdas.length === 2 && b.celdas[0].colab_id !== b.celdas[1].colab_id;
    const tipo = b.tipo === "permuta" && !entre ? "ajuste" : b.tipo;
    let celdas: CuerpoCambio["celdas"];
    if (b.modo === "intercambio") {
      const [x, y] = b.celdas;
      if (codigoDe(x.colab_id, x.fecha) === codigoDe(y.colab_id, y.fecha)) return setErrorCambio("Las dos celdas ya tienen el mismo turno: no hay nada que intercambiar.");
      celdas = [{ ...x, turno: codigoDe(y.colab_id, y.fecha) }, { ...y, turno: codigoDe(x.colab_id, x.fecha) }];
    } else celdas = b.celdas.map((c) => ({ ...c, turno: b.turno }));
    const motivo = b.motivo.trim() || (tipo === "ajuste" && celdas.length > 1 && b.modo === "asignar" ? `Lote: ${celdas.length} celdas → ${b.turno}` : "");
    setEnviando(true);
    setErrorCambio(null);
    guardado.guardar({ ...b, tipo }, uid); // si la sesión vence a mitad de camino, se recupera al ingresar de nuevo
    try {
      const r = await cambios.registrar(area.id, actual.id, actual.revision, { tipo, celdas, motivo, excepcion: tipo === "permuta" && sinCupo(b, cupos).length > 0 });
      guardado.borrar();
      setBorrador(null);
      setPendiente(null);
      setResultado({ nivel: r.alertas_nuevas.length ? "aviso" : "ok", texto: "Cambio registrado." + (r.alertas_nuevas.length ? " Ojo: " + r.alertas_nuevas.slice(0, 3).join("; ") + (r.alertas_nuevas.length > 3 ? "…" : ".") : "") });
      setRecarga((n) => n + 1);
    } catch (x) {
      if (!(x instanceof ErrorApi)) return setErrorCambio("No se pudo registrar el cambio");
      const d = x.detalle as { revision?: number; modificado_por?: string; ids?: number[] } | undefined;
      if (x.estado === 409 && d?.revision !== undefined) {
        setErrorCambio(`${d.modificado_por ?? "Alguien"} cambió este periodo mientras tanto. Ya se actualizó el cuadro; revisa y confirma de nuevo.`);
        setRecarga((n) => n + 1); // trae la revisión vigente; el borrador se conserva
      } else if (x.estado === 401) {
        setErrorCambio("Tu sesión venció. Ingresa de nuevo: el cambio quedará pendiente.");
      } else {
        setErrorCambio(x.message);
        if (x.estado === 409 && d?.ids) cambios.cupos(area.id, actual.id).then(setCupos).catch(() => undefined);
      }
    } finally {
      setEnviando(false);
    }
  };
  const cerrarCambio = (b: Borrador | null) => { if (!b) { guardado.borrar(); setErrorCambio(null); } setBorrador(b); };

  if (error) return <div className={e.pagina}><Alert color="error" action={<Button color="secondary" size="sm" onPress={() => setRecarga((n) => n + 1)}>Reintentar</Button>}>{error}</Alert></div>;
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
            {dias.length} días · versión {actual.revision}
            {deficit && (deficit.dias_deficit || deficit.puestos_sin_cubrir
              ? ` · ${deficit.dias_deficit} días con falta de personal, ${deficit.puestos_sin_cubrir} puestos sin cubrir`
              : " · todos los puestos cubiertos")}
          </p>
        </div>
        <div className={e.acciones} data-no-imprimir>
          {actual.cerrado_en ? <span className={e.estado}>Cerrado</span> : actual.publicado_en && <span className={e.estado}>Publicado</span>}
          <NativeSelect size="sm" label="Periodo" value={actual.id} onChange={(x) => ir(`/areas/${area.id}/cuadro/${x.target.value}`)}>
            {periodos.map((p) => <option key={p.id} value={p.id}>{nombrePeriodo(p.clave)}</option>)}
          </NativeSelect>
          <Exportar area={area.id} periodo={actual.id} hayCuadro={!datos || datos.cuadro.celdas.length > 0} />
          <Button color="secondary" size="sm" onPress={() => window.print()}>Imprimir</Button>
          {area.permiso === "editar" && <AccionesPeriodo area={area.id} periodo={actual} alTerminar={() => setRecarga((n) => n + 1)} />}
          {area.permiso === "editar" && <Generar area={area.id} periodo={actual} bloqueado={!!actual.cerrado_en} alTerminar={() => setRecarga((n) => n + 1)} />}
        </div>
      </div>

      {datos && area.permiso === "editar" && <Pasos hay={datos.cuadro.celdas.length > 0} alertas={datos.alertas} publicado={!!actual.publicado_en} />}

      <Ayuda titulo="¿Cómo se usa el cuadro?" clave="cuadro">
        Cada fila es una persona y cada columna un día; los colores son los turnos (la leyenda está debajo).
        {puedeEditar
          ? " Haz clic en una celda para cambiar el turno, o arrastra una celda sobre otra para intercambiarlas. Todo cambio queda registrado con su motivo y se puede anular."
          : " Puedes exportarlo a Excel o imprimirlo."}
        {" "}Las celdas con borde rojo tienen una alerta: revísalas en la lista de abajo.
      </Ayuda>

      {actual.solapa_con && actual.solapa_con.length > 0 && (
        <Alert color="warning">Este periodo comparte fechas con otro del área; una persona puede quedar con dos turnos el mismo día. Cierra o revisa uno de los dos.</Alert>
      )}
      {pendiente && !borrador && pendiente.periodo === actual.id && (
        <Alert color="brand" action={<Button color="secondary" size="sm" onPress={() => { abrirCambio(pendiente); setPendiente(null); }}>Revisarlo</Button>}>
          Tienes un cambio sin enviar de antes de que venciera tu sesión.
        </Alert>
      )}
      {resultado && <Alert color={COLOR_NIVEL[resultado.nivel]}>{resultado.texto}</Alert>}

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
              editable={puedeEditar ? editable : undefined}
              alAccionar={accionar}
              alSoltar={soltar}
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

      <RegistrarCambio borrador={borrador} alCambiar={cerrarCambio} nombres={nombres} turnos={datos?.turnos ?? []} actual={codigoDe}
        cupos={cupos} error={errorCambio} enviando={enviando} alEnviar={enviar} />

      {datos && (
        <Tarjeta data-solo-pantalla titulo={<>Alertas {datos.alertas.length > 0 && <span className={e.cuenta}>{datos.alertas.length}</span>}</>}>
          {datos.alertas.length === 0 ? (
            <p className={e.vacio}>Sin alertas: el cuadro cumple las reglas.</p>
          ) : (
            <>
              <p className={e.sub}>Corrige primero las rojas; las amarillas son recomendaciones.</p>
              {(["error", "aviso"] as const).map((nivel) => {
                const grupo = agrupar(datos.alertas.filter((a) => (a.nivel === "error") === (nivel === "error")));
                if (!grupo.length) return null;
                const errores = nivel === "error";
                return (
                  <details key={nivel} className={e.grupo} open={errores || !datos.alertas.some((a) => a.nivel === "error")}>
                    <summary><span className={`${e.chip} ${errores ? e["chip-error"] : e["chip-aviso"]}`}>{errores ? "Por corregir" : "Para revisar"} · {grupo.length}</span></summary>
                    <ul className={e.alertas}>
                      {grupo.map(({ alerta: a, veces }) => (
                        <li key={a.texto} className={e.alerta}>
                          <span className={e.texto}>{a.texto}{veces > 1 && <span className={e.veces}> (×{veces})</span>}</span>
                          {a.fecha && (
                            <Button color="link-color" size="sm" onPress={() => irA(a)} aria-label={`${a.colab_id ? "Ir a la celda" : "Ir al día"}: ${a.texto}`}>
                              {a.colab_id ? "Ir a la celda" : `Ir al ${fechaCorta(a.fecha)}`}
                            </Button>
                          )}
                        </li>
                      ))}
                    </ul>
                  </details>
                );
              })}
            </>
          )}
        </Tarjeta>
      )}

      {datos && (
        <div data-solo-pantalla>
        <Cambios area={area.id} periodo={actual.id} revision={actual.revision} nombres={nombres} puedeAnular={puedeEditar}
          alConflicto={() => setRecarga((n) => n + 1)}
          alAnular={(a) => { setResultado({ nivel: a.length ? "aviso" : "ok", texto: "Cambio anulado." + (a.length ? " Ojo: " + a.slice(0, 3).join("; ") : "") }); setRecarga((n) => n + 1); }} />
        </div>
      )}
    </div>
  );
}

/** Guía de tres pasos del periodo: generar → revisar alertas → publicar. Solo informa; las acciones están arriba. */
function Pasos({ hay, alertas, publicado }: { hay: boolean; alertas: Alerta[]; publicado: boolean }) {
  // Mismas cuentas que la lista de alertas (agrupada), para que los números coincidan.
  const errores = agrupar(alertas.filter((a) => a.nivel === "error")).length, avisos = agrupar(alertas.filter((a) => a.nivel !== "error")).length;
  const pasos = [
    { titulo: "Generar", hecho: hay, texto: hay ? "Hecho: el cuadro está armado." : "Usa «Generar» para que el sistema arme el cuadro." },
    { titulo: "Revisar alertas", hecho: hay && !errores, texto: errores ? `${errores} por corregir · ${avisos} para revisar` : avisos ? `Sin errores · ${avisos} recomendaciones` : "Sin alertas." },
    { titulo: "Publicar", hecho: publicado, texto: publicado ? "Publicado: el equipo ve esta versión." : "Cuando esté listo, publícalo para el equipo." },
  ];
  const actual = pasos.findIndex((p) => !p.hecho);
  return (
    <ol className={e.pasos} aria-label="Pasos del periodo" data-no-imprimir>
      {pasos.map((p, i) => (
        <li key={p.titulo} className={p.hecho ? e.hecho : i === actual ? e.actual : undefined} aria-current={i === actual ? "step" : undefined}>
          <span className={e.numero} aria-hidden="true">{p.hecho ? "✓" : i + 1}</span>
          <span><strong>{i + 1}. {p.titulo}</strong><span className={e.paso}>{p.texto}</span></span>
        </li>
      ))}
    </ol>
  );
}
