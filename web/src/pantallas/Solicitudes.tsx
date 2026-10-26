import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, EstadoSolicitud, Periodo, Solicitud, Turno } from "../api/tipos";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Fila, Formulario, Pagina, useAccion } from "./comun";
import { fechaCorta } from "./fechas";

const TIPO = { libre: "Pide el día libre", quiero: "Prefiere un turno", evitar: "Prefiere no hacer un turno" } as const;

/** Deseos de las personas (libre, quiero, evitar). El solver los intenta cumplir sin garantía; la columna Estado mira el último periodo. */
export function Solicitudes() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const lista = usar<Solicitud[]>(`${base}/solicitudes`);
  const personas = usar<Colaborador[]>(`${base}/colaboradores`);
  const turnos = usar<Turno[]>(`${base}/turnos`);
  const periodos = usar<Periodo[]>(`${base}/periodos`);
  const ultimo = periodos.datos?.at(-1);
  const estados = usar<EstadoSolicitud[]>(ultimo ? `${base}/periodos/${ultimo.id}/solicitudes` : null);
  const { ocupado, aviso, hacer } = useAccion();
  const [f, setF] = useState({ colab_id: "", tipo: "libre", desde: "", hasta: "", turno: "", prioridad: "normal", nota: "" });
  const nombre = useMemo(() => new Map((personas.datos ?? []).map((p) => [p.id, p.nombre])), [personas.datos]);
  const estado = useMemo(() => new Map((estados.datos ?? []).map((s) => [s.id, s])), [estados.datos]);
  const editar = area.permiso === "editar";

  const guardar = () => hacer(async () => {
    await enviar("POST", `${base}/solicitudes`, { ...f, colab_id: Number(f.colab_id), turno: f.tipo === "libre" ? "" : f.turno });
    setF({ ...f, nota: "" });
    lista.recargar(); estados.recargar();
    return "Solicitud guardada. Se tiene en cuenta al generar; no es una garantía.";
  });

  return (
    <Pagina titulo="Solicitudes" sub="Preferencias del personal para el próximo cuadro." ayuda={<>Una solicitud es un <strong>deseo, no una garantía</strong>: el sistema intenta cumplirla al generar, pero primero cubre los puestos y respeta las reglas legales. Usa prioridad <strong>alta</strong> solo para lo importante (una cita médica, un compromiso familiar). Después de generar verás si cada solicitud se cumplió.</>} error={lista.error ?? personas.error} aviso={aviso}>
      {editar && (
        <Tarjeta titulo="Nueva solicitud">
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar(); }}>
            <Seleccion etiqueta="Persona" required value={f.colab_id} onChange={(x) => setF({ ...f, colab_id: x.target.value })}>
              <option value="">Elige…</option>
              {(personas.datos ?? []).filter((p) => p.activo).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </Seleccion>
            <Seleccion etiqueta="Tipo" value={f.tipo} onChange={(x) => setF({ ...f, tipo: x.target.value })}>
              {Object.entries(TIPO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </Seleccion>
            {f.tipo !== "libre" && (
              <Seleccion etiqueta="Turno" required value={f.turno} onChange={(x) => setF({ ...f, turno: x.target.value })}>
                <option value="">Elige…</option>
                {(turnos.datos ?? []).filter((t) => t.activo).map((t) => <option key={t.codigo} value={t.codigo}>{t.codigo} · {t.nombre}</option>)}
              </Seleccion>
            )}
            <Campo etiqueta="Desde" type="date" required value={f.desde} onChange={(x) => setF({ ...f, desde: x.target.value })} />
            <Campo etiqueta="Hasta" type="date" required value={f.hasta} onChange={(x) => setF({ ...f, hasta: x.target.value })} />
            <Seleccion etiqueta="Prioridad" value={f.prioridad} onChange={(x) => setF({ ...f, prioridad: x.target.value })}>
              <option value="normal">Normal</option><option value="alta">Alta</option>
            </Seleccion>
            <Campo etiqueta="Nota" maxLength={300} value={f.nota} onChange={(x) => setF({ ...f, nota: x.target.value })} />
            <Fila><Boton type="submit" variante="primario" disabled={ocupado || !f.colab_id || !f.desde || !f.hasta}>{ocupado ? "Guardando…" : "Guardar"}</Boton></Fila>
          </Formulario>
        </Tarjeta>
      )}
      <Tarjeta titulo="Solicitudes registradas">
        <Tabla
          descripcion="Solicitudes del área"
          cargando={!lista.datos && !lista.error}
          vacio="Aún no hay solicitudes."
          columnas={["Persona", "Tipo", "Fechas", "Prioridad", ultimo ? "Estado en el último periodo" : "Estado", "Nota", ""]}
          filas={(lista.datos ?? []).map((s) => [
            nombre.get(s.colab_id) ?? `#${s.colab_id}`,
            TIPO[s.tipo] + (s.turno ? ` ${s.turno}` : ""),
            `${fechaCorta(s.desde)} – ${fechaCorta(s.hasta)}`,
            s.prioridad === "alta" ? "Alta" : "Normal",
            estado.get(s.id) ? `${estado.get(s.id)!.estado}${estado.get(s.id)!.motivo ? ` (${estado.get(s.id)!.motivo})` : ""}` : "",
            s.nota,
            editar ? <Boton variante="texto" disabled={ocupado} onClick={() => hacer(async () => { await enviar("DELETE", `${base}/solicitudes/${s.id}`); lista.recargar(); estados.recargar(); })}>Borrar</Boton> : null,
          ])}
        />
      </Tarjeta>
    </Pagina>
  );
}
