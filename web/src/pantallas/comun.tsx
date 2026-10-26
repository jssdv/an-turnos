import { useState, type ReactNode } from "react";
import { mensaje } from "../api/catalogos";
import { Ayuda } from "../componentes/Ayuda";
import e from "./Cuadro.module.css";
import f from "./Formulario.module.css";
import { Alert, COLOR_NIVEL } from "@/components/application/alerts/alert";
import { Dialog, Modal, ModalOverlay } from "@/components/application/modals/modal";

/** Marco de una pantalla de catálogo: título, aviso de resultado y errores de lectura. */
export function Pagina({ titulo, sub, ayuda, error, aviso, children }: { titulo: string; sub?: string; ayuda?: ReactNode; error?: string | null; aviso?: { nivel: "ok" | "aviso" | "error"; texto: string } | null; children: ReactNode }) {
  return (
    <div className={e.pagina}>
      <div><h1 className={e.titulo}>{titulo}</h1>{sub && <p className={e.sub}>{sub}</p>}</div>
      {ayuda && <Ayuda titulo="¿Cómo se usa esta sección?" clave={titulo}>{ayuda}</Ayuda>}
      {error && <Alert color="error">{error}</Alert>}
      {aviso && <Alert color={COLOR_NIVEL[aviso.nivel]}>{aviso.texto}</Alert>}
      {children}
    </div>
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

export const Formulario = ({ children, ...r }: React.FormHTMLAttributes<HTMLFormElement>) => <form className={f.form} {...r}>{children}</form>;
export const Fila = ({ children }: { children: ReactNode }) => <div className={f.fila}>{children}</div>;
export function Casilla({ etiqueta, ...r }: { etiqueta: string } & React.InputHTMLAttributes<HTMLInputElement>) {
  return <label className={f.casilla}><input type="checkbox" {...r} /> {etiqueta}</label>;
}

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
