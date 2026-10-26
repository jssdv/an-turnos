import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { aHHMM, aMinutos, enviar, usar } from "../api/catalogos";
import type { Area, Demanda, Puesto, Requerimiento } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Fila, Formulario, Pagina, useAccion, Seccion } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Badge } from "@/components/base/badges/badges";
import { Alert } from "@/components/application/alerts/alert";

const TIPO_DIA = { LS: "Lunes a sábado", DF: "Domingo y festivo" } as const;

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom", "Festivo"];
const FRANJAS = [["M", "Mañana"], ["T", "Tarde"], ["N", "Noche"]] as const;

/** Área sin puestos: personas pedidas por franja (M/T/N) y día de la semana. */
function MatrizRequerimiento({ base, editar }: { base: string; editar: boolean }) {
  const req = usar<Requerimiento[]>(`${base}/requerimiento`);
  const { ocupado, aviso, hacer } = useAccion();
  const [n, setN] = useState<Record<string, number>>({});
  useEffect(() => { if (req.datos) setN(Object.fromEntries(req.datos.map((r) => [`${r.dia}${r.franja}`, r.personas]))); }, [req.datos]);
  const guardar = () => hacer(async () => {
    const filas = DIAS.flatMap((_, dia) => FRANJAS.map(([franja]) => ({ dia, franja, personas: n[`${dia}${franja}`] ?? 0, obligatorio: true }))).filter((f) => f.personas > 0);
    await enviar("PUT", `${base}/requerimiento`, filas);
    req.recargar();
    return "Requerimiento guardado. Regenera el cuadro para que lo tome en cuenta.";
  });
  return (
    <Seccion titulo="Personas por jornada">
      {aviso && <Alert color={aviso.nivel === "ok" ? "success" : "error"}>{aviso.texto}</Alert>}
      <p className="text-sm text-tertiary">Cuántas personas hacen falta en cada franja, según el día de la semana. El festivo reemplaza al día de la semana.</p>
      <div className="overflow-x-auto"><table className="text-sm"><thead><tr><th className="p-1 text-left">Franja</th>{DIAS.map((d) => <th key={d} className="p-1">{d}</th>)}</tr></thead>
        <tbody>{FRANJAS.map(([f, nombre]) => (
          <tr key={f}><th className="p-1 text-left font-medium">{nombre}</th>
            {DIAS.map((d, dia) => <td key={d} className="p-1"><Input aria-label={`${nombre} ${d}`} type="number" size="sm" className="w-20" isDisabled={!editar} value={String(n[`${dia}${f}`] ?? 0)}
              onChange={(x) => setN({ ...n, [`${dia}${f}`]: Math.max(0, Number(x)) })} /></td>)}
          </tr>))}</tbody></table></div>
      {editar && <Fila><Button color="primary" size="sm" isDisabled={ocupado} onPress={guardar}>Guardar requerimiento</Button></Fila>}
    </Seccion>
  );
}

/** Puestos de trabajo y sus reglas de demanda (cuántas personas, en qué horas, obligatorio o deseable). */
export function Puestos() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const puestos = usar<Puesto[]>(`${base}/puestos`);
  const demandas = usar<Demanda[]>(`${base}/demandas`);
  const parametros = usar<Record<string, string>>(`${base}/parametros`);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const usaPuestos = parametros.datos?.usa_puestos !== "0";
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
    <Pagina titulo="Requerimiento" sub="Cuántas personas hacen falta y, si el servicio usa puestos, dónde trabajan." ayuda={<>Cada puesto tiene <strong>reglas de cobertura</strong>: cuántas personas necesita, qué días y en qué turno. El sistema usa estas reglas al generar el cuadro y te avisa si un puesto queda sin cubrir.</>} error={puestos.error ?? demandas.error ?? parametros.error} aviso={aviso}>
      {editar && <Seccion titulo="Cómo se define la necesidad"><Checkbox label="Este servicio trabaja por puestos" hint="Apagado: solo se pide un número de personas por jornada y día de la semana."
        isSelected={usaPuestos} isDisabled={ocupado || !parametros.datos} onChange={cambiarModo} /></Seccion>}
      {!usaPuestos && <MatrizRequerimiento base={base} editar={editar} />}
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
      {editar && sel && (
        <Seccion titulo={`Demanda del puesto ${sel.numero}`} acciones={<Button color="secondary" size="sm" onPress={() => setReglas([...reglas, { puesto_id: sel.id, tipo_dia: "LS", inicio: 360, fin: 1080, personas: 1, obligatorio: true }])}>Agregar regla</Button>}>
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
        </Seccion>
      )}
      </>}
    </Pagina>
  );
}
