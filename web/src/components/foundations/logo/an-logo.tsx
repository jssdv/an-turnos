import { cx } from "@/utils/cx";

/** Marca de An (reemplaza el logo de Untitled en la navegación). */
export const AnLogo = ({ area, className }: { area?: string; className?: string }) => (
    <div className={cx("flex items-center gap-3", className)}>
        <span aria-hidden="true" className="grid size-8 place-items-center rounded-lg bg-brand-solid text-sm font-bold text-white">An</span>
        <div className="leading-tight">
            <div className="text-md font-semibold text-primary">An</div>
            {area && <div className="text-xs font-medium text-tertiary">{area}</div>}
        </div>
    </div>
);
