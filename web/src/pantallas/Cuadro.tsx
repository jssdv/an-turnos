import { useEffect, useMemo, useState } from "react";
import { useNavigate, useOutletContext, useParams } from "react-router";
import { borrador as guardado, cambios, type Borrador } from "../api/cambios";
import { ErrorApi, leer } from "../api/cliente";
import { useSesion } from "../Sesion";
import type { Alerta, Analiticas, Area, Colaborador, Cuadro as CuadroApi, Cupo, CuerpoCambio, Horas, Novedad, Periodo, Puesto, Turno } from "../api/tipos";
import { Planilla, type Foco, type Sel } from "../componentes/Planilla";
import { Tabla } from "../componentes/Tabla";
import { AccionesPeriodo } from "./AccionesPeriodo";
import { Cambios } from "./Cambios";
import { dias as diasDe, fechaCorta, mesDe, nombrePeriodo } from "./fechas";
import { Exportar } from "./Exportar";
import { Generar } from "./Generar";
import { RegistrarCambio, sinCupo } from "./RegistrarCambio";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";
import { Seccion, Ayuda } from "./comun";
import { cx } from "@/utils/cx";
import { Badge } from "@/components/base/badges/badges";

interface Datos {
  cuadro: CuadroApi;
  alertas: Alerta[];
  horas: Horas[];
  colabs: Colaborador[];
  turnos: Turno[];
  puestos: Puesto[];
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
  const [version, setVersion] = useState<"cambios" | "original">("cambios");
  const [verPuestos, setVerPuestos] = useState(false);
  const [foco, setFoco] = useState<Foco | null>(null);
  const [persona, setPersona] = useState("");  // filtro de la lista de alertas: "" = todas
  const uid = useSesion().usuario?.id ?? 0;
  const [borrador, setBorrador] = useState<Borrador | null>(null);
  const [cupos, setCupos] = useState<Cupo[] | null>(null);
  const [errorCambio, setErrorCambio] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [resultado, setResultado] = useState<{ nivel: "ok" | "aviso"; texto: string } | null>(null);
  const [pendiente, setPendiente] = useState<Borrador | null>(() => guardado.leer(area.id, uid));

