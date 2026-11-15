import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, Novedad } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Plus } from "@untitledui/icons";
import { Estado, Filtro, Fila, Formulario, Pagina, Pista, useAccion, useConfirmar, useVentanaNueva, Seccion, Ventana } from "./comun";
import { Alert } from "@/components/application/alerts/alert";
import { fechaCorta, isoHoy } from "./fechas";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Button } from "@/components/base/buttons/button";
import { CampoFecha } from "../componentes/CampoFecha";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";

const TIPOS = ["Vacaciones", "Incapacidad", "Licencia", "Libre solicitado"];
/** Días calendario de desde a hasta, ambos incluidos. */
const diasEntre = (desde: string, hasta: string) => Math.round((Date.parse(hasta) - Date.parse(desde)) / 86_400_000) + 1;

/** Vacaciones, incapacidades y licencias: la persona no se programa esos días. */
export function Novedades() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const lista = usar<Novedad[]>(`${base}/novedades`);
  const personas = usar<Colaborador[]>(`${base}/colaboradores`);
  const { ocupado, aviso, hacer } = useAccion();
  const [pedir, confirmacion] = useConfirmar();
  const [f, setF] = useState({ colab_id: "", tipo: TIPOS[0], desde: "", hasta: "", nota: "" });
  const nombre = useMemo(() => new Map((personas.datos ?? []).map((p) => [p.id, p.nombre])), [personas.datos]);
  const editar = area.permiso === "editar";
  const [ventana, setVentana] = useVentanaNueva(editar);
  const [quien, setQuien] = useState("");  // "" = todas las personas
  const [verTerminadas, setVerTerminadas] = useState(false);
  const hoy = isoHoy();
  const terminadas = (lista.datos ?? []).filter((n) => n.hasta < hoy).length;
  const visibles = (lista.datos ?? [])
    .filter((n) => (verTerminadas || n.hasta >= hoy) && (!quien || String(n.colab_id) === quien))
    .sort((a, b) => a.desde.localeCompare(b.desde) || a.colab_id - b.colab_id);

  const guardar = () => hacer(async () => {
    await enviar("POST", `${base}/novedades`, { ...f, colab_id: Number(f.colab_id) });
    setF({ ...f, nota: "" });
    lista.recargar();
    return "Novedad guardada. Regenera el cuadro (una semana o respetando tus cambios) para aplicarla.";
  });

  return (
    <Pagina titulo="Ausencias"
      acciones={editar && <Pista texto="Vacaciones, incapacidad, licencia o día libre concedido: esa persona no se programa esos días."><Button color="primary" size="sm" iconLeading={Plus} onPress={() => setVentana(true)}>Registrar ausencia</Button></Pista>} sub="Vacaciones, incapacidades, licencias y días libres concedidos." ayuda={<>Registra aquí cuándo alguien <strong>no puede trabajar</strong>. Al generar el cuadro, el sistema no le asigna turnos esos días. Si el cuadro ya existe, las alertas te avisan de los turnos que chocan con una ausencia.</>} error={lista.error ?? personas.error} aviso={aviso}>
      {editar && (
        <Ventana abierto={ventana} alCambiar={setVentana} titulo="Nueva ausencia" ancha descripcion="Esa persona no se programa esos días.">
          {aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>}
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar().then((ok) => ok && setVentana(false)); }}>
            <NativeSelect size="sm" label="Persona" required value={f.colab_id} onChange={(x) => setF({ ...f, colab_id: x.target.value })}>
              <option value="">Elige…</option>
              {(personas.datos ?? []).filter((p) => p.activo).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </NativeSelect>
            <NativeSelect size="sm" label="Tipo" value={f.tipo} onChange={(x) => setF({ ...f, tipo: x.target.value })}>
              {TIPOS.map((t) => <option key={t}>{t}</option>)}
            </NativeSelect>
            <CampoFecha value={f.desde} label="Desde" isRequired onChange={(x) => setF({ ...f, desde: x })} />
            <CampoFecha value={f.hasta} label="Hasta" isRequired onChange={(x) => setF({ ...f, hasta: x })} />
            <Input value={String(f.nota)} label="Nota" maxLength={300} onChange={(x) => setF({ ...f, nota: x })} />
            <Fila><Button color="secondary" size="sm" onPress={() => setVentana(false)}>Cancelar</Button><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !f.colab_id || !f.desde || !f.hasta}>{ocupado ? "Guardando…" : "Guardar"}</Button></Fila>
          </Formulario>
        </Ventana>
      )}
      <Seccion titulo="Ausencias registradas" acciones={<div className="flex flex-wrap items-center gap-4">
        <Filtro etiqueta="Persona" value={quien} onChange={(x) => setQuien(x.target.value)}>
          <option value="">Todas las personas</option>
          {(personas.datos ?? []).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
        </Filtro>
        <Checkbox label={`Mostrar las terminadas (${terminadas})`} isSelected={verTerminadas} onChange={setVerTerminadas} />
      </div>}>
        <Tabla
          descripcion="Ausencias del área"
          cargando={!lista.datos && !lista.error}
          vacio={lista.datos?.length ? "Ninguna ausencia vigente o próxima con este filtro." : "Aún no hay ausencias."}
          columnas={["Persona", "Tipo", "Desde", "Hasta", "Días", "Nota", ""]}
          filas={visibles.map((n) => [
            nombre.get(n.colab_id) ?? `#${n.colab_id}`,
            n.desde <= hoy && hoy <= n.hasta ? <span className="flex items-center gap-2 whitespace-nowrap">{n.tipo}<Estado>En curso</Estado></span> : n.tipo,
            fechaCorta(n.desde), fechaCorta(n.hasta), diasEntre(n.desde, n.hasta), n.nota,
            editar ? <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => pedir(`¿Borrar ${n.tipo.toLowerCase()} de ${nombre.get(n.colab_id) ?? `#${n.colab_id}`}?`, "Borrar", () => hacer(async () => { await enviar("DELETE", `${base}/novedades/${n.id}`); lista.recargar(); }), `${fechaCorta(n.desde)} – ${fechaCorta(n.hasta)}. El cuadro volverá a contar a esta persona como disponible esos días.`)}>Borrar</Button> : null,
          ])}
        />
      </Seccion>
      {confirmacion}
    </Pagina>
  );
}
