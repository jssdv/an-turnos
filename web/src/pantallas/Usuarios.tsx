import { useState } from "react";
import { Navigate, useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import { ErrorApi } from "../api/cliente";
import type { Area, UsuarioClinica } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { useSesion } from "../Sesion";
import { Plus, UserCheck01 } from "@untitledui/icons";
import { Fila, Formulario, Pagina, Pista, useAccion, useConfirmar, Seccion, Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Alert } from "@/components/application/alerts/alert";
import { Badge } from "@/components/base/badges/badges";

/** Usuarios de la clínica y su permiso por área (solo el administrador). Un solo usuario edita cada área; el resto ve. */
export function Usuarios() {
  const { usuario } = useSesion();
  const area = useOutletContext<Area>();
  const lista = usar<UsuarioClinica[]>(usuario?.es_admin ? "/api/usuarios" : null);
  const areas = usar<Area[]>(usuario?.es_admin ? "/api/areas" : null);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const [pedir, confirmacion] = useConfirmar();
  const [ventana, setVentana] = useState(false);
  const [f, setF] = useState({ correo: "", nombre: "", es_admin: false });
  const [clave, setClave] = useState<{ para: string; valor: string } | null>(null);
  const [choque, setChoque] = useState<{ id: number; area: number; texto: string } | null>(null);
  if (!usuario?.es_admin) return <Navigate to={`/areas/${area.id}/cuadro`} replace />;

  const fijar = (u: UsuarioClinica, a: number, permiso: string) => hacer(async () => {
    const ruta = `/api/usuarios/${u.id}/areas/${a}`;
    try {
      await enviar("PUT", ruta, { permiso: permiso || null });
      setChoque(null);
    } catch (x) {
      if (x instanceof ErrorApi && x.estado === 409 && permiso === "editar") { setChoque({ id: u.id, area: a, texto: x.message }); return; }
      throw x;
    }
    lista.recargar();
    return "Permiso actualizado.";
  });
  const reemplazar = (id: number, a: number) => hacer(async () => {
    await enviar("PUT", `/api/usuarios/${id}/areas/${a}?reemplazar=true`, { permiso: "editar" });
    setChoque(null);
    lista.recargar();
    return "Listo: quien editaba ahora solo ve.";
  });
  const crear = () => hacer(async () => {
    const r = await enviar<{ clave_temporal: string }>("POST", "/api/usuarios", f);
    setClave({ para: f.correo, valor: r.clave_temporal });
    setF({ correo: "", nombre: "", es_admin: false });
    lista.recargar();
  });
  const restablecer = (u: UsuarioClinica) => pedir(`¿Restablecer la contraseña de ${u.nombre}?`, "Restablecer contraseña", () => void hacer(async () => {
    const r = await enviar<{ clave_temporal: string }>("POST", `/api/usuarios/${u.id}/clave`);
    setClave({ para: u.correo, valor: r.clave_temporal });
  }), "Se cerrarán sus sesiones y recibirá una contraseña temporal.");
  const desactivar = (u: UsuarioClinica) => pedir(`¿Desactivar a ${u.nombre}?`, "Desactivar usuario", () => void hacer(async () => {
    await enviar("POST", `/api/usuarios/${u.id}/desactivar`);
    lista.recargar();
    avisar({ nivel: "ok", texto: "Usuario desactivado." });
  }), "No podrá ingresar hasta que se reactive.");
  const permisoDe = (u: UsuarioClinica, a: number) => u.permisos.find((p) => p.area_id === a)?.permiso ?? "";

  return (
    <Pagina titulo="Usuarios" icono={UserCheck01}
      acciones={<Pista texto="Crea un acceso con contraseña temporal; la persona la cambia al entrar."><Button color="primary" size="sm" iconLeading={Plus} onPress={() => setVentana(true)}>Nuevo usuario</Button></Pista>} sub="Quién ingresa a la clínica y qué puede hacer en cada área." ayuda={<>Cada persona puede tener, por área: <strong>Editar</strong> (genera y cambia el cuadro), <strong>Ver</strong> (solo consulta y exporta) o <strong>Sin acceso</strong>. Al crear un usuario se le asigna una contraseña temporal que deberá cambiar la primera vez que entre.</>} error={lista.error ?? areas.error} aviso={aviso}>
      {clave && (
        <Alert color="warning" action={<Button color="secondary" size="sm" onPress={() => setClave(null)}>Ya la copié</Button>}>
          Contraseña temporal de {clave.para}: <strong>{clave.valor}</strong>. Se muestra una sola vez; la persona debe cambiarla al ingresar.
        </Alert>
      )}
      {choque && (
        <Alert color="warning" action={<Button color="primary" size="sm" isDisabled={ocupado} onPress={() => reemplazar(choque.id, choque.area)}>Pasar al editor actual a «ver»</Button>}>{choque.texto}</Alert>
      )}
      <Ventana abierto={ventana} alCambiar={setVentana} titulo="Nuevo usuario" ancha descripcion="Recibe una contraseña temporal que cambia al entrar.">
          {aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>}
        <Formulario onSubmit={(x) => { x.preventDefault(); void crear().then((ok) => ok && setVentana(false)); }}>
          <Input value={String(f.correo)} label="Correo" type="email" isRequired onChange={(x) => setF({ ...f, correo: x })} />
          <Input value={String(f.nombre)} label="Nombre" isRequired maxLength={120} onChange={(x) => setF({ ...f, nombre: x })} />
          <Checkbox label="Administra la clínica" isSelected={f.es_admin} onChange={(x) => setF({ ...f, es_admin: x })} />
          <Fila><Button color="secondary" size="sm" onPress={() => setVentana(false)}>Cancelar</Button><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !f.correo || !f.nombre.trim()}>Crear usuario</Button></Fila>
        </Formulario>
      </Ventana>
      <Seccion titulo="Usuarios y permisos">
        <Tabla
          descripcion="Usuarios de la clínica"
          cargando={!lista.datos && !lista.error}
          vacio="Aún no hay usuarios."
          columnas={["Usuario", "Estado", ...(areas.datos ?? []).map((a) => a.nombre), ""]}
          filas={(lista.datos ?? []).map((u) => [
            <>{u.nombre}<br />{u.correo}{u.es_admin && " · administra"}</>,
            <Badge size="sm" color={!u.activo ? "gray" : u.debe_cambiar ? "warning" : "success"}>{!u.activo ? "Inactivo" : u.debe_cambiar ? "Debe cambiar la contraseña" : "Activo"}</Badge>,
            ...(areas.datos ?? []).map((a) => (
              u.es_admin ? <span key={a.id} className="text-sm text-tertiary">Edita todo</span> :
              <NativeSelect size="sm" key={a.id} label={`Permiso de ${u.nombre} en ${a.nombre}`} value={permisoDe(u, a.id)} disabled={ocupado || !u.activo} onChange={(x) => fijar(u, a.id, x.target.value)}>
                <option value="">Sin acceso</option><option value="ver">Ver</option><option value="editar">Editar</option>
              </NativeSelect>
            )),
            <Fila>
              <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => restablecer(u)}>Restablecer contraseña</Button>
              {u.activo && u.id !== usuario.id && <Button color="link-color" size="sm" isDisabled={ocupado} onPress={() => desactivar(u)}>Desactivar</Button>}
            </Fila>,
          ])}
        />
      </Seccion>
      {confirmacion}
    </Pagina>
  );
}
