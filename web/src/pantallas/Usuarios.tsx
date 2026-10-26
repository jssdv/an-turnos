import { useState } from "react";
import { Navigate, useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import { ErrorApi } from "../api/cliente";
import type { Area, UsuarioClinica } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { useSesion } from "../Sesion";
import { Casilla, Fila, Formulario, Pagina, useAccion } from "./comun";

/** Usuarios de la clínica y su permiso por área (solo el administrador). Un solo usuario edita cada área; el resto ve. */
export function Usuarios() {
  const { usuario } = useSesion();
  const area = useOutletContext<Area>();
  const lista = usar<UsuarioClinica[]>(usuario?.es_admin ? "/api/usuarios" : null);
  const areas = usar<Area[]>(usuario?.es_admin ? "/api/areas" : null);
  const { ocupado, aviso, hacer, avisar } = useAccion();
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
  const restablecer = (u: UsuarioClinica) => window.confirm(`¿Restablecer la contraseña de ${u.nombre}? Se cerrarán sus sesiones.`) && hacer(async () => {
    const r = await enviar<{ clave_temporal: string }>("POST", `/api/usuarios/${u.id}/clave`);
    setClave({ para: u.correo, valor: r.clave_temporal });
  });
  const desactivar = (u: UsuarioClinica) => window.confirm(`¿Desactivar a ${u.nombre}? No podrá ingresar.`) && hacer(async () => {
    await enviar("POST", `/api/usuarios/${u.id}/desactivar`);
    lista.recargar();
    avisar({ nivel: "ok", texto: "Usuario desactivado." });
  });
  const permisoDe = (u: UsuarioClinica, a: number) => u.permisos.find((p) => p.area_id === a)?.permiso ?? "";

  return (
    <Pagina titulo="Usuarios" sub="Quién ingresa a la clínica y qué puede hacer en cada área." error={lista.error ?? areas.error} aviso={aviso}>
      {clave && (
        <Aviso nivel="aviso" accion={<Boton onClick={() => setClave(null)}>Ya la copié</Boton>}>
          Contraseña temporal de {clave.para}: <strong>{clave.valor}</strong>. Se muestra una sola vez; la persona debe cambiarla al ingresar.
        </Aviso>
      )}
      {choque && (
        <Aviso nivel="aviso" accion={<Boton variante="primario" disabled={ocupado} onClick={() => reemplazar(choque.id, choque.area)}>Pasar al editor actual a «ver»</Boton>}>{choque.texto}</Aviso>
      )}
      <Tarjeta titulo="Nuevo usuario">
        <Formulario onSubmit={(x) => { x.preventDefault(); void crear(); }}>
          <Campo etiqueta="Correo" type="email" required value={f.correo} onChange={(x) => setF({ ...f, correo: x.target.value })} />
          <Campo etiqueta="Nombre" required maxLength={120} value={f.nombre} onChange={(x) => setF({ ...f, nombre: x.target.value })} />
          <Casilla etiqueta="Administra la clínica" checked={f.es_admin} onChange={(x) => setF({ ...f, es_admin: x.target.checked })} />
          <Fila><Boton type="submit" variante="primario" disabled={ocupado || !f.correo || !f.nombre.trim()}>Crear usuario</Boton></Fila>
        </Formulario>
      </Tarjeta>
      <Tarjeta titulo="Usuarios y permisos">
        <Tabla
          descripcion="Usuarios de la clínica"
          vacio="Aún no hay usuarios."
          columnas={["Usuario", "Estado", ...(areas.datos ?? []).map((a) => a.nombre), ""]}
          filas={(lista.datos ?? []).map((u) => [
            <>{u.nombre}<br />{u.correo}{u.es_admin && " · administra"}</>,
            !u.activo ? "Inactivo" : u.debe_cambiar ? "Debe cambiar la contraseña" : "Activo",
            ...(areas.datos ?? []).map((a) => (
              <Seleccion key={a.id} etiqueta={`Permiso de ${u.nombre} en ${a.nombre}`} value={permisoDe(u, a.id)} disabled={ocupado || !u.activo} onChange={(x) => fijar(u, a.id, x.target.value)}>
                <option value="">Sin acceso</option><option value="ver">Ver</option><option value="editar">Editar</option>
              </Seleccion>
            )),
            <Fila>
              <Boton variante="texto" disabled={ocupado} onClick={() => restablecer(u)}>Restablecer contraseña</Boton>
              {u.activo && u.id !== usuario.id && <Boton variante="texto" disabled={ocupado} onClick={() => desactivar(u)}>Desactivar</Boton>}
            </Fila>,
          ])}
        />
      </Tarjeta>
    </Pagina>
  );
}
