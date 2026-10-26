import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { aHHMM, aMinutos, enviar, usar } from "../api/catalogos";
import type { Area, Tarifa, Turno } from "../api/tipos";
import { Boton } from "../componentes/Boton";
import { Campo, Seleccion } from "../componentes/Campo";
import { Tabla } from "../componentes/Tabla";
import { Tarjeta } from "../componentes/Tarjeta";
import { Casilla, Fila, Formulario, Pagina, useAccion } from "./comun";
import { fechaCorta } from "./fechas";

const NUM: [string, string, number, number, string][] = [
  ["ventana_semanas", "Promedio de horas (semanas)", 1, 8, "Las 42 h semanales se miden como promedio de este número de semanas (art. 165 CST)."],
  ["limite_permutas", "Permutas por persona y periodo", 0, 20, "Cuántos intercambios de turno puede pedir cada persona. Pasado el límite hace falta una excepción."],
  ["periodo_semanas", "Semanas por periodo", 1, 8, "Solo si el periodo es «Semanas desde un lunes»."],
  ["max_noches_seguidas", "Noches seguidas (máximo)", 0, 7, "Cuántas noches puede hacer alguien sin parar. 0 = sin límite."],
  ["max_c_seguidos", "Corridos seguidos (máximo)", 0, 7, "Turnos de 12 h de día seguidos. 0 = sin límite."],
  ["max_igual_seguidos", "Mismo turno corto seguido", 0, 7, "Días seguidos con el mismo turno de 6 h (mañana o tarde). 0 = sin límite."],
  ["libre_tras_noche", "Días libres después de noche", 0, 3, "Descanso mínimo al terminar una noche. 0 = no aplicar la regla."],
  ["libres_por_semana", "Días libres por semana", 1, 3, "Mínimo de días sin turno cada semana."],
  ["fines_semana_libres", "Fines de semana libres al mes", 0, 4, "Sábado y domingo completos sin turno. 0 = no aplicar la regla."],
  ["banco_tope_favor_h", "Banco: máximo a favor (h)", 0, 48, "Horas de más que se pueden guardar por periodo para compensar después. 0 = no compensar."],
  ["banco_tope_deuda_h", "Banco: máximo en deuda (h)", 0, 48, "Horas de menos que se pueden deber por periodo. 0 = no compensar."],
];
const CONCEPTOS = ["dominical", "nocturno", "extra_diurna", "extra_nocturna", "noche_inicio"];
const TURNO_NUEVO = { codigo: "", nombre: "", inicio: 360, fin: 720, color: "FFF2CC", pmin: 0, pini: 60, ppag: false, dom_fest: true, solver: true, activo: true };

