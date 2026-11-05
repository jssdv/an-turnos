import { cx } from "@/utils/cx";

/** Marca de An (reemplaza el logo de Untitled en la navegación). `plegado`: solo el cuadro verde. */
export const AnLogo = ({ area, plegado, className }: { area?: string; plegado?: boolean; className?: string }) => (
    <div className={cx("flex items-center gap-3", className)}>
        <span aria-hidden="true" className="grid size-10 shrink-0 place-items-center rounded-xl bg-linear-to-br from-brand-500 to-brand-700 text-md font-bold text-white shadow-sm">An</span>
        <div className={cx("leading-tight", plegado && "sr-only")}>
            <div className="text-lg font-bold text-primary">An</div>
            {area && <div className="text-xs font-medium text-tertiary">{area}</div>}
        </div>
    </div>
);
