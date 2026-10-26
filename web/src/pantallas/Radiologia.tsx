import { useEffect, useRef, useState, type DragEvent } from "react";
import { useOutletContext, useParams } from "react-router";
import { enviar, mensaje, usar } from "../api/catalogos";
import { base, rutaSemana, subirCuadro, rutaDescarga, type Archivo, type Exporte, type Semana, type Semanas } from "../api/radiologia";
import type { Area } from "../api/tipos";
import { Agendas, Alertas, Cambios, Equidad, Previa, Resumen } from "./RadiologiaVistas";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert } from "@/components/application/alerts/alert";
import { cx } from "@/utils/cx";

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
    <div className="flex max-w-[1500px] flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div><h1 className="text-display-xs font-semibold text-primary">Radiología</h1><p className="mt-1 text-md text-tertiary">Planilla semanal a partir del cuadro mensual de turnos.</p></div>
        {editar && (
          <>
            <input ref={entrada} className="sr-only" type="file" accept=".xlsx" aria-label="Elegir cuadro mensual" tabIndex={-1} onChange={(ev) => { subir(ev.target.files?.[0]); ev.target.value = ""; }} />
            <Button color="primary" size="sm" isDisabled={subiendo} onPress={() => entrada.current?.click()}>{subiendo ? "Subiendo…" : "Elegir cuadro mensual…"}</Button>
          </>
        )}
      </div>
      {guardado && <Alert color="success">{guardado}</Alert>}
      {errorSubida && <Alert color="error">{errorSubida}</Alert>}
      {error && <Alert color="error">{error}</Alert>}
      {archivos.datos && archivos.datos.length === 0 && (
        <div className={cx("flex flex-col items-center gap-3 rounded-xl border-2 border-dashed border-primary bg-primary p-8 text-center text-tertiary", encima && "border-brand bg-brand-primary")} onDragOver={(ev) => { ev.preventDefault(); setEncima(true); }} onDragLeave={() => setEncima(false)} onDrop={soltar}>
          <strong>Aún no hay un cuadro mensual</strong>
          <span>{editar ? "Arrastra aquí el cuadro mensual de turnos (.xlsx) o elígelo con el botón. Guárdalo en Excel antes de subirlo." : "Pide a quien coordina que suba el cuadro mensual."}</span>
        </div>
      )}
      {id && semanas.datos && (
        <div className="flex flex-wrap items-end gap-3 print:hidden">
          {archivos.datos && archivos.datos.length > 1 && (
            <NativeSelect size="sm" label="Cuadro mensual" value={id} onChange={(ev) => setElegido(Number(ev.target.value))}>
              {archivos.datos.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </NativeSelect>
          )}
          <Button color="secondary" size="sm" isDisabled={i <= 0} onPress={() => { setLunes(lista[i - 1].lunes); setGuardado(null); }} aria-label="Semana anterior">←</Button>
          <NativeSelect size="sm" label="Semana" value={actual ?? ""} onChange={(ev) => { setLunes(ev.target.value); setGuardado(null); }}>
            {lista.map((s) => <option key={s.lunes} value={s.lunes}>{s.etiqueta}</option>)}
          </NativeSelect>
          <Button color="secondary" size="sm" isDisabled={i < 0 || i >= lista.length - 1} onPress={() => { setLunes(lista[i + 1].lunes); setGuardado(null); }} aria-label="Semana siguiente">→</Button>
          {actual && <Button color="primary" size="sm" onPress={guardar}>Guardar y descargar libro</Button>}
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
    </div>
  );
}
