# Coverage and staffing-versus-demand analytics for shift rostering

Context: small hospital support team (~40 people), monthly rosters, demand per position in 30-min slots split into mandatory and desirable, roster person x day -> shift with start/end. Already built: days with deficit/excess, N+1 margin days, risk days. Notes below focus on what else is computable from roster + demand slots only.

Source-quality note: Infor and Dayforce pages were fetched in full. Dialpad, ServiceNow, Snap Schedule, Timefold, Oracle, UKG and Quinyx details come from search-result summaries of their own help/product pages (Timefold and UKG help pages returned 404 on direct fetch). Treat those as indicative, not verbatim.

## 1. Standard coverage / understaffing / overstaffing metrics and their formulas

### Takeaway
The core vendor metrics are all built on per-interval net gap (scheduled minus required), summed separately for shortfall and surplus, then normalized by total required. Infor publishes exact formulas for "coverage" and "efficiency"; NHS uses "fill rate" (actual/planned hours) by day/night; research uses "% of shifts understaffed beyond a threshold" (e.g. >15% short). All are computable from roster + demand slots.

### Cited Findings
- Infor WFM: **Coverage = 1 − (Total Understaffed ÷ Interval Requirement)**; **Efficiency = 1 − ((Total Overstaffed + Total Understaffed) ÷ Interval Requirement)**. Interval Requirement is the sum of required employees across intervals, per department; rounded to whole percent. Worked example: requirement 36, understaffed 9, overstaffed 9, so coverage 75%, efficiency 50% — [Infor WFM 2026, Coverage and efficiency calculations](https://docs.infor.com/wfm/2026/en-us/wfmclolh/reporting_birst_user_cloud/lnj1614975615197.html); also [Infor WFM 7.0 doc](https://docs.infor.com/wfm/7.0.0/en-us/wfmolh/wfmsrug/sml1476285324239.html)
- Infor scenario docs warn that surplus in one period can mask a shortfall in another, so a day can look fully covered when it is not (argues for computing gaps per slot before aggregating) — [Infor Job Times Coverage Scenarios](https://docs.infor.com/wfm/2026.10/en-us/wfmopolh/mvs_legacy_user_on-premise/dvu1475661991644.html); a UC Health (API Healthcare) report similarly treats a shift as fully staffed when under- and overstaffed profiles offset — [UC Health API Healthcare help](https://api2018.uchealth.com/APIHC/TASS/WebPortal/APIHealthcare_Live/help/60333.htm)
- Dayforce "Coverage Score": a percentage of how closely the schedule matches requirements across the day; "100% score means that your schedule matches the staffing requirements at each point in the day". Score drops whenever a zone is under- or overstaffed at any point; for zones without a labor curve, overstaffing lowers it proportionally (10% overstaffed = 90%). Example zone: 72.8% score, 106.5 planned hours, 39.75 hours understaffed. No exact formula published — [Dayforce Coverage Scores](https://help.dayforce.com/r/manager-guide/Coverage-Scores)
- Oracle Workforce Scheduling "Schedule Coverage Variance" shows hours overstaffed or understaffed for each day interval — [Oracle 24A readiness](https://docs.oracle.com/en/cloud/saas/readiness/hcm/24a/wosc-24a/24A-workforce-scheduling-wn-f31256.htm)
- Dialpad and Soon.works compute net = scheduled − required per interval (positive = surplus); Dialpad lets users toggle hours vs FTE — [Dialpad Insights report](https://help.dialpad.com/docs/using-the-insights-report.md); [Soon.works staffing coverage and gaps](https://soon.works/help/schedule-board/understand-staffing-coverage-and-gaps)
- UKG Dimensions "Coverage Detail Weekly" report: scheduled coverage and variance per job by shift or schedule zone, against a workload/forecast plan, at 15-minute granularity; "Staffing Sheet Daily" for charge nurses to check each zone/shift has sufficient coverage — [UKG blog, healthcare reports](https://www.ukg.com/blogs/ukg-blog-post/make-better-healthcare-staffing-decisions-these-ukg-dimensions-reports)
- NHS **fill rate** = actual hours as % of planned hours, reported separately for registered nurses and care staff and for day vs night shifts — [FHFT safe staffing page](https://www.fhft.nhs.uk/about-us/how-we-are-run/our-performance/nursing-and-midwifery-safe-staffing-inpatient-bedded-area); trust monthly reports publish planned hours, actual hours, fill rate and CHPPD by ward, and ward fill rates above 100% occur (one March 2026 line: 147.5% care staff day) — [The Christie, safe staffing March 2026](https://www.christie.nhs.uk/media/04gc3x44/safe-staffing-march-2026.pdf)
- A trust RAG scheme on fill rate: green 90–110% of planned, amber 80–<90%, red <80%, blue >110% (overfill). Trusts set their own bands — [Sherwood Forest Hospitals, safe staffing appendix 2](https://www.sfh-tr.nhs.uk/media/2475/enc-11-safe-staffing-appendix-2-description-of-tha-data-monitoring-colour-codes.pdf)
- Research metric (Saville, Monks, Griffiths, Ball): primary outcome is **% of patient shifts understaffed**, defined as more than 15% short of the day's requirement; also % of shifts overstaffed. Standard (mean-demand) staffing gave 31.8% understaffed / 4.4% overstaffed shifts; ward-level understaffing ranged 7%–80% of shifts — [Saville et al., BMJ Qual Saf (PMC7788209)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7788209)
- Nurse-rostering OR literature treats coverage as minimum/maximum thresholds per shift; going below min or above max is allowed but penalized as soft-constraint violation (Bilgin et al. 2012), while in practice head nurses often relax "hard" coverage constraints (De Causmaecker and Vanden Berghe 2003) — [search summary of Bilgin et al., Annals of OR](https://springerlink.bibliotecabuap.elogim.com/content/pdf/10.1007/s10479-010-0804-0.pdf); [Relaxation of Coverage Constraints in Hospital Personnel Rostering](https://bvbvf1.bib-bvb.de/vufind/PrimoRecord/cdi_pascalfrancis_primary_15691829). Survey reference: Burke, De Causmaecker, Vanden Berghe, Van Landeghem, "The State of the Art of Nurse Rostering", J. Scheduling 7(6) 2004 — [PDF](https://alexandrechecoli.github.io/1-meta/Materiais/Artigos/2004%20-%20The%20State%20of%20the%20Art%20of%20Nurse%20Rostering%20-%20Burke,%20Causmaecker.pdf)

### Inferences
Concrete metrics computable from roster + 30-min demand slots (s = slot, p = position; staffed(s,p) = people on shift covering slot; M = mandatory, D = desirable):
- **Under person-hours (mandatory)** = Σ_s max(0, M − staffed) × 0.5 h. Compute per slot, then sum (avoids the Infor netting trap).
- **Over person-hours (vs desirable)** = Σ_s max(0, staffed − D) × 0.5 h. Using D as the upper reference fits the mandatory/desirable split: below M = deficit, M..D = acceptable band, above D = excess. This mirrors the OR min/max coverage thresholds.
- **Desirable gap hours** = Σ_s max(0, D − staffed) restricted to slots where staffed ≥ M (shortfall that is not a safety issue).
- **Coverage % (Infor)** = 1 − Σunder / ΣM, and **Efficiency % (Infor)** = 1 − (Σunder + Σover) / ΣM. Report by month, position, franja, weekday.
- **Slot coverage %** = count(slots with staffed ≥ M) / count(slots with M > 0). Simple and intuitive; complements the hours-weighted version.
- **Fill rate % by franja** = scheduled person-hours / required (M) person-hours, split morning/afternoon/night like NHS day/night split, with a RAG band (e.g. 90–110 green, 80–90 amber, <80 red, >110 blue). Band values are local policy, not a standard.
- **% of franjas understaffed beyond threshold** (Saville style): franja-days where Σunder / ΣM in that franja > 15%. Gives a single "how often are we badly short" number, more robust than counting any deficit.
- **Daily coverage score** (Dayforce style): per day, 1 − (Σ|staffed − M| over slots outside [M, D]) / ΣM, giving 100% when every slot is within band.

### Gaps
- No published formula for Dayforce coverage score; "staffing variance" and "schedule efficiency" are used loosely across vendors (Infor's efficiency is the only exact definition found).
- Shiftboard, Planday, Humanity, ShiftWizard, Rotaville: no coverage-metric documentation found in searches.

## 2. Recommended visualizations and evidence they help

### Takeaway
The dominant pattern across vendors is a time-interval grid (hour/slot x day or weekday) colored by signed net gap with a diverging palette (one hue for shortfall, another for surplus, gray/green for match), plus a daily line/area chart of scheduled vs required. No rigorous evidence was found that a particular visualization improves decisions; justification is vendor usability claims.

### Cited Findings
- Timefold "Shift efficiency" view (preview feature): grid with hour of day vs day of week; each cell counts unassigned shifts overlapping that slot, to surface recurring shortages and time-of-day bottlenecks — [Timefold visualizations docs (search summary)](https://docs.timefold.ai/employee-shift-scheduling/1.31.x/user-guide/visualizations)
- Dialpad coverage heatmap: net staffing (scheduled − required) per interval; day range per queue per hour, week range per day per hour; not available at month range. Coverage bar uses 15-min cells: gray met, red deficit, blue surplus; darker shade = larger gap — [Dialpad Schedule Coverage Bar](https://help.dialpad.com/hc/en-us/articles/55396397107099); [Dialpad Insights](https://help.dialpad.com/docs/using-the-insights-report.md)
- Assembled "Staffing Heatmap" report defines net staffing as scheduled minus required (page 403 on fetch; from search summary) — [Assembled support](https://support.assembled.com/hc/en-us/articles/4414692713357-Understanding-the-Staffing-Heatmap-report)
- ServiceNow Demand Forecast: hourly cells green when scheduled matches demand, yellow surplus, red shortfall — [ServiceNow docs](https://www.servicenow.com/docs/r/t~YvqQkg2oQX4L7ySrpyuQ/FRtoZQYnL35PSXnq_yhzcA)
- Snap Schedule: daily line-and-area chart of scheduled vs required staff; understaffing visible where fill falls below required line — [Snap Schedule Scheduler Dashboard](https://www.snapschedule.com/docs/ss365/scheduler-manual/Scheduling_Your_Employees/Scheduler-Dashboard.html)
- Dayforce: hovering a zone shows its coverage graph, hours demanded, and hours under/overstaffed; overall location coverage combines zones — [Dayforce Coverage Scores](https://help.dayforce.com/r/manager-guide/Coverage-Scores)
- Quinyx Insights "visually compares scheduled vs optimal staffing" per hour/day/site; Business View compares scheduled employees across shift types and days to spot imbalances. Vendor-claimed (unverified) 20–30% reduction in overstaffing costs — [Quinyx Workforce Insights](https://www.quinyx.com/workforce-management/workforce-insights); [Quinyx Business View](https://www.quinyx.com/product-hub/business-view-staff-coverage)
- UKG Dimensions supports configurable heatmaps in calendar views (configuration page found, content not retrieved) — [UKG Configure heatmaps](https://dcus11-hlp01.gss.mykronos.com/help/en_US/Content/ApplicationSetup/CalendarViewsSetup/Calendar_Configuration_Heatmap.htm)

### Inferences
Worth adding, in order of value for a monthly roster:
1. **Weekday x 30-min slot heatmap of mean net gap** (staffed − M, or staffed − D toggle), aggregated over the month, diverging palette. Reveals structural shortfalls (e.g. every Monday 06:00–07:00 short) that day-level deficit lists hide. Slot grain already exists in the data.
2. **Calendar heatmap (day of month x franja)** colored by fill-rate RAG band — closest analog to NHS ward safe-staffing tables.
3. **Daily step chart for a selected day**: required M and D as lines/band, staffed as step area. Directly explains why a day is flagged.
4. **Histogram of per-slot margin (staffed − M)**: shows how much of the month is at exactly 0 margin (fragile) vs comfortably above. Complements existing N+1 flag.
Evidence for decision benefit is anecdotal/vendor-only.

### Gaps
- No peer-reviewed study found comparing coverage visualizations for rostering decisions.
- No documentation found for Allocate/RLDatix HealthRoster, ShiftWizard, Rotaville, Planday, Humanity, Shiftboard coverage chart designs.

## 3. How tools present coverage analytics (vendor survey)

### Takeaway
Healthcare-specific suites (RLDatix SafeCare, UKG Dimensions) frame coverage as planned vs actual vs required hours per ward/shift with RAG bands; general WFM tools (Infor, Dayforce, Dialpad, ServiceNow, Quinyx) frame it as per-interval net gap with a summary percentage score.

### Cited Findings
- RLDatix/Allocate SafeCare: reports planned, actual and required care hours; computes required care hours (CHPPD) from census and levels of care (SNCT, MHOST acuity tools); "Unfilled Duties Mode" measures planned vs actual using the budget/establishment in Allocate Optima — [RLDatix SafeCare for care homes brochure](https://www.rldatix.com/en-uki/wp-content/uploads/sites/6/2025/08/SafeCare-for-Indie-Care-Homes-2024-Rebrand.pdf); [Allocate SafeCare](https://allocate-workforce.rldatix.com/allocate-safecare)
- UKG Dimensions: Coverage Detail Weekly (15-min variance per job/zone), Staffing Sheet Daily, Department Actuals (actual vs scheduled) — [UKG blog](https://www.ukg.com/blogs/ukg-blog-post/make-better-healthcare-staffing-decisions-these-ukg-dimensions-reports)
- Infor: coverage % and efficiency %, staff coverage view in Schedule Zone — [Infor coverage calc](https://docs.infor.com/wfm/2026/en-us/wfmclolh/reporting_birst_user_cloud/lnj1614975615197.html); [Infor Schedule Zone coverage](https://docs.infor.com/wfm/2025/en-us/wfmclolh/mvs_user_cloud/alb1586376069308.html)
- Dayforce: single coverage score per day/zone, with hours under/overstaffed — [Dayforce](https://help.dayforce.com/r/manager-guide/Coverage-Scores)
- Deputy: "coverage view" where required staff amounts are set and shown in the schedule (article outline only retrieved) — [Deputy help](https://help.deputy.com/hc/en-au/articles/4688843118223)

### Inferences
- The app's mandatory/desirable split maps neatly onto the min/max coverage band used in OR and onto RAG bands; presenting deficit (red), acceptable-but-below-desirable (amber), in band (green), excess (blue) is consistent with both NHS RAG practice and vendor diverging palettes.
- Headline numbers vendors converge on: one coverage %, one efficiency/over-coverage measure, under hours, over hours. Adding exactly these four to the monthly summary would match industry practice.

### Gaps
- Could not read NHS England 2019 e-rostering guidance PDF (compressed, no extractor available) — it lists roster KPIs; worth reading manually: [NHS E-Rostering Guidance Sept 2019](https://www.england.nhs.uk/wp-content/uploads/2020/08/20190903_UPDATED_Nursing_Midwifery_E-Rostering_Guidance_September_2019.pdf).

## 4. Cost of under/overstaffing research and safe-staffing indicators adaptable to a support service

### Takeaway
Evidence links each day/shift of below-target staffing to worse outcomes (mortality hazard +3% per day below ward mean RN staffing), and simulation shows setting baseline capacity at mean demand produces frequent understaffing; capacity near the 90th percentile of demand is recommended. NHS indicators (fill rate, CHPPD, red flags) adapt to a support service if "patients" is replaced by demand hours.

### Cited Findings
- Griffiths et al. 2019 (BMJ Qual Saf 28(8):609–617, 32 wards): hazard of death +3% for every day a patient experienced RN staffing below ward mean (aHR 1.03, 95% CI 1.01–1.05); high nursing-assistant staffing also associated with higher mortality — [eprint](https://eprints.whiterose.ac.uk/141740/1/bmjqs_2018_008043.full.pdf)
- A separate Griffiths et al. NIHR report found +9% hazard for each day RN hours per patient day fell below estimated establishment (HR 1.09, 95% CI 1.06–1.11) (seen in search summary; full page blocked by CAPTCHA) — [NIHR / NCBI Bookshelf NBK534522](https://ncbi.nlm.nih.gov/books/NBK534522)
- Saville et al. simulation (81 wards, 4 trusts): baselines at mean demand gave 31.8% understaffed shifts vs 21.2% for high baseline; low baseline (80%) gave 65.4%. Cost per patient-day £120 (low), £135 (standard), £142 (high). Low baselines "saved" money mainly because shifts went unfilled; authors recommend baselines around the 90th percentile of demand — [Saville et al. (PMC7788209)](https://pmc.ncbi.nlm.nih.gov/articles/PMC7788209)
- Flexible staffing was most effective at avoiding understaffing when many permanent staff were employed — [Saville et al., eprints](https://eprints.soton.ac.uk/439240/)
- CHPPD = (registered nurse hours + support worker hours) / patient count at 23:59 each day, accumulated over the month; national standard DCB2039 — [The Christie safe staffing reports](https://www.christie.nhs.uk/media/04gc3x44/safe-staffing-january-2026.pdf); [NHS England CHPPD guidance](https://www.england.nhs.uk/long-read/care-hours-per-patient-day-chppd-guidance-for-all-inpatient-trusts/). Carter review proposed tracking planned (establishment), required (daily demand) and actual hours via CHPPD — [HFMA Carter feature](https://hfma.org.uk/system/files/20-23_mar16_carter2-final-features-3.pdf)
- Trusts note a fill rate under 100% is not always a shortfall (lower occupancy/acuity) — [FHFT](https://www.fhft.nhs.uk/about-us/how-we-are-run/our-performance/nursing-and-midwifery-safe-staffing-inpatient-bedded-area)
- HSJ reported national publication of nurse fill-rate data was dropped (date/status not confirmed) — [HSJ](https://www.hsj.co.uk/workforce/exclusive-government-drops-key-safe-staffing-measure/7024892.article)
- NICE SG1 (2014) nursing red flags include fewer than two registered nurses on a ward during any shift and unplanned omission of medications; red flags should prompt immediate escalation; missed breaks and overtime are listed as safe-staffing indicators (not red flags); local red flags may be added — [NHS England safe staffing appendices](https://www.england.nhs.uk/wp-content/uploads/2021/05/safe-staffing-adult-in-patient-appendices.pdf); [NICE SG1](https://nice.org.uk/guidance/sg1/resources/safe-staffing-for-nursing-in-adult-inpatient-wards-in-acute-hospitals-61918998469)
- NHS rostering KPIs (Carter / NHSI 2016 Good Practice Guide): roster approval lead time (trust policies: 6–12 weeks before start); approval lead time correlated with HCA shift fill rate in an NHS England case study; leave spread evenly through the year; unused hours tracked — [Leicestershire Partnership e-rostering policy](https://www.leicspart.nhs.uk/wp-content/uploads/2022/11/Electronic-Rostering-Policy.pdf); [Royal Wolverhampton policy](https://royalwolverhampton.nhs.uk/wp-content/uploads/2024/10/OP_103_PUBLIC_Policy_Printable_Version.pdf); [NHS England, Improving workforce visibility through e-rostering](https://www.england.nhs.uk/wp-content/uploads/2020/08/Improving_workforce_visibility_through_e-rostering.pdf)

### Inferences
Adaptations for a support service without acuity or payroll data:
- **Hours per required hour** (CHPPD analog): scheduled person-hours / mandatory demand person-hours per day, trended across months. Same as fill rate but as a ratio for trend charts.
- **Red flag analog (hard flag)**: any slot where staffed < M for a position, or staffed below an absolute floor (e.g. fewer than 1–2 people on night franja). Count per month; NICE treats these as escalation triggers, not averages.
- **Days-below-target count per month**: directly mirrors the Griffiths "each day below" exposure measure; already partly built (deficit days), but reporting it as a monthly count/trend per position adds the evidence-backed framing.
- **Capacity vs demand percentile**: compare staffed per slot with the P90 of mandatory demand across the month's same weekday/slot; Saville suggests baseline near P90 to limit understaffing.
- **Roster lead time**: days between roster publication and first day of month (if publication date is stored). Only roster-quality KPI from NHS guidance computable without extra data.
- **Excess cost proxy**: over person-hours × surcharge rate for those slots (night/Sunday/holiday surcharges are known), giving a rough cost of overstaffing without payroll data. Understaffing cost cannot be monetized from available data.

### Gaps
- No research found specific to hospital support services (porters, cleaning, stores) on under/overstaffing outcomes; evidence is nursing-only.
- Exact NHS NHSI 2016 KPI thresholds (net hours, annual leave %) not retrieved.
- No Colombia-specific safe-staffing standard searched/found for support services.
