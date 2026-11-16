# Spacing, density and print for a data-dense rostering web app (Nov 2026)

Context: React 19 + Tailwind v4 app used by hospital coordinators on desktop PCs, sometimes on phones. Screens: monthly roster grid (people × 28–31 days, 22 px chips in 30×32 px cells, 44 px on touch), an analytics dashboard with many sections, reports, settings forms, tables and modals. Floating sidebar, white cards on a gradient background, IBM Plex Sans.

Source-quality note: values come from official design-system docs. Salesforce (403), Material 3 (rendered client-side), Refactoring UI (book) and current Polaris (redirect) could not be loaded directly; their values come from search snippets, older docs or a pinned token package, as marked.

## 1. Spacing scales in major design systems

| System | Base | Scale (px) | Semantic layer |
|---|---|---|---|
| IBM Carbon | 8 px "mini unit" | `$spacing-01..13` = 2, 4, 8, 12, 16, 24, 32, 40, 48, 64, 80, 96, 160 | None. Tokens aren't responsive, so step down at breakpoints |
| Atlassian | 8 px = `space.100` | 0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80 | Small 0–8 (table cells, badges, input padding); medium 12–24 (buttons, gaps inside cards); large 32–80 (page sections) |
| Primer | 4/8 | 2, 4, 6, 8, 12, 16, 20, 24, 28, 32, 36, 40, 44, 48, 64, 80, 96, 112, 128 | Stack gap/padding: condensed 8, normal 16, spacious 24. Control heights 24/28/32/40/48 |
| Polaris (tokens 9.4.2) | 4 px | 1, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96, 112, 128 | `card-padding` 16, `card-gap` 16 (8 on mobile), `table-cell-padding` 6, `button-group-gap` 8 |
| Cloudscape | 4 px | 2, 4, 8, 12, 16, 20, 24, 32, 40 | 20 between form fields, 20 horizontal container padding, 16 inside cards, 8 between buttons |
| Refactoring UI (secondary) | 4/16 | 4, 8, 12, 16, 24, 32, 48, 64, 96, 128 | Start with too much space and remove; more space around groups than inside; fewer borders |

- **EightShapes (Nathan Curtis) vocabulary.** *Inset* is padding. A *squish* inset has about half the vertical padding (table cells, list items, buttons); *stretch* is for inputs. *Stack* is vertical gaps and *inline* is horizontal. Name tokens by concept, not by CSS property. https://eightshapes.com/articles/space-in-design-systems/
- **Material.** Each density step removes 4 dp of height. Touch targets are turned off at negative density, and density is not inherited. Default data-table rows are 52 dp, too roomy for rosters. https://cdn.jsdelivr.net/npm/@material/density@14.0.0/README.md
- **Salesforce Lightning (snippet).** Compact roughly halves medium spacing (16 to 8) and puts labels beside fields. Admins set the org default; users can override it.

Sources: https://carbondesignsystem.com/elements/spacing/overview/ · https://atlassian.design/foundations/spacing · https://primer.style/foundations/primitives/size · https://cloudscape.design/foundation/visual-foundation/spacing/

## 2. Data-dense UI

- **Carbon tables.** Row heights: xs 24 (very dense), sm 32 (compact), md 40 (default), lg 48 (spacious), xl 64 (two-line). The header matches the body row height, and the toolbar and pagination follow the row size. At least 16 px between columns. https://carbondesignsystem.com/components/data-table/style/
- **Primer DataTable.** Padding (block/inline) is condensed 4/8, normal 8/12, spacious 12/16. Text is 12 px with a 20 px line-height, so rows are about 28, 36 or 44 px. Height comes from padding plus line-height, not a fixed value. https://github.com/primer/react/blob/main/packages/react/src/DataTable/Table.module.css
- **WCAG 2.2 SC 2.5.8 (target size).** Targets must be 24×24 CSS px, or have enough spacing around them, or have an equivalent control. In the app the clickable element is the 30×32 px `td`, not the 22 px chip, so the roster passes. https://www.w3.org/WAI/WCAG22/Understanding/target-size-minimum.html
- **Carbon grid.** Gutters: wide 32, narrow 16 (the most common), condensed 1 px. Condensed suits dashboards where the tiles form one picture, and needs 1 px borders. Grid boxes have a fixed 16 px padding. https://carbondesignsystem.com/elements/2x-grid/usage/
- **Cloudscape.** Fixed 20 px gutter; 16 px between a page header and its content.
- **Proximity.** Space inside a group must be clearly smaller than space between groups, and a heading sits closer to its own section than to the one above. Prefer whitespace or a tint over borders inside cards. Use dividers where whitespace costs too much room (table rows, dense lists). https://www.nngroup.com/articles/gestalt-proximity/

