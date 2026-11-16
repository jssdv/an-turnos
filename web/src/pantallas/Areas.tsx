import { useState } from "react";
import { Navigate, useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { useSesion } from "../Sesion";
import { Plus } from "@untitledui/icons";
import { Fila, Formulario, Pagina, Pista, useAccion, useConfirmar, Seccion, Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert } from "@/components/application/alerts/alert";
import { Badge } from "@/components/base/badges/badges";

interface Respaldo { nombre: string; fecha: string; archivos: number; bytes: number }
interface Respaldos { carpeta: string | null; respaldos: Respaldo[] }
const tamano = (b: number) => (b < 1048576 ? `${Math.max(1, Math.round(b / 1024))} KB` : `${(b / 1048576).toFixed(1).replace(".", ",")} MB`);
const cuando = (iso: string) => new Date(iso).toLocaleString("es-CO", { dateStyle: "medium", timeStyle: "short" });

const TIPO: Record<Area["tipo"], string> = { turnos: "Turnos", radiologia: "Radiología" };

/** Áreas (servicios) de la clínica, solo para el administrador: crear, renombrar y eliminar.
 * Tras renombrar o eliminar se recarga la app entera: el selector de área y el logo viven en el estado de Disposicion. */
export function Areas() {
  const { usuario } = useSesion();
  const area = useOutletContext<Area>();
  const lista = usar<Area[]>(usuario?.es_admin ? "/api/areas" : null);
  const respaldos = usar<Respaldos>(usuario?.es_admin ? "/api/respaldos" : null);
  const { ocupado, aviso, hacer } = useAccion();
  const [pedir, confirmacion] = useConfirmar();
  const [ventana, setVentana] = useState<null | { modo: "nueva" } | { modo: "nombre" | "eliminar"; area: Area }>(null);
  const [nombre, setNombre] = useState("");
  const [tipo, setTipo] = useState<Area["tipo"]>("turnos");
  if (!usuario?.es_admin) return <Navigate to={`/areas/${area.id}`} replace />;

  const abrir = (v: typeof ventana, inicial = "") => { setNombre(inicial); setTipo("turnos"); setVentana(v); };
  const crear = () => hacer(async () => {
    const r = await enviar<{ id: number }>("POST", "/api/areas", { nombre: nombre.trim(), tipo });
    location.assign(`/areas/${r.id}/inicio`);
  });
  const renombrar = (a: Area) => hacer(async () => {
    await enviar("PUT", `/api/areas/${a.id}`, { nombre: nombre.trim() });
    location.assign("/areas");
  });
  const eliminar = (a: Area) => hacer(async () => {
    await enviar("DELETE", `/api/areas/${a.id}`, { nombre });
    location.assign("/areas");
  });
  const respaldar = () => hacer(async () => {
    const r = await enviar<{ nombre: string }>("POST", "/api/respaldos");
    respaldos.recargar();
    return `Copia guardada en la carpeta ${r.nombre}.`;
  });
  /** Tras restaurar se recarga todo: los datos y las sesiones vienen de la copia. */
  const restaurar = (r: Respaldo) => pedir("¿Restaurar esta copia?", "Restaurar copia", () => void hacer(async () => {
    await enviar("POST", `/api/respaldos/${r.nombre}/restaurar`);
    location.reload();
  }), `Se reemplazan todos los datos de la clínica por los de la copia del ${cuando(r.fecha).replace(/\.$/, "")}. Antes se guarda una copia de lo actual. Después puede que tengas que volver a ingresar.`);
  const error = aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>;

  return (
    <Pagina titulo="Áreas"
      acciones={<Pista texto="Crea un servicio con su propio personal, turnos y cuadros."><Button color="primary" size="sm" iconLeading={Plus} onPress={() => abrir({ modo: "nueva" })}>Nueva área</Button></Pista>}
      sub="Los servicios de la clínica; cada uno con su personal, turnos y cuadros, independientes entre sí."
      ayuda={<>Cada área es de tipo <strong>Turnos</strong> (cuadro con solver, puestos y horas) o <strong>Radiología</strong> (cuadro mensual en Excel y asignación semanal). Los permisos por área se dan en «Usuarios».</>}
      error={lista.error}>
      <Ventana abierto={ventana?.modo === "nueva"} alCambiar={(v) => !v && setVentana(null)} titulo="Nueva área" descripcion="Arranca vacía: luego se cargan su personal y sus parámetros.">
        {error}
        <Formulario onSubmit={(x) => { x.preventDefault(); void crear(); }}>
          <Input value={nombre} label="Nombre" isRequired maxLength={80} onChange={setNombre} />
          <NativeSelect label="Tipo" value={tipo} onChange={(x) => setTipo(x.target.value as Area["tipo"])}>
            <option value="turnos">Turnos</option><option value="radiologia">Radiología</option>
          </NativeSelect>
          <Fila><Button color="secondary" size="sm" onPress={() => setVentana(null)}>Cancelar</Button><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !nombre.trim()}>Crear</Button></Fila>
        </Formulario>
      </Ventana>
      <Ventana abierto={ventana?.modo === "nombre"} alCambiar={(v) => !v && setVentana(null)} titulo="Cambiar nombre">
        {error}
        {ventana?.modo === "nombre" && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void renombrar(ventana.area); }}>
            <Input value={nombre} label="Nombre" isRequired maxLength={80} onChange={setNombre} />
            <Fila><Button color="secondary" size="sm" onPress={() => setVentana(null)}>Cancelar</Button><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !nombre.trim() || nombre.trim() === ventana.area.nombre}>Guardar</Button></Fila>
          </Formulario>
        )}
      </Ventana>
      <Ventana abierto={ventana?.modo === "eliminar"} alCambiar={(v) => !v && setVentana(null)} titulo={ventana?.modo === "eliminar" ? `Eliminar «${ventana.area.nombre}»` : ""}>
        {error}
        {ventana?.modo === "eliminar" && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void eliminar(ventana.area); }}>
            <div className="col-span-full"><Alert color="warning">Se borran su personal, turnos, cuadros, solicitudes y exportes. No se puede deshacer.</Alert></div>
            <div className="col-span-full"><Input value={nombre} label="Escribe el nombre del área para confirmar" isRequired onChange={setNombre} /></div>
            <Fila><Button color="secondary" size="sm" onPress={() => setVentana(null)}>Cancelar</Button><Button color="primary-destructive" size="sm" type="submit" isDisabled={ocupado || nombre !== ventana.area.nombre}>Eliminar área</Button></Fila>
          </Formulario>
        )}
      </Ventana>
      {confirmacion}
      <Seccion titulo="Áreas de la clínica">
        <Tabla
          descripcion="Áreas de la clínica"
          cargando={!lista.datos && !lista.error}
          vacio="Aún no hay áreas."
          columnas={["Área", "Tipo", ""]}
          filas={(lista.datos ?? []).map((a) => [
            a.nombre,
            <Badge size="sm" color={a.tipo === "radiologia" ? "blue" : "brand"}>{TIPO[a.tipo]}</Badge>,
            <Fila>
              <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => abrir({ modo: "nombre", area: a }, a.nombre)}>Cambiar nombre</Button>
              <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => abrir({ modo: "eliminar", area: a })}>Eliminar</Button>
            </Fila>,
          ])}
        />
      </Seccion>
      {respaldos.datos?.carpeta && (
        <Seccion titulo="Copias de respaldo" className="flex flex-col gap-3"
          acciones={<Button color="secondary" size="sm" isDisabled={ocupado} onPress={() => void respaldar()}>Respaldar ahora</Button>}>
          <p className="text-sm text-tertiary">
            La app guarda una copia al abrir y al cerrar (las últimas 10) en <span className="font-medium text-secondary break-all">{respaldos.datos.carpeta}</span>.
            «Restaurar» vuelve a los datos de una copia; antes guarda otra con lo actual.
          </p>
          {aviso && !ventana && <Alert color={aviso.nivel === "error" ? "error" : "success"}>{aviso.texto}</Alert>}
          <Tabla
            descripcion="Copias de respaldo"
            vacio="Aún no hay copias."
            columnas={["Fecha", "Carpeta", "Tamaño", ""]}
            filas={respaldos.datos.respaldos.map((r) => [cuando(r.fecha), r.nombre, `${tamano(r.bytes)} · ${r.archivos} archivos`,
              <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => restaurar(r)}>Restaurar</Button>])}
          />
        </Seccion>
      )}
    </Pagina>
  );
}
