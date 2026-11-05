import { useState } from "react";
import { useNavigate } from "react-router";
import { cambios } from "../api/cambios";
import { ErrorApi } from "../api/cliente";
import type { Periodo } from "../api/tipos";
import { CalendarPlus01, Lock01, LockUnlocked01, RefreshCcw01, Send01, SwitchHorizontal01, Trash01 } from "@untitledui/icons";
import { Pista, Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { CampoFecha } from "../componentes/CampoFecha";
import { Alert } from "@/components/application/alerts/alert";

type Accion = "publicar" | "restaurar" | "cerrar" | "reabrir" | "eliminar" | "reasignar";
const TEXTO: Record<Accion, [string, string]> = {
  publicar: ["Publicar", "El cuadro actual será el original que ve el equipo."],
  restaurar: ["Restaurar", "Descarta tus cambios y vuelve al original."],
  cerrar: ["Cerrar periodo", "Las horas pasan al banco de horas y el cuadro queda de solo lectura."],
  reabrir: ["Reabrir periodo", "El cuadro vuelve a ser editable y se borra su cierre del banco de horas."],
  reasignar: ["Reasignar puestos", "Reparte de nuevo solo los puestos. Los turnos y los puestos fijados no cambian. Opcional: desde una fecha."],
  eliminar: ["Eliminar periodo", "Se borran el cuadro, los puestos, los cambios y los exportes. No se puede deshacer."],
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
  const [desde, setDesde] = useState("");
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
      } else if (accion === "reasignar") {
        await cambios.reasignarPuestos(area, periodo!.id, periodo!.revision, desde || null);
        setAccion(null);
        alTerminar();
      } else if (accion === "eliminar") {
        await cambios.eliminarPeriodo(area, periodo!.id, periodo!.revision);
        setAccion(null);
        alTerminar();
        ir(`/areas/${area}/cuadro`); // sin periodo en la URL: Cuadro muestra el último
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
      {!periodo ? null : cerrado ? <Pista texto={TEXTO.reabrir[1]}><Button color="secondary" size="sm" iconLeading={LockUnlocked01} onPress={() => abrir("reabrir")}>Reabrir</Button></Pista> : (
        <>
          <Pista texto={TEXTO.reasignar[1]}><Button color="secondary" size="sm" iconLeading={SwitchHorizontal01} onPress={() => abrir("reasignar")}>Reasignar puestos</Button></Pista>
          <Pista texto={TEXTO.publicar[1]}><Button color="secondary" size="sm" iconLeading={Send01} onPress={() => abrir("publicar")} data-accion="publicar">Publicar</Button></Pista>
          <Pista texto={TEXTO.cerrar[1]}><Button color="secondary" size="sm" iconLeading={Lock01} onPress={() => abrir("cerrar")}>Cerrar periodo</Button></Pista>
        </>
      )}
      <Pista texto="Crea el siguiente periodo: elige desde y hasta."><Button color={periodo ? "secondary" : "primary"} size="sm" iconLeading={CalendarPlus01} onPress={() => abrir("nuevo")}>Nuevo periodo</Button></Pista>
      {periodo && !cerrado && (
        <>
          <Pista texto={TEXTO.restaurar[1]}><Button color="secondary-destructive" size="sm" iconLeading={RefreshCcw01} onPress={() => abrir("restaurar")}>Restaurar</Button></Pista>
          <Pista texto={TEXTO.eliminar[1]}><Button color="secondary-destructive" size="sm" iconLeading={Trash01} onPress={() => abrir("eliminar")}>Eliminar periodo</Button></Pista>
        </>
      )}
      <Ventana abierto={accion !== null} alCambiar={(a) => !a && setAccion(null)}
        titulo={accion === "nuevo" ? "Nuevo periodo" : accion ? TEXTO[accion][0] : ""}
        descripcion={accion === "nuevo" ? "Un periodo no puede compartir fechas con otro del área." : accion ? TEXTO[accion][1] : undefined}>
        {error && <Alert color="error">{error}</Alert>}
        {accion === "nuevo" && (
          <div className="flex flex-col gap-4">
            <CampoFecha value={inicio} label="Desde" onChange={(x) => setInicio(x)} />
            <CampoFecha value={fin} label="Hasta" onChange={(x) => setFin(x)} />
          </div>
        )}
        {accion === "reasignar" && periodo && (
          <CampoFecha value={desde} label="Desde (opcional)" onChange={(x) => setDesde(x)} />
        )}
        <div className="flex flex-wrap justify-end gap-2">
          <Button color="secondary" size="sm" onPress={() => setAccion(null)}>Cancelar</Button>
          <Button color={accion === "eliminar" || accion === "restaurar" ? "primary-destructive" : "primary"} size="sm" onPress={confirmar} isDisabled={enviando || (accion === "nuevo" && (!inicio || !fin))}>{enviando ? "Un momento…" : accion === "nuevo" ? "Crear" : accion ? TEXTO[accion][0] : "Confirmar"}</Button>
        </div>
      </Ventana>
    </>
  );
}