## 3. Density toggles

- **Cloudscape.** Comfortable is the default; compact can hurt readability and target size, so it never replaces comfortable. The setting is app-wide and saved. Don't mix densities on a page unless a component supports it. https://cloudscape.design/foundation/visual-foundation/content-density/ · https://cloudscape.design/patterns/general/density-settings/
- **Primer** switches some spacing on `pointer: coarse` vs `pointer: fine`.
- **Verdict for a small app.** A global toggle isn't worth it. Size the roster by `@media (pointer: coarse)` and keep one density elsewhere. If a toggle is ever needed, semantic tokens overridden under `[data-density="compact"]` make it a block of variable overrides.

## 4. Tailwind v4

- Keep `--spacing: 0.25rem`. `p-4` compiles to `calc(var(--spacing) * 4)`; use `--spacing(n)` in custom CSS.
- Any `--spacing-<name>` in `@theme` generates `p-<name>`, `gap-<name>`, `m-<name>` and so on. Avoid t-shirt names, which clash with container sizes.
- To switch density, override the theme variables under a selector. Use `@theme inline` when a variable references another.
- `@custom-variant compact (&:where([data-density="compact"] *));` gives a `compact:` variant. `print:` is built in.
- Container queries: `@container` on the card, `@md:` on its children; `--container-*` extends the sizes.
- https://tailwindcss.com/docs/theme · https://tailwindcss.com/docs/adding-custom-styles · https://tailwindcss.com/docs/responsive-design#container-queries

## 5. Print CSS

- `@page { size: A4 landscape }` works in all current browsers (Baseline 2024). `page-orientation` and margin boxes have weak support. https://developer.mozilla.org/en-US/docs/Web/CSS/@page/size
- `print-color-adjust: exact` is Baseline 2025; user print settings still win. https://developer.mozilla.org/en-US/docs/Web/CSS/print-color-adjust
- Chromium and Firefox repeat `thead` on every page; Safari has been reported to show it only on the first page. Headers repeat only on real `<table>` elements. Flex and Grid split poorly across pages.
- DevTools print emulation doesn't show page breaks, so check with Print to PDF.

### Checklist for a monthly roster and a dashboard

1. `@page { size: A4 landscape; margin: 10mm; }`
2. Hide chrome (sidebar, toolbars, buttons, toasts). White background, no shadows, 1 px borders on cards.
3. `print-color-adjust: exact` on shift colours and the heatmap. Keep text codes in cells so colour is never the only signal.
4. Roster as a real table: `thead { display: table-header-group }`, `tr { break-inside: avoid }`, `table-layout: fixed; width: 100%`.
5. Fitting 31 days: A4 landscape leaves 277 mm. A name column of about 30 mm leaves about 8 mm per day, with 7.5–8 pt text and 1–2 px cell padding.
6. Remove `position: sticky`, `overflow: auto`/`hidden`, `vh` heights and transforms. If it still overflows, shrink the text rather than using `transform: scale`.
7. Dashboard: `break-inside: avoid` on cards, `break-after: avoid` on headings, grids collapsed to 1–2 columns, SVGs at `width: 100%` with a `viewBox`.
8. `orphans: 3; widows: 3`. A print-only header with unit, month and print date, because margin boxes are unreliable.

## Recommendation for An

- Primitive steps (px): 0, 2, 4, 6, 8, 12, 16, 20, 24, 32, 40, 48, 64. No arbitrary values.
- Rhythm: page gutter 16–24; card gap 16; card padding 16 on mobile, 20 from `sm`; heading to body 16; stacks 8; inline 8; table cells about 12/8 (default) or 8/4 (compact).
- Table rows: 32 px compact, 40 px default, 44–48 px touch. The header row matches the body.
- Rule: space inside a group is always smaller than space between groups.
- Applied on 15/11/2026 (PR 71): the `Seccion` and `Vacio` components carry the rhythm, and `checks/diseno.py` rejects arbitrary spacing values outside the roster grid.
