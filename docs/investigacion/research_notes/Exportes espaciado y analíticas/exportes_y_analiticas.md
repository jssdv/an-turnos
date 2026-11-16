# Exports, reporting and analytics in shift-scheduling products (Nov 2026)

Context: portable Spanish-language rostering app for a hospital support service in Colombia (12 h shifts, nights, Sunday/holiday surcharges, hours bank, CP-SAT solver, 20–40 staff, non-technical coordinators). Already built: Excel exports (roster, posts, hours, hours bank, an 11-sheet analytics workbook), `.ics` per person and as a zip, roster and per-person print, schedule copied as text; analytics on absenteeism, 30-min coverage with a day × hour map, stability after publishing, overtime and its concentration, fairness against the team mean, requests, fatigue, absence patterns and Bradford factor, forecast, solver runs, next Sunday surcharge, notice and replacements.

Source-quality note: UKG blogs, Capterra, Deputy help, Rotaready and the NHS PDFs blocked direct fetching. Facts marked (excerpt) come from search-result excerpts of those pages. Vendor marketing claims are flagged.

## A. Export features

- **Deputy, custom payroll exporter.** Each column is named and formatted to match the payroll system. You can add a header line (some payroll systems want a file version), a joining character and value-rewrite rules. Templates are shared between managers. The export fails if a field has no data, and the date range must match the pay run exactly. Built-in formats include "CSV/Excel: All Fields" and "Daily Totals and Overtime". https://whatsnew.deputy.com/new-custom-payroll-exporter-features-now-available-1Wi4Jq · https://help.deputy.com/hc/en-au/sections/4614419318159-Timesheet-Export
- **Planday, payroll export.** Semicolon CSV, Excel or PDF. "Payroll Prints" add Excel columns from the employee profile or schedule. A salary code per shift type puts "Sick" hours on their own lines. https://help.planday.com/en/articles/4413251-payroll-prints · https://help.planday.com/en/articles/205831-payroll-exports-faqs-and-troubleshooting
- **Planday, schedule export.** A printable PDF roster or a CSV shift list, for a day, two weeks or a month, grouped by group or position. Also: an Excel report of working-time-rule breaches, contracted vs scheduled hours, and a schedule history log. https://help.planday.com/en/articles/30408-generate-reports-in-planday
- **Rotaready.** The payroll export has hours plus absence per employee and uses signed-off data only. Absence exports come per booking or per day; raw cost figures by department are also exportable (excerpt). https://help.rotaready.com/en/articles/5799909-reports
- **When I Work.**
  - The schedule export has two tabs: the shift list for the chosen range, and total hours and wages per person.
  - Timesheets export by user, by schedule, by job site, or as a breaks report.
  - Custom reports keep their filters, sort order and columns when exported.
  - Shift History covers 60 days and filters by reason code.
  - https://help.wheniwork.com/articles/exporting-schedules · https://help.wheniwork.com/articles/reporting-reference-computer
- **Report filters.**
  - Sling: day, week, month or a custom range; group by employee, position or location; pick and reorder columns; hours as h:mm or decimal; totals only or detail. https://support.toasttab.com/en/article/Sling-by-Toast-Reports
  - Humanity: filter by period, location, position and employee; export CSV or Excel, or print. https://ithelpdesk.wol.org/support/solutions/articles/19000104372-pulling-reports-within-humanity
- **Scheduled reports.**
  - UKG can run a report on a recurring schedule as PDF, CSV or XLSX and send it to a list of recipients. It recommends CSV for large reports because Excel is slow to render. https://usa50.southalabama.edu/departments/financialaffairs/payroll/resources/dataviews-and-reports.pdf
  - Deputy offers emailed reports in its Analytics+ plan (excerpt).
  - Humanity sends daily email or SMS alerts about staff close to overtime. https://tcpsoftware.com/products/humanity/reporting/
- **Printable sign-in sheets.** A "Daily Schedule Sign-In" report lists position, employee, shift time and hours, with a space for the manager's signature. https://inclusionsystems.zendesk.com/hc/en-us/articles/360045223972-Sign-Off-Sheets
- **Amion.** Tally reports count calls, shifts, clinics and off-schedule items. There is no export button: users copy the table as text into Excel. The docs warn that an overnight shift counted toward the next day can add a phantom shift, so a 19–07 night needs an explicit date rule in every export. https://support.amion.com/hc/en-us/articles/26324867136275-Tally-Statistic-Reports
- **Colombian payroll import files.** Senior/Novasoft's import requires unchanged column headers and a sheet named "DATOS"; its "novedades" include overtime and surcharges. No templates turned up for Siigo or Alegra. https://documentacao.senior.com.br/es/novasoft/manual-del-usuario/docs/manuales_de_usuario/n%C3%B3mina/manuales/IMPORTACI%C3%93N%20DE%20NOVEDADES%20E%20HIST%C3%93RICO%20DE%20VACACIONES.pdf

