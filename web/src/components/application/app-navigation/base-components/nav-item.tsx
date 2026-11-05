"use client";

import type { FC, HTMLAttributes, MouseEventHandler, ReactNode, RefAttributes } from "react";
import { ChevronDown, Share04 } from "@untitledui/icons";
import type { LinkProps as AriaLinkProps } from "react-aria-components";
import { Link as AriaLink } from "react-aria-components";
import { cx, sortCx } from "@/utils/cx";

const styles = sortCx({
    // An: ítem de 44 px, activo en píldora de marca con barra a la izquierda (rediseño 2026-11).
    root: "group relative flex h-11 w-full cursor-pointer items-center rounded-xl bg-primary outline-focus-ring transition duration-100 ease-linear select-none hover:bg-primary_hover focus-visible:z-10 focus-visible:outline-2 focus-visible:outline-offset-2",
    rootSelected: "bg-brand-50 hover:bg-brand-50 before:absolute before:inset-y-2.5 before:left-0 before:w-[3px] before:rounded-full before:bg-brand-500",
});

/**
 * Props shared between the collapsible and link variants
 */
interface NavItemCommonProps {
    /** Icon component to display. */
    icon?: FC<HTMLAttributes<HTMLOrSVGElement>>;
    /** Badge to display. */
    badge?: ReactNode;
    /** Whether the nav item is currently active. */
    current?: boolean;
    /** Whether to truncate the label text. */
    truncate?: boolean;
    /** Handler for click events. */
    onClick?: MouseEventHandler;
    /** Content to display. */
    children?: ReactNode;
}

/**
 * Props for the collapsible variant (renders a `summary` element)
 */
export interface NavItemCollapsibleProps extends NavItemCommonProps {
    /** Type of the nav item. */
    type: "collapsible";
}

/**
 * Props for the link variants (anchor tag). Accepts all React Aria `Link` props such as `routerOptions`, `isDisabled` and `onPress`.
 */
export interface NavItemLinkProps extends NavItemCommonProps, Omit<AriaLinkProps, "children" | "className" | "onClick">, RefAttributes<HTMLAnchorElement> {
    /** Type of the nav item. */
    type: "link" | "collapsible-child";
    /** URL to navigate to when the nav item is clicked. */
    href?: AriaLinkProps["href"];
}

/** Union type of collapsible and link props */
export type NavItemBaseProps = NavItemCollapsibleProps | NavItemLinkProps;

export const NavItemBase = (props: NavItemBaseProps) => {
    const { icon: Icon, badge, current, truncate = true, onClick, children, ...rest } = props;

    const iconElement = Icon && (
        <Icon
            aria-hidden="true"
            className={cx(
                "mr-3 size-5 shrink-0 text-fg-quaternary transition-inherit-all group-hover/item:text-fg-quaternary_hover",
                current && "text-brand-600 group-hover/item:text-brand-600",
            )}
        />
    );

    const badgeElement =
        badge && (typeof badge === "string" || typeof badge === "number") ? (
            <span data-texto className="ml-3 rounded-full bg-brand-600 px-2 py-0.5 text-xs font-semibold text-white">
                {badge}
            </span>
        ) : (
            badge
        );

    const labelElement = (
        <span
            data-texto
            className={cx(
                "flex-1 text-sm font-medium text-secondary transition-inherit-all group-hover/item:text-secondary_hover",
                truncate && "truncate",
                current && "font-semibold text-brand-secondary group-hover/item:text-brand-secondary",
            )}
        >
            {children}
        </span>
    );

    if (rest.type === "collapsible") {
        return (
            <summary className={cx("p-2", styles.root, current && styles.rootSelected)} onClick={onClick}>
                {iconElement}

                {labelElement}

                {badgeElement}

                <ChevronDown aria-hidden="true" className="ml-3 size-4 shrink-0 stroke-[2.5px] text-fg-quaternary in-open:-scale-y-100" />
            </summary>
        );
    }

    const { type, href, isDisabled, ...linkProps } = rest;

    const isExternal = href?.startsWith("http");
    const externalIcon = isExternal && <Share04 className="size-4 stroke-[2.5px] text-fg-quaternary" />;

    return (
        <AriaLink
            // Defaults that consumers can override through React Aria link props.
            target={isExternal ? "_blank" : "_self"}
            rel="noopener noreferrer"
            aria-current={current ? "page" : undefined}
            {...linkProps}
            // Dropping `href` when disabled prevents navigation via middle-click or "open in new tab".
            href={isDisabled ? undefined : href}
            isDisabled={isDisabled}
            onClick={onClick}
            className={cx(
                type === "collapsible-child" ? "py-2 pr-3 pl-10" : "group/item px-3.5",
                styles.root,
                current && styles.rootSelected,
                "disabled:pointer-events-none disabled:cursor-not-allowed disabled:opacity-50",
            )}
        >
            {type === "link" && iconElement}
            {labelElement}
            {externalIcon}
            {badgeElement}
        </AriaLink>
    );
};
