import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, EstadoSolicitud, Periodo, Solicitud, Turno } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Plus, Users01 } from "@untitledui/icons";
import { Fila, Filtro, Formulario, Pagina, Pista, useAccion, Seccion, Ventana } from "./comun";
import { Alert } from "@/components/application/alerts/alert";
import { fechaCorta } from "./fechas";
import { Button } from "@/components/base/buttons/button";
import { CampoFecha } from "../componentes/CampoFecha";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Badge } from "@/components/base/badges/badges";

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
  const [ventana, setVentana] = useState(false);
  const [f, setF] = useState({ colab_id: "", tipo: "libre", desde: "", hasta: "", turno: "", prioridad: "normal", nota: "" });
  const nombre = useMemo(() => new Map((personas.datos ?? []).map((p) => [p.id, p.nombre])), [personas.datos]);
  const estado = useMemo(() => new Map((estados.datos ?? []).map((s) => [s.id, s])), [estados.datos]);
  const editar = area.permiso === "editar";
  const [persona, ver] = useState("");  // filtro de la tabla: "" = todas
  const visibles = (lista.datos ?? []).filter((x) => !persona || String(x.colab_id) === persona);
  const cumplidas = visibles.filter((x) => estado.get(x.id)?.estado === "cumplida").length;

  const guardar = () => hacer(async () => {
    await enviar("POST", `${base}/solicitudes`, { ...f, colab_id: Number(f.colab_id), turno: f.tipo === "libre" ? "" : f.turno });
    setF({ ...f, nota: "" });
    lista.recargar(); estados.recargar();
    return "Solicitud guardada. Se tiene en cuenta al generar; no es una garantía.";
  });

  return (
    <Pagina titulo="Solicitudes" sub="Preferencias del personal para el próximo cuadro."
      filtros={<Filtro etiqueta="Persona" icono={Users01} value={persona} onChange={(x) => ver(x.target.value)}>
        <option value="">Todas las personas</option>
        {(personas.datos ?? []).filter((p) => p.activo).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
      </Filtro>}
      acciones={editar && <Pista texto="Registra un deseo de una persona: día libre, turno preferido o turno a evitar."><Button color="primary" size="sm" iconLeading={Plus} onPress={() => setVentana(true)}>Nueva solicitud</Button></Pista>} ayuda={<>Una solicitud es un <strong>deseo, no una garantía</strong>: el sistema intenta cumplirla al generar, pero primero cubre los puestos y respeta las reglas legales. Usa prioridad <strong>alta</strong> solo para lo importante (una cita médica, un compromiso familiar). Después de generar verás si cada solicitud se cumplió.</>} error={lista.error ?? personas.error} aviso={aviso}>
      {editar && (
        <Ventana abierto={ventana} alCambiar={setVentana} titulo="Nueva solicitud" ancha descripcion="Un deseo, no una garantía: se intenta cumplir al generar.">
          {aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>}
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar().then((ok) => ok && setVentana(false)); }}>
            <NativeSelect size="sm" label="Persona" required value={f.colab_id} onChange={(x) => setF({ ...f, colab_id: x.target.value })}>
              <option value="">Elige…</option>
              {(personas.datos ?? []).filter((p) => p.activo).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </NativeSelect>
            <NativeSelect size="sm" label="Tipo" value={f.tipo} onChange={(x) => setF({ ...f, tipo: x.target.value })}>
              {Object.entries(TIPO).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
            </NativeSelect>
            {f.tipo !== "libre" && (
              <NativeSelect size="sm" label="Turno" required value={f.turno} onChange={(x) => setF({ ...f, turno: x.target.value })}>
                <option value="">Elige…</option>
                {(turnos.datos ?? []).filter((t) => t.activo).map((t) => <option key={t.codigo} value={t.codigo}>{t.codigo} · {t.nombre}</option>)}
              </NativeSelect>
            )}
            <CampoFecha value={f.desde} label="Desde" isRequired onChange={(x) => setF({ ...f, desde: x })} />
            <CampoFecha value={f.hasta} label="Hasta" isRequired onChange={(x) => setF({ ...f, hasta: x })} />
            <NativeSelect size="sm" label="Prioridad" value={f.prioridad} onChange={(x) => setF({ ...f, prioridad: x.target.value })}>
              <option value="normal">Normal</option><option value="alta">Alta</option>
            </NativeSelect>
            <Input value={String(f.nota)} label="Nota" maxLength={300} onChange={(x) => setF({ ...f, nota: x })} />
            <Fila><Button color="secondary" size="sm" onPress={() => setVentana(false)}>Cancelar</Button><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !f.colab_id || !f.desde || !f.hasta}>{ocupado ? "Guardando…" : "Guardar"}</Button></Fila>
          </Formulario>
        </Ventana>
      )}
      <Seccion titulo="Solicitudes registradas">
        {persona && ultimo && <p className="mb-3 text-md text-tertiary">{visibles.length ? `${cumplidas} de ${visibles.length} cumplidas en el último periodo.` : "Esta persona no tiene solicitudes."}</p>}
        <Tabla
          descripcion="Solicitudes del área"
          cargando={!lista.datos && !lista.error}
          vacio={persona ? "Esta persona no tiene solicitudes." : "Aún no hay solicitudes."}
          columnas={["Persona", "Tipo", "Fechas", "Prioridad", ultimo ? "Estado en el último periodo" : "Estado", "Nota", ""]}
          filas={visibles.map((s) => [
            nombre.get(s.colab_id) ?? `#${s.colab_id}`,
            TIPO[s.tipo] + (s.turno ? ` ${s.turno}` : ""),
            `${fechaCorta(s.desde)} – ${fechaCorta(s.hasta)}`,
            s.prioridad === "alta" ? <Badge size="sm" color="warning">Alta</Badge> : "Normal",
            estado.get(s.id) ? `${estado.get(s.id)!.estado}${estado.get(s.id)!.motivo ? ` (${estado.get(s.id)!.motivo})` : ""}` : "",
            s.nota,
            editar ? <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => hacer(async () => { await enviar("DELETE", `${base}/solicitudes/${s.id}`); lista.recargar(); estados.recargar(); })}>Borrar</Button> : null,
          ])}
        />
      </Seccion>
    </Pagina>
  );
}
