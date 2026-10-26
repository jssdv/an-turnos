import { useState, type HTMLAttributes, type ReactNode } from "react";
import { HelpCircle } from "@untitledui/icons";
import { cx } from "@/utils/cx";
import { mensaje } from "../api/catalogos";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";

/** Encabezado de pantalla (título, subtítulo, ayuda y avisos) y su contenido. */
export function Pagina({ titulo, sub, ayuda, error, aviso, children }: { titulo: string; sub?: string; ayuda?: ReactNode; error?: string | null; aviso?: { nivel: "ok" | "aviso" | "error"; texto: string } | null; children: ReactNode }) {
  return (
    <div className="flex max-w-[1500px] flex-col gap-5">
      <header>
        <h1 className="text-display-xs font-semibold text-primary">{titulo}</h1>
        {sub && <p className="mt-1 text-md text-tertiary">{sub}</p>}
      </header>
      {ayuda && <Ayuda clave={titulo}>{ayuda}</Ayuda>}
      {error && <Alert color="error">{error}</Alert>}
      {aviso && <Alert color={COLOR_NIVEL[aviso.nivel]}>{aviso.texto}</Alert>}
      {children}
    </div>
  );
}

/** Bloque de contenido con título y acciones a la derecha (tarjeta de Untitled UI). */
export function Seccion({ titulo, acciones, children, className, ...r }: { titulo?: ReactNode; acciones?: ReactNode } & HTMLAttributes<HTMLElement>) {
  return (
    <section className={cx("rounded-xl bg-primary p-5 shadow-xs ring-1 ring-secondary ring-inset", className)} {...r}>
      {(titulo || acciones) && (
        <header className="mb-4 flex items-center justify-between gap-3">
          <h2 className="flex items-center gap-2 text-lg font-semibold text-primary">{titulo}</h2>
          {acciones}
        </header>
      )}
      {children}
    </section>
  );
}

const recordar = (clave: string, abierta?: boolean) => {
  try {
    if (abierta === undefined) return localStorage.getItem(clave) !== "cerrada";
    localStorage.setItem(clave, abierta ? "abierta" : "cerrada");
  } catch { /* almacenamiento bloqueado: se muestra abierta */ }
  return true;
};

/** Recuadro «¿Cómo se usa?». Abierto la primera vez; si se cierra, este navegador lo recuerda. */
export function Ayuda({ titulo = "¿Cómo se usa esta sección?", clave, children }: { titulo?: string; clave: string; children: ReactNode }) {
  const [abierta] = useState(() => recordar(`ayuda/${clave}`));
  return (
    <details className="group rounded-xl bg-utility-brand-50 px-4 py-3 text-sm text-utility-brand-700 ring-1 ring-utility-brand-200 ring-inset" open={abierta}
      onToggle={(x) => recordar(`ayuda/${clave}`, x.currentTarget.open)}>
      <summary className="flex cursor-pointer list-none items-center gap-3 font-semibold">
        <HelpCircle aria-hidden="true" className="size-5 shrink-0" />{titulo}
        <span className="ml-auto text-xs font-semibold group-open:hidden">Mostrar</span>
        <span className="ml-auto hidden text-xs font-semibold group-open:inline">Ocultar</span>
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
export const Fila = ({ children }: { children: ReactNode }) => <div className="col-span-full flex flex-wrap items-center gap-3">{children}</div>;
/** Grupo de casillas con leyenda, a lo ancho del formulario. */
export const Grupo = ({ leyenda, children }: { leyenda: string; children: ReactNode }) => (
  <fieldset className="col-span-full flex flex-wrap gap-x-5 gap-y-2">
    <legend className="mb-2 text-sm font-medium text-secondary">{leyenda}</legend>
    {children}
  </fieldset>
);

/** Ventana modal con título: Untitled UI trae solo las piezas (fondo, caja, diálogo); el título y el relleno van aquí.
 * `bloqueado`: un trabajo en marcha no se cierra con Escape ni con un clic fuera. */
export function Ventana({ abierto, alCambiar, titulo, descripcion, bloqueado, children }: { abierto: boolean; alCambiar: (abierto: boolean) => void; titulo: string; descripcion?: string; bloqueado?: boolean; children: ReactNode }) {
  return (
    <ModalOverlay isOpen={abierto} onOpenChange={alCambiar} isDismissable={!bloqueado} isKeyboardDismissDisabled={bloqueado}>
      <Modal className="max-w-xl">
        <Dialog className="flex flex-col gap-4 p-6">
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