## B. Excel and print quality

- **UK Government Analysis Function, "Releasing statistics in spreadsheets"** (the strongest primary source here):
  - The first sheet is a cover sheet: title in A1, summary, source, date, whether figures are provisional, contact.
  - Then a contents sheet and a single notes table.
  - One table per sheet, as a named Excel table with unique headers.
  - No merged cells or blank rows inside tables. Units go in brackets. Colour is never the only signal.
  - Select A1 on every sheet and set zoom to 100 % before saving.
  - It advises against freeze panes and filters for accessibility. For an internal working tool a frozen header and filters on data sheets are still worth having.
  - https://analysisfunction.civilservice.gov.uk/policy-store/releasing-statistics-in-spreadsheets/ · https://analysisfunction.civilservice.gov.uk/policy-store/making-spreadsheets-accessible-a-brief-checklist-of-the-basics/
- **Microsoft, Page Setup.** Repeat header rows (and left columns) on every printed page; fit to one page wide with automatic height; landscape. https://support.microsoft.com/en-us/Excel/page-setup
- **Deputy, print redesign.** The Excel export comes pre-formatted. Logo top-left. Published shifts print green, unpublished yellow. Print by area, week or day; two-week views print one week under the other; only what is visible prints. https://www.deputy.com/blog/schedule-printing-improved
- **When I Work, print options.** Toggles for annotations, availability, open shifts, positions, shift notes, site details and unscheduled staff. Unpublished shifts carry an "unpublished" watermark. Output is PDF, or editable XLS for the week view. https://help.wheniwork.com/articles/printing-the-schedule-computer
- **Infor, weekly printout.** Includes absences, availability under each shift, and job, department and break segments. https://docs.infor.com/wfm/2026/en-us/wfmclolh/lfso_admin_cloud/fna1632159426511.html
- **Connecteam.** You choose what to include before printing. https://help.connecteam.com/en/articles/6453258-can-i-export-my-team-s-schedule

## C. Analytics and KPIs not yet in the app

- **Budget vs planned vs actual.** When I Work's weekly Labor Breakdown; Humanity's daily and weekly cost against budget; Deputy's daily wage budget with variance and a same-period-last-year comparison; Sling's projected vs actual spend and labour % against a goal. https://help.deputy.com/hc/en-au/articles/4764591177871
- **Overtime projection.** Humanity's Labor Optimizer adds hours already worked to upcoming shifts and flags who is heading into overtime. SmartLinx shows staff nearing overtime on its dashboard (vendor claim).
- **Schedule quality score.**
  - HotSchedules gives a colour-coded score while you build, with flags that explain each issue (demand vs scheduled hours, overtime risk, availability, labour rules, rest and split shifts), and tracks it over time. https://www.fourth.com/solution/workforce-management-software/schedule-score
  - Zebra proposes a weighted score from under- and overstaffing, coverage, cost including premiums, rule compliance, swap and give-away frequency, and skill match. https://zebra.com/us/en/blog/posts/2023/how-and-why--you-should-assess-schedule-quality-in-workforce-management-software.html
- **Coverage gap per role.** UKG's "Coverage Variance by Zone" shows scheduled vs planned headcount and the gap by time span and job; "Staffing Sheet Detail Daily" works in 15-minute steps (excerpt). The piece the app lacks is the gap per role, totalled as missing staff-hours.
- **Hours per unit of work (HPPD analogue).**
  - Infor's HPPD report: target vs actual hours per patient day, plus agency and non-productive hours. https://docs.infor.com/wfm/7.1.0/en-us/wfmolh/wfmprug/yfw1475662031368.html
  - NHS CHPPD: planned vs actual hours, registered vs non-registered, published with roster fill rates. https://england.nhs.uk/long-read/care-hours-per-patient-day-chppd-guidance-for-all-inpatient-trusts
  - Equivalent here: staff-hours per 100 instrument sets or per imaging study.
- **NHS / RLDatix rostering KPIs.**
  - Roster approval lead time of 6–12 weeks before the roster starts; one RLDatix case used a 42-day target.
  - Net hours balance, with unused hours capped at one shift (7.5 h).
  - Temporary staffing, unfilled extra duties, leave %, planned vs actual unavailability.
  - Benchmarking against other organisations.
  - https://www.rldatix.com/en-uki/solution/workforce-insights/ · https://www.leicspart.nhs.uk/wp-content/uploads/2022/11/Electronic-Rostering-Policy-Exp-Oct-28.pdf
