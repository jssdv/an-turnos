import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { aHHMM, aMinutos, enviar, usar } from "../api/catalogos";
import type { Area, Demanda, Puesto } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Fila, Formulario, Pagina, useAccion } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Checkbox } from "@/components/base/checkbox/checkbox";

const TIPO_DIA = { LS: "Lunes a sábado", DF: "Domingo y festivo" } as const;

/** Puestos de trabajo y sus reglas de demanda (cuántas personas, en qué horas, obligatorio o deseable). */
export function Puestos() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const puestos = usar<Puesto[]>(`${base}/puestos`);
  const demandas = usar<Demanda[]>(`${base}/demandas`);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const [sel, setSel] = useState<Puesto | null>(null);
  const [p, setP] = useState({ numero: 1, nombre: "", color: "DDEBF7", activo: true });
  const [reglas, setReglas] = useState<Demanda[]>([]);
  const editar = area.permiso === "editar";

  useEffect(() => { if (sel && demandas.datos) setReglas(demandas.datos.filter((d) => d.puesto_id === sel.id)); }, [sel, demandas.datos]);
  const elegir = (q: Puesto | null) => {
    setSel(q);
    setP(q ? { numero: q.numero, nombre: q.nombre, color: q.color, activo: q.activo } : { numero: Math.max(0, ...(puestos.datos ?? []).map((x) => x.numero)) + 1, nombre: "", color: "DDEBF7", activo: true });
    if (!q) setReglas([]);
  };
  const cambiarRegla = (i: number, d: Partial<Demanda>) => setReglas(reglas.map((r, j) => (j === i ? { ...r, ...d } : r)));

  const guardar = () => hacer(async () => {
    const r = sel ? await enviar<{ id: number }>("PUT", `${base}/puestos/${sel.id}`, p) : await enviar<{ id: number }>("POST", `${base}/puestos`, p);
    puestos.recargar();
    setSel({ id: r.id, ...p });
    return "Puesto guardado. Regenera el cuadro para que lo tome en cuenta.";
  });
  const guardarReglas = () => hacer(async () => {
    const r = await enviar<{ avisos: string[] }>("PUT", `${base}/puestos/${sel!.id}/demandas`, reglas.map(({ tipo_dia, inicio, fin, personas, obligatorio }) => ({ tipo_dia, inicio, fin, personas, obligatorio })));
    demandas.recargar();
    avisar({ nivel: r.avisos.length ? "aviso" : "ok", texto: `Reglas de demanda guardadas. ${r.avisos.join(" ")} Regenera el cuadro para que las tome en cuenta.`.replace("  ", " ") });
  });
  const borrar = () => window.confirm(`¿Eliminar el puesto «${sel!.nombre}»?`) && hacer(async () => {
    const r = await enviar<{ resultado: string }>("DELETE", `${base}/puestos/${sel!.id}`);
    elegir(null); puestos.recargar(); demandas.recargar();
    avisar({ nivel: r.resultado === "borrado" ? "ok" : "aviso", texto: r.resultado === "borrado" ? "Puesto eliminado." : "Tiene historial o es el único puesto de alguien, así que quedó inactivo." });
  });

  return (
    <Pagina titulo="Puestos" sub="Dónde trabaja la gente y cuántas personas hacen falta en cada uno." ayuda={<>Cada puesto tiene <strong>reglas de cobertura</strong>: cuántas personas necesita, qué días y en qué turno. El sistema usa estas reglas al generar el cuadro y te avisa si un puesto queda sin cubrir.</>} error={puestos.error ?? demandas.error} aviso={aviso}>
      <Tarjeta titulo="Puestos">
        <Tabla descripcion="Puestos del área" cargando={!puestos.datos && !puestos.error} vacio="Aún no hay puestos." columnas={["N.º", "Nombre", "Estado", "Reglas", ""]}
          filas={(puestos.datos ?? []).map((q) => [q.numero, q.nombre, q.activo ? "Activo" : "Inactivo", (demandas.datos ?? []).filter((d) => d.puesto_id === q.id).length,
            editar ? <Button color="link-color" size="sm" onPress={() => elegir(q)}>{sel?.id === q.id ? "Editando" : "Editar"}</Button> : null])} />
      </Tarjeta>
      {editar && (
        <Tarjeta titulo={sel ? `Puesto ${sel.numero}` : "Nuevo puesto"}>
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
        </Tarjeta>
      )}
      {editar && sel && (
        <Tarjeta titulo={`Demanda del puesto ${sel.numero}`} acciones={<Button color="secondary" size="sm" onPress={() => setReglas([...reglas, { puesto_id: sel.id, tipo_dia: "LS", inicio: 360, fin: 1080, personas: 1, obligatorio: true }])}>Agregar regla</Button>}>
          {reglas.length === 0 && <p>Sin reglas: el puesto no pide gente.</p>}
          {reglas.map((r, i) => (
            <Formulario key={i} aria-label={`Regla ${i + 1}`} onSubmit={(x) => x.preventDefault()}>
              <NativeSelect size="sm" label="Días" value={r.tipo_dia} onChange={(x) => cambiarRegla(i, { tipo_dia: x.target.value as Demanda["tipo_dia"] })}>
                {Object.entries(TIPO_DIA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </NativeSelect>
              <Input value={String(aHHMM(r.inicio))} label="Desde" type="time" onChange={(x) => cambiarRegla(i, { inicio: aMinutos(x) })} />
              <Input value={String(aHHMM(r.fin))} label="Hasta" type="time" onChange={(x) => cambiarRegla(i, { fin: aMinutos(x) })} />
              <Input value={String(r.personas)} label="Personas" type="number" onChange={(x) => cambiarRegla(i, { personas: Number(x) })} />
              <Checkbox label="Obligatorio" isSelected={r.obligatorio} onChange={(x) => cambiarRegla(i, { obligatorio: x })} />
              <Button color="link-color" size="sm" onPress={() => setReglas(reglas.filter((_, j) => j !== i))}>Quitar</Button>
            </Formulario>
          ))}
          <Fila><Button color="primary" size="sm" isDisabled={ocupado} onPress={guardarReglas}>Guardar reglas</Button></Fila>
        </Tarjeta>
      )}
    </Pagina>
  );
}
