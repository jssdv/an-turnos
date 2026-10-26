import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { aHHMM, aMinutos, enviar, usar } from "../api/catalogos";
import type { Area, Demanda, Puesto } from "../api/tipos";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Casilla, Fila, Formulario, Pagina, useAccion } from "./comun";

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
    <Pagina titulo="Puestos" sub="Dónde trabaja la gente y cuántas personas hacen falta." error={puestos.error ?? demandas.error} aviso={aviso}>
      <Tarjeta titulo="Puestos">
        <Tabla descripcion="Puestos del área" vacio="Aún no hay puestos." columnas={["N.º", "Nombre", "Estado", "Reglas", ""]}
          filas={(puestos.datos ?? []).map((q) => [q.numero, q.nombre, q.activo ? "Activo" : "Inactivo", (demandas.datos ?? []).filter((d) => d.puesto_id === q.id).length,
            editar ? <Boton variante="texto" onClick={() => elegir(q)}>{sel?.id === q.id ? "Editando" : "Editar"}</Boton> : null])} />
      </Tarjeta>
      {editar && (
        <Tarjeta titulo={sel ? `Puesto ${sel.numero}` : "Nuevo puesto"}>
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar(); }}>
            <Campo etiqueta="Número" type="number" min={1} max={99} required value={p.numero} onChange={(x) => setP({ ...p, numero: Number(x.target.value) })} />
            <Campo etiqueta="Nombre" required maxLength={60} value={p.nombre} onChange={(x) => setP({ ...p, nombre: x.target.value })} />
            <Campo etiqueta="Color (RRGGBB)" pattern="[0-9A-Fa-f]{6}" maxLength={6} value={p.color} onChange={(x) => setP({ ...p, color: x.target.value })} />
            <Casilla etiqueta="Activo" checked={p.activo} onChange={(x) => setP({ ...p, activo: x.target.checked })} />
            <Fila>
              <Boton type="submit" variante="primario" disabled={ocupado || !p.nombre.trim()}>{ocupado ? "Guardando…" : "Guardar"}</Boton>
              <Boton onClick={() => elegir(null)}>Nuevo puesto</Boton>
              {sel && <Boton variante="peligro" disabled={ocupado} onClick={borrar}>Eliminar</Boton>}
            </Fila>
          </Formulario>
        </Tarjeta>
      )}
      {editar && sel && (
        <Tarjeta titulo={`Demanda del puesto ${sel.numero}`} acciones={<Boton onClick={() => setReglas([...reglas, { puesto_id: sel.id, tipo_dia: "LS", inicio: 360, fin: 1080, personas: 1, obligatorio: true }])}>Agregar regla</Boton>}>
          {reglas.length === 0 && <p>Sin reglas: el puesto no pide gente.</p>}
          {reglas.map((r, i) => (
            <Formulario key={i} aria-label={`Regla ${i + 1}`} onSubmit={(x) => x.preventDefault()}>
              <Seleccion etiqueta="Días" value={r.tipo_dia} onChange={(x) => cambiarRegla(i, { tipo_dia: x.target.value as Demanda["tipo_dia"] })}>
                {Object.entries(TIPO_DIA).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
              </Seleccion>
              <Campo etiqueta="Desde" type="time" value={aHHMM(r.inicio)} onChange={(x) => cambiarRegla(i, { inicio: aMinutos(x.target.value) })} />
              <Campo etiqueta="Hasta" type="time" value={aHHMM(r.fin)} onChange={(x) => cambiarRegla(i, { fin: aMinutos(x.target.value) })} />
              <Campo etiqueta="Personas" type="number" min={0} max={50} value={r.personas} onChange={(x) => cambiarRegla(i, { personas: Number(x.target.value) })} />
              <Casilla etiqueta="Obligatorio" checked={r.obligatorio} onChange={(x) => cambiarRegla(i, { obligatorio: x.target.checked })} />
              <Boton variante="texto" onClick={() => setReglas(reglas.filter((_, j) => j !== i))}>Quitar</Boton>
            </Formulario>
          ))}
          <Fila><Boton variante="primario" disabled={ocupado} onClick={guardarReglas}>Guardar reglas</Boton></Fila>
        </Tarjeta>
      )}
    </Pagina>
  );
}
