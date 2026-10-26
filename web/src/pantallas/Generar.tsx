import { useEffect, useRef, useState } from "react";
import { ErrorApi } from "../api/cliente";
import type { PedidoGenerar, Periodo, Trabajo } from "../api/tipos";
import { trabajos, trabajosSimulados } from "../api/trabajos";
import { ProgressBar } from "@/components/base/progress-indicators/progress-indicators";
import { Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { NativeSelect } from "@/components/base/select/select-native";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";

const CADA_MS = 1500;
const TERMINALES = new Set(["listo", "fallido", "cancelado", "conflicto"]);
function textoListo(t: Trabajo) {
  const falta = t.resultado?.faltan.length ?? 0, sol = t.resultado?.solicitudes.length ?? 0;
  const notas = [falta && `${falta} ${falta === 1 ? "tramo sin cubrir" : "tramos sin cubrir"}`, sol && `${sol} ${sol === 1 ? "solicitud sin cumplir del todo" : "solicitudes sin cumplir del todo"}`].filter(Boolean);
  return `Cuadro generado.${notas.length ? ` Revisa: ${notas.join(" y ")}.` : " Ya puedes revisarlo."}`;
}
const MENSAJE: Record<string, [("ok" | "aviso" | "error"), string]> = {
  listo: ["ok", ""],
  cancelado: ["aviso", "Generación cancelada. No se cambió nada."],
  conflicto: ["aviso", "Alguien editó este periodo mientras se generaba, así que no se guardó nada. Vuelve a generar."],
  fallido: ["error", "La generación se interrumpió. Vuelve a generar."],
};

interface Props {
  area: number;
  periodo: Periodo;
  bloqueado: boolean;
  alTerminar: () => void;
}

/** Botón «Generar» con su diálogo: lanza el trabajo, consulta el progreso cada ~1,5 s y permite cancelar. */
export function Generar({ area, periodo, bloqueado, alTerminar }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [modo, setModo] = useState<PedidoGenerar["modo"]>("respetar");
  const [lunes, setLunes] = useState("");
  const [trabajo, setTrabajo] = useState<Trabajo | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [cancelando, setCancelando] = useState(false);
  const id = useRef<number | null>(null);

  const corriendo = !!trabajo && !TERMINALES.has(trabajo.estado);

  useEffect(() => {
    if (!abierto || !corriendo) return;
    let vivo = true;
    let t: ReturnType<typeof setTimeout>;
    const consultar = async () => {
      try {
        const r = await trabajos.consultar(id.current!);
        if (!vivo) return;
        setTrabajo(r);
        if (r.estado === "listo") alTerminar();
        if (!TERMINALES.has(r.estado)) t = setTimeout(consultar, CADA_MS);
      } catch (x) {
        if (vivo) { setError(x instanceof ErrorApi ? x.message : "Se perdió la conexión"); t = setTimeout(consultar, CADA_MS * 2); }
      }
    };
    t = setTimeout(consultar, CADA_MS);
    return () => { vivo = false; clearTimeout(t); };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [abierto, corriendo]);

  const abrir = () => { setTrabajo(null); setError(null); setCancelando(false); setAbierto(true); };

  const iniciar = async () => {
    setError(null);
    setEnviando(true);
    try {
      const pedido: PedidoGenerar = modo === "semana" ? { modo, lunes } : { modo };
      const r = await trabajos.iniciar(area, periodo.id, periodo.revision, pedido);
      id.current = r.id;
      setTrabajo({ id: r.id, estado: "en_cola", progreso: null, resultado: null, error: null });
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo iniciar");
      if (x instanceof ErrorApi && x.estado === 409) alTerminar(); // la revisión cambió: se recarga el cuadro para tener la vigente
    } finally {
      setEnviando(false);
    }
  };

  const cancelar = async () => {
    setCancelando(true);
    try { setTrabajo(await trabajos.cancelar(id.current!)); } catch (x) { setError(x instanceof ErrorApi ? x.message : "No se pudo cancelar"); }
    setCancelando(false);
  };

  const p = trabajo?.progreso;
  const fin = trabajo && MENSAJE[trabajo.estado];

  return (
    <>
      <span title={bloqueado ? "El periodo está cerrado" : undefined}><Button color="primary" size="sm" onPress={abrir} isDisabled={bloqueado}>Generar</Button></span>
      <Ventana
        abierto={abierto}
        alCambiar={setAbierto}
        bloqueado={corriendo}
        titulo="Generar cuadro"
        descripcion="Calcula un cuadro nuevo con las reglas actuales. Puede tardar unos segundos; mientras corre no se puede editar este periodo."
      >
        {trabajosSimulados && <Alert color="brand">Modo simulado: no se llama al servidor.</Alert>}
        {error && <Alert color="error">{error}</Alert>}
        {!trabajo && (
          <div className="flex flex-col gap-4">
            <NativeSelect size="sm" label="Alcance" value={modo} onChange={(x) => setModo(x.target.value as PedidoGenerar["modo"])}>
              <option value="respetar">Mes completo, respetando lo editado a mano</option>
              <option value="cero">Mes completo, desde cero</option>
              <option value="semana">Una semana</option>
            </NativeSelect>
            {modo === "semana" && <Input value={String(lunes)} label="Lunes de la semana" type="date" onChange={(x) => setLunes(x)} />}
          </div>
        )}
        {trabajo && !fin && (
          <div className="flex flex-col gap-2" aria-live="polite">
            <p className="text-sm font-medium text-secondary">{trabajo.estado === "en_cola" ? "En cola…" : "Generando…"}</p>
            <ProgressBar value={p ? Math.min(100, (p.segundos / p.limite) * 100) : 0} labelPosition="right" />
            <p className="text-xs text-tertiary">{p ? `${Math.round(p.segundos)} s de ${p.limite} s · ${p.soluciones} soluciones${p.objetivo !== null ? ` · objetivo ${p.objetivo}` : ""}` : "Esperando turno del servidor"}</p>
          </div>
        )}
        {fin && <Alert color={COLOR_NIVEL[fin[0]]}>{trabajo?.error ?? (trabajo?.estado === "listo" ? textoListo(trabajo) : fin[1])}</Alert>}
        <div className="flex flex-wrap justify-end gap-2">
          {!trabajo && <Button color="secondary" size="sm" onPress={() => setAbierto(false)}>Cerrar</Button>}
          {!trabajo && <Button color="primary" size="sm" onPress={iniciar} isDisabled={enviando || (modo === "semana" && !lunes)}>{enviando ? "Iniciando…" : "Iniciar"}</Button>}
          {corriendo && <Button color="primary-destructive" size="sm" onPress={cancelar} isDisabled={cancelando}>{cancelando ? "Cancelando…" : "Cancelar"}</Button>}
          {fin && <Button color="primary" size="sm" onPress={() => setAbierto(false)}>{trabajo?.estado === "listo" ? "Ver cuadro" : "Cerrar"}</Button>}
        </div>
      </Ventana>
    </>
  );
}
