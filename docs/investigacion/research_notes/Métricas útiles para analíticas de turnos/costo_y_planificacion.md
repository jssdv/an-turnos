# Métricas de costo laboral, calidad de planificación y eficiencia del planificador (dashboards de turnos)

Context: small team (~40), Colombia, no salary data, so cost is shown in equivalent hours. Researched November 2026. A lot of the vendor material is marketing or help-center content. Each item is labelled.

## Which KPIs do WFM tools (UKG, Quinyx, Deputy, Shiftboard, Legion, HealthRoster) put on manager scheduling dashboards, and how are they defined?

### Takeaway
The KPIs that recur across vendors are:
- scheduled vs nominal/contract hours
- scheduled vs optimal (forecast) staffing
- scheduled vs worked hours
- labor cost or hours vs budget
- overtime %
- fill rate and time-to-fill for open shifts
- schedule stability (changes after publication)
- a composite "schedule score"

No vendor publishes a standard formula. Definitions vary, especially the denominator for overtime %. For a team of 40 with no salaries, the useful subset is the hours-based one: premium hours, overtime %, fill rate, changes after publication, and scheduled vs contract hours.

### Cited Findings
- Quinyx lists these scheduling KPIs, with no formulas or benchmarks given: number of scheduled employees (with absent/requests shown); scheduled hours vs nominal (contract) hours, to see over- or under-use, noting that the extra hours may be employee-requested or gap-filling; worked vs nominal hours; expected hours (upcoming shifts) vs nominal, to project the period total; forecasted metrics; optimal headcount vs scheduled, called "the ultimate scheduling metric" — [Quinyx blog](https://www.quinyx.com/blog/the-scheduling-kpis-you-should-be-measuring)
- Quinyx configurable Scheduling KPI types include "Productivity" and "Labour Cost or Hours", with totals for the whole schedule period. They are set under Optimisation settings > Scheduling KPIs and Targets — [Quinyx help: Scheduling KPIs](https://quinyx.helpdocs.io/l/en/article/3va431v8rj-scheduling-kp-is)
- Quinyx Advanced Analytics (beta) predefined KPIs include "Scheduled Hours vs Worked Hours" and "Actual Staff Cost trend". Insights compares scheduled vs optimal staffing per hour, day and site — [Quinyx Advanced Analytics](https://quinyx.helpdocs.io/l/en/article/dpy9hazv7m-advanced-analytics); [Quinyx Insights](https://www.quinyx.com/optimize-your-business/optimize-insights)
- Legion uses a weighted "Schedule Score" to judge whether a schedule meets objectives (peak/non-peak accuracy, compliance, budget, employee availability). Its dashboards show whether manager edits raise or lower the score, and only edits that raise the score without breaking rules feed its learning. The formula is not published — [Legion automated scheduling datasheet](https://legion.co/resources/datasheets/automated-scheduling-datasheet/pdf); [Legion schedule optimization](https://legion.co/en-gb/products/schedule-optimization/)
- Shyft gives these definitions (one vendor's blog, not a standard):
  - Fill rate: % of shifts filled as scheduled without last-minute adjustments or overtime. Target 95–100%.
  - Time-to-fill: average time to cover an open shift.
  - Schedule adherence: (hours worked as scheduled ÷ scheduled hours) × 100.
  - Overtime %: overtime hours ÷ total hours worked. Shyft also defines a separate "overtime cost %" (premium cost ÷ labor cost).
  - Schedule stability: how often schedules change after publication.
  — [Shyft: schedule optimization metrics](https://www.myshyft.com/blog/schedule-optimization-metrics/); [Shyft: schedule-related KPIs](https://myshyft.com/blog/schedule-related-kpis)
- Healthcare usage of "fill rate" (NHS) comes in two forms:
  - Shift level: shifts filled (bank + agency) ÷ shifts requested. Example: an East Lancashire FOI table totals 4,513 / 5,541 = 81.45%. — [ELHT FOI 2024-369](https://elht.nhs.uk/about-us/freedom-of-information/foi-requests/foi-2024-369)
  - Ward level: actual nursing hours delivered ÷ planned hours (the post-Francis "safe staffing" fill rate). Nuffield Trust warns that fill rate alone hides permanent vacancies and skill-mix problems. — [Nuffield Trust](https://nuffieldtrust.org.uk/news-item/temporary-nursing-we-re-banking-on-better-information)
- Buckinghamshire Healthcare reported a bank fill rate of about 85% (June 2023), later 93% for Band 2–3 nurses — [NHS Professionals case study](https://www.nhsprofessionals.nhs.uk/partners/publications-and-insights/case-studies/closing-the-gap-between-substantive-and-contingent-workforce-at-buckinghamshire-healthcare)
- Patchwork Health (vendor data) says shifts requested at least 6 weeks ahead have a fill rate 10% higher than shifts requested up to 1 week ahead. This supports showing fill rate split by lead time — [Patchwork: 5 tactics to improve fill rates](https://www.patchwork.health/blog/patchwork-insights-5-tactics-to-improve-your-shift-fill-rates)

### Inferences
- Metrics that map onto the app's data, for a 40-person team:
  - (1) Premium hours as % of scheduled hours, split by night, Sunday/holiday and overtime. Shown as a monthly stacked bar.
  - (2) Overtime % = overtime hours ÷ total scheduled hours. State the denominator on the chart.
  - (3) Scheduled vs contract hours per person. A dot or bar chart with a reference line at the contract value shows over- and under-use.
  - (4) Shortages / unmet coverage from the solver log, as the analogue of "scheduled vs optimal". Uncovered slot-hours ÷ required slot-hours = coverage fill rate.
  - (5) Schedule stability: changes after publication per 100 shifts, by change type (swap, service need, adjustment), from the change log plus the published-version timestamp.
- A Legion-style composite score is not worth building for one team. The separate components (coverage, unmet requests, rule violations) are easier to read and explain.
- Ward-level "planned vs delivered hours" fill rate works well here: published roster = planned, current roster = delivered or expected.

### Gaps
- I did not open UKG, Deputy, Shiftboard or Allocate/RLDatix HealthRoster help-center KPI pages. I found no published formal definitions for UKG "schedule stability" or for HealthRoster KPIs (for example its "roster approval lead time"). Those pages may need a logged-in account.
- None of the sources gives a benchmark for "changes after publication per 100 shifts".

## How should Colombian surcharge cost be presented given the 2025–2027 Sunday/holiday increase (Ley 2466 de 2025), and is there guidance on projecting its impact?

### Takeaway
The Sunday/holiday surcharge rises in dated steps: 75% until 30 Jun 2025, 80% from 1 Jul 2025, 90% from 1 Jul 2026 (in force now), and 100% from 1 Jul 2027. The night window also widened on 25 Dec 2025 (19:00–06:00, previously 21:00–06:00). The ordinary week fell to 42 h on 15 Jul 2026. Without salaries, the clean presentation is "premium equivalent hours" = Σ(hours × surcharge rate in force on that date). The impact of the 2027 step can be projected by re-pricing the same planned hours at the next rate. I found no official projection method; the published guidance is per-shift worked examples only.

### Cited Findings
- Sunday/holiday schedule under art. 14 of Ley 2466 (modifies art. 179 CST, transitional paragraph): 75% until June 2025; 80% from 1 Jul 2025; 90% from 1 Jul 2026; 100% from 1 Jul 2027 — [Bloomberg Línea, 1 Jul 2026](https://www.bloomberglinea.com/latinoamerica/colombia/pago-de-domingos-y-festivos-sube-al-90-desde-hoy-1-de-julio-de-2026-en-colombia/); [Buk](https://www.buk.co/blog/reforma-laboral-ley-2466-de-2025-impacto-en-nomina); [Portafolio](https://www.portafolio.co/economia/gobierno/atencion-desde-hoy-primero-de-julio-el-recargo-dominical-sube-al-90-y-la-reduccion-de-la-jornada-inicia-el-497268)
- MinTrabajo Concepto 24429 de 2026 restates the gradual schedule and says habitual Sunday work requires both the surcharge and paid compensatory rest — [Accounter summary of Concepto 24429/2026](https://accounter.co/normatividad/trabajo-dominical-habitual-exige-recargo-y-descanso-compensatorio-remunerado-concepto-mintrabajo-24429-de-2026)
- Night work runs 19:00–06:00 from 25 Dec 2025 (art. 10 of Ley 2466, modifying art. 160 CST). It previously started at 21:00. The night surcharge stays at 35% over the ordinary hour — [Actualícese](https://actualicese.com/recargo-nocturno-en-colombia-conoce-el-horario-aplicable-a-partir-del-25-de-diciembre-de-2025/); [Buk](https://www.buk.co/blog/reforma-laboral-ley-2466-de-2025-impacto-en-nomina); [El Tiempo](https://www.eltiempo.com/economia/finanzas-personales/inicio-el-pago-de-las-horas-nocturnas-desde-las-7-de-la-noche-el-abc-del-cambio-que-comenzo-a-regir-a-partir-del-25-de-diciembre-3519795)
- Maximum ordinary week reached 42 h on 15 Jul 2026 (Ley 2101 de 2021) — [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/colombia/pago-de-domingos-y-festivos-sube-al-90-desde-hoy-1-de-julio-de-2026-en-colombia/)
- Buk's worked example: salary COP 2,500,000, divisor 210 (42 h week), ordinary hour ≈ 11,904.76. An 8 h Sunday shift then costs: base 95,238 + surcharge 71,429 at 75% = 166,667; at 90%, surcharge 85,714 = 180,952; at 100%, surcharge 95,238 = 190,476. The surcharge is proportional to hours worked — [Buk](https://www.buk.co/blog/reforma-laboral-ley-2466-de-2025-impacto-en-nomina)
- Overtime (art. 168 CST): daytime overtime +25%, night overtime +75%, over the ordinary hour. Limit is 2 h/day and 12 h/week — [Gerencie](https://www.gerencie.com/horas-extras-y-recargos-nocturnos-dominicales-y-festivos.html); [vLex art. 168](https://vlex.com.co/vid/trabajo-nocturno-suplementario-439187418)
- Stacking: secondary sources say surcharges are cumulative. Sunday night = Sunday % + 35%; overtime on a Sunday = overtime % + Sunday %. Pre-reform examples are 25+75 = 100% and 75+75 = 150%, and one calculator applies 200% to Sunday night overtime. Sources disagree on the exact composition — [Gerencie](https://www.gerencie.com/horas-extras-y-recargos-nocturnos-dominicales-y-festivos.html); [Siempre al Día](https://siemprealdia.co/colombia/derecho-laboral/horas-extra-y-recargos-nocturnos/)
- Article 12 of Ley 2466: employers must keep a record of overtime hours; no prior MinTrabajo permit is needed — [Buk](https://www.buk.co/blog/reforma-laboral-ley-2466-de-2025-impacto-en-nomina)
- Press coverage says the changes raise employer labor cost and force a review of shift programming. Affected sectors named include health, security and transport. The coverage gives no quantitative estimates — [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/colombia/pago-de-domingos-y-festivos-sube-al-90-desde-hoy-1-de-julio-de-2026-en-colombia/)

### Inferences
- **Equivalent-hours metric.** Premium equivalent hours (PEH) = Σ over hours h of rate(h, date). Example: 8 h Sunday at 90% = 7.2 PEH. Full cost in equivalent hours = ordinary hours + PEH. This is salary-independent. With a uniform salary, PEH ÷ ordinary hours equals the premium share of payroll for those hours.
- **Rates as dated data.** The app should store rates with validity dates: Sunday 75/80/90/100 and the night window 21:00 to 19:00. Each shift is then priced by its own date. Otherwise historical months get re-priced wrongly. The night-window change on 25 Dec 2025 is a second step change in the series, and the app's rate table does not seem to model it yet.
- **Chart 1:** monthly stacked bars of PEH by component (night, Sunday/holiday, overtime daytime/night), with vertical markers at 1 Jul 2025, 25 Dec 2025, 1 Jul 2026 and 1 Jul 2027. This separates "more Sunday hours scheduled" (volume) from "higher rate" (price).
- **Chart 2:** a simple projection. Take the current or last-12-months Sunday/holiday hours and show PEH at 80%, 90% and 100%. Δ PEH for the 2027 step = Sunday hours × 0.10; for example 300 Sunday hours/month gives +30 PEH/month. Optionally split the variance into volume effect (Δhours × old rate) and rate effect (hours × Δrate).
- **Denominator caveat.** The ordinary hour value changed with the 44, then 42 h week (divisor 220 to 210 in Buk's example). PEH expressed in hours is unaffected. Any conversion to pesos must use the divisor in force on that date.

### Gaps
- I could not fetch the official text of Ley 2466 (Secretaría del Senado / Función Pública). Dates and percentages come from consistent secondary sources (Buk, Bloomberg Línea, Portafolio, Actualícese) and a summary of MinTrabajo Concepto 24429/2026.
- The exact stacking rule for overtime on Sunday/holiday under the new rates is inconsistent across secondary sources. It needs a check with a labor lawyer or the official CST text.
- Whether the Sunday surcharge treats a habitual vs occasional Sunday differently in the premium calculation (beyond compensatory rest) was not fully resolved.
- I found no official MinTrabajo guidance on projecting the payroll impact.

## What does absence seasonality look like (monthly, holiday periods), what simple forecasting suits a small team, and is there evidence it helps planning?

### Takeaway
Healthcare sickness absence peaks in winter, and published SARIMA studies found the winter rise "largely predictable". For a 40-person team with a short history, sophisticated models are not justified. A seasonal-naive forecast (same month last year) and a trailing 3–12-month moving average are the standard baselines. Papers use them as benchmarks, and complex models must beat them. The evidence that forecasting helps planning is mostly indirect: requesting cover earlier raises fill rates.

### Cited Findings
- RCN analysis of NHS England data: sickness absence rises in certain months across all integrated care systems, and seasonal sickness combines with higher winter demand — [RCN workforce sickness absence](https://rcn.org.uk/employment-and-pay/Nursing-workforce-insights/Workforce-sickness-and-absence)
- NHS staff absence peaked at 4.41% in December 2018 (all staff groups) — [HR Review, "Dire December"](https://www.hrreview.co.uk/hr-news/this-week-will-see-unplanned-staff-leave-spike/122418)
- BMJ Open (2021, ambulance service staff, clinical group including nurses): winter increases in sickness absence were "largely predictable" with seasonally adjusted (SARIMA) time-series models — [BMJ Open, doi 10.1136/bmjopen-2021-053885 (White Rose eprint)](https://eprints.whiterose.ac.uk/185096/1/e053885.full.pdf). I could not read the full PDF text; the finding comes from the search snippet.
- A 2023 review of sick-leave determinants in healthcare found that seasonality is moderately strongly associated with absence — [Scholastica BHM PDF](https://bhm.scholasticahq.com/article/57688.pdf)
- A Hong Kong study of healthcare workers during a seasonal flu epidemic found 8.4% excess absenteeism from any cause and 26.5% from respiratory causes (cited in an Italian hospital study) — [Univ. Torino / PLOS ONE](https://iris.unito.it/retrieve/handle/2318/1660473/391018/pone.0182510.pdf)
- IEEE DSAA 2024 "No Data Left Behind" forecasts nursing staff capacity by ward and benchmarks models against ARIMA and a seasonal-naive baseline — [Unpaywall record](https://unpaywall.org/10.1109%2FDSAA61799.2024.10722806)
- A UT Austin thesis forecast weekly nurse sick-leave use with neural networks from 3 years of absence reports — [UT repository](https://repositories.tdl.org/tdl-ir/handle/2152/ETD-UT-2010-12-2259)
- A Melbourne secondary hospital 10-year payroll study (2007–2016) analysed absence seasonality and leave category. I could not access the monthly results — [CORE](https://core.ac.uk/works/8487628)
- Lead time and coverage: shifts requested at least 6 weeks ahead fill about 10% better than those requested at most 1 week ahead (vendor data) — [Patchwork](https://www.patchwork.health/blog/patchwork-insights-5-tactics-to-improve-your-shift-fill-rates)

### Inferences
- **Absence calendar.** Absence-days by month (and by type), drawn as a heatmap or small-multiple bars with one line per year. Planned types (vacation, leave) should be separated from unplanned ones (sickness, calamity). Their seasonality has different causes: Colombian vacations cluster in December–January and mid-year, while sickness follows the respiratory season. Colombia is equatorial, so there is no winter. Bogotá-area respiratory peaks follow the rainy seasons (roughly April–May and October–November). This is my inference and is not sourced here; verify with INS data if needed.
- **Forecast.** For month m: seasonal-naive = absences(m, last year). Moving average = mean of the last 3 months. Show both as a band and the next 3 months as a forecast. With fewer than 2 years of history, label it "reference, not forecast". Accuracy can be tracked with MAE against actuals.
- **Short-notice absences.** The app has no creation timestamp, so true notice cannot be measured. Possible proxies:
  - (a) the change-log entry (type "service need") that replaced the absent worker; the gap between the change timestamp and the shift start is the effective notice / time-to-fill;
  - (b) absences that start after the roster version was published count as "post-publication absences".
  - The recommendation is to add `created_at` to absences.
- **Replacement metrics.**
  - Fill rate = absence-affected shifts covered ÷ absence-affected shifts.
  - Time-to-fill = time from the change-log entry to coverage, or time from publication to the replacement.
  - Unfilled shifts per month.

### Gaps
- I found no study that quantifies the planning benefit of absence forecasting for small teams (for example, fewer unfilled shifts).
- I found no Colombian data on monthly absence seasonality for health workers. MinSalud, Fasecolda and INS sources were not searched.
- The monthly curve from the Melbourne study and the full BMJ Open results were not readable.

## Which metrics describe the scheduling process itself (time to publish, number of regenerations, % of solver runs feasible, manual edit rate), and is there evidence on time saved by automated vs manual rostering?

### Takeaway
Hard evidence is thin. Surveyed nurse rosterers spend 1–3+ days per month on rosters. Case studies report 50–90% reductions in rostering time with automated or AI tools, but these are self-reported by vendors or award entries. Advance notice is a measured outcome in fair-workweek research, where the 2-week threshold is the common benchmark. Healthcare rosters in one study were published 6–8 weeks ahead. Solver-process KPIs (feasibility rate, runs per published roster, manual edit rate) are not standardised in the sources. Legion's "edits vs score" view is the closest vendor analogue.

### Cited Findings
- Booker et al., *BMC Nursing* 2024 (24 roster-creating nurses, 3 Victorian hospitals):
  - Rosterers get about 1 day/month for rostering; one said "at least 3 days a month", sometimes working at home.
  - Rosters were completed 6–8 weeks ahead.
  - Informal swaps after publication were common and led to "double-handling".
  — [PMC11057102](https://pmc.ncbi.nlm.nih.gov/articles/PMC11057102/)
- Royal Hobart Hospital (vendor HosPortal whitepaper, medical rosters): manual drafts took up to 4 days per roster. AI cut review and finalisation to 4–5 hours (about 90% less). Self-reported by the vendor — [HosPortal whitepaper PDF](https://www.hosportal.com/wp-content/uploads/2025/06/RHHAIJan2025v2.pdf)
- Singapore NurseShift.ai (NHIP 2025 award entry) reports a 51% reduction in roster-management time (self-reported) — [CHI Singapore](https://child.chi.sg/learn/child-collection/projects/ai-powered-nurse-rostering-for-smarter-care-and-better-outcomes/); [award PDF](https://chiinnovate2025.klobbi.com/pdfs/winners/automation/2.pdf)
- Deputy case study: NurseWatch reached "1-hour rostering" (vendor case study) — [casestudies.com](https://www.casestudies.com/company/deputy/case-study/reinventing-premium-on-demand-wellness-and-care-in-australia-and-beyond)
- In an Irish audit of an automated rostering system, 33% of nurse managers said a roster took 5 minutes to 1 hour; the full distribution is not visible — [IOS Press](https://ebooks.iospress.nl/pdf/doi/10.3233/978-1-60750-024-7-96)
- UK ward-manager interviews: one red/amber staffing incident often took about 4 hours of manager and staff time to resolve. This shows the cost of reactive rescheduling — [Southampton thesis](https://eprints.soton.ac.uk/501117/1/FinalVer_Thesis_TE.pdf)
- Advance-notice evidence:
  - A PNAS study of Seattle's secure-scheduling ordinance found a 13 percentage-point increase in workers getting at least 2 weeks' notice and 6 pp fewer last-minute changes, with no evidence of wage or benefit cuts. — [HKS summary](https://www.hks.harvard.edu/faculty-research/policy-topics/business-regulation/study-more-notice-shift-schedules-improves-lives)
  - Nationally, 59% of US service workers get less than 2 weeks' notice. — [Shift Project fact sheet](https://shift.hks.harvard.edu/wp-content/uploads/2026/07/fww_factsheet_report_final.pdf)
  - In Los Angeles, 41% get at least 2 weeks' notice; the ordinance requires 14 days. — [Shift Project LA brief](https://shift.hks.harvard.edu/wp-content/uploads/2026/01/LosAngeles_SchedulingBrief.pdf)
- Legion dashboards show whether manager edits improve or worsen the Schedule Score. This is in effect a "manual edit quality" metric — [Legion datasheet](https://legion.co/resources/datasheets/automated-scheduling-datasheet/pdf)
- Schedule stability (changes after publication) is used as a quality signal: fewer late changes means higher quality (vendor definition) — [Shyft](https://www.myshyft.com/blog/schedule-optimization-metrics/)

### Inferences
Process KPIs computable from the app's data:
- **Publication lead time** = start of the roster period − publication timestamp, in days. Chart it per period against reference lines at 14 days (fair-workweek benchmark) and 6–8 weeks (Booker et al. practice).
- **Runs per published roster** = solver runs between the previous publication and this one. Also the elapsed planning window = last run end − first run start.
- **Feasibility rate** = runs with status optimal/feasible ÷ total runs. Also **median solve time** = end − start.
- **Residual unmet requests and shortages** of the run that became the published version. Show their trend across periods, and optionally the objective value.
- **Post-publication change rate** = change-log entries after publication ÷ shifts in the period, split by swap / service need / adjustment. Swaps are employee-driven and are less a sign of planning failure. "Adjustment" entries are the manual-edit rate.
- **Published vs current diff** = % of shift assignments that differ between the published version and the current version. This is a stability index.
- **Time saved vs manual** cannot be measured without a baseline. Options: record the pre-tool manual time once (interview the planner), or show "planner active time" = sum of run windows plus edit sessions. Literature for context: manual 1–4 days per roster, tools report 50–90% reductions, vendor self-reported.
- **Simple charts:** a lead-time bar per period with a 14-day line; stacked bars of changes by type per period; a runs-per-period dot plot coloured by status; a small KPI tile row (lead time, feasibility %, post-publication changes, unmet requests).

### Gaps
- I found no peer-reviewed controlled study of manual vs automated nurse-rostering time. All quantitative savings found are vendor- or award-reported.
- I found no published benchmark for solver feasibility rate, runs per roster, or manual-edit rate in OR or WFM literature. The Burke et al. state-of-the-art nurse rostering review was not consulted.
- I found no Colombian legal requirement on how far ahead rosters must be published. The CST/Ley 2466 search did not surface one; this needs a check.
