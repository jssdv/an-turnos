import { useEffect, useRef, useState, type DragEvent } from "react";
import { useOutletContext, useParams } from "react-router";
import { enviar, mensaje, usar } from "../api/catalogos";
import { base, rutaSemana, subirCuadro, rutaDescarga, type Archivo, type Exporte, type Semana, type Semanas } from "../api/radiologia";
import type { Area } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Seleccion } from "../componentes/Campo";
import { Agendas, Alertas, Cambios, Equidad, Previa, Resumen } from "./RadiologiaVistas";
import r from "./Radiologia.module.css";
import c from "./Cuadro.module.css";

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
    <div className={c.pagina}>
      <div className={c.barra}>
        <div><h1 className={c.titulo}>Radiología</h1><p className={c.sub}>Planilla semanal a partir del cuadro mensual de turnos.</p></div>
        {editar && (
          <>
            <input ref={entrada} className={r.oculto} type="file" accept=".xlsx" aria-label="Elegir cuadro mensual" tabIndex={-1} onChange={(ev) => { subir(ev.target.files?.[0]); ev.target.value = ""; }} />
            <Boton variante="primario" disabled={subiendo} onClick={() => entrada.current?.click()}>{subiendo ? "Subiendo…" : "Elegir cuadro mensual…"}</Boton>
          </>
        )}
      </div>
      {guardado && <Aviso nivel="ok">{guardado}</Aviso>}
      {errorSubida && <Aviso nivel="error">{errorSubida}</Aviso>}
      {error && <Aviso nivel="error">{error}</Aviso>}
      {archivos.datos && archivos.datos.length === 0 && (
        <div className={`${r.subida} ${encima ? r.encima : ""}`} onDragOver={(ev) => { ev.preventDefault(); setEncima(true); }} onDragLeave={() => setEncima(false)} onDrop={soltar}>
          <strong>Aún no hay un cuadro mensual</strong>
          <span>{editar ? "Arrastra aquí el cuadro mensual de turnos (.xlsx) o elígelo con el botón. Guárdalo en Excel antes de subirlo." : "Pide a quien coordina que suba el cuadro mensual."}</span>
        </div>
      )}
      {id && semanas.datos && (
        <div className={r.selector}>
          {archivos.datos && archivos.datos.length > 1 && (
            <Seleccion etiqueta="Cuadro mensual" value={id} onChange={(ev) => setElegido(Number(ev.target.value))}>
              {archivos.datos.map((a) => <option key={a.id} value={a.id}>{a.nombre}</option>)}
            </Seleccion>
          )}
          <Boton disabled={i <= 0} onClick={() => { setLunes(lista[i - 1].lunes); setGuardado(null); }} aria-label="Semana anterior">←</Boton>
          <Seleccion etiqueta="Semana" value={actual ?? ""} onChange={(ev) => { setLunes(ev.target.value); setGuardado(null); }}>
            {lista.map((s) => <option key={s.lunes} value={s.lunes}>{s.etiqueta}</option>)}
          </Seleccion>
          <Boton disabled={i < 0 || i >= lista.length - 1} onClick={() => { setLunes(lista[i + 1].lunes); setGuardado(null); }} aria-label="Semana siguiente">→</Boton>
          {actual && <Boton variante="primario" onClick={guardar}>Guardar y descargar libro</Boton>}
        </div>
      )}
      {semana.datos?.resumen.aviso && seccion !== "resumen" && <Aviso nivel="aviso">{semana.datos.resumen.aviso}</Aviso>}
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
