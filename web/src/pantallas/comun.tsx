import { useState, type FC, type HTMLAttributes, type ReactElement, type ReactNode, type SelectHTMLAttributes } from "react";
import { Check, ChevronDown, ChevronRight, HelpCircle } from "@untitledui/icons";
import { cx } from "@/utils/cx";
import { mensaje } from "../api/catalogos";
import type { Alerta } from "../api/tipos";
import { Campana } from "../componentes/Avisos";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { Tooltip } from "@/components/base/tooltip/tooltip";

type Icono = FC<{ className?: string }>;

/** Encabezado de pantalla en tarjeta: ícono, título y estado a la izquierda; filtros y campana a la derecha; acciones debajo
 *  (la principal primero, las destructivas al final). Luego ayuda, avisos y el contenido. Es el mismo orden en todas las pantallas. */
export function Pagina({ titulo, sub, icono: Icono, estado, filtros, acciones, ayuda, error, aviso, children }: {
  titulo: ReactNode; sub?: ReactNode; icono?: Icono; estado?: ReactNode; filtros?: ReactNode; acciones?: ReactNode;
  ayuda?: ReactNode; error?: string | null; aviso?: { nivel: "ok" | "aviso" | "error"; texto: string } | null; children: ReactNode;
}) {
  return (
    <div className="flex max-w-[1500px] flex-col gap-4">
      <header className="tarjeta flex flex-col gap-4 p-4 sm:p-5">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex min-w-0 flex-1 basis-64 items-center gap-3">
            {Icono && (
              <span className="grid size-11 shrink-0 place-items-center rounded-xl bg-brand-50 text-brand-600 ring-1 ring-brand-100 ring-inset" aria-hidden="true">
                <Icono className="size-5.5" />
              </span>
            )}
            <div className="min-w-0">
              <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1"><h1 className="text-xl font-semibold text-primary">{titulo}</h1>{estado}</div>
              {sub && <p className="mt-0.5 text-sm text-tertiary">{sub}</p>}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2.5" data-no-imprimir>{filtros}<span className="hidden lg:contents"><Campana /></span></div>
        </div>
        {acciones && <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Acciones" data-no-imprimir>{acciones}</div>}
      </header>
      {ayuda && <Ayuda clave={String(titulo)}>{ayuda}</Ayuda>}
      {error && <Alert color="error">{error}</Alert>}
      {aviso && <div role="status" aria-live="polite"><Alert color={COLOR_NIVEL[aviso.nivel]}>{aviso.texto}</Alert></div>}
      {children}
    </div>
  );
}

/** Bloque de contenido en tarjeta blanca, con título y acciones a la derecha. */
export function Seccion({ titulo, acciones, children, className, ...r }: { titulo?: ReactNode; acciones?: ReactNode } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={cx("tarjeta p-4 sm:p-5", className)} {...r}>
      {(titulo || acciones) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">{titulo}</h2>
          {acciones}
        </header>
      )}
      {children}
    </section>
  );
}

/** Texto informativo al pasar el mouse o al llegar con el teclado. El hijo debe ser un `Button` (de React Aria). */
export const Pista = ({ texto, children }: { texto?: string; children: ReactElement }) =>
  texto ? <Tooltip title={texto} placement="bottom" arrow delay={400}>{children}</Tooltip> : children;

