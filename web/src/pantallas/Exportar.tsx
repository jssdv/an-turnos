import { useCallback, useEffect, useState } from "react";
import { exportes } from "../api/exportes";
import { ErrorApi } from "../api/cliente";
import type { Exporte, TipoExporte } from "../api/tipos";
import { Ventana } from "./comun";
import { Button } from "@/components/base/buttons/button";
import { Alert } from "@/components/application/alerts/alert";

const TIPOS: [TipoExporte, string][] = [["cuadro", "Cuadro"], ["puestos", "Puestos"], ["horas", "Horas y recargos"]];
const tamano = (b: number) => (b < 1024 * 1024 ? `${Math.max(1, Math.round(b / 1024))} KB` : `${(b / 1024 / 1024).toFixed(1)} MB`);

interface Props {
  area: number;
  periodo: number;
  /** Sin cuadro no hay nada que exportar. */
  hayCuadro: boolean;
}

/** Botón «Exportar»: genera el libro en el servidor (nunca sobrescribe: v2, v3…) y lista los ya generados con su descarga. Basta con poder ver el área. */
export function Exportar({ area, periodo, hayCuadro }: Props) {
  const [abierto, setAbierto] = useState(false);
  const [lista, setLista] = useState<Exporte[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [haciendo, setHaciendo] = useState<TipoExporte | null>(null);
  const [nuevo, setNuevo] = useState<string | null>(null);

  const cargar = useCallback(() => {
    exportes.listar(area, periodo).then(setLista).catch((x) => setError(x.message));
  }, [area, periodo]);
  useEffect(() => { if (abierto) { setError(null); setNuevo(null); cargar(); } }, [abierto, cargar]);

  const crear = async (tipo: TipoExporte) => {
    setHaciendo(tipo);
    setError(null);
    setNuevo(null);
    try {
      const x = await exportes.crear(area, periodo, tipo);
      setNuevo(x.nombre_archivo);
      cargar();
    } catch (x) {
      setError(x instanceof ErrorApi ? x.message : "No se pudo generar el exporte");
    } finally {
      setHaciendo(null);
    }
  };

  return (
    <>
      <Button color="secondary" size="sm" onPress={() => setAbierto(true)}>Exportar</Button>
      <Ventana abierto={abierto} alCambiar={setAbierto} titulo="Exportar a Excel"
        descripcion="Cada exportación crea un archivo nuevo; los anteriores se conservan y se pueden volver a descargar.">
        {error && <Alert color="error">{error}</Alert>}
        {nuevo && <Alert color="success">Listo: {nuevo}</Alert>}
        <div className="flex flex-wrap gap-2">
          {TIPOS.map(([tipo, titulo]) => (
            <Button color="primary" size="sm" key={tipo} isDisabled={!hayCuadro || haciendo !== null} onPress={() => crear(tipo)}>
              {haciendo === tipo ? "Generando…" : titulo}
            </Button>
          ))}
        </div>
        {!hayCuadro && <p className="text-tertiary">Este periodo no tiene cuadro todavía.</p>}
        {lista && (lista.length === 0 ? <p className="text-tertiary">Aún no hay exportes de este periodo.</p> : (
          <ul className="max-h-[260px] overflow-auto" aria-label="Exportes anteriores">
            {lista.map((x) => (
              <li key={x.id} className="flex items-center justify-between gap-3 border-t border-secondary py-2 first:border-t-0">
                <div>
                  <div className="font-semibold break-words text-primary">{x.nombre_archivo}</div>
                  <div className="text-xs text-tertiary">{tamano(x.bytes)} · {x.creado_por ?? "—"} · {new Date(x.creado).toLocaleString("es-CO")}</div>
                </div>
                <a href={exportes.urlDescarga(area, periodo, x.id)} download={x.nombre_archivo}>Descargar</a>
              </li>
            ))}
          </ul>
        ))}
        <div className="flex justify-end"><Button color="secondary" size="sm" onPress={() => setAbierto(false)}>Cerrar</Button></div>
      </Ventana>
    </>
  );
}
