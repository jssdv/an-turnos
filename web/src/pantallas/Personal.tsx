import { useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, Puesto, Turno } from "../api/tipos";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Casilla, Fila, Formulario, Pagina, useAccion } from "./comun";
import f from "./Formulario.module.css";

const TIPOS = ["regular", "restringido", "estudiante", "refuerzo"];
const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"];
interface Borrador { nombre: string; tipo: string; horas_sem: number; pct: number; permitidos: string[]; puestos: number[]; estudio: string[]; activo: boolean }
const vacio = (turnos: Turno[], puestos: Puesto[]): Borrador => ({ nombre: "", tipo: "regular", horas_sem: 42, pct: 100, permitidos: turnos.map((t) => t.codigo), puestos: puestos.map((p) => p.id), estudio: [], activo: true });
const alternar = <T,>(l: T[], x: T) => (l.includes(x) ? l.filter((y) => y !== x) : [...l, x]);

/** Personal del área: tipo, horas, turnos que puede hacer, puestos que puede ocupar y bloques de estudio. */
export function Personal() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const lista = usar<Colaborador[]>(`${base}/colaboradores`);
  const turnosL = usar<Turno[]>(`${base}/turnos`);
  const puestosL = usar<Puesto[]>(`${base}/puestos`);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const turnos = (turnosL.datos ?? []).filter((t) => t.activo), puestos = (puestosL.datos ?? []).filter((p) => p.activo);
  const [sel, setSel] = useState<number | null>(null);
  const [b, setB] = useState<Borrador | null>(null);
  const [verInactivos, setVerInactivos] = useState(false);
  const editar = area.permiso === "editar";
  const actual = b ?? vacio(turnos, puestos);

  const elegir = (p: Colaborador) => {
    setSel(p.id);
    setB({ nombre: p.nombre, tipo: p.tipo, horas_sem: p.horas_sem, pct: Math.round(p.pct * 100), permitidos: p.permitidos ?? turnos.map((t) => t.codigo),
      puestos: p.puestos_permitidos ?? puestos.map((q) => q.id), estudio: p.estudio.map(([d, t]) => `${d}${t}`), activo: p.activo });
  };
  const nuevo = () => { setSel(null); setB(vacio(turnos, puestos)); };
  const set = (p: Partial<Borrador>) => setB({ ...actual, ...p });

  const guardar = () => hacer(async () => {
    const todosT = actual.permitidos.length === turnos.length, todosP = actual.puestos.length === puestos.length;
    const cuerpo = { nombre: actual.nombre, tipo: actual.tipo, horas_sem: actual.horas_sem, pct: actual.pct / 100, activo: actual.activo,
      permitidos: todosT ? null : actual.permitidos, puestos_permitidos: todosP ? null : actual.puestos,
      estudio: actual.estudio.map((x) => [Number(x[0]), x[1]]) };
    const r = sel ? await enviar<{ id: number }>("PUT", `${base}/colaboradores/${sel}`, cuerpo) : await enviar<{ id: number }>("POST", `${base}/colaboradores`, cuerpo);
    setSel(r.id);
    lista.recargar();
    return `«${actual.nombre.trim()}» guardado. Regenera el cuadro para que lo tome en cuenta.`;
  });
  const borrar = () => window.confirm(`¿Eliminar a «${actual.nombre}»?`) && hacer(async () => {
    const r = await enviar<{ resultado: string }>("DELETE", `${base}/colaboradores/${sel}`);
    nuevo(); lista.recargar();
    avisar({ nivel: r.resultado === "borrado" ? "ok" : "aviso", texto: r.resultado === "borrado" ? "Colaborador eliminado." : "Tiene cuadros o novedades en su historial, así que quedó inactivo en lugar de borrarse." });
  });

  return (
    <Pagina titulo="Personal" sub="Las personas que entran al cuadro y qué turnos y puestos pueden cubrir." ayuda={<><strong>Horas por semana</strong> es lo contratado (42 h por defecto). <strong>Dedicación</strong> es el porcentaje de jornada: 100 % es tiempo completo, 50 % media jornada. Marca solo los turnos y puestos que la persona sabe hacer; el sistema no le asignará otros. Quien deja el área se marca como inactiva en lugar de borrarse, para conservar su historial.</>} error={lista.error ?? turnosL.error ?? puestosL.error} aviso={aviso}>
      <Tarjeta titulo="Colaboradores" acciones={<Casilla etiqueta="Mostrar inactivos" checked={verInactivos} onChange={(x) => setVerInactivos(x.target.checked)} />}>
        <Tabla
          descripcion="Personal del área"
          cargando={!lista.datos && !lista.error}
          vacio="Aún no hay personal. Agrega a la primera persona abajo."
          columnas={["Nombre", "Tipo", "Horas/sem", "Dedicación", "Estado", ""]}
          filas={(lista.datos ?? []).filter((p) => p.activo || verInactivos).map((p) => [
            p.nombre, p.tipo, p.horas_sem, `${Math.round(p.pct * 100)} %`, p.activo ? "Activo" : "Inactivo",
            editar ? <Boton variante="texto" onClick={() => elegir(p)} aria-pressed={sel === p.id}>{sel === p.id ? "Editando" : "Editar"}</Boton> : null,
          ])}
        />
      </Tarjeta>
      {editar && (
        <Tarjeta titulo={sel ? "Editar persona" : "Nueva persona"}>
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar(); }}>
            <Campo etiqueta="Nombre" required maxLength={120} value={actual.nombre} onChange={(x) => set({ nombre: x.target.value })} />
            <Seleccion etiqueta="Tipo" value={actual.tipo} onChange={(x) => set({ tipo: x.target.value })}>{TIPOS.map((t) => <option key={t}>{t}</option>)}</Seleccion>
            <Campo etiqueta="Horas por semana" type="number" min={1} max={84} step="0.5" value={actual.horas_sem} onChange={(x) => set({ horas_sem: Number(x.target.value) })} />
            <Campo etiqueta="Dedicación (%)" type="number" min={1} max={100} value={actual.pct} onChange={(x) => set({ pct: Number(x.target.value) })} />
            <fieldset className={f.grupo}><legend>Turnos que puede hacer</legend>
              {turnos.map((t) => <Casilla key={t.codigo} etiqueta={`${t.codigo} · ${t.nombre}`} checked={actual.permitidos.includes(t.codigo)} onChange={() => set({ permitidos: alternar(actual.permitidos, t.codigo) })} />)}
            </fieldset>
            <fieldset className={f.grupo}><legend>Puestos que puede ocupar</legend>
              {puestos.map((p) => <Casilla key={p.id} etiqueta={`${p.numero} · ${p.nombre}`} checked={actual.puestos.includes(p.id)} onChange={() => set({ puestos: alternar(actual.puestos, p.id) })} />)}
            </fieldset>
            <fieldset className={f.grupo}><legend>Bloques de estudio (no disponible)</legend>
              {(["M", "T"] as const).map((fr) => DIAS.map((d, i) => (
                <Casilla key={`${i}${fr}`} etiqueta={`${d} ${fr === "M" ? "mañana" : "tarde"}`} checked={actual.estudio.includes(`${i}${fr}`)} onChange={() => set({ estudio: alternar(actual.estudio, `${i}${fr}`) })} />
              )))}
            </fieldset>
            <Casilla etiqueta="Activo" checked={actual.activo} onChange={(x) => set({ activo: x.target.checked })} />
            <Fila>
              <Boton type="submit" variante="primario" disabled={ocupado || !actual.nombre.trim() || !actual.permitidos.length || !actual.puestos.length}>{ocupado ? "Guardando…" : "Guardar"}</Boton>
              <Boton onClick={nuevo}>Nueva persona</Boton>
              {sel && <Boton variante="peligro" disabled={ocupado} onClick={borrar}>Eliminar</Boton>}
            </Fila>
          </Formulario>
        </Tarjeta>
      )}
    </Pagina>
  );
}
