import { useState } from "react";
import { useNavigate } from "react-router";
import { cambios } from "../api/cambios";
import { ErrorApi } from "../api/cliente";
import type { Periodo } from "../api/tipos";
import { Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Input } from "@/components/base/input/input";
import { Alert } from "@/components/application/alerts/alert";

type Accion = "publicar" | "restaurar" | "cerrar" | "reabrir";
const TEXTO: Record<Accion, [string, string]> = {
  publicar: ["Publicar", "El cuadro actual pasará a ser el «original». ¿Continuar?"],
  restaurar: ["Restaurar", "Se devolverán todas las celdas al original. ¿Continuar?"],
  cerrar: ["Cerrar periodo", "Se guardarán las horas trabajadas y contratadas de cada persona en el banco de horas y el cuadro quedará en solo lectura. ¿Continuar?"],
  reabrir: ["Reabrir periodo", "El cuadro volverá a ser editable y se borrará el cierre de este periodo del banco de horas. ¿Continuar?"],
};

interface Props {
  area: number;
  periodo: Periodo | null; // null: el área no tiene periodos, solo se ofrece «Nuevo periodo»
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
  const cerrado = !!periodo?.cerrado_en;

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
        await cambios.accion(area, periodo!.id, periodo!.revision, accion);
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
      {!periodo ? null : cerrado ? <Button color="secondary" size="sm" onPress={() => abrir("reabrir")}>Reabrir</Button> : (
        <>
          <Button color="secondary" size="sm" onPress={() => abrir("publicar")}>Publicar</Button>
          <Button color="secondary" size="sm" onPress={() => abrir("restaurar")}>Restaurar</Button>
          <Button color="secondary" size="sm" onPress={() => abrir("cerrar")}>Cerrar periodo</Button>
        </>
      )}
      <Button color="secondary" size="sm" onPress={() => abrir("nuevo")}>Nuevo periodo</Button>
      <Ventana abierto={accion !== null} alCambiar={(a) => !a && setAccion(null)}
        titulo={accion === "nuevo" ? "Nuevo periodo" : accion ? TEXTO[accion][0] : ""}
        descripcion={accion === "nuevo" ? "Un periodo no puede compartir fechas con otro del área." : accion ? TEXTO[accion][1] : undefined}>
        {error && <Alert color="error">{error}</Alert>}
        {accion === "nuevo" && (
          <div className="flex flex-col gap-4">
            <Input value={String(inicio)} label="Desde" type="date" onChange={(x) => setInicio(x)} />
            <Input value={String(fin)} label="Hasta" type="date" onChange={(x) => setFin(x)} />
          </div>
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Button color="secondary" size="sm" onPress={() => setAccion(null)}>Cancelar</Button>
          <Button color="primary" size="sm" onPress={confirmar} isDisabled={enviando || (accion === "nuevo" && (!inicio || !fin))}>{enviando ? "Un momento…" : "Confirmar"}</Button>
        </div>
      </Ventana>
    </>
  );
}