/** Reglas del área, turnos y tarifas legales (editables: confirmar con RR. HH./legal). */
export function Parametros() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const params = usar<Record<string, string>>(`${base}/parametros`);
  const turnos = usar<Turno[]>(`${base}/turnos`);
  const tarifas = usar<Tarifa[]>(`${base}/tarifas`);
  const { ocupado, aviso, hacer, avisar } = useAccion();
  const [v, setV] = useState<Record<string, string>>({});
  const [t, setT] = useState(TURNO_NUEVO);
  const [nuevo, setNuevo] = useState(true);
  const [tar, setTar] = useState({ concepto: CONCEPTOS[0], valor: "", desde: "" });
  const editar = area.permiso === "editar";
  useEffect(() => { if (params.datos) setV(params.datos); }, [params.datos]);

  const guardarReglas = () => hacer(async () => {
    const cuerpo: Record<string, number | string> = { periodo_modo: v.periodo_modo ?? "mes" };
    for (const [k] of NUM) if (v[k] !== undefined) cuerpo[k] = Number(v[k]);
    await enviar("PUT", `${base}/parametros`, cuerpo);
    params.recargar();
    return "Reglas guardadas.";
  });
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
  const agregarTarifa = () => hacer(async () => {
    await enviar("POST", `${base}/tarifas`, { ...tar, valor: Number(tar.valor) });
    tarifas.recargar();
    setTar({ ...tar, valor: "" });
    return "Tarifa agregada.";
  });

  return (
    <Pagina titulo="Reglas y turnos" sub="Lo que el sistema respeta al armar el cuadro. Los valores legales son editables: confírmalos con RR. HH." ayuda={<>Las <strong>reglas</strong> limitan cómo se reparten los turnos (descansos, noches seguidas, fines de semana libres). Los <strong>turnos</strong> definen horarios y pausas. Las <strong>tarifas</strong> son los recargos legales para calcular horas equivalentes. Si cambias algo, vuelve a generar el cuadro o revisa las alertas.</>} error={params.error ?? turnos.error ?? tarifas.error} aviso={aviso}>
      <Tarjeta titulo="Reglas" aria-busy={!params.datos}>
        {!params.datos ? !params.error && <p aria-busy="true">Cargando…</p> : (
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardarReglas(); }}>
            <Seleccion etiqueta="Periodo" ayuda="Cómo se corta cada cuadro." disabled={!editar} value={v.periodo_modo ?? "mes"} onChange={(x) => setV({ ...v, periodo_modo: x.target.value })}>
              <option value="mes">Mes calendario</option><option value="semanas">Semanas desde un lunes</option>
            </Seleccion>
            {NUM.map(([k, etiqueta, lo, hi, ayuda]) => (
              <Campo key={k} etiqueta={etiqueta} ayuda={ayuda} type="number" min={lo} max={hi} disabled={!editar} value={v[k] ?? ""} onChange={(x) => setV({ ...v, [k]: x.target.value })} />
            ))}
            {editar && <Fila><Boton type="submit" variante="primario" disabled={ocupado}>Guardar reglas</Boton></Fila>}
          </Formulario>
        )}
      </Tarjeta>

      <Tarjeta titulo="Turnos">
        <Tabla descripcion="Turnos del área" cargando={!turnos.datos && !turnos.error} vacio="Sin turnos." columnas={["Código", "Nombre", "Horario", "Estado", ""]}
          filas={(turnos.datos ?? []).map((x) => [x.codigo, x.nombre, `${aHHMM(x.inicio)} – ${aHHMM(x.fin)}`, x.activo ? "Activo" : "Inactivo",
            editar ? <Boton variante="texto" onClick={() => elegirTurno(x)}>Editar</Boton> : null])} />
        {editar && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void guardarTurno(); }}>
            <Campo etiqueta="Código" required maxLength={6} disabled={!nuevo} value={t.codigo} onChange={(x) => setT({ ...t, codigo: x.target.value })} />
            <Campo etiqueta="Nombre" maxLength={60} value={t.nombre} onChange={(x) => setT({ ...t, nombre: x.target.value })} />
            <Campo etiqueta="Entra" type="time" value={aHHMM(t.inicio)} onChange={(x) => setT({ ...t, inicio: aMinutos(x.target.value) })} />
            <Campo etiqueta="Sale" type="time" value={aHHMM(t.fin)} onChange={(x) => setT({ ...t, fin: aMinutos(x.target.value) })} />
            <Campo etiqueta="Color en el cuadro" type="color" value={`#${t.color}`} onChange={(x) => setT({ ...t, color: x.target.value.slice(1).toUpperCase() })} />
            <Campo etiqueta="Pausa (min, 0 = sin pausa)" type="number" min={0} max={240} value={t.pmin} onChange={(x) => setT({ ...t, pmin: Number(x.target.value) })} />
            {t.pmin > 0 && <Campo etiqueta="Pausa empieza (min desde la entrada)" type="number" min={0} max={1439} value={t.pini} onChange={(x) => setT({ ...t, pini: Number(x.target.value) })} />}
            {t.pmin > 0 && <Casilla etiqueta="Pausa pagada" checked={t.ppag} onChange={(x) => setT({ ...t, ppag: x.target.checked })} />}
            <Casilla etiqueta="Permitido en domingo y festivo" checked={t.dom_fest} onChange={(x) => setT({ ...t, dom_fest: x.target.checked })} />
            <Casilla etiqueta="Lo usa el solver" checked={t.solver} onChange={(x) => setT({ ...t, solver: x.target.checked })} />
            <Casilla etiqueta="Activo" checked={t.activo} onChange={(x) => setT({ ...t, activo: x.target.checked })} />
            <Fila>
              <Boton type="submit" variante="primario" disabled={ocupado || !t.codigo.trim()}>Guardar turno</Boton>
              <Boton onClick={() => elegirTurno(null)}>Nuevo turno</Boton>
              {!nuevo && <Boton variante="peligro" disabled={ocupado} onClick={borrarTurno}>Eliminar</Boton>}
            </Fila>
          </Formulario>
        )}
      </Tarjeta>

      <Tarjeta titulo="Tarifas">
        <Tabla descripcion="Tarifas vigentes por fecha" cargando={!tarifas.datos && !tarifas.error} vacio="Sin tarifas." columnas={["Concepto", "Valor", "Desde"]}
          filas={[...(tarifas.datos ?? [])].sort((a, b) => a[0].localeCompare(b[0]) || a[2].localeCompare(b[2])).map(([c, valor, d]) => [c, valor, fechaCorta(d)])} />
        {editar && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void agregarTarifa(); }}>
            <Seleccion etiqueta="Concepto" value={tar.concepto} onChange={(x) => setTar({ ...tar, concepto: x.target.value })}>{CONCEPTOS.map((c) => <option key={c}>{c}</option>)}</Seleccion>
            <Campo etiqueta="Valor (% o minutos)" type="number" min={0} max={5000} required value={tar.valor} onChange={(x) => setTar({ ...tar, valor: x.target.value })} />
            <Campo etiqueta="Rige desde" type="date" required value={tar.desde} onChange={(x) => setTar({ ...tar, desde: x.target.value })} />
            <Fila><Boton type="submit" variante="primario" disabled={ocupado || !tar.valor || !tar.desde}>Agregar tarifa</Boton></Fila>
          </Formulario>
        )}
      </Tarjeta>
    </Pagina>
  );
}
