import { useEffect, useRef, useState, type DragEvent } from "react";
import { useOutletContext, useParams } from "react-router";
import { enviar, mensaje, usar } from "../api/catalogos";
import { base, rutaSemana, subirCuadro, rutaDescarga, type Archivo, type Exporte, type Semana, type Semanas } from "../api/radiologia";
import type { Area } from "../api/tipos";
import { Agendas, Alertas, Cambios, Equidad, Previa, Resumen } from "./RadiologiaVistas";
import { Button } from "@/components/base/buttons/button";
import { Alert } from "@/components/application/alerts/alert";
import { cx } from "@/utils/cx";
import { ArrowLeft, ArrowRight, Calendar, Download01, Home02, Upload01 } from "@untitledui/icons";
import { Filtro, Pagina, Pista } from "./comun";

export const SECCIONES: [string, string][] = [["Resumen", "resumen"], ["Vista previa", "previa"], ["Alertas", "alertas"], ["Equidad y horas", "equidad"], ["Agendas", "agendas"], ["Cambios", "cambios"]];

/** Radiología con lo que hace hoy la app de escritorio: se sube el cuadro mensual (.xlsx), se elige la semana y se revisa. */
export function Radiologia() {
  const area = useOutletContext<Area>();
  const { seccion = "resumen" } = useParams();
  const editar = area.permiso === "editar";
  const archivos = usar<Archivo[]>(`${base(area.id)}/archivos`);
  const [elegido, setElegido] = useState<number | null>(null);
  const [lunes, setLunes] = useState<string | null>(null);
  const [errorSubida, setErrorSubida] = useState<string | null>(null);
  const [subiendo, setSubiendo] = useState(false);
  const [encima, setEncima] = useState(false);
  const entrada = useRef<HTMLInputElement>(null);

  const id = elegido ?? archivos.datos?.[0]?.id ?? null;  // el último subido, como «último archivo» de la app
  const semanas = usar<Semanas>(id ? `${base(area.id)}/archivos/${id}/semanas` : null);
  useEffect(() => { setLunes(null); }, [id]);
  const actual = lunes ?? semanas.datos?.defecto ?? null;
  const semana = usar<Semana>(id && actual ? rutaSemana(area.id, id, actual) : null);

  const subir = async (archivo: File | undefined) => {
    if (!archivo) return;
    setSubiendo(true);
    setErrorSubida(null);
    try {
      const nuevo = await subirCuadro(area.id, archivo);
      setElegido(nuevo.id);
      archivos.recargar();
    } catch (x) {
      setErrorSubida(mensaje(x));
    } finally {
      setSubiendo(false);
    }
  };
  const [guardado, setGuardado] = useState<string | null>(null);
  const guardar = async () => {
    if (!id || !actual) return;
    setErrorSubida(null);
    try {
      const x = await enviar<Exporte>("POST", `${rutaSemana(area.id, id, actual)}/exportes`);
      setGuardado(`Guardado: ${x.nombre_archivo}`);
      location.assign(rutaDescarga(area.id, x));
      semana.recargar();
    } catch (x) {
      setErrorSubida(mensaje(x));
    }
  };
  const soltar = (ev: DragEvent) => { ev.preventDefault(); setEncima(false); if (editar) subir(ev.dataTransfer.files[0]); };

  const lista = semanas.datos?.semanas ?? [];
  const i = lista.findIndex((s) => s.lunes === actual);
  const error = archivos.error ?? semanas.error ?? semana.error;

  return (
    <Pagina titulo="Radiología" icono={Home02} sub="Planilla semanal a partir del cuadro mensual de turnos."
      filtros={id && semanas.datos && <>
        {archivos.datos && archivos.datos.length > 1 && (
          <Filtro etiqueta="Cuadro mensual" value={id} onChange={(ev) => setElegido(Number(ev.target.value))}>
            {archivos.datos.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
          </Filtro>
        )}
        <Button color="secondary" size="sm" iconLeading={ArrowLeft} isDisabled={i <= 0} onPress={() => { setLunes(lista[i - 1].lunes); setGuardado(null); }} aria-label="Semana anterior" />
        <Filtro etiqueta="Semana" icono={Calendar} value={actual ?? ""} onChange={(ev) => { setLunes(ev.target.value); setGuardado(null); }}>
          {lista.map((s) => <option key={s.lunes} value={s.lunes}>{s.etiqueta}</option>)}
        </Filtro>
        <Button color="secondary" size="sm" iconLeading={ArrowRight} isDisabled={i < 0 || i >= lista.length - 1} onPress={() => { setLunes(lista[i + 1].lunes); setGuardado(null); }} aria-label="Semana siguiente" />
      </>}
      acciones={(editar || (id && actual && semanas.datos)) && <>
        {id && actual && semanas.datos && <Pista texto="Guarda la semana en el historial y descarga el libro de Excel."><Button color="primary" size="sm" iconLeading={Download01} onPress={guardar}>Guardar y descargar libro</Button></Pista>}
        {editar && (
          <>
            <input ref={entrada} className="sr-only" type="file" accept=".xlsx" aria-label="Elegir cuadro mensual" tabIndex={-1} onChange={(ev) => { subir(ev.target.files?.[0]); ev.target.value = ""; }} />
            <Pista texto="Sube el cuadro mensual de turnos (.xlsx), guardado antes en Excel."><Button color={id ? "secondary" : "primary"} size="sm" iconLeading={Upload01} isDisabled={subiendo} onPress={() => entrada.current?.click()}>{subiendo ? "Subiendo…" : "Elegir cuadro mensual…"}</Button></Pista>
          </>
        )}
      </>}>
      {guardado && <Alert color="success">{guardado}</Alert>}
      {errorSubida && <Alert color="error">{errorSubida}</Alert>}
      {error && <Alert color="error">{error}</Alert>}
      {archivos.datos && archivos.datos.length === 0 && (
        <div className={cx("tarjeta flex flex-col items-center gap-3 border-2 border-dashed border-primary p-8 text-center text-tertiary", encima && "border-brand bg-brand-primary")} onDragOver={(ev) => { ev.preventDefault(); setEncima(true); }} onDragLeave={() => setEncima(false)} onDrop={soltar}>
          <strong>Aún no hay un cuadro mensual</strong>
          <span>{editar ? "Arrastra aquí el cuadro mensual de turnos (.xlsx) o elígelo con el botón. Guárdalo en Excel antes de subirlo." : "Pide a quien coordina que suba el cuadro mensual."}</span>
        </div>
      )}
      {semana.datos?.resumen.aviso && seccion !== "resumen" && <Alert color="warning">{semana.datos.resumen.aviso}</Alert>}
      {id && actual && semana.datos && (
        seccion === "previa" ? <Previa area={area.id} archivo={id} lunes={actual} /> :
        seccion === "alertas" ? <Alertas datos={semana.datos.alertas} /> :
        seccion === "equidad" ? <Equidad area={area.id} archivos={archivos.datos ?? []} actual={id} datos={semana.datos.equidad} /> :
        seccion === "agendas" ? <Agendas area={area.id} archivo={id} lunes={actual} agendas={semana.datos.agendas} /> :
        seccion === "cambios" ? <Cambios datos={semana.datos.cambios} /> :
        <Resumen datos={semana.datos.resumen} />
      )}
    </Pagina>
  );
}
