import { useEffect, useRef, useState } from "react";
import { ErrorApi } from "../api/cliente";
import type { PedidoGenerar, Periodo, Trabajo } from "../api/tipos";
import { trabajos, trabajosSimulados } from "../api/trabajos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Seleccion, Campo } from "../componentes/Campo";
import { Dialogo } from "../componentes/Dialogo";
import { Progreso } from "../componentes/Progreso";
import e from "./Generar.module.css";

const CADA_MS = 1500;
const TERMINALES = new Set(["listo", "fallido", "cancelado", "conflicto"]);
const MENSAJE: Record<string, [("ok" | "aviso" | "error"), string]> = {
  listo: ["ok", "Cuadro generado. Ya puedes revisarlo."],
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
  const [modo, setModo] = useState<PedidoGenerar["modo"]>("mes");
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
      setError(x instanceof ErrorApi ? (x.estado === 409 ? `${x.message}. Recarga el cuadro e inténtalo de nuevo.` : x.message) : "No se pudo iniciar");
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
      <Boton variante="primario" onClick={abrir} disabled={bloqueado} title={bloqueado ? "El periodo está cerrado" : undefined}>Generar</Boton>
      <Dialogo
        abierto={abierto}
        alCambiar={setAbierto}
        bloqueado={corriendo}
        titulo="Generar cuadro"
        descripcion="Calcula un cuadro nuevo con las reglas actuales. Las celdas editadas a mano se conservan."
      >
        {trabajosSimulados && <Aviso>Modo simulado: el servidor aún no tiene las rutas de generación.</Aviso>}
        {error && <Aviso nivel="error">{error}</Aviso>}
        {!trabajo && (
          <div className={e.form}>
            <Seleccion etiqueta="Alcance" value={modo} onChange={(x) => setModo(x.target.value as PedidoGenerar["modo"])}>
              <option value="mes">Mes completo</option>
              <option value="semana">Una semana</option>
            </Seleccion>
            {modo === "semana" && <Campo etiqueta="Lunes de la semana" type="date" value={lunes} onChange={(x) => setLunes(x.target.value)} />}
          </div>
        )}
        {trabajo && !fin && (
          <Progreso
            valor={p ? p.segundos / p.limite : 0}
            etiqueta={trabajo.estado === "en_cola" ? "En cola…" : "Generando…"}
            detalle={p ? `${Math.round(p.segundos)} s de ${p.limite} s · ${p.soluciones} soluciones${p.objetivo !== null ? ` · objetivo ${p.objetivo}` : ""}` : "Esperando turno del servidor"}
          />
        )}
        {fin && <Aviso nivel={fin[0]}>{trabajo?.error ?? fin[1]}</Aviso>}
        <div className={e.fila}>
          {!trabajo && <Boton onClick={() => setAbierto(false)}>Cerrar</Boton>}
          {!trabajo && <Boton variante="primario" onClick={iniciar} disabled={enviando || (modo === "semana" && !lunes)}>{enviando ? "Iniciando…" : "Iniciar"}</Boton>}
          {corriendo && <Boton variante="peligro" onClick={cancelar} disabled={cancelando}>{cancelando ? "Cancelando…" : "Cancelar"}</Boton>}
          {fin && <Boton variante="primario" onClick={() => setAbierto(false)}>{trabajo?.estado === "listo" ? "Ver cuadro" : "Cerrar"}</Boton>}
        </div>
      </Dialogo>
    </>
  );
}
