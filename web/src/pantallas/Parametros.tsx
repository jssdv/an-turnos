import { useEffect, useState } from "react";
import { useOutletContext } from "react-router";
import { enviar, usar } from "../api/catalogos";
import type { Area, Tarifa } from "../api/tipos";
import { Tabla } from "../componentes/Tabla";
import { Check, Settings01 } from "@untitledui/icons";
import { Fila, Formulario, Pagina, Pista, useAccion, Seccion } from "./comun";
import { fechaCorta } from "./fechas";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";

const NUM: [string, string, number, number, string][] = [
  ["ventana_semanas", "Promedio de horas (semanas)", 1, 8, "Las 42 h semanales se miden como promedio de este número de semanas (art. 165 CST)."],
  ["limite_permutas", "Permutas por persona y periodo", 0, 20, "Cuántos intercambios de turno puede pedir cada persona. Pasado el límite hace falta una excepción."],
  ["periodo_semanas", "Semanas por periodo", 1, 8, "Solo si el periodo es «Semanas desde un lunes»."],
  ["max_horas_semana", "Horas por semana (máximo)", 0, 84, "Tope de horas que el cuadro asigna a una persona en una semana de lunes a domingo. 0 = sin tope."],
  ["max_noches_seguidas", "Noches seguidas (máximo)", 0, 7, "Cuántas noches puede hacer alguien sin parar. 0 = sin límite."],
  ["max_c_semana", "Corridos por semana (máximo)", 0, 7, "Máx. de corridos (C, 12 h) por semana. 0 = sin límite."],
  ["partir_corridos", "Partir corridos entre puestos", 0, 1, "1 = el corrido (C) se parte: un puesto en la mañana y otro distinto en la tarde. 0 = se prefiere el mismo puesto todo el día."],
  ["peso_corrido", "Costo de los corridos", 0, 10, "Qué tanto evitar corridos. 0 = nada, 1 = normal, más = menos corridos."],
  ["max_c_seguidos", "Corridos seguidos (máximo)", 0, 7, "Turnos de 12 h de día seguidos. 0 = sin límite."],
  ["max_igual_seguidos", "Mismo turno corto seguido", 0, 7, "Días seguidos con el mismo turno de 6 h (mañana o tarde). 0 = sin límite."],
  ["libre_tras_noche", "Días libres después de noche", 0, 3, "Descanso mínimo al terminar una noche. 0 = no aplicar la regla."],
  ["libres_por_semana", "Días libres por semana", 1, 3, "Mínimo de días sin turno cada semana."],
  ["fines_semana_libres", "Fines de semana libres al mes", 0, 4, "Sábado y domingo completos sin turno. 0 = no aplicar la regla."],
  ["banco_tope_favor_h", "Banco: máximo a favor (h)", 0, 48, "Horas de más que se pueden guardar por periodo para compensar después. 0 = no compensar."],
  ["banco_tope_deuda_h", "Banco: máximo en deuda (h)", 0, 48, "Horas de menos que se pueden deber por periodo. 0 = no compensar."],
];
const CONCEPTOS = ["dominical", "nocturno", "extra_diurna", "extra_nocturna", "noche_inicio"];
const NOMBRE_CONCEPTO: Record<string, string> = {
  dominical: "Recargo dominical y festivo", nocturno: "Recargo nocturno", extra_diurna: "Hora extra diurna",
  extra_nocturna: "Hora extra nocturna", noche_inicio: "Inicio de la noche (minutos desde 00:00)",
};
const nombreConcepto = (c: string) => NOMBRE_CONCEPTO[c] ?? c;
/** Reglas por tema, para no mostrar 15 campos seguidos. */
const GRUPOS: [string, string[]][] = [
  ["Horas", ["ventana_semanas", "max_horas_semana", "periodo_semanas"]],
  ["Descansos", ["max_noches_seguidas", "libre_tras_noche", "libres_por_semana", "fines_semana_libres", "max_igual_seguidos"]],
  ["Corridos (C, 12 h)", ["max_c_semana", "max_c_seguidos", "peso_corrido", "partir_corridos"]],
  ["Permutas y banco de horas", ["limite_permutas", "banco_tope_favor_h", "banco_tope_deuda_h"]],
];

