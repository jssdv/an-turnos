import { useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Colaborador, Puesto, Turno } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { ClipboardPlus, Plus, SearchLg, Trash01 } from "@untitledui/icons";
import { leerLista } from "./pegar";
import { Estado, Fila, Formulario, Pagina, Pista, sinTildes, useAccion, useConfirmar, Seccion, Grupo, Ventana } from "./comun";
import { Alert } from "@/components/application/alerts/alert";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Checkbox } from "@/components/base/checkbox/checkbox";

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
  const [pedir, confirmacion] = useConfirmar();
  const [ventana, setVentana] = useState(false);
  const turnos = (turnosL.datos ?? []).filter((t) => t.activo), puestos = (puestosL.datos ?? []).filter((p) => p.activo);
  const [sel, setSel] = useState<number | null>(null);
  const [b, setB] = useState<Borrador | null>(null);
  const [verInactivos, setVerInactivos] = useState(false);
  const [buscar, setBuscar] = useState("");
  const [pegado, setPegado] = useState<string | null>(null);  // null = ventana «Pegar lista» cerrada
  const lectura = pegado === null ? null : leerLista(pegado, (lista.datos ?? []).map((p) => p.nombre));
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
  const agregarLista = () => hacer(async () => {
    if (!lectura) return;
    let n = 0;
    try {
      for (const p of lectura.personas) { await enviar("POST", `${base}/colaboradores`, { ...p, tipo: "regular" }); n++; }
    } finally {
      lista.recargar();
    }
    setPegado(null);
    return `${n} ${n === 1 ? "persona agregada" : "personas agregadas"}. Revisa sus turnos y puestos con «Editar» y regenera el cuadro.`;
  });
  const borrar = () => pedir(`¿Eliminar a «${actual.nombre}»?`, "Eliminar persona", () => { setVentana(false); void hacer(async () => {
    const r = await enviar<{ resultado: string }>("DELETE", `${base}/colaboradores/${sel}`);
    nuevo(); lista.recargar();
    avisar({ nivel: r.resultado === "borrado" ? "ok" : "aviso", texto: r.resultado === "borrado" ? "Colaborador eliminado." : "Tiene cuadros o novedades en su historial, así que quedó inactivo en lugar de borrarse." });
  }); }, "Si tiene cuadros o novedades en su historial, quedará inactiva en lugar de borrarse.");

  return (
    <Pagina titulo="Personal"
      acciones={editar && <><Pista texto="Pega filas copiadas de Excel: nombre, horas por semana y dedicación."><Button color="secondary" size="sm" iconLeading={ClipboardPlus} onPress={() => setPegado("")}>Pegar lista</Button></Pista><Pista texto="Agrega a alguien al área: horas, turnos y puestos que puede cubrir."><Button color="primary" size="sm" iconLeading={Plus} onPress={() => { nuevo(); setVentana(true); }}>Agregar persona</Button></Pista></>} sub="Las personas que entran al cuadro y qué turnos y puestos pueden cubrir." ayuda={<><strong>Horas por semana</strong> es lo contratado (42 h por defecto). <strong>Dedicación</strong> es el porcentaje de jornada: 100 % es tiempo completo, 50 % media jornada. Marca solo los turnos y puestos que la persona sabe hacer; el sistema no le asignará otros. Quien deja el área se marca como inactiva en lugar de borrarse, para conservar su historial.</>} error={lista.error ?? turnosL.error ?? puestosL.error} aviso={aviso}>
      <Seccion titulo="Colaboradores" acciones={<div className="flex items-center gap-4"><Input className="w-56" size="sm" type="search" icon={SearchLg} placeholder="Buscar persona" value={buscar} onChange={setBuscar} /><Checkbox label="Mostrar inactivos" isSelected={verInactivos} onChange={(x) => setVerInactivos(x)} /></div>}>
        <Tabla
          descripcion="Personal del área"
          cargando={!lista.datos && !lista.error}
          vacio={buscar ? `Nadie coincide con «${buscar}».` : "Aún no hay personal. Agrega a la primera persona con «Agregar persona»."}
          columnas={["Nombre", "Tipo", "Horas/sem", "Dedicación", "Estado", ""]}
          filas={(lista.datos ?? []).filter((p) => (p.activo || verInactivos) && sinTildes(p.nombre).includes(sinTildes(buscar.trim()))).map((p) => [
            p.nombre, p.tipo, p.horas_sem, `${Math.round(p.pct * 100)} %`, <Estado tono={p.activo ? "ok" : "neutro"}>{p.activo ? "Activo" : "Inactivo"}</Estado>,
            editar ? <Button color="link-color" size="sm" onPress={() => { elegir(p); setVentana(true); }} >Editar</Button> : null,
          ])}
        />
      </Seccion>
      {editar && (
        <Ventana abierto={ventana} alCambiar={setVentana} titulo={sel ? "Editar persona" : "Nueva persona"} ancha>
          {aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>}
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardar().then((ok) => ok && setVentana(false)); }}>
            <Input value={String(actual.nombre)} label="Nombre" isRequired maxLength={120} onChange={(x) => set({ nombre: x })} />
            <NativeSelect size="sm" label="Tipo" value={actual.tipo} onChange={(x) => set({ tipo: x.target.value })}>{TIPOS.map((t) => <option key={t}>{t}</option>)}</NativeSelect>
            <Input value={String(actual.horas_sem)} label="Horas por semana" type="text" inputMode="decimal" onChange={(x) => set({ horas_sem: Number(x.replace(",", ".")) })} />
            <Input value={String(actual.pct)} label="Dedicación (%)" type="number" onChange={(x) => set({ pct: Number(x) })} />
            <Grupo leyenda="Turnos que puede hacer">
              {turnos.map((t) => <Checkbox key={t.codigo} label={`${t.codigo} · ${t.nombre}`} isSelected={actual.permitidos.includes(t.codigo)} onChange={() => set({ permitidos: alternar(actual.permitidos, t.codigo) })} />)}
            </Grupo>
            <Grupo leyenda="Puestos que puede ocupar">
              {puestos.map((p) => <Checkbox key={p.id} label={`${p.numero} · ${p.nombre}`} isSelected={actual.puestos.includes(p.id)} onChange={() => set({ puestos: alternar(actual.puestos, p.id) })} />)}
            </Grupo>
            <Grupo leyenda="Bloques de estudio (no disponible)">
              {(["M", "T"] as const).map((fr) => DIAS.map((d, i) => (
                <Checkbox key={`${i}${fr}`} label={`${d} ${fr === "M" ? "mañana" : "tarde"}`} isSelected={actual.estudio.includes(`${i}${fr}`)} onChange={() => set({ estudio: alternar(actual.estudio, `${i}${fr}`) })} />
              )))}
            </Grupo>
            <Checkbox label="Activo" isSelected={actual.activo} onChange={(x) => set({ activo: x })} />
            <Fila>
              {sel && <Button color="secondary-destructive" size="sm" className="mr-auto" iconLeading={Trash01} isDisabled={ocupado} onPress={borrar}>Eliminar</Button>}
              <Button color="secondary" size="sm" onPress={() => setVentana(false)}>Cancelar</Button>
              <Button color="primary" size="sm" type="submit" isDisabled={ocupado || !actual.nombre.trim() || !actual.permitidos.length || !actual.puestos.length}>{ocupado ? "Guardando…" : "Guardar"}</Button>
            </Fila>
          </Formulario>
        </Ventana>
      )}
      {editar && (
        <Ventana abierto={pegado !== null} alCambiar={(v) => !v && setPegado(null)} titulo="Pegar lista de personal" ancha
          descripcion="Copia en Excel las columnas Nombre, Horas por semana y Dedicación (las dos últimas son opcionales: 42 h y 100 %) y pégalas aquí.">
          {aviso?.nivel === "error" && <Alert color="error">{aviso.texto}</Alert>}
          <Formulario onSubmit={(x) => { x.preventDefault(); void agregarLista(); }}>
            <label className="col-span-full flex flex-col gap-1.5 text-sm font-medium text-secondary">
              Filas copiadas
              <textarea value={pegado ?? ""} onChange={(x) => setPegado(x.target.value)} rows={8} autoFocus spellCheck={false}
                placeholder={"Ana Pérez\t42\t100\nLuis Gómez\t36\t50 %"}
                className="rounded-lg bg-primary px-3 py-2 font-mono text-sm text-primary shadow-xs ring-1 ring-primary ring-inset outline-none placeholder:text-placeholder focus:ring-2 focus:ring-brand" />
            </label>
            {lectura && (lectura.personas.length > 0 || lectura.repetidas.length > 0 || lectura.errores.length > 0) && (
              <div className="col-span-full flex flex-col gap-2 text-sm" role="status" aria-live="polite">
                <p className="text-secondary">
                  Se agregarán <strong>{lectura.personas.length}</strong> {lectura.personas.length === 1 ? "persona" : "personas"} como «regular», con todos los turnos y puestos.
                  {lectura.repetidas.length > 0 && <> {lectura.repetidas.length === 1 ? "Se omite 1 que ya está" : `Se omiten ${lectura.repetidas.length} que ya están`}: {lectura.repetidas.slice(0, 5).join(", ")}{lectura.repetidas.length > 5 && "…"}.</>}
                </p>
                {lectura.errores.length > 0 && <Alert color="warning"><ul className="list-disc pl-5">{lectura.errores.slice(0, 5).map((e) => <li key={e}>{e}</li>)}</ul></Alert>}
              </div>
            )}
            <Fila>
              <Button color="secondary" size="sm" onPress={() => setPegado(null)}>Cancelar</Button>
              <Button color="primary" size="sm" type="submit" isDisabled={ocupado || !lectura?.personas.length}>{ocupado ? "Agregando…" : `Agregar ${lectura?.personas.length || ""}`.trim()}</Button>
            </Fila>
          </Formulario>
        </Ventana>
      )}
      {confirmacion}
    </Pagina>
  );
}
