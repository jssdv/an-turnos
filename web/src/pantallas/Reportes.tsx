import { useState, type FC, type ReactNode } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { Building02, Calendar, CalendarDate, Clock, Copy01, Download01, LineChartUp01, Printer } from "@untitledui/icons";
import { aHHMM, mensaje, usar } from "../api/catalogos";
import { leer } from "../api/cliente";
import { exportes } from "../api/exportes";
import type { Area, Colaborador, Cuadro, Periodo, TipoExporte, Turno } from "../api/tipos";
import { Filtro, Pagina, Pista, Seccion, useAccion, Vacio } from "./comun";
import { fechaCorta, nombrePeriodo, vigente } from "./fechas";
import { Button } from "@/components/base/buttons/button";

const TIPOS: [TipoExporte, string, string, Icono][] = [
  ["cuadro", "Cuadro de turnos", "La grilla del periodo con las horas de cada semana.", Calendar],
  ["puestos", "Puestos", "Quién está en cada puesto, día por día.", Building02],
  ["horas", "Horas y recargos", "Horas trabajadas, nocturnas, dominicales y festivas por persona.", LineChartUp01],
];

type Icono = FC<{ className?: string }>;

/** Tarjeta de una descarga: los botones quedan abajo, alineados entre tarjetas de la misma fila. */
const Tarjeta = ({ icono: I, titulo, texto, children }: { icono: Icono; titulo: string; texto: string; children: ReactNode }) => (
  <Seccion className="flex flex-col" titulo={<><I aria-hidden="true" className="size-5 text-fg-quaternary" />{titulo}</>} descripcion={texto}>
    <div className="mt-auto flex flex-col items-start gap-3">{children}</div>
  </Seccion>
);

