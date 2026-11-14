import { cx } from "@/utils/cx";

/** Marca de An: la palabra «An» en el texto principal, sin cuadro ni degradado. `plegado`: solo la palabra. */
export const AnLogo = ({ area, plegado, className }: { area?: string; plegado?: boolean; className?: string }) => (
    <div className={cx("flex items-baseline gap-2.5", className)}>
        <span className="text-xl font-semibold tracking-tight text-primary">An</span>
        {area && <span className={cx("border-l border-secondary pl-2.5 text-sm text-tertiary", plegado && "sr-only")}>{area}</span>}
    </div>
);
