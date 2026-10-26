import { useMemo, useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, Novedad } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Fila, Formulario, Pagina, useAccion } from "./comun";
import { fechaCorta } from "./fechas";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";

const TIPOS = ["Vacaciones", "Incapacidad", "Licencia", "Libre solicitado"];

/** Vacaciones, incapacidades y licencias: la persona no se programa esos días. */
export function Novedades() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const lista = usar<Novedad[]>(`${base}/novedades`);
  const personas = usar<Colaborador[]>(`${base}/colaboradores`);
  const { ocupado, aviso, hacer } = useAccion();
  const [f, setF] = useState({ colab_id: "", tipo: TIPOS[0], desde: "", hasta: "", nota: "" });
  const nombre = useMemo(() => new Map((personas.datos ?? []).map((p) => [p.id, p.nombre])), [personas.datos]);
  const editar = area.permiso === "editar";

  const guardar = () => hacer(async () => {
    await enviar("POST", `${base}/novedades`, { ...f, colab_id: Number(f.colab_id) });
    setF({ ...f, nota: "" });
    lista.recargar();
    return "Novedad guardada. Regenera el cuadro (una semana o respetando tus cambios) para aplicarla.";
  });

  return (
    <Pagina titulo="Ausencias" sub="Vacaciones, incapacidades, licencias y días libres concedidos." ayuda={<>Registra aquí cuándo alguien <strong>no puede trabajar</strong>. Al generar el cuadro, el sistema no le asigna turnos esos días. Si el cuadro ya existe, las alertas te avisan de los turnos que chocan con una ausencia.</>} error={lista.error ?? personas.error} aviso={aviso}>
      {editar && (
        <Tarjeta titulo="Nueva ausencia">
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar(); }}>
            <NativeSelect size="sm" label="Persona" required value={f.colab_id} onChange={(x) => setF({ ...f, colab_id: x.target.value })}>
              <option value="">Elige…</option>
              {(personas.datos ?? []).filter((p) => p.activo).map((p) => <option key={p.id} value={p.id}>{p.nombre}</option>)}
            </NativeSelect>
            <NativeSelect size="sm" label="Tipo" value={f.tipo} onChange={(x) => setF({ ...f, tipo: x.target.value })}>
              {TIPOS.map((t) => <option key={t}>{t}</option>)}
            </NativeSelect>
            <Input value={String(f.desde)} label="Desde" type="date" isRequired onChange={(x) => setF({ ...f, desde: x })} />
            <Input value={String(f.hasta)} label="Hasta" type="date" isRequired onChange={(x) => setF({ ...f, hasta: x })} />
            <Input value={String(f.nota)} label="Nota" maxLength={300} onChange={(x) => setF({ ...f, nota: x })} />
            <Fila><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !f.colab_id || !f.desde || !f.hasta}>{ocupado ? "Guardando…" : "Guardar"}</Button></Fila>
          </Formulario>
        </Tarjeta>
      )}
      <Tarjeta titulo="Ausencias registradas">
        <Tabla
          descripcion="Ausencias del área"
          cargando={!lista.datos && !lista.error}
          vacio="Aún no hay novedades."
          columnas={["Persona", "Tipo", "Desde", "Hasta", "Nota", ""]}
          filas={(lista.datos ?? []).map((n) => [
            nombre.get(n.colab_id) ?? `#${n.colab_id}`, n.tipo, fechaCorta(n.desde), fechaCorta(n.hasta), n.nota,
            editar ? <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => hacer(async () => { await enviar("DELETE", `${base}/novedades/${n.id}`); lista.recargar(); })}>Borrar</Button> : null,
          ])}
        />
      </Tarjeta>
    </Pagina>
  );
}
