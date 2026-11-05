import { useState } from "react";
import { AlertTriangle, CalendarPlus01, ChevronLeft, ChevronRight, FileDownload02, Send01, Stars02, SwitchHorizontal01 } from "@untitledui/icons";
import { Ventana } from "../pantallas/comun";
import { Button } from "@/components/base/buttons/button";
import { cx } from "@/utils/cx";

const PASOS = [
  { icono: CalendarPlus01, boton: "Nuevo periodo", titulo: "Crear el periodo", texto: "En «Cuadro de turnos» pulsa «Nuevo periodo» y elige desde y hasta. Un periodo no comparte fechas con otro." },
  { icono: Stars02, boton: "Generar", titulo: "Generar el cuadro", texto: "Pulsa «Generar». En unos segundos el sistema arma el cuadro respetando reglas, ausencias y solicitudes." },
  { icono: AlertTriangle, boton: "Ver alertas", titulo: "Revisar las alertas", texto: "Corrige primero las rojas; las amarillas son recomendaciones. «Ir a la celda» te lleva al problema." },
  { icono: SwitchHorizontal01, boton: "Doble clic", titulo: "Ajustar a mano", texto: "Doble clic en una celda para cambiar su turno o puesto; arrastra una sobre otra para intercambiarlas. Cada cambio queda registrado y se puede anular." },
  { icono: Send01, boton: "Publicar", titulo: "Publicar", texto: "Al publicar, el equipo ve esa versión como la oficial. Lo que cambies después queda en «Cambios (vigente)»." },
  { icono: FileDownload02, boton: "Descargar Excel", titulo: "Descargar", texto: "En «Reportes» descargas el cuadro, los puestos y las horas en Excel, o imprimes el cuadro." },
];

/** Guía de seis pasos: la abren «Ver tutorial» de la barra lateral y el botón flotante de ayuda. */
export function Tutorial({ abierto, alCambiar }: { abierto: boolean; alCambiar: (a: boolean) => void }) {
  const [i, setI] = useState(0);
  const p = PASOS[i];
  const cambiar = (a: boolean) => { if (!a) setI(0); alCambiar(a); };
  return (
    <Ventana abierto={abierto} alCambiar={cambiar} titulo={`Paso ${i + 1} de ${PASOS.length} · ${p.titulo}`}>
      <div className="grid h-44 place-items-center rounded-2xl bg-linear-to-br from-brand-50 to-fondo-2" aria-hidden="true">
        <span className="flex items-center gap-2 rounded-xl bg-linear-to-b from-brand-600 to-brand-700 px-4 py-2.5 text-sm font-semibold text-white shadow-md"><p.icono className="size-5" />{p.boton}</span>
      </div>
      <p className="text-md text-secondary" aria-live="polite">{p.texto}</p>
      <div className="flex flex-wrap items-center gap-2">
        <span className="mr-auto flex gap-1.5" aria-hidden="true">{PASOS.map((_, j) => <span key={j} className={cx("size-2 rounded-full", j === i ? "bg-brand-600" : "bg-quaternary")} />)}</span>
        <Button color="secondary" size="sm" iconLeading={ChevronLeft} isDisabled={i === 0} onPress={() => setI(i - 1)}>Anterior</Button>
        {i < PASOS.length - 1
          ? <Button color="primary" size="sm" iconTrailing={ChevronRight} onPress={() => setI(i + 1)}>Siguiente</Button>
          : <Button color="primary" size="sm" onPress={() => cambiar(false)}>Listo</Button>}
      </div>
    </Ventana>
  );
}
