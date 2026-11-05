import { useContext } from "react";
import { parseDate, today, getLocalTimeZone } from "@internationalized/date";
import { Calendar as CalendarioIcono, ChevronLeft, ChevronRight } from "@untitledui/icons";
import {
  Button, Calendar, CalendarCell, CalendarGrid, CalendarGridBody, CalendarGridHeader, CalendarHeaderCell, DateInput, DatePicker,
  DatePickerStateContext, DateSegment, Dialog, Group, Heading, I18nProvider, Label, Popover,
} from "react-aria-components";
import { cx } from "@/utils/cx";

const ISO = /^\d{4}-\d{2}-\d{2}$/;
const flecha = "grid size-8 cursor-pointer place-items-center rounded-lg text-fg-quaternary outline-focus-ring hover:bg-primary_hover hover:text-fg-quaternary_hover focus-visible:outline-2";

function Hoy() {
  const st = useContext(DatePickerStateContext);
  return (
    <Button onPress={() => { st?.setValue(today(getLocalTimeZone())); st?.close(); }}
      className="mt-1 w-full cursor-pointer rounded-lg py-2 text-sm font-semibold text-brand-secondary outline-focus-ring hover:bg-primary_hover focus-visible:outline-2">
      Hoy
    </Button>
  );
}

/** Selector de fecha con calendario propio (reemplaza `<input type="date">`). Valor y cambio son texto ISO `YYYY-MM-DD`; vacío = sin fecha. */
export function CampoFecha({ value, onChange, label, isRequired, className }: {
  value: string; onChange: (iso: string) => void; label: string; isRequired?: boolean; className?: string;
}) {
  return (
    <I18nProvider locale="es-CO">
      <DatePicker value={ISO.test(value) ? parseDate(value) : null} onChange={(v) => onChange(v ? v.toString() : "")}
        isRequired={isRequired} granularity="day" className={cx("flex flex-col gap-1.5", className)}>
        <Label className="flex items-center gap-0.5 text-sm font-medium text-secondary">
          {label}{isRequired && <span aria-hidden="true" className="text-brand-tertiary">*</span>}
        </Label>
        <Group className="flex items-center rounded-lg bg-primary shadow-xs ring-1 ring-primary transition ring-inset focus-within:ring-2 focus-within:ring-brand data-[invalid]:ring-error_subtle">
          <DateInput className="flex flex-1 items-center px-3 py-2 text-sm text-primary">
            {(s) => <DateSegment segment={s} className="rounded-xs px-0.5 tabular-nums outline-hidden data-[placeholder]:text-placeholder data-[type=literal]:px-0 focus:bg-brand-solid focus:text-white" />}
          </DateInput>
          <Button aria-label={`Abrir calendario: ${label}`}
            className="mr-1 grid size-8 shrink-0 cursor-pointer place-items-center rounded-md text-fg-quaternary outline-focus-ring transition hover:bg-primary_hover hover:text-fg-quaternary_hover focus-visible:outline-2">
            <CalendarioIcono aria-hidden="true" className="size-4.5" />
          </Button>
        </Group>
        <Popover placement="bottom start" offset={6}
          className="w-[min(320px,calc(100vw-32px))] overscroll-contain rounded-2xl bg-primary p-3 shadow-xl ring-1 ring-secondary outline-hidden data-[entering]:animate-in data-[entering]:fade-in data-[entering]:zoom-in-95 data-[exiting]:animate-out data-[exiting]:fade-out">
          <Dialog className="outline-hidden">
            <Calendar firstDayOfWeek="mon" className="flex flex-col gap-2">
              <header className="flex items-center justify-between">
                <Button slot="previous" aria-label="Mes anterior" className={flecha}><ChevronLeft aria-hidden="true" className="size-5" /></Button>
                <Heading className="text-sm font-semibold text-primary first-letter:uppercase" />
                <Button slot="next" aria-label="Mes siguiente" className={flecha}><ChevronRight aria-hidden="true" className="size-5" /></Button>
              </header>
              <CalendarGrid className="w-full border-separate border-spacing-y-0.5">
                <CalendarGridHeader>{(d) => <CalendarHeaderCell className="pb-1 text-xs font-medium text-tertiary uppercase">{d}</CalendarHeaderCell>}</CalendarGridHeader>
                <CalendarGridBody>
                  {(f) => (
                    <CalendarCell date={f}
                      className="mx-auto grid size-9 cursor-pointer touch-manipulation place-items-center rounded-full text-sm text-secondary tabular-nums outline-focus-ring transition-colors hover:bg-primary_hover focus-visible:outline-2 data-[outside-month]:hidden data-[disabled]:cursor-default data-[disabled]:text-disabled data-[selected]:bg-brand-solid data-[selected]:font-semibold data-[selected]:text-white data-[selected]:hover:bg-brand-solid_hover data-[today]:font-semibold data-[today]:text-brand-secondary data-[today]:data-[selected]:text-white" />
                  )}
                </CalendarGridBody>
              </CalendarGrid>
            </Calendar>
            <Hoy />
          </Dialog>
        </Popover>
      </DatePicker>
    </I18nProvider>
  );
}
