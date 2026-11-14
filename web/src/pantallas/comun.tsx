import { useState, type FC, type HTMLAttributes, type ReactElement, type ReactNode, type SelectHTMLAttributes } from "react";
import { Check, ChevronDown, ChevronRight, HelpCircle } from "@untitledui/icons";
import { cx } from "@/utils/cx";
import { mensaje } from "../api/catalogos";
import type { Alerta } from "../api/tipos";

import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";
import { Button } from "@/components/base/buttons/button";
import { NativeSelect } from "@/components/base/select/select-native";
import { Tooltip } from "@/components/base/tooltip/tooltip";

type Icono = FC<{ className?: string }>;

/** Encabezado de pantalla, sin tarjeta: título y estado a la izquierda; filtros y acciones a la derecha en una sola fila
 *  (la principal al final, junto a ⋯). Luego ayuda, avisos y el contenido. Es el mismo orden en todas las pantallas. */
export function Pagina({ titulo, sub, estado, filtros, acciones, ayuda, error, aviso, children }: {
  titulo: ReactNode; sub?: ReactNode; estado?: ReactNode; filtros?: ReactNode; acciones?: ReactNode;
  ayuda?: ReactNode; error?: string | null; aviso?: { nivel: "ok" | "aviso" | "error"; texto: string } | null; children: ReactNode;
}) {
  return (
    <div className="flex max-w-[1500px] flex-col gap-4">
      <header className="flex flex-wrap items-end gap-x-4 gap-y-3">
        <div className="min-w-0 flex-1 basis-64">
          <div className="flex flex-wrap items-center gap-x-2.5 gap-y-1"><h1 className="text-display-xs font-semibold tracking-tight text-primary">{titulo}</h1>{estado}</div>
          {sub && <p className="mt-0.5 text-sm text-tertiary">{sub}</p>}
        </div>
        {(filtros || acciones) && (
          <div className="flex flex-wrap items-center gap-2" data-no-imprimir>
            {filtros}
            {acciones && <div className="flex flex-wrap items-center gap-2" role="group" aria-label="Acciones">{acciones}</div>}
          </div>
        )}
      </header>
      {ayuda && <Ayuda clave={String(titulo)}>{ayuda}</Ayuda>}
      {error && <Alert color="error">{error}</Alert>}
      {aviso && <div role="status" aria-live="polite"><Alert color={COLOR_NIVEL[aviso.nivel]}>{aviso.texto}</Alert></div>}
      {children}
    </div>
  );
}

/** Estado junto al título (Publicado, Cerrado…): punto y palabra en un recuadro fino; el color nunca va solo. */
export const Estado = ({ tono = "ok", children }: { tono?: "ok" | "neutro"; children: ReactNode }) => (
  <span className={cx("inline-flex items-center gap-1.5 rounded-md px-2 py-0.5 text-xs font-medium ring-1 ring-secondary ring-inset before:size-1.5 before:rounded-full",
    tono === "ok" ? "text-success-primary before:bg-fg-success-secondary" : "text-tertiary before:bg-fg-quaternary")}>{children}</span>
);

/** Bloque de contenido: hoja blanca con línea fina; título de sección y acciones a la derecha. */
export function Seccion({ titulo, acciones, children, className, ...r }: { titulo?: ReactNode; acciones?: ReactNode } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={cx("tarjeta p-4 sm:p-5", className)} {...r}>
      {(titulo || acciones) && (
        <header className="mb-4 flex flex-wrap items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-md font-semibold text-primary">{titulo}</h2>
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

/** Lista desplegable para el encabezado (periodo, versión, persona…). La etiqueta queda para lectores de pantalla. */
export function Filtro({ etiqueta, icono: Icono, className, children, ...r }: { etiqueta: string; icono?: Icono } & Omit<SelectHTMLAttributes<HTMLSelectElement>, "size">) {
  return (
    <div className={cx("relative", className)}>
      {Icono && <Icono aria-hidden="true" className="pointer-events-none absolute top-1/2 left-3 z-10 size-4.5 -translate-y-1/2 text-fg-quaternary" />}
      <NativeSelect size="sm" label={etiqueta} className="[&_label]:sr-only" selectClassName={cx("h-9 pr-9", Icono && "pl-9")} {...r}>{children}</NativeSelect>
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
    <details className="group tarjeta px-4 py-2.5 text-sm sm:px-5 text-secondary" open={abierta} data-no-imprimir
      onToggle={(x) => recordar(`ayuda2/${clave}`, x.currentTarget.open)}>
      <summary className="flex cursor-pointer list-none items-center gap-3 font-medium text-primary">
        <HelpCircle aria-hidden="true" className="size-4.5 shrink-0 text-fg-quaternary" />{titulo}
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
    <ol className="tarjeta grid grid-cols-1 divide-y divide-secondary sm:grid-cols-3 sm:divide-x sm:divide-y-0" aria-label="Pasos del periodo" data-no-imprimir>
      {pasos.map((p, i) => (
        <li key={p.titulo} data-hecho={p.hecho || undefined} data-actual={(!p.hecho && i === actual) || undefined} aria-current={i === actual ? "step" : undefined}
          className="flex min-h-14 items-center gap-3 px-4 py-2.5">
          <span className="w-4 shrink-0 text-center font-mono text-xs font-semibold text-quaternary in-data-actual:text-warning-primary" aria-hidden="true">
            {p.hecho ? <Check className="size-4 text-fg-success-primary" /> : i + 1}
          </span>
          <span className="min-w-0 flex-1">
            <strong className="block text-sm font-medium text-primary">{p.titulo}</strong>
            <span className="block text-xs text-tertiary in-data-actual:text-warning-primary">{p.texto}</span>
          </span>
          {p.boton && <Button color="secondary" size="sm" iconTrailing={ChevronRight} onPress={p.boton[1]}>{p.boton[0]}</Button>}
        </li>
      ))}
    </ol>
  );
}

/** Tira de indicadores: una hoja dividida por líneas finas (sin tarjetas sueltas). Va con `Indicador` dentro. */
export const Indicadores = ({ etiqueta, children }: { etiqueta: string; children: ReactNode }) => (
  <div role="list" aria-label={etiqueta} className="tarjeta grid grid-cols-2 divide-secondary max-sm:[&>*:nth-child(n+3)]:border-t max-sm:[&>*:nth-child(n+3)]:border-secondary sm:grid-flow-col sm:auto-cols-fr sm:divide-x [&>*:nth-child(2n)]:max-sm:border-l [&>*:nth-child(2n)]:max-sm:border-secondary">
    {children}
  </div>
);

/** Indicador dentro de `Indicadores`: rótulo en versalitas, valor en mono y una nota. `tono` marca el valor (con palabra en la nota, nunca solo color). */
export function Indicador({ titulo, valor, nota, tono }: { titulo: string; valor: string; nota: string; tono?: "ok" | "aviso" | "error" }) {
  return (
    <div className="flex min-w-0 flex-col px-4 py-3" role="listitem">
      <span className="rotulo">{titulo}</span>
      <strong className={cx("mt-0.5 font-mono text-xl font-medium text-primary", tono === "ok" && "text-success-primary", tono === "aviso" && "text-warning-primary", tono === "error" && "text-error-primary")}>{valor}</strong>
      <span className="text-xs text-tertiary">{nota}</span>
    </div>
  );
}
