import { createContext, useContext, useEffect, useState, type FC } from "react";
import { AlertTriangle, Bell01, CalendarMinus01, CheckCircle, Inbox01, XCircle } from "@untitledui/icons";
import { Button as AriaButton, Dialog, DialogTrigger, Link, Popover } from "react-aria-components";
import { leer } from "../api/cliente";
import type { Alerta, Area, Colaborador, EstadoSolicitud, Novedad, Periodo } from "../api/tipos";
import { fechaCorta, instante, isoHoy, nombrePeriodo, vigente } from "../pantallas/fechas";
import { Badge } from "@/components/base/badges/badges";
import { cx } from "@/utils/cx";

interface Aviso { id: string; icono: FC<{ className?: string }>; tono: keyof typeof TONO; titulo: string; sub: string; href: string }
interface Trabajo { id: number; periodo_id: number; estado: string; terminado: string | null }
export interface Avisos { avisos: Aviso[]; noCumplidas: number }

const TONO = { error: "text-fg-error-primary", brand: "text-brand-600", warning: "text-fg-warning-primary", success: "text-fg-success-primary" };
const Contexto = createContext<Avisos | null>(null);
export const ProveedorAvisos = Contexto.Provider;
export const useAvisos = () => useContext(Contexto);

/** Avisos calculados al vuelo (no hay tabla de notificaciones): alertas rojas y solicitudes no cumplidas del periodo vigente,
 *  ausencias que empiezan en los próximos 7 días y la última generación de las últimas 24 h. Se recalcula al cambiar de pantalla. */
export function useCargarAvisos(area: Area | undefined, clave: string): Avisos {
  const [e, setE] = useState<Avisos>({ avisos: [], noCumplidas: 0 });
  useEffect(() => {
    if (!area || area.tipo !== "turnos") return setE({ avisos: [], noCumplidas: 0 });
    let vivo = true;
    const b = `/api/areas/${area.id}`, r = `/areas/${area.id}`;
    (async () => {
      const p = vigente(await leer<Periodo[]>(`${b}/periodos`));
      const [alertas, sol, novs, colabs, trab] = await Promise.all([
        p ? leer<Alerta[]>(`${b}/periodos/${p.id}/alertas`) : [], p ? leer<EstadoSolicitud[]>(`${b}/periodos/${p.id}/solicitudes`) : [],
        leer<Novedad[]>(`${b}/novedades`), leer<Colaborador[]>(`${b}/colaboradores`), leer<Trabajo[]>(`${b}/trabajos?limite=1`)]);
      const avisos: Aviso[] = [];
      const errores = new Set(alertas.filter((a) => a.nivel === "error").map((a) => a.texto)).size;  // agrupadas, como la lista del cuadro
      if (p && errores) avisos.push({ id: "alertas", icono: AlertTriangle, tono: "error", titulo: `${errores} ${errores === 1 ? "alerta" : "alertas"} por corregir`, sub: `Cuadro ${nombrePeriodo(p.clave)}`, href: `${r}/cuadro/${p.id}` });
      const noCumplidas = sol.filter((s) => s.estado === "no cumplida").length;
      if (noCumplidas) avisos.push({ id: "solicitudes", icono: Inbox01, tono: "brand", titulo: `${noCumplidas} ${noCumplidas === 1 ? "solicitud no cumplida" : "solicitudes no cumplidas"}`, sub: "Ver solicitudes", href: `${r}/solicitudes` });
      const nombre = new Map(colabs.map((c) => [c.id, c.nombre]));
      const hoy = isoHoy(), en7 = isoHoy(7);
      for (const n of novs.filter((n) => n.desde >= hoy && n.desde <= en7).sort((x, y) => x.desde.localeCompare(y.desde)).slice(0, 3))
        avisos.push({ id: `nov${n.id}`, icono: CalendarMinus01, tono: "warning", titulo: `${n.tipo} desde el ${fechaCorta(n.desde)}`, sub: nombre.get(n.colab_id) ?? "", href: `${r}/novedades` });
      const t = trab[0];
      if (t?.terminado && Date.now() - instante(t.terminado).getTime() < 864e5 && t.estado !== "cancelado") {
        const ok = t.estado === "listo";
        avisos.push({ id: `trabajo${t.id}`, icono: ok ? CheckCircle : XCircle, tono: ok ? "success" : "error", titulo: ok ? "Generación terminada" : "La generación no se guardó",
          sub: instante(t.terminado).toLocaleTimeString("es-CO", { hour: "numeric", minute: "2-digit" }), href: `${r}/cuadro/${t.periodo_id}` });
      }
      if (vivo) setE({ avisos, noCumplidas });
    })().catch(() => undefined);  // la campana nunca bloquea la pantalla
    return () => { vivo = false; };
  }, [area?.id, area?.tipo, clave]); // eslint-disable-line react-hooks/exhaustive-deps
  return e;
}

/** Campana del encabezado: número de avisos y un panel con enlaces a cada uno. */
export function Campana() {
  const e = useAvisos();
  if (!e) return null;
  const n = e.avisos.length;
  return (
    <DialogTrigger>
      <AriaButton aria-label={n ? `Avisos: ${n}` : "Avisos: ninguno"}
        className="relative grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-fg-quaternary outline-focus-ring hover:bg-primary_hover hover:text-fg-quaternary_hover focus-visible:outline-2 focus-visible:outline-offset-2">
        <Bell01 aria-hidden="true" className="size-5" />
        {n > 0 && <span aria-hidden="true" className="absolute -top-1 -right-1.5 font-mono text-xs font-semibold text-brand-secondary">{n}</span>}
      </AriaButton>
      <Popover placement="bottom end" offset={8} className="w-[min(400px,calc(100vw-32px))] rounded-xl bg-primary p-2 shadow-lg ring-1 ring-secondary outline-hidden">
        <Dialog aria-label="Avisos" className="outline-hidden">
          {({ close }) => (
            <>
              <div className="flex items-center justify-between px-3 py-2">
                <h2 className="text-md font-semibold text-primary">Avisos</h2>
                {n > 0 && <Badge size="sm" color="error">{n}</Badge>}
              </div>
              {n === 0 ? <p className="px-3 pb-3 text-sm text-tertiary">Nada pendiente por ahora.</p> : (
                <ul>
                  {e.avisos.map((a) => (
                    <li key={a.id}>
                      <Link href={a.href} onPress={close} className="flex items-start gap-3 rounded-md p-3 outline-focus-ring hover:bg-primary_hover focus-visible:outline-2">
                        <a.icono aria-hidden="true" className={cx("mt-0.5 size-4.5 shrink-0", TONO[a.tono])} />
                        <span className="min-w-0"><span className="block text-sm font-semibold text-primary">{a.titulo}</span><span className="block text-xs text-tertiary">{a.sub}</span></span>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </>
          )}
        </Dialog>
      </Popover>
    </DialogTrigger>
  );
}
