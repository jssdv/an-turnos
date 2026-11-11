import { useState } from "react";
import { Navigate, useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { useSesion } from "../Sesion";
import { Building02, Plus } from "@untitledui/icons";
import { Fila, Formulario, Pagina, Pista, useAccion, Seccion, Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert } from "@/components/application/alerts/alert";
import { Badge } from "@/components/base/badges/badges";

const TIPO: Record<Area["tipo"], string> = { turnos: "Turnos", radiologia: "Radiología" };

/** Áreas (servicios) de la clínica, solo para el administrador: crear, renombrar y eliminar.
 * Tras renombrar o eliminar se recarga la app entera: el selector de área y el logo viven en el estado de Disposicion. */
export function Areas() {
  const { usuario } = useSesion();
  const area = useOutletContext<Area>();
  const lista = usar<Area[]>(usuario?.es_admin ? "/api/areas" : null);
  const { ocupado, aviso, hacer } = useAccion();
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
  const error = aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>;

  return (
    <Pagina titulo="Áreas" icono={Building02}
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
    </Pagina>
  );
}
