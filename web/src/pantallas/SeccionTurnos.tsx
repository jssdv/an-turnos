import { useState } from "react";
import { aHHMM, aMinutos, enviar, type usar } from "../api/catalogos";
import type { Turno } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Fila, Formulario, useAccion, Seccion } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Checkbox } from "@/components/base/checkbox/checkbox";
import { Badge } from "@/components/base/badges/badges";
import { Alert } from "@/components/application/alerts/alert";

const TURNO_NUEVO = { codigo: "", nombre: "", inicio: 360, fin: 720, color: "FFF2CC", pmin: 0, pini: 60, ppag: false, dom_fest: true, solver: true, activo: true };

/** Turnos del área: la base de la necesidad, que se pide por el horario de cada turno. */
export function SeccionTurnos({ base, editar, turnos }: { base: string; editar: boolean; turnos: ReturnType<typeof usar<Turno[]>> }) {
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const [t, setT] = useState(TURNO_NUEVO);
  const [nuevo, setNuevo] = useState(true);
  const elegirTurno = (x: Turno | null) => {
    setNuevo(!x);
    setT(x ? { codigo: x.codigo, nombre: x.nombre, inicio: x.inicio, fin: x.fin, color: x.color, pmin: x.pausas[0]?.min ?? 0, pini: x.pausas[0]?.ini ?? 60, ppag: x.pausas[0]?.pagada ?? false, dom_fest: x.dom_fest, solver: x.solver, activo: x.activo } : TURNO_NUEVO);
  };
  const guardarTurno = () => hacer(async () => {
    const cuerpo = { codigo: t.codigo, nombre: t.nombre, inicio: t.inicio, fin: t.fin, color: t.color, dom_fest: t.dom_fest, solver: t.solver, activo: t.activo,
      pausa: t.pmin > 0 ? { ini: t.pini, min: t.pmin, pagada: t.ppag } : null };
    await enviar(nuevo ? "POST" : "PUT", nuevo ? `${base}/turnos` : `${base}/turnos/${t.codigo}`, cuerpo);
    turnos.recargar();
    setNuevo(false);
    return `Turno «${t.codigo.toUpperCase()}» guardado. El cuadro existente se revalida; regenera si hay alertas.`;
  });
  const borrarTurno = () => window.confirm(`¿Eliminar el turno «${t.codigo}»?`) && hacer(async () => {
    const r = await enviar<{ resultado: string }>("DELETE", `${base}/turnos/${t.codigo}`);
    elegirTurno(null); turnos.recargar();
    avisar({ nivel: r.resultado === "borrado" ? "ok" : "aviso", texto: r.resultado === "borrado" ? "Turno eliminado." : "Ya está en cuadros guardados, así que quedó inactivo en lugar de borrarse." });
  });

  return (
    <>
      {aviso && <Alert color={aviso.nivel === "ok" ? "success" : "error"}>{aviso.texto}</Alert>}
      <Seccion titulo="Turnos">
        <Tabla descripcion="Turnos del área" cargando={!turnos.datos && !turnos.error} vacio="Sin turnos." columnas={["Código", "Nombre", "Horario", "Estado", ""]}
          filas={(turnos.datos ?? []).map((x) => [x.codigo, x.nombre, `${aHHMM(x.inicio)} – ${aHHMM(x.fin)}`, <Badge size="sm" color={x.activo ? "success" : "gray"}>{x.activo ? "Activo" : "Inactivo"}</Badge>,
            editar ? <Button color="link-color" size="sm" onPress={() => elegirTurno(x)}>Editar</Button> : null])} />
        {editar && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardarTurno(); }}>
            <Input value={String(t.codigo)} label="Código" isRequired maxLength={6} isDisabled={!nuevo} onChange={(x) => setT({ ...t, codigo: x })} />
            <Input value={String(t.nombre)} label="Nombre" maxLength={60} onChange={(x) => setT({ ...t, nombre: x })} />
            <Input value={String(aHHMM(t.inicio))} label="Entra" type="time" onChange={(x) => setT({ ...t, inicio: aMinutos(x) })} />
            <Input value={String(aHHMM(t.fin))} label="Sale" type="time" onChange={(x) => setT({ ...t, fin: aMinutos(x) })} />
            <Input value={String(`#${t.color}`)} label="Color en el cuadro" type="color" onChange={(x) => setT({ ...t, color: x.slice(1).toUpperCase() })} />
            <Input value={String(t.pmin)} label="Pausa (min, 0 = sin pausa)" type="number" onChange={(x) => setT({ ...t, pmin: Number(x) })} />
            {t.pmin > 0 && <Input value={String(t.pini)} label="Pausa empieza (min desde la entrada)" type="number" onChange={(x) => setT({ ...t, pini: Number(x) })} />}
            {t.pmin > 0 && <Checkbox label="Pausa pagada" isSelected={t.ppag} onChange={(x) => setT({ ...t, ppag: x })} />}
            <Checkbox label="Permitido en domingo y festivo" isSelected={t.dom_fest} onChange={(x) => setT({ ...t, dom_fest: x })} />
            <Checkbox label="Lo usa el solver" isSelected={t.solver} onChange={(x) => setT({ ...t, solver: x })} />
            <Checkbox label="Activo" isSelected={t.activo} onChange={(x) => setT({ ...t, activo: x })} />
            <Fila>
              <Button color="primary" size="sm" type="submit" isDisabled={ocupado || !t.codigo.trim()}>Guardar turno</Button>
              <Button color="secondary" size="sm" onPress={() => elegirTurno(null)}>Nuevo turno</Button>
              {!nuevo && <Button color="primary-destructive" size="sm" isDisabled={ocupado} onPress={borrarTurno}>Eliminar</Button>}
            </Fila>
          </Formulario>
        )}
      </Seccion>
    </>
  );
}
