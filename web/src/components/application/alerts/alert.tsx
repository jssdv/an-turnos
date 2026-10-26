import type { ReactNode } from "react";
import { AlertCircle, AlertTriangle, CheckCircle, InfoCircle } from "@untitledui/icons";
import { cx } from "@/utils/cx";

/** Untitled UI (gratis) no trae alerta en línea: esta usa sus colores utility-* y sus iconos. */
const estilos = {
    brand: { caja: "bg-utility-brand-50 text-utility-brand-700 ring-utility-brand-200", Icono: InfoCircle },
    success: { caja: "bg-utility-green-50 text-utility-green-700 ring-utility-green-200", Icono: CheckCircle },
    warning: { caja: "bg-utility-yellow-50 text-utility-yellow-700 ring-utility-yellow-200", Icono: AlertTriangle },
    error: { caja: "bg-utility-red-50 text-utility-red-700 ring-utility-red-200", Icono: AlertCircle },
};

/** Niveles que devuelve la API y `useAccion` → color de la alerta. */
export const COLOR_NIVEL = { info: "brand", ok: "success", aviso: "warning", error: "error" } as const;

interface AlertProps {
    color?: keyof typeof estilos;
    children: ReactNode;
    /** Botón o enlace a la derecha (p. ej. «Reintentar»). */
    action?: ReactNode;
    className?: string;
}

/** `error` y `warning` se anuncian de inmediato a lectores de pantalla; el resto, con calma. */
export const Alert = ({ color = "brand", children, action, className }: AlertProps) => {
    const { caja, Icono } = estilos[color];
    return (
        <div role={color === "error" || color === "warning" ? "alert" : "status"} className={cx("flex items-start gap-3 rounded-xl px-4 py-3 text-sm font-medium ring-1 ring-inset", caja, className)}>
            <Icono aria-hidden="true" className="mt-0.5 size-5 shrink-0" />
            <div className="flex-1">{children}</div>
            {action}
        </div>
    );
};