- **Rule-breach register.** UKG gives each breach a severity: informational, warning, or blocks saving. Shiftboard audits manual overrides and records the justification. https://tech.rochester.edu/wp-content/uploads/Track_Rule_Violations.pdf · https://www.shiftboard.com/wp-content/uploads/2021/10/scheduling-compliance-solution-sheet-shiftboard.pdf
- **Audit of changes after publishing.** UKG's Schedule Post Audit Report comes as Full (every day) or Delta (changed days only), with time changes, transfers, break changes and comments (excerpt).
- **Open shifts and time to fill.** Humanity reports open and unfilled shifts, shift acknowledgements and forecasts. ShiftMed (vendor blog) defines time-to-fill and the share filled within a target window. https://www.shiftmed.com/insights/knowledge-center/healthcare-workforce-metrics/
- **Turnover warning signs in schedule data** (M7, vendor blog): sick calls rising against the person's own history; preferences repeatedly overridden; preferences no longer submitted; floating far more than peers; extra shifts no longer picked up; overtime creeping up. https://www.m7health.com/blogs/scheduling-data-nurse-turnover-signals
- **Per-person reliability score.** MangoApps' MangoScore runs from 0 to 1, built from weighted parts with tier thresholds. https://www.mangoapps.com/help/workforce_intelligence
- **Fatigue standards.** ANA (dated 2025 or 2026 depending on the source): at most 40 h a week, at most 3 consecutive 12-hour shifts, 10–12 h rest between shifts. NANN recommends at least 11 h rest. Joint Commission (2011): errors rise above 40 h a week. https://nann.org/wp-content/uploads/2026/08/The-Effect-of-Shift-Work-and-Fatigue_FINAL_2026-1.pdf
- **Colombian law (Ley 2466 de 2025)** (news sources):
  - Night hours start at 19:00 from 25 Dec 2025.
  - The Sunday/holiday surcharge is 90 % from 1 Jul 2026 and 100 % from 1 Jul 2027.
  - The 42-hour week starts 15 Jul 2026 according to most sources.
  - Checked against the app on 15/11/2026: `TARIFAS_BASE` in `an/turnos/db.py` already holds `noche_inicio` 1140 min from 2025-12-25 and `dominical` 90 / 100 from 2026-07-01 / 2027-07-01.
- **Radiology credentials.** Planday tracks document expiry dates. In Colombia, Resolución 1811 de 2025 replaced 482 de 2018 and requires dosimetry records for exposed workers. CST art. 186 gives X-ray workers 15 days of vacation per 6 months worked.

## D. What reviews complain about

- **QGenda:** weak audit trail, calendar views, printing and report setup; some reports are "hard to understand" or "limited". https://www.capterra.com/p/90628/QGenda/reviews/
- **When I Work:** users want to print directly, call the export outdated, want several schedules in one document, and find pay and time reports hard to read. https://www.capterra.com/p/121248/When-I-Work/reviews/
- **Humanity:** reporting covers "the basics" but some fields are missing. https://www.g2.com/products/humanity-schedule-by-tcp/reviews
- **Deputy:** users want control of font size and bold on printed exports. https://www.g2.com/products/deputy/reviews_and_filters
- **EasyShifts:** users want a daily printout and a staffing-level report.
- **ShiftWizard:** approval notices don't say which day was approved, so change notices should always state explicit dates.

Pattern: reports that read without explanation, control over print layout, every field available, combined printouts, and a clear audit trail.

## Ranked candidates for a small portable app (S/M/L effort)

1. Date-aware surcharge rates and a forecast (M). Already present in the app's data.
2. Payroll "novedades" export with a configurable column template (M). The user deferred this until the payroll system is known.
3. Rule-breach register in Excel and print: rule, person, date, severity, override reason (S/M).
4. Comparison between published roster versions (full or changes only), with notices only for the people affected (S/M).
5. Schedule quality score with a traffic light and a trend (M).
6. Budget vs planned vs actual (M). Needs budget data.
7. Excel standards pass: cover/README information, frozen headers, filters, repeated print titles, landscape fit to width, no merged cells in data (S).
8. Print pack: one-page landscape wall poster with legend, version, draft watermark and signature box; daily sign-in sheet (S).
9. One-page profile per person (M).
10. NHS-style roster KPIs: publication lead time, fill rate, time to fill, hours balances outside tolerance (S/M).

Next in line: credentials and dosimetry tracking (M); staff-hours per unit of work (M); a one-click monthly zip of every report (S).