/** Descargas en Excel del periodo. Cada descarga genera el libro en el servidor y lo borra al bajarlo (como «Exportar» del cuadro). */
export function Reportes() {
  const area = useOutletContext<Area>();
  const ir = useNavigate();
  const periodos = usar<Periodo[]>(`/api/areas/${area.id}/periodos`);
  const gente = usar<Colaborador[]>(`/api/areas/${area.id}/colaboradores`);
  const [quien, setQuien] = useState("");
  const [elegido, setElegido] = useState<number | null>(null);
  const [haciendo, setHaciendo] = useState<TipoExporte | null>(null);
  const { aviso, avisar } = useAccion();
  const p = periodos.datos?.find((x) => x.id === elegido) ?? (periodos.datos ? vigente(periodos.datos) : null);

  const descargar = async (tipo: TipoExporte) => {
    if (!p) return;
    setHaciendo(tipo);
    avisar(null);
    try {
      const x = await exportes.crear(area.id, p.id, tipo);
      bajar(exportes.urlDescarga(area.id, p.id, x.id));
      avisar({ nivel: "ok", texto: `Descargando ${x.nombre_archivo}.` });
    } catch (x) {
      avisar({ nivel: "error", texto: mensaje(x) });
    } finally {
      setHaciendo(null);
    }
  };

  // Horario de una persona en texto, para mandarlo por WhatsApp: el cuadro suele vivir en la cartelera y no en el teléfono.
  const copiarHorario = async () => {
    if (!p || !quien) return;
    try {
      const [cuadro, turnos] = await Promise.all([leer<Cuadro>(`/api/areas/${area.id}/periodos/${p.id}/cuadro?version=cambios`), leer<Turno[]>(`/api/areas/${area.id}/turnos`)]);
      const t = new Map(turnos.map((x) => [x.codigo, x]));
      const dias = cuadro.celdas.filter((c) => String(c.colab_id) === quien && c.turno !== "L").sort((a, b) => a.fecha.localeCompare(b.fecha));
      const nombre = gente.datos?.find((c) => String(c.id) === quien)?.nombre ?? "";
      const texto = [`Horario de ${nombre} · ${nombrePeriodo(p.clave)}`, "",
        ...dias.map((c) => { const x = t.get(c.turno); return `${fechaCorta(c.fecha)}: ${x ? `${x.nombre} (${aHHMM(x.inicio)} a ${aHHMM(x.fin)})` : c.turno}`; }),
        "", dias.length ? "Los demás días: libre." : "Sin turnos en este periodo."].join("\n");
      await navigator.clipboard.writeText(texto);
      avisar({ nivel: "ok", texto: `Horario de ${nombre} copiado (${dias.length} turnos). Pégalo en su chat.` });
    } catch (x) {
      avisar({ nivel: "error", texto: mensaje(x, "No se pudo copiar el horario.") });
    }
  };

  // Enlace normal, no de React Aria: su RouterProvider llevaría /api/... por react-router.
  const bajar = (href: string) => Object.assign(document.createElement("a"), { href, download: "" }).click();

  return (
    <Pagina titulo="Reportes" sub="Descargas en Excel del periodo" error={periodos.error} aviso={aviso}
      filtros={periodos.datos && p && (
        <Filtro etiqueta="Periodo" icono={Calendar} value={p.id} onChange={(x) => setElegido(Number(x.target.value))}>
          {periodos.datos.map((q) => <option key={q.id} value={q.id}>{nombrePeriodo(q.clave)}</option>)}
        </Filtro>
      )}
      acciones={p && <>
        <Pista texto="Abre el cuadro de este periodo y la ventana de impresión."><Button color="secondary" size="sm" iconLeading={Printer} onPress={() => ir(`/areas/${area.id}/cuadro/${p.id}?imprimir=1`)}>Imprimir el cuadro</Button></Pista>
        <Pista texto="Los cinco Excel de este periodo (cuadro, puestos, horas, banco y analíticas) en un solo .zip, para archivar o mandar a RR. HH."><Button color="primary" size="sm" iconLeading={Download01} onPress={() => bajar(exportes.urlReportes(area.id, p.id))}>Todo el periodo (.zip)</Button></Pista>
      </>}>
      {periodos.datos && !p && <Vacio className="tarjeta">Aún no hay periodos.</Vacio>}
      {p && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-4">
          {TIPOS.map(([tipo, titulo, texto, Icono]) => (
            <Tarjeta key={tipo} icono={Icono} titulo={titulo} texto={texto}>
              <Button color="secondary" size="sm" iconLeading={Download01} isDisabled={haciendo !== null} onPress={() => descargar(tipo)}>{haciendo === tipo ? "Preparando…" : "Descargar Excel"}</Button>
            </Tarjeta>
          ))}
          <Tarjeta icono={Clock} titulo="Banco de horas" texto="Saldo de horas por persona y movimientos manuales.">
            <Button color="secondary" size="sm" iconLeading={Download01} onPress={() => bajar(exportes.urlBanco(area.id, p.id))}>Descargar Excel</Button>
          </Tarjeta>
          <Tarjeta icono={LineChartUp01} titulo="Analíticas" texto="Resumen para gerencia o RR. HH. de este periodo: ausentismo, cobertura, estabilidad, fatiga y patrones. Para otro rango, descárgalo desde Analíticas.">
            <Button color="secondary" size="sm" iconLeading={Download01} onPress={() => bajar(exportes.urlAnaliticas(area.id, ...(p.clave.split("/") as [string, string])))}>Descargar Excel</Button>
          </Tarjeta>
          <Tarjeta icono={CalendarDate} titulo="Agendas" texto="El horario de cada persona para su calendario (.ics), para imprimir o en texto para su chat.">
            <Button color="secondary" size="sm" iconLeading={Download01} onPress={() => bajar(exportes.urlAgendas(area.id, p.id))}>Todas (.zip)</Button>
            <Filtro etiqueta="Persona" className="w-full" value={quien} onChange={(x) => setQuien(x.target.value)}>
              <option value="">Elige una persona…</option>
              {gente.datos?.filter((c) => c.activo).map((c) => <option key={c.id} value={c.id}>{c.nombre}</option>)}
            </Filtro>
            <div className="flex flex-wrap gap-2">
              <Button color="secondary" size="sm" iconLeading={Download01} isDisabled={!quien} onPress={() => bajar(exportes.urlAgenda(area.id, p.id, Number(quien)))}>Su calendario</Button>
              <Button color="secondary" size="sm" iconLeading={Printer} isDisabled={!quien} onPress={() => ir(`/areas/${area.id}/cuadro/${p.id}?imprimir=1&persona=${quien}`)}>Imprimir su horario</Button>
              <Button color="secondary" size="sm" iconLeading={Copy01} isDisabled={!quien} onPress={() => void copiarHorario()}>Copiar su horario</Button>
            </div>
          </Tarjeta>
        </div>
      )}
    </Pagina>
  );
}
