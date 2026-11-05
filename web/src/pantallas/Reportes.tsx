import { useState, type FC } from "react";
import { useNavigate, useOutletContext } from "react-router";
import { Building02, Calendar, Download01, FileDownload02, LineChartUp01, Printer } from "@untitledui/icons";
import { mensaje, usar } from "../api/catalogos";
import { exportes } from "../api/exportes";
import type { Area, Periodo, TipoExporte } from "../api/tipos";
import { Filtro, Pagina, Pista, useAccion } from "./comun";
import { nombrePeriodo, vigente } from "./fechas";
import { Button } from "@/components/base/buttons/button";

const TIPOS: [TipoExporte, string, string, FC<{ className?: string }>][] = [
  ["cuadro", "Cuadro de turnos", "La grilla del periodo con las horas de cada semana.", Calendar],
  ["puestos", "Puestos", "Quién está en cada puesto, día por día.", Building02],
  ["horas", "Horas y recargos", "Horas trabajadas, nocturnas, dominicales y festivas por persona.", LineChartUp01],
];

/** Descargas en Excel del periodo. Cada descarga genera el libro en el servidor y lo borra al bajarlo (como «Exportar» del cuadro). */
export function Reportes() {
  const area = useOutletContext<Area>();
  const ir = useNavigate();
  const periodos = usar<Periodo[]>(`/api/areas/${area.id}/periodos`);
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
      const a = Object.assign(document.createElement("a"), { href: exportes.urlDescarga(area.id, p.id, x.id), download: x.nombre_archivo });
      a.click();
      avisar({ nivel: "ok", texto: `Descargando ${x.nombre_archivo}.` });
    } catch (x) {
      avisar({ nivel: "error", texto: mensaje(x) });
    } finally {
      setHaciendo(null);
    }
  };

  return (
    <Pagina titulo="Reportes" icono={FileDownload02} sub="Descargas en Excel del periodo" error={periodos.error} aviso={aviso}
      filtros={periodos.datos && p && (
        <Filtro etiqueta="Periodo" icono={Calendar} value={p.id} onChange={(x) => setElegido(Number(x.target.value))}>
          {periodos.datos.map((q) => <option key={q.id} value={q.id}>{nombrePeriodo(q.clave)}</option>)}
        </Filtro>
      )}
      acciones={p && <Pista texto="Abre el cuadro de este periodo y la ventana de impresión."><Button color="secondary" size="sm" iconLeading={Printer} onPress={() => ir(`/areas/${area.id}/cuadro/${p.id}?imprimir=1`)}>Imprimir el cuadro</Button></Pista>}>
      {periodos.datos && !p && <p className="tarjeta p-5 text-tertiary">Aún no hay periodos.</p>}
      {p && (
        <div className="grid grid-cols-[repeat(auto-fit,minmax(260px,1fr))] gap-4">
          {TIPOS.map(([tipo, titulo, texto, Icono]) => (
            <section key={tipo} className="tarjeta flex flex-col items-start gap-3 p-5">
              <span className="grid size-12 place-items-center rounded-2xl bg-brand-50 text-brand-600 ring-1 ring-brand-100 ring-inset" aria-hidden="true"><Icono className="size-6" /></span>
              <h2 className="text-lg font-semibold text-primary">{titulo}</h2>
              <p className="flex-1 text-sm text-tertiary">{texto}</p>
              <Button color="secondary" size="sm" iconLeading={Download01} isDisabled={haciendo !== null} onPress={() => descargar(tipo)}>{haciendo === tipo ? "Preparando…" : "Descargar Excel"}</Button>
            </section>
          ))}
        </div>
      )}
    </Pagina>
  );
}
