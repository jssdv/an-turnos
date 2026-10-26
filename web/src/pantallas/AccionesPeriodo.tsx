import { useState } from "react";
import { useNavigate } from "react-router";
import { cambios } from "../api/cambios";
import { ErrorApi } from "../api/cliente";
import type { Periodo } from "../api/tipos";
import { Aviso } from "../componentes/Aviso";
import { Boton } from "../componentes/Boton";
import { Campo } from "../componentes/Campo";
import { Dialogo } from "../componentes/Dialogo";
import e from "./Generar.module.css";

type Accion = "publicar" | "restaurar" | "cerrar" | "reabrir";
const TEXTO: Record<Accion, [string, string]> = {
  publicar: ["Publicar", "El cuadro actual pasará a ser el «original». ¿Continuar?"],
  restaurar: ["Restaurar", "Se devolverán todas las celdas al original. ¿Continuar?"],
  cerrar: ["Cerrar periodo", "Se guardarán las horas trabajadas y contratadas de cada persona en el banco de horas y el cuadro quedará en solo lectura. ¿Continuar?"],
  reabrir: ["Reabrir periodo", "El cuadro volverá a ser editable y se borrará el cierre de este periodo del banco de horas. ¿Continuar?"],
};

interface Props {
  area: number;
  periodo: Periodo;
  alTerminar: () => void;
}

/** Publicar, Restaurar, Cerrar/Reabrir y Nuevo periodo, cada uno con su confirmación. Solo se muestra a quien edita. */
export function AccionesPeriodo({ area, periodo, alTerminar }: Props) {
  const ir = useNavigate();
  const [accion, setAccion] = useState<Accion | "nuevo" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);
  const [inicio, setInicio] = useState("");
  const [fin, setFin] = useState("");
  const cerrado = !!periodo.cerrado_en;

  const abrir = (a: Accion | "nuevo") => { setError(null); setAccion(a); };
  const confirmar = async () => {
    if (!accion) return;
    setEnviando(true);
    setError(null);
    try {
      if (accion === "nuevo") {
        const r = await cambios.crearPeriodo(area, inicio, fin);
        setAccion(null);
        alTerminar();
        ir(`/areas/${area}/cuadro/${r.id}`);
      } else {
        await cambios.accion(area, periodo.id, periodo.revision, accion);
        setAccion(null);
        alTerminar();
      }
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo completar la operación");
      if (x instanceof ErrorApi && x.estado === 409) alTerminar(); // tal vez la revisión cambió: se recarga para tener la vigente
    } finally {
      setEnviando(false);
    }
  };

  return (
    <>
      {cerrado ? <Boton onClick={() => abrir("reabrir")}>Reabrir</Boton> : (
        <>
          <Boton onClick={() => abrir("publicar")}>Publicar</Boton>
          <Boton onClick={() => abrir("restaurar")}>Restaurar</Boton>
          <Boton onClick={() => abrir("cerrar")}>Cerrar periodo</Boton>
        </>
      )}
      <Boton onClick={() => abrir("nuevo")}>Nuevo periodo</Boton>
      <Dialogo abierto={accion !== null} alCambiar={(a) => !a && setAccion(null)}
        titulo={accion === "nuevo" ? "Nuevo periodo" : accion ? TEXTO[accion][0] : ""}
        descripcion={accion === "nuevo" ? "Un periodo no puede compartir fechas con otro del área." : accion ? TEXTO[accion][1] : undefined}>
        {error && <Aviso nivel="error">{error}</Aviso>}
        {accion === "nuevo" && (
          <div className={e.form}>
            <Campo etiqueta="Desde" type="date" value={inicio} onChange={(x) => setInicio(x.target.value)} />
            <Campo etiqueta="Hasta" type="date" value={fin} onChange={(x) => setFin(x.target.value)} />
          </div>
        )}
        <div className={e.fila}>
          <Boton onClick={() => setAccion(null)}>Cancelar</Boton>
          <Boton variante="primario" onClick={confirmar} disabled={enviando || (accion === "nuevo" && (!inicio || !fin))}>{enviando ? "Un momento…" : "Confirmar"}</Boton>
        </div>
      </Dialogo>
    </>
  );
}
