import { Dialog } from "@base-ui/react/dialog";
import type { ReactNode } from "react";
import e from "./Dialogo.module.css";

interface Props {
  abierto: boolean;
  alCambiar: (abierto: boolean) => void;
  titulo: string;
  descripcion?: string;
  children: ReactNode;
  /** Un trabajo en marcha no se cierra con Escape ni con un clic fuera. */
  bloqueado?: boolean;
}

export function Dialogo({ abierto, alCambiar, titulo, descripcion, children, bloqueado }: Props) {
  return (
    <Dialog.Root open={abierto} onOpenChange={(a, d) => { if (!(bloqueado && !a && d.reason !== "close-press")) alCambiar(a); }}>
      <Dialog.Portal>
        <Dialog.Backdrop className={e.fondo} />
        <Dialog.Popup className={e.ventana}>
          <Dialog.Title className={e.titulo}>{titulo}</Dialog.Title>
          {descripcion && <Dialog.Description className={e.descripcion}>{descripcion}</Dialog.Description>}
          {children}
        </Dialog.Popup>
      </Dialog.Portal>
    </Dialog.Root>
  );
}

export const CierreDialogo = Dialog.Close;