/** Lista en píldora para el encabezado (periodo, versión, persona…). La etiqueta queda para lectores de pantalla. */
export function Filtro({ etiqueta, icono: Icono, className, children, ...r }: { etiqueta: string; icono?: Icono } & Omit<SelectHTMLAttributes<HTMLSelectElement>, "size">) {
  return (
    <div className={cx("relative", className)}>
      {Icono && <Icono aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 z-10 size-4.5 -translate-y-1/2 text-fg-quaternary" />}
      <NativeSelect size="sm" label={etiqueta} className="[&_label]:sr-only" selectClassName={cx("h-10 rounded-xl pr-9 shadow-xs", Icono && "pl-9")} {...r}>{children}</NativeSelect>
    </div>
  );
}

/** Lleva a una sección de la página y enfoca su primer campo (botones del encabezado como «Nueva solicitud»). */
export const irA = (id: string) => {
  const el = document.getElementById(id);
  el?.scrollIntoView({ behavior: "smooth", block: "start" });
  el?.querySelector<HTMLElement>("input, select, textarea")?.focus({ preventScroll: true });
};

const recordar = (clave: string, abierta?: boolean) => {
  try {
    if (abierta === undefined) return localStorage.getItem(clave) === "abierta";
    localStorage.setItem(clave, abierta ? "abierta" : "cerrada");
  } catch { /* almacenamiento bloqueado: se muestra plegada */ }
  return false;
};

/** Recuadro «¿Cómo se usa?». Plegado por defecto (como el diseño); si se abre, este navegador lo recuerda. */
export function Ayuda({ titulo = "¿Cómo se usa esta sección?", clave, children }: { titulo?: string; clave: string; children: ReactNode }) {
  const [abierta] = useState(() => recordar(`ayuda2/${clave}`));
  return (
    <details className="group tarjeta px-4 py-3 text-sm sm:px-5 text-secondary" open={abierta} data-no-imprimir
      onToggle={(x) => recordar(`ayuda2/${clave}`, x.currentTarget.open)}>
      <summary className="flex cursor-pointer list-none items-center gap-3 font-semibold text-primary">
        <HelpCircle aria-hidden="true" className="size-5 shrink-0 text-brand-600" />{titulo}
        <span className="ml-auto flex items-center gap-1 text-sm font-semibold text-brand-secondary">
          <span className="group-open:hidden">Mostrar</span><span className="hidden group-open:inline">Ocultar</span>
          <ChevronDown aria-hidden="true" className="size-4 group-open:rotate-180" />
        </span>
      </summary>
      <div className="mt-2 ml-8 max-w-[80ch] leading-relaxed">{children}</div>
    </details>
  );
}

/** Estado de una acción que guarda: ocupado + aviso con el mensaje de la API si falla. */
export function useAccion() {
  const [ocupado, setOcupado] = useState(false);
  const [aviso, setAviso] = useState<{ nivel: "ok" | "aviso" | "error"; texto: string } | null>(null);
  const hacer = async (f: () => Promise<string | void>) => {
    setOcupado(true);
    setAviso(null);
    try {
      const t = await f();
      if (t) setAviso({ nivel: "ok", texto: t });
      return true;
    } catch (x) {
      setAviso({ nivel: "error", texto: mensaje(x) });
      return false;
    } finally {
      setOcupado(false);
    }
  };
  return { ocupado, aviso, hacer, avisar: setAviso };
}

/** Grilla de campos que se reacomoda sola: columnas de al menos 200 px. */
export const Formulario = ({ children, ...r }: React.FormHTMLAttributes<HTMLFormElement>) => (
  <form className="grid grid-cols-[repeat(auto-fill,minmax(200px,1fr))] items-start gap-4" {...r}>{children}</form>
);
/** Fila de botones o casillas a lo ancho del formulario. */
export const Fila = ({ children }: { children: ReactNode }) => <div className="col-span-full flex flex-wrap items-center gap-3 in-[[role=dialog]]:justify-end">{children}</div>;
/** Grupo de casillas con leyenda, a lo ancho del formulario. */
export const Grupo = ({ leyenda, children }: { leyenda: string; children: ReactNode }) => (
  <fieldset className="col-span-full flex flex-wrap gap-x-5 gap-y-2">
    <legend className="mb-2 text-sm font-medium text-secondary">{leyenda}</legend>
    {children}
  </fieldset>
);

/** Ventana modal con título: Untitled UI trae solo las piezas (fondo, caja, diálogo); el título y el relleno van aquí.
 * `bloqueado`: un trabajo en marcha no se cierra con Escape ni con un clic fuera. */
export function Ventana({ abierto, alCambiar, titulo, descripcion, bloqueado, ancha, children }: { abierto: boolean; alCambiar: (abierto: boolean) => void; titulo: string; descripcion?: string; bloqueado?: boolean; ancha?: boolean; children: ReactNode }) {
  return (
    <ModalOverlay isOpen={abierto} onOpenChange={alCambiar} isDismissable={!bloqueado} isKeyboardDismissDisabled={bloqueado}>
      <Modal className={ancha ? "max-w-3xl" : "max-w-xl"}>
        <Dialog className="flex flex-col gap-4 p-4 sm:p-6">
          <div>
            <h2 slot="title" className="text-lg font-semibold text-primary">{titulo}</h2>
            {descripcion && <p className="mt-1 text-sm text-tertiary">{descripcion}</p>}
          </div>
          {children}
        </Dialog>
      </Modal>
    </ModalOverlay>
  );
}

/** Confirmación propia (en vez de `window.confirm`): título claro y botón con el verbo de la acción. Poner `nodo` una vez en la pantalla. */
export function useConfirmar() {
  const [p, setP] = useState<{ titulo: string; texto?: string; verbo: string; ok: () => void } | null>(null);
  const [abierto, setAbierto] = useState(false);
  const pedir = (titulo: string, verbo: string, ok: () => void, texto?: string) => { setP({ titulo, texto, verbo, ok }); setAbierto(true); };
  const nodo = (
    <Ventana abierto={abierto} alCambiar={setAbierto} titulo={p?.titulo ?? ""} descripcion={p?.texto}>
      <Fila>
        <Button color="secondary" size="sm" onPress={() => setAbierto(false)}>Cancelar</Button>
        <Button color="primary-destructive" size="sm" onPress={() => { setAbierto(false); p?.ok(); }}>{p?.verbo}</Button>
      </Fila>
    </Ventana>
  );
  return [pedir, nodo] as const;
}

/** Junta alertas de texto idéntico (p. ej. el mismo turno prohibido en dos celdas) para no repetir la misma línea. */
export function agrupar(alertas: Alerta[]) {
  const g = new Map<string, { alerta: Alerta; veces: number }>();
  for (const a of alertas) {
    const x = g.get(a.texto);
    if (x) x.veces++; else g.set(a.texto, { alerta: a, veces: 1 });
  }
  return [...g.values()];
}

/** Guía de tres pasos del periodo: generar → revisar alertas → publicar. Cada paso pendiente trae su botón. */
export function Pasos({ hay, alertas, publicado, alGenerar, alVerAlertas, alPublicar }: {
  hay: boolean; alertas: Alerta[]; publicado: boolean; alGenerar?: () => void; alVerAlertas?: () => void; alPublicar?: () => void;
}) {
  // Mismas cuentas que la lista de alertas (agrupada), para que los números coincidan.
  const errores = agrupar(alertas.filter((a) => a.nivel === "error")).length, avisos = agrupar(alertas.filter((a) => a.nivel === "aviso")).length;
  const pasos = [
    { titulo: "Generar", hecho: hay, texto: hay ? "Hecho: el cuadro está armado." : "Aún sin cuadro.", boton: hay || !alGenerar ? null : ["Generar", alGenerar] as const },
    { titulo: "Revisar alertas", hecho: hay && !errores, texto: errores ? `${errores} por corregir · ${avisos} para revisar` : avisos ? `Sin errores · ${avisos} recomendaciones` : "Sin alertas.", boton: (errores || avisos) && alVerAlertas ? ["Ver alertas", alVerAlertas] as const : null },
    { titulo: "Publicar", hecho: publicado, texto: publicado ? "Publicado: el equipo ve esta versión." : "Aún no publicado.", boton: hay && !publicado && !errores && alPublicar ? ["Publicar", alPublicar] as const : null },
  ];
  const actual = pasos.findIndex((p) => !p.hecho);
  return (
    <ol className="grid grid-cols-[repeat(auto-fit,minmax(240px,1fr))] gap-4" aria-label="Pasos del periodo" data-no-imprimir>
      {pasos.map((p, i) => (
        <li key={p.titulo} data-hecho={p.hecho || undefined} data-actual={(!p.hecho && i === actual) || undefined} aria-current={i === actual ? "step" : undefined}
          className={cx("flex items-center gap-3.5 rounded-2xl bg-primary px-4 py-3.5 shadow-xs ring-1 ring-secondary ring-inset",
            p.hecho && "bg-linear-to-r from-utility-green-50 to-primary ring-utility-green-200", !p.hecho && i === actual && "bg-linear-to-r from-utility-yellow-50 to-primary ring-utility-yellow-200")}>
          <span className="grid size-8 shrink-0 place-items-center rounded-full bg-secondary font-bold text-tertiary in-data-hecho:bg-success-solid in-data-hecho:text-white in-data-actual:bg-warning-solid in-data-actual:text-white" aria-hidden="true">{p.hecho ? "✓" : i + 1}</span>
          <span className="min-w-0 flex-1"><strong className="text-[15px] text-primary in-data-hecho:text-utility-green-700">{i + 1}. {p.titulo}</strong><span className="mt-0.5 block text-xs text-tertiary in-data-actual:text-utility-yellow-700 in-data-hecho:text-utility-green-700">{p.texto}</span></span>
          {p.boton ? <Button color="secondary" size="sm" iconTrailing={ChevronRight} onPress={p.boton[1]}>{p.boton[0]}</Button>
            : p.hecho && <Check aria-hidden="true" className="size-5 shrink-0 text-fg-success-secondary" />}
        </li>
      ))}
    </ol>
  );
}

/** Indicador en tarjeta: ícono y título, valor grande y una nota (Inicio, Analíticas). */
export function Indicador({ icono: Icono, titulo, valor, nota }: { icono: Icono; titulo: string; valor: string; nota: string }) {
  return (
    <div className="tarjeta flex flex-col gap-3 p-5" role="listitem">
      <span className="flex items-center gap-2.5 text-sm font-medium text-tertiary">
        <span className="grid size-9 place-items-center rounded-lg bg-brand-50 text-brand-600" aria-hidden="true"><Icono className="size-4.5" /></span>{titulo}
      </span>
      <strong className="text-display-xs font-semibold text-primary">{valor}</strong>
      <span className="text-xs text-tertiary">{nota}</span>
    </div>
  );
}