  // Al recargar (p. ej. tras generar) se conserva lo que hay en pantalla: vaciarlo desmontaría el diálogo de Generar.
  useEffect(() => { setPeriodos(null); setDatos(null); }, [area.id]);
  useEffect(() => setVersion("cambios"), [periodo]);
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
      leer<CuadroApi>(`${base}/periodos/${actual.id}/cuadro?version=${version}`),
      leer<Alerta[]>(`${base}/periodos/${actual.id}/alertas`),
      leer<Horas[]>(`${base}/periodos/${actual.id}/horas`),
      leer<Colaborador[]>(`${base}/colaboradores`),
      leer<Turno[]>(`${base}/turnos`),
      leer<Puesto[]>(`${base}/puestos`),
      leer<Novedad[]>(`${base}/novedades`),
      leer<Analiticas>(`${base}/analiticas?desde=${desde}&hasta=${hasta}`),
    ])
      .then(([cuadro, alertas, horas, colabs, turnos, puestos, novedades, analiticas]) => {
        if (!vivo) return;
        performance.mark("cuadro:datos");
        setDatos({ cuadro, alertas, horas, colabs, turnos, puestos, novedades, analiticas });
      })
      .catch((x) => vivo && setError(x.message));
    return () => { vivo = false; };
  }, [area.id, actual?.id, recarga, version]); // eslint-disable-line react-hooks/exhaustive-deps

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
    const puestos = new Map(datos.puestos.map((q) => [q.id, q]));
    return { celdas, turnos, puestos, horas, faltan, diaMalo, novedades, presentes };
  }, [datos, dias]);

  const nombres = useMemo(() => new Map((datos?.colabs ?? []).map((c) => [c.id, c.nombre])), [datos]);
  const puedeEditar = area.permiso === "editar" && !!actual && !actual.cerrado_en && version === "cambios";
  const codigoDe = (id: number, fecha: string) => vista?.celdas.get(`${id}|${fecha}`)?.turno ?? "L";
  const usaPuestos = !!datos?.cuadro.usa_puestos;
  /** Nombre del puesto de una celda con turno, o "" (libre, apoyo o área sin puestos). */
  const puestoDe = (id: number, fecha: string) => {
    const c = vista?.celdas.get(`${id}|${fecha}`);
    return usaPuestos && c && c.turno !== "L" && c.puesto ? `${vista?.puestos.get(c.puesto)?.nombre ?? ""}${c.puesto_fijo ? " (fijo)" : ""}` : "";
  };
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
    } else celdas = b.celdas.map((c) => ({ ...c, turno: b.turno, ...(b.puesto ? { puesto: Number(b.puesto) } : {}) }));
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

  if (error) return <div className="flex max-w-[1500px] flex-col gap-5"><Alert color="error" action={<Button color="secondary" size="sm" onPress={() => setRecarga((n) => n + 1)}>Reintentar</Button>}>{error}</Alert></div>;
  if (!periodos) return <p className="p-6 text-center text-tertiary" aria-busy="true">Cargando…</p>;
  if (!actual) return (
    <div className="flex flex-col items-center gap-4 p-6 text-center text-tertiary">
      <p>Esta área aún no tiene periodos. Crea uno para poder generar el cuadro.</p>
      {area.permiso === "editar" && <AccionesPeriodo area={area.id} periodo={null} alTerminar={() => setRecarga((n) => n + 1)} />}
    </div>
  );

  const deficit = datos?.analiticas.cobertura[0];
  const irA = (a: Alerta) => a.fecha && setFoco({ fila: a.colab_id, fecha: a.fecha, marca: Date.now() });

  return (
    <div className="flex max-w-[1500px] flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-display-xs font-semibold text-primary">Cuadro de {mesDe(actual.clave)}</h1>
          <p className="mt-1 text-md text-tertiary">
            {dias.length} días · versión {actual.revision}
            {deficit && (deficit.dias_deficit || deficit.puestos_sin_cubrir
              ? ` · ${deficit.dias_deficit} días con falta de personal, ${deficit.puestos_sin_cubrir} puestos sin cubrir`
              : " · todos los puestos cubiertos")}
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-3" data-no-imprimir>
          {actual.cerrado_en ? <Badge color="gray">Cerrado</Badge> : actual.publicado_en && <Badge color="success">Publicado</Badge>}
          <NativeSelect size="sm" className="w-56" label="Periodo" value={actual.id} onChange={(x) => ir(`/areas/${area.id}/cuadro/${x.target.value}`)}>
            {periodos.map((p) => <option key={p.id} value={p.id}>{nombrePeriodo(p.clave)}</option>)}
          </NativeSelect>
          <NativeSelect size="sm" className="w-40" label="Planilla" value={version} onChange={(x) => setVersion(x.target.value as "cambios" | "original")}>
            <option value="cambios">Cambios (vigente)</option>
            <option value="original">Original (publicada)</option>
          </NativeSelect>
          {usaPuestos && (
            <label className="flex items-center gap-2 pb-2 text-sm text-secondary">
              <input type="checkbox" checked={verPuestos} onChange={(x) => setVerPuestos(x.target.checked)} /> Ver puestos
            </label>
          )}
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
      {version === "original" && <Alert color="brand">Planilla original (publicada): solo lectura. Los cambios y los puestos están en «Cambios».</Alert>}
      {resultado && <Alert color={COLOR_NIVEL[resultado.nivel]}>{resultado.texto}</Alert>}

      <Seccion aria-busy={!datos}>
        {!datos || !vista ? (
          <p className="p-6 text-center text-tertiary">Cargando el cuadro…</p>
        ) : datos.cuadro.celdas.length === 0 ? (
          <p className="p-6 text-center text-tertiary">Este periodo no tiene cuadro todavía.</p>
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
              semanal={(id, lunes) => { const v = vista.horas.get(id)?.semanas[lunes]; return v ? Math.round(v * 10) / 10 : ""; }}
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
                  codigo, color: t?.color, cambiada: c?.fijo, puesto: verPuestos && c?.puesto ? String(vista.puestos.get(c.puesto)?.numero ?? "") : undefined, novedad: nov ? (SIGLA_NOVEDAD[nov] ?? nov) : null, faltante: falta,
                  etiqueta: `${nov ?? t?.nombre ?? (codigo === "L" ? "Libre" : codigo)}${puestoDe(id, fecha) ? `, puesto ${puestoDe(id, fecha)}` : ""}${c?.fijo ? ", editada a mano" : ""}${falta ? ", con alerta" : ""}`,
                };
              }}
              pie={(["M", "T", "N"] as const).map((f) => ({
                titulo: { M: "Presentes mañana", T: "Presentes tarde", N: "Presentes noche" }[f],
                valor: (fecha) => vista.presentes(fecha, f),
                alerta: (fecha) => vista.diaMalo.has(fecha),
              }))}
            />
            <div className="mt-3 flex flex-wrap gap-x-4 gap-y-2 text-xs text-tertiary">
              {datos.turnos.filter((t) => t.activo).map((t) => <span key={t.codigo}>{t.codigo} {t.nombre}</span>)}
              <span>L Libre</span>
              {verPuestos && usaPuestos && datos.puestos.filter((q) => q.activo).map((q) => <span key={q.id}>{q.numero} {q.nombre}</span>)}
              <span>◥ editada a mano</span>
              <span>columnas grises: domingo</span>
            </div>
            <HorasSemana horas={datos.horas} colabs={datos.colabs.filter((c) => c.activo)} />
          </>
        )}
      </Seccion>

      <RegistrarCambio borrador={borrador} alCambiar={cerrarCambio} nombres={nombres} turnos={datos?.turnos ?? []} actual={codigoDe} puestos={usaPuestos ? datos!.puestos.filter((q) => q.activo) : null} puestoDe={puestoDe}
        cupos={cupos} error={errorCambio} enviando={enviando} alEnviar={enviar} />

      {datos && (() => {
        const vista = persona ? datos.alertas.filter((a) => String(a.colab_id) === persona) : datos.alertas;
        const reglas = vista.filter((a) => a.nivel !== "info").length;
        const niveles = [["error", "Por corregir", "error"], ["aviso", "Para revisar", "warning"], ["info", "Deseables sin cubrir", "gray"]] as const;
        return (
          <Seccion data-solo-pantalla titulo={<>Alertas {reglas > 0 && <Badge size="sm" color="warning">{reglas}</Badge>}</>}>
            <NativeSelect size="sm" className="w-64" label="Persona" value={persona} onChange={(x) => setPersona(x.target.value)}>
              <option value="">Todas</option>
              {datos.colabs.filter((c) => c.activo).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </NativeSelect>
            {persona && <p className="mt-1 text-md text-tertiary">Solo alertas de esta persona; las de cobertura de un día no se muestran.</p>}
            {vista.length === 0 ? (
              <p className="p-6 text-center text-tertiary">{persona ? "Sin alertas para esta persona." : "Sin alertas: el cuadro cumple las reglas."}</p>
            ) : (
              <>
                {reglas > 0 && <p className="mt-1 text-md text-tertiary">Corrige primero las rojas; las amarillas son recomendaciones.</p>}
                {niveles.map(([nivel, titulo, color]) => {
                  const grupo = agrupar(vista.filter((a) => a.nivel === nivel));
                  if (!grupo.length) return null;
                  const info = nivel === "info";
                  return (
                    <details key={nivel} className="[&+&]:mt-3 [&>summary]:cursor-pointer [&>summary]:py-2" open={nivel === "error" || (nivel === "aviso" && !vista.some((a) => a.nivel === "error"))}>
                      <summary><Badge size="sm" color={color}>{titulo} · {grupo.length}</Badge></summary>
                      <ul className="">
                        {grupo.map(({ alerta: a, veces }) => (
                          <li key={a.texto} className={`flex items-center gap-3 border-t border-secondary first:border-t-0 ${info ? "py-1 text-sm text-tertiary" : "py-2"}`}>
                            <span className="flex-1">{a.texto}{veces > 1 && <span className="text-tertiary"> (×{veces})</span>}</span>
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
          </Seccion>
        );
      })()}

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
  const errores = agrupar(alertas.filter((a) => a.nivel === "error")).length, avisos = agrupar(alertas.filter((a) => a.nivel === "aviso")).length;
  const pasos = [
    { titulo: "Generar", hecho: hay, texto: hay ? "Hecho: el cuadro está armado." : "Usa «Generar» para que el sistema arme el cuadro." },
    { titulo: "Revisar alertas", hecho: hay && !errores, texto: errores ? `${errores} por corregir · ${avisos} para revisar` : avisos ? `Sin errores · ${avisos} recomendaciones` : "Sin alertas." },
    { titulo: "Publicar", hecho: publicado, texto: publicado ? "Publicado: el equipo ve esta versión." : "Cuando esté listo, publícalo para el equipo." },
  ];
  const actual = pasos.findIndex((p) => !p.hecho);
  return (
    <ol className="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-3 print:hidden" aria-label="Pasos del periodo" data-no-imprimir>
      {pasos.map((p, i) => (
        <li key={p.titulo} data-hecho={p.hecho || undefined} data-actual={(!p.hecho && i === actual) || undefined}
          className={cx("flex items-center gap-3 rounded-xl bg-primary px-4 py-3 text-primary ring-1 ring-secondary ring-inset", p.hecho && "bg-utility-green-50 text-utility-green-700 ring-utility-green-200", !p.hecho && i === actual && "bg-utility-yellow-50 text-utility-yellow-700 ring-utility-yellow-200")} aria-current={i === actual ? "step" : undefined}>
          <span className="grid size-7 shrink-0 place-items-center rounded-full bg-secondary font-bold text-tertiary in-data-hecho:bg-success-solid in-data-hecho:text-white in-data-actual:bg-warning-solid in-data-actual:text-white" aria-hidden="true">{p.hecho ? "✓" : i + 1}</span>
          <span><strong>{i + 1}. {p.titulo}</strong><span className="mt-0.5 block text-xs text-tertiary in-data-actual:text-utility-yellow-700 in-data-hecho:text-utility-green-700">{p.texto}</span></span>
        </li>
      ))}
    </ol>
  );
}

/** Horas trabajadas por semana (lunes a domingo). El rojo marca semanas sobre lo contratado; la regla legal es el promedio de varias semanas. */
function HorasSemana({ horas, colabs }: { horas: Horas[]; colabs: Colaborador[] }) {
  const lunes = [...new Set(horas.flatMap((h) => Object.keys(h.semanas)))].sort();
  const porId = new Map(horas.map((h) => [h.colab_id, h]));
  const filas = colabs.filter((c) => porId.has(c.id)).map((c) => {
    const h = porId.get(c.id)!;
    return [c.nombre, ...lunes.map((l) => {
      const v = h.semanas[l] ?? 0;
      return <span key={l} className={v > h.contratadas_sem ? "font-semibold text-error-primary" : undefined}>{v}</span>;
    }), h.trabajadas, h.contratadas, h.adicionales || "", h.pendientes || ""];
  });
  return (
    <details className="mt-4 [&>summary]:cursor-pointer [&>summary]:py-2" data-solo-pantalla>
      <summary>Horas por semana</summary>
      <p className="mb-2 text-sm text-tertiary">Cada semana cuenta de lunes a domingo; en rojo, las que superan lo contratado por semana. La ley mira el promedio de varias semanas (De más / De menos).</p>
      <Tabla descripcion="Horas trabajadas por semana" vacio="Sin horas todavía." filas={filas}
        columnas={["Colaborador", ...lunes.map((l) => fechaCorta(l)), "Total", "Contratadas", "De más", "De menos"]} />
    </details>
  );
}
