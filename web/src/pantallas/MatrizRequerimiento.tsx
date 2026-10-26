import { useEffect, useState } from "react";
import { aHHMM, enviar, usar } from "../api/catalogos";
import type { Requerimiento, Turno } from "../api/tipos";
import { Fila, useAccion, Seccion } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Alert } from "@/components/application/alerts/alert";

const DIAS = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom", "Festivo"];
const clave = (dia: number, inicio: number, fin: number) => `${dia}|${inicio}|${fin}`;

/** Personas pedidas por horario de turno y día de la semana: del área (sin puestos) o de un puesto (`deseable` = casilla del puesto).
 *  Un horario = una fila (los turnos con el mismo horario la comparten). */
export function MatrizRequerimiento({ ruta, titulo, editar, turnos, conDeseable = false }: { ruta: string; titulo: string; editar: boolean; turnos: Turno[]; conDeseable?: boolean }) {
  const req = usar<Requerimiento[]>(ruta);
  const { ocupado, aviso, hacer } = useAccion();
  const [n, setN] = useState<Record<string, number>>({});
  const [deseable, setDeseable] = useState(false);
  useEffect(() => {
    if (!req.datos) return;
    setN(req.datos.reduce<Record<string, number>>((a, r) => ({ ...a, [clave(r.dia, r.inicio, r.fin)]: (a[clave(r.dia, r.inicio, r.fin)] ?? 0) + r.personas }), {}));
    setDeseable(req.datos.length > 0 && req.datos.every((r) => !r.obligatorio));
  }, [req.datos]);
  const mezcla = conDeseable && !!req.datos?.some((r) => r.obligatorio) && !!req.datos?.some((r) => !r.obligatorio);
  const filas = new Map<string, { inicio: number; fin: number; codigos: string[] }>();
  for (const t of turnos.filter((x) => x.activo && x.solver)) {
    const f = filas.get(`${t.inicio}|${t.fin}`) ?? { inicio: t.inicio, fin: t.fin, codigos: [] };
    filas.set(`${t.inicio}|${t.fin}`, { ...f, codigos: [...f.codigos, t.codigo] });
  }
  for (const r of req.datos ?? []) if (!filas.has(`${r.inicio}|${r.fin}`)) filas.set(`${r.inicio}|${r.fin}`, { inicio: r.inicio, fin: r.fin, codigos: [] }); // horario que ya no es de ningún turno
  const lista = [...filas.values()].sort((a, b) => a.inicio - b.inicio || a.fin - b.fin);
  const guardar = () => hacer(async () => {
    const cuerpo = lista.flatMap((f) => DIAS.map((_, dia) => ({ dia, inicio: f.inicio, fin: f.fin, personas: n[clave(dia, f.inicio, f.fin)] ?? 0, obligatorio: !deseable }))).filter((x) => x.personas > 0);
    await enviar("PUT", ruta, cuerpo);
    req.recargar();
    return "Requerimiento guardado. Regenera el cuadro para que lo tome en cuenta.";
  });
  return (
    <Seccion titulo={titulo}>
      {(aviso || req.error) && <Alert color={aviso?.nivel === "ok" ? "success" : "error"}>{aviso?.texto ?? req.error}</Alert>}
      <p className="text-sm text-tertiary">Cuántas personas hacen falta en el horario de cada turno, según el día de la semana. El festivo reemplaza al día de la semana. Si dos filas se solapan (por ejemplo un corrido y una mañana), las personas se suman en las horas comunes.</p>
      {mezcla && <Alert color="warning">Este puesto mezclaba cobertura obligatoria y deseable. Al guardar, la casilla de abajo se aplica a todo.</Alert>}
      <div className="overflow-x-auto"><table className="text-sm"><thead><tr><th className="sticky left-0 z-10 bg-primary p-1 text-left">Turno</th>{DIAS.map((d) => <th key={d} className="p-1">{d}</th>)}</tr></thead>
        <tbody>{lista.map((f) => {
          const nombre = f.codigos.length ? f.codigos.join(" / ") : "Sin turno";
          return (
            <tr key={`${f.inicio}|${f.fin}`}><th className="sticky left-0 z-10 bg-primary p-1 pr-2 text-left font-medium whitespace-nowrap">{nombre}<span className="block text-xs font-normal text-tertiary">{aHHMM(f.inicio)} – {aHHMM(f.fin)}</span></th>
              {DIAS.map((d, dia) => <td key={d} className="p-1"><Input aria-label={`${nombre} ${aHHMM(f.inicio)} ${d}`} type="number" size="sm" className="w-20" isDisabled={!editar} value={String(n[clave(dia, f.inicio, f.fin)] ?? 0)}
                onChange={(x) => setN({ ...n, [clave(dia, f.inicio, f.fin)]: Math.max(0, Number(x)) })} /></td>)}
            </tr>);
        })}</tbody></table></div>
      {lista.length === 0 && <p>Primero define los turnos del área.</p>}
      {conDeseable && <Checkbox label="Cobertura deseable, no obligatoria" hint="El sistema intenta cubrirla pero no avisa si falta." isSelected={deseable} isDisabled={!editar} onChange={setDeseable} />}
      {editar && <Fila><Button color="primary" size="sm" isDisabled={ocupado || !lista.length} onPress={guardar}>Guardar requerimiento</Button></Fila>}
    </Seccion>
  );
}