/** Reglas del área, turnos y tarifas legales (editables: confirmar con RR. HH./legal). */
export function Parametros() {
  const area = useOutletContext<Area>();
  const base = `/api/areas/${area.id}`;
  const params = usar<Record<string, string>>(`${base}/parametros`);
  const tarifas = usar<Tarifa[]>(`${base}/tarifas`);
  const { ocupado, aviso, hacer } = useAccion();
  const [v, setV] = useState<Record<string, string>>({});
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
  const agregarTarifa = () => hacer(async () => {
    await enviar("POST", `${base}/tarifas`, { ...tar, valor: Number(tar.valor) });
    tarifas.recargar();
    setTar({ ...tar, valor: "" });
    return "Tarifa agregada.";
  });

  return (
    <Pagina titulo="Parámetros" icono={Settings01}
      acciones={editar && params.datos && <Pista texto="Guarda las reglas. El cuadro ya armado no cambia: genera de nuevo para aplicarlas."><Button color="primary" size="sm" iconLeading={Check} type="submit" form="reglas" isDisabled={ocupado}>Guardar reglas</Button></Pista>} sub="Lo que el sistema respeta al armar el cuadro. Los valores legales son editables: confírmalos con RR. HH." ayuda={<>Las <strong>reglas</strong> limitan cómo se reparten los turnos (descansos, noches seguidas, fines de semana libres). Las <strong>tarifas</strong> son los recargos legales para calcular horas equivalentes. Si cambias algo, vuelve a generar el cuadro o revisa las alertas.</>} error={params.error ?? tarifas.error} aviso={aviso}>
      {!params.datos ? !params.error && <p className="tarjeta p-5" aria-busy="true">Cargando…</p> : (
        <form id="reglas" aria-label="Reglas" className="grid items-start gap-4 lg:grid-cols-2" onSubmit={(x) => { x.preventDefault(); void guardarReglas(); }}>
          {GRUPOS.map(([titulo, claves], i) => (
            <Seccion key={titulo} titulo={titulo}>
              <fieldset className="flex flex-col gap-4">
                <legend className="sr-only">{titulo}</legend>
                {i === 0 && (
                  <NativeSelect size="sm" label="Periodo" hint="Cómo se corta cada cuadro." disabled={!editar} value={v.periodo_modo ?? "mes"} onChange={(x) => setV({ ...v, periodo_modo: x.target.value })}>
                    <option value="mes">Mes calendario</option><option value="semanas">Semanas desde un lunes</option>
                  </NativeSelect>
                )}
                {NUM.filter(([k]) => claves.includes(k)).map(([k, etiqueta, lo, hi, ayuda]) => (
                  <Input value={String(v[k] ?? "")} key={k} label={etiqueta} ayuda={ayuda} hint={`Entre ${lo} y ${hi}.`} type="number" isDisabled={!editar} onChange={(x) => setV({ ...v, [k]: x })} />
                ))}
              </fieldset>
            </Seccion>
          ))}
        </form>
      )}

      <Seccion titulo="Tarifas">
        <Tabla descripcion="Tarifas vigentes por fecha" cargando={!tarifas.datos && !tarifas.error} vacio="Sin tarifas." columnas={["Concepto", "Valor", "Desde"]}
          filas={[...(tarifas.datos ?? [])].sort((a, b) => a[0].localeCompare(b[0]) || a[2].localeCompare(b[2])).map(([c, valor, d]) => [nombreConcepto(c), valor, fechaCorta(d)])} />
        {editar && (
          <Formulario onSubmit={(x) => { x.preventDefault(); void agregarTarifa(); }}>
            <NativeSelect size="sm" label="Concepto" value={tar.concepto} onChange={(x) => setTar({ ...tar, concepto: x.target.value })}>{CONCEPTOS.map((c) => <option key={c} value={c}>{nombreConcepto(c)}</option>)}</NativeSelect>
            <Input value={String(tar.valor)} label={tar.concepto === "noche_inicio" ? "Valor (minutos)" : "Valor (%)"} type="number" isRequired onChange={(x) => setTar({ ...tar, valor: x })} />
            <Input value={String(tar.desde)} label="Rige desde" type="date" isRequired onChange={(x) => setTar({ ...tar, desde: x })} />
            <Fila><Button color="primary" size="sm" type="submit" isDisabled={ocupado || !tar.valor || !tar.desde}>Agregar tarifa</Button></Fila>
          </Formulario>
        )}
      </Seccion>
    </Pagina>
  );
}
