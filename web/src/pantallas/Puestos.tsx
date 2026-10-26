import { useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import { SeccionTurnos } from "./SeccionTurnos";
import { MatrizRequerimiento } from "./MatrizRequerimiento";
import type { Area, Demanda, Puesto, Turno } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Fila, Formulario, Pagina, useAccion, Seccion } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Badge } from "@/components/base/badges/badges";

/** Turnos, modo de trabajo (con o sin puestos) y necesidad por turno y día: del área o de cada puesto. */
export function Puestos() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const puestos = usar<Puesto[]>(`${base}/puestos`);
  const demandas = usar<Demanda[]>(`${base}/demandas`);
  const parametros = usar<Record<string, string>>(`${base}/parametros`);
  const turnos = usar<Turno[]>(`${base}/turnos`);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const usaPuestos = parametros.datos?.usa_puestos !== "0";
  const [sel, setSel] = useState<Puesto | null>(null);
  const [p, setP] = useState({ numero: 1, nombre: "", color: "DDEBF7", activo: true });
  const editar = area.permiso === "editar";

  const elegir = (q: Puesto | null) => {
    setSel(q);
    setP(q ? { numero: q.numero, nombre: q.nombre, color: q.color, activo: q.activo } : { numero: Math.max(0, ...(puestos.datos ?? []).map((x) => x.numero)) + 1, nombre: "", color: "DDEBF7", activo: true });
  };

  const cambiarModo = (v: boolean) => hacer(async () => {
    await enviar("PUT", `${base}/parametros`, { usa_puestos: v ? 1 : 0 });
    parametros.recargar();
    return "Modo guardado. Regenera el cuadro para que lo tome en cuenta.";
  });
  const guardar = () => hacer(async () => {
    const r = sel ? await enviar<{ id: number }>("PUT", `${base}/puestos/${sel.id}`, p) : await enviar<{ id: number }>("POST", `${base}/puestos`, p);
    puestos.recargar();
    setSel({ id: r.id, ...p });
    return "Puesto guardado. Regenera el cuadro para que lo tome en cuenta.";
  });
  const borrar = () => window.confirm(`¿Eliminar el puesto «${sel!.nombre}»?`) && hacer(async () => {
    const r = await enviar<{ resultado: string }>("DELETE", `${base}/puestos/${sel!.id}`);
    elegir(null); puestos.recargar(); demandas.recargar();
    avisar({ nivel: r.resultado === "borrado" ? "ok" : "aviso", texto: r.resultado === "borrado" ? "Puesto eliminado." : "Tiene historial o es el único puesto de alguien, así que quedó inactivo." });
  });

  return (
    <Pagina titulo="Requerimiento" sub="Los turnos del área, si el servicio usa puestos y cuántas personas hacen falta." ayuda={<>Primero define los <strong>turnos</strong> (sus horarios son la base). Luego elige si trabajan por puestos. Con puestos, cada uno tiene su propia <strong>necesidad por turno y día</strong>; sin puestos, la necesidad es la del área. El sistema usa estas reglas al generar el cuadro y te avisa si un puesto queda sin cubrir.</>} error={puestos.error ?? demandas.error ?? parametros.error ?? turnos.error} aviso={aviso}>
      <SeccionTurnos base={base} editar={editar} turnos={turnos} />
      {editar && <Seccion titulo="Cómo se define la necesidad"><Checkbox label="Este servicio trabaja por puestos" hint="Apagado: solo se pide un número de personas por jornada y día de la semana."
        isSelected={usaPuestos} isDisabled={ocupado || !parametros.datos} onChange={cambiarModo} /></Seccion>}
      {!usaPuestos && <MatrizRequerimiento ruta={`${base}/requerimiento`} titulo="Personas por turno" editar={editar} turnos={turnos.datos ?? []} />}
      {usaPuestos && <>
      <Seccion titulo="Puestos">
        <Tabla descripcion="Puestos del área" cargando={!puestos.datos && !puestos.error} vacio="Aún no hay puestos." columnas={["N.º", "Nombre", "Estado", "Reglas", ""]}
          filas={(puestos.datos ?? []).map((q) => [q.numero, q.nombre, <Badge size="sm" color={q.activo ? "success" : "gray"}>{q.activo ? "Activo" : "Inactivo"}</Badge>, (demandas.datos ?? []).filter((d) => d.puesto_id === q.id).length,
            editar ? <Button color="link-color" size="sm" onPress={() => elegir(q)}>{sel?.id === q.id ? "Editando" : "Editar"}</Button> : null])} />
      </Seccion>
      {editar && (
        <Seccion titulo={sel ? `Puesto ${sel.numero}` : "Nuevo puesto"}>
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar(); }}>
            <Input value={String(p.numero)} label="Número" type="number" isRequired onChange={(x) => setP({ ...p, numero: Number(x) })} />
            <Input value={String(p.nombre)} label="Nombre" isRequired maxLength={60} onChange={(x) => setP({ ...p, nombre: x })} />
            <Input value={String(`#${p.color}`)} label="Color en el cuadro" type="color" onChange={(x) => setP({ ...p, color: x.slice(1).toUpperCase() })} />
            <Checkbox label="Activo" isSelected={p.activo} onChange={(x) => setP({ ...p, activo: x })} />
            <Fila>
              <Button color="primary" size="sm" type="submit" isDisabled={ocupado || !p.nombre.trim()}>{ocupado ? "Guardando…" : "Guardar"}</Button>
              <Button color="secondary" size="sm" onPress={() => elegir(null)}>Nuevo puesto</Button>
              {sel && <Button color="primary-destructive" size="sm" isDisabled={ocupado} onPress={borrar}>Eliminar</Button>}
            </Fila>
          </Formulario>
        </Seccion>
      )}
      {sel && <MatrizRequerimiento key={sel.id} ruta={`${base}/puestos/${sel.id}/requerimiento`} titulo={`Necesidad del puesto ${sel.numero}`} editar={editar} turnos={turnos.datos ?? []} conDeseable />}
      </>}
    </Pagina>
  );
}
