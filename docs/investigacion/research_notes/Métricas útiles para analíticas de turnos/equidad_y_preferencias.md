# Fairness, preference-fulfilment and workload-distribution metrics for staff rosters

Scope: metrics (with formulas) and charts for measuring how fairly undesirable work (nights, Sundays, holidays, overtime, covering changes) and request fulfilment (libre/quiero/evitar, with priority, met or not) are spread across a ~40-person team on monthly rosters in Colombia. The app already has per-person night/Sunday/holiday counts with max−min spread, a "who covers most" ranking and overtime totals.

## 1. How nurse-rostering papers measure fairness, and which measure suits a small team

### Takeaway
The literature uses a small set of measures over a per-person "burden" or "penalty" value: max−min range, minimax (the worst-off person), mean absolute deviation, standard deviation / CV, sum of squares, Gini and Jain's index. In head-to-head nurse-rostering experiments, minimising mean absolute deviation from the average (MinDev) and minimax gave the fairest rosters. Plain weighted-sum totals gave the least fair ones. For a team of about 40, the most practical set is easy-to-read absolute measures (range, deviation from the team mean per person, MAD) plus one scale-free index (CV or Gini) to compare months and categories. Long-term fairness needs counters that carry across months.

### Cited Findings
- Smet and Vanden Berghe note that rosters are usually scored with a weighted sum of soft-constraint violations, `WO = Σ_n Σ_c violations(n,c) × weight_c`. They say this "far from guarantees a fair solution": one nurse's very bad roster can be offset by another's good one. They propose a minimax objective, `FO = max_n Σ_c violations(n,c) × weight_c`, in which the worst individual roster sets the quality of the whole roster. — [Smet & Vanden Berghe, "A study on fairness objectives for nurse rostering" (KU Leuven)](https://lirias.kuleuven.be/retrieve/176620)
- Martin, Ouelhadj, Smet, Vanden Berghe and Özcan define a per-nurse penalty `q(n) = Σ_c w_c·n_c` (weighted violations of that nurse's soft constraints, requests included) and the team mean `μ = (1/|N|) Σ q(n)`. They compare four fairness objectives:
  - MinMax = |N|·max q(n)
  - MinDev = Σ|μ − q(n)| + |N|·μ
  - MinError = |N|·((max q − min q) + μ)
  - MinSS = Σ q(n)²

  Each objective also carries a coverage-penalty term. — [Martin et al., "Cooperative search for fair nurse rosters", Expert Systems with Applications (DOI 10.1016/j.eswa.2013.06.019), preprint](https://people.cs.nott.ac.uk/pszeo/docs/publications/fairnessNurseRosteringCoop.pdf)
- That paper scores rosters with Jain's fairness index over per-nurse penalties: `J = (Σ q(n))² / (|N| · Σ q(n)²)`. J runs from 1/|N| (worst) to 1 (every nurse has the same violations). The paper also notes that a roster with zero violations is taken as J = 1. — [Martin et al. preprint](https://people.cs.nott.ac.uk/pszeo/docs/publications/fairnessNurseRosteringCoop.pdf)
- Results:
  - MinDev and MinMax were "the best choices", and MinDev did better on average across instances.
  - The authors conclude that "the function minimising the deviation from the average roster turned out to be superior", while the weighted-sum objective "produced the least fair rosters".
  - MinSS was "one of the worst performing" on fairness.
  - Fairer rosters generally cost more total violations.

  — [Martin et al. preprint](https://people.cs.nott.ac.uk/pszeo/docs/publications/fairnessNurseRosteringCoop.pdf)
- Wolbeck's literature review of fairness in personnel scheduling lists the most common objectives over per-employee penalty scores `p_i`:
  1. sum
  2. min-max
  3. range max−min
  4. mean
  5. mean absolute deviation `Σ|p̄ − p_i|`
  6. standard deviation
  7. sum of squares
  8. percentage of fulfilled requests

  It notes that effects of schedules perceived as unfair include lower job satisfaction, absenteeism, higher turnover and even strikes. It cites Bard & Purnomo 2005 and Abbink et al. 2005 for this. — [Wolbeck, "Fairness Aspects in Personnel Scheduling", FU Berlin discussion paper 2019/16](https://d-nb.info/1202043291/34)
- Wolbeck reports Jain et al.'s four properties for a fairness measure: independence from population size, scale and metric independence, boundedness, and continuity. Jain et al. showed that variance, CV and the min-max ratio do not meet all of them, which is why they defined their bounded index. — [Wolbeck 2019](https://d-nb.info/1202043291/34); original: [Jain, Chiu & Hawe 1984, DEC technical report](https://research.engineering.wustl.edu/~jain/atmf/ftp/af_fairn.pdf)
- Jain's index is very sensitive when one element takes a large share. Worked example: if 80% of users are served equally and 20% get nothing, J = 0.8. — [Jain fairness index summary in search results / Jain et al. 1984](https://research.engineering.wustl.edu/~jain/atmf/ftp/af_fairn.pdf)
- Long-term fairness mechanisms. Wolbeck classifies approaches that look beyond one period as either adjusting penalty costs from history (PEN) or carrying cumulative satisfaction scores (SC). Examples:
  - Miller et al. 1976: an "aversion index" for nurses previously given bad shifts.
  - Bard & Purnomo 2005: an exponential weight that grows with the number of earlier preference violations.
  - Bester et al. 2007: an accumulated satisfaction score.
  - Alsheddy & Tsang 2011: each employee spreads 100 points over their requests, and a "power score" tracks fulfilment across periods.

  Wolbeck also notes that global counters (hours worked, number of granted requests) carried between periods can serve fairness. — [Wolbeck 2019](https://d-nb.info/1202043291/34)
- Gross, Brunner and Blobner propose a per-physician satisfaction indicator for monthly plans. It is computed each month and used to weight preference fulfilment in the current and future plans. With the right update strategy it produces equal satisfaction across a peer group and stable satisfaction for each individual over a long horizon. The motivation is that monthly-only planning leaves the same people repeatedly disadvantaged. Published in Health Care Management Science 2019;22(4):691–708. — [PubMed 30046927](https://pubmed.ncbi.nlm.nih.gov/30046927); code for the experiments, with three strategies named "C", "ESA" and "ESD": [GitHub chrisnig/long-term-fairness](https://github.com/chrisnig/long-term-fairness)
- Recent applied examples report several measures side by side:
  - An operating-room goal-programming study: 37 permanent nurses in Türkiye, data from December 2025. Monthly working days went from SD 3.51 to 0.49, CV 0.171 to 0.025, Gini 0.096 to 0.007 and range 14–26 to 18–20, manual versus model. Nights per nurse were not equalised and still ranged from 1 to 8. — [Demircioğlu & Mutlu, Healthcare 2026, PMC13606332](https://pmc.ncbi.nlm.nih.gov/articles/PMC13606332)
  - A JMIR Nursing 2026 pre-post study: 156 nurses. Gini fell from 0.24 to 0.13 (−45.8%), "corroborating" the CV results. It also used disparate impact ratios. I could not open the full text (403), so I only have the search snippet. — [JMIR Nursing, doi 10.2196/94450](https://doi.org/10.2196/94450)
- A non-nursing paper on decentralised resource allocation says SD measures spread around the mean but "does not distinguish between random variability and systematic concentration". Gini is sensitive to the burden being concentrated on particular individuals. — [arXiv 2510.04192](https://arxiv.org/pdf/2510.04192)

### Inferences
- Recommended core formulas. Let `x_i` be person i's count or hours for one category over a period, for example nights in the month, and `x̄` the team mean.
  - Range: `max x − min x`. Already built. Intuitive, but it rests on two people and ignores everyone else.
  - Deviation per person: `d_i = x_i − x̄`. When contracts differ, use the normalised form `d_i = x_i − x̄_norm·FTE_i` (see §4). This is the most actionable number for a supervisor ("Ana has +3 nights over the team average").
  - Mean absolute deviation: `MAD = (1/n) Σ|x_i − x̄|`. This is what MinDev minimises, the best-performing objective in Martin et al. It is robust and reads in the same units as the data.
  - SD and CV: `σ = sqrt(Σ(x_i − x̄)²/n)`, `CV = σ / x̄`. CV is scale-free, so it can compare nights against Sundays, or month against month.
  - Gini: `G = Σ_i Σ_j |x_i − x_j| / (2 n² x̄)`. Range 0 (equal) to (n−1)/n. For small n, multiply by n/(n−1) so the maximum is 1. With n ≈ 40 the correction is about 2.5%, minor but cheap.
  - Jain: `J = (Σx)² / (n Σx²)`. J equals `1/(1+CV²)` with the population CV, so it adds nothing over CV. Using both is redundant.
- For a ~40-person team, n is small, so one or two people move every index. Show people (deviation bars, a per-person table) next to any single index, and do not lean on an index alone. MAD and deviation-from-mean are the easiest to explain to staff. Gini or CV is useful as one trend number per category per month.
- Monthly counts of rare events are lumpy. Someone with 0 holidays one month is not necessarily treated unfairly, because there may have been only 1–2 holidays in the month. Fairness for nights, Sundays and holidays should mostly be judged cumulatively, over a rolling 3, 6 or 12 months, which matches the long-term-fairness literature (Gross et al., Bard & Purnomo).
- Exclude, or pro-rate, people who are not eligible: those on leave, newly hired, or on contracts that exempt them from nights. Otherwise the indexes report "unfairness" that is just a matter of availability.

### Gaps
- I could not retrieve the full text of Smet et al. 2013b ("Investigation of fairness measures for nurse rostering") or of Gross et al. 2019, so the exact indicator formula and update rules (C / ESA / ESD) are not documented here.
- I found no study that tests which statistical measure (Gini, SD, MAD, Jain) best matches how fair nurses perceive a roster to be. Papers pick measures for optimisation convenience.
- I found no source that says explicitly that a given index is "recommended for small teams". The small-team advice above is my inference.

## 2. Request/preference fulfilment per person, and evidence it matters

### Takeaway
The standard metric is the percentage of requests granted, per person and overall. Fairness of fulfilment is then measured by applying the same dispersion measures (min-max, deviation, Gini) to per-person fulfilment or dissatisfaction scores, preferably cumulatively and weighted by priority. The evidence that self-scheduling and preference fulfilment improve satisfaction and retention is generally positive but limited and mixed. Perceived unfairness and unwanted shift assignment are linked to intent to leave.

### Cited Findings
- Objective [8] in Wolbeck's taxonomy is the percentage of fulfilled requests, `max Σ_i (1 − p_i/|R_i|)`, where `|R_i|` is the number of requests employee i made. Wolbeck says that maximising the total without a fairness term can mean "the same persons will always be affected by violations". Without an explicit fairness objective, fairness ends up "solver-dependent", citing Gross et al. 2019. — [Wolbeck 2019](https://d-nb.info/1202043291/34)
- In Martin et al., requests are soft constraints, so unmet requests add to each nurse's penalty `q(n)`, weighted by importance. Fairness of fulfilment is therefore the fairness of `q(n)` across nurses. — [Martin et al. preprint](https://people.cs.nott.ac.uk/pszeo/docs/publications/fairnessNurseRosteringCoop.pdf)
- Alsheddy & Tsang let each employee spread 100 points across their requests, as a priority weight. They track a cumulative "power score" of fulfilment across periods to aim for long-term fairness. Ásgeirsson 2014 is cited as arguing that staff and managers need to understand why a preference was not met, so a black box is not acceptable. — [Wolbeck 2019](https://d-nb.info/1202043291/34)
- NSW Health's example rostering measures include a "Fairness" category: the number of occasions the unit's preferred rostering patterns were not met. — [NSW Health, Example measures of success](https://www.health.nsw.gov.au:443/Performance/rostering/Documents/example-measures-of-success.pdf) (seen in a search result only, not opened)
- Self-scheduling evidence:
  - A systematic review of 23 studies found a limited evidence base. Several studies showed positive effects on nurses and organisations, while others found negative outcomes or no change. — [Wright et al., PubMed 33016472](https://pubmed.ncbi.nlm.nih.gov/33016472/)
  - A 2024 mixed-method systematic review (J Clin Nursing) reports that self-rostering improves work-life balance, perceived autonomy and job satisfaction, contributing to retention and lower turnover. One included study found self-scheduling less fair than fixed scheduling, with no effect on satisfaction. — [O'Connell et al. 2024, J Clin Nurs, doi 10.1111/jocn.17114](https://onlinelibrary.wiley.com/doi/10.1111/jocn.17114) (search-snippet level; the full text was blocked)
  - A systematic review on staffing, schedules and turnover concluded that flexible scheduling is an important but not standalone contributor to retention. Self-scheduling, shift exchanges and predictable hours help most when combined with adequate staffing and fair policies. — [ResearchGate: Assessing the impacts of nurse staffing and work schedules on nurse turnover](https://www.researchgate.net/publication/370950840_Assessing_the_impacts_of_nurse_staffing_and_work_schedules_on_nurse_turnover_A_systematic_review)
- Perceived fairness and turnover:
  - Kida & Takemura, a cross-sectional study of Japanese shift-work nurses, found that shift assignment and organisational justice each had direct effects on turnover intention. Justice did not buffer the shift effect, and the authors suggest nurses may need equality in shift planning, not just perceived justice. — [UTokyo Nursing summary](https://utokyonursing.m.u-tokyo.ac.jp/?p=47250); paper [doi 10.1111/jjns.12570](https://doi.org/10.1111/jjns.12570)
  - Iranian nurses: organisational justice was inversely related to turnover intention (r = −0.41), mainly indirectly through commitment. — [Fardid et al. 2018, sid.ir](https://sid.ir/fileserver/je/5062320180403.pdf) (search-snippet level)

### Inferences
- Per-person metrics that can be computed from the app's request log (type libre/quiero/evitar, priority, met yes/no):
  - Fulfilment rate: `FR_i = met_i / requests_i`. Show the count next to the rate: 1 of 1 is not the same as 9 of 10.
  - Priority-weighted fulfilment: `WFR_i = Σ w_p·met / Σ w_p`, with weights per priority level (for example high = 3, medium = 2, low = 1).
  - Unmet-request debt: cumulative `Σ w_p·(1 − met)` over rolling months. This is a simple version of the cumulative satisfaction score (SC) or aversion index (PEN) from the literature, and is the natural input for "who should be favoured next month".
  - Team fairness of fulfilment: the range or Gini of `FR_i` or of cumulative debt across people who made requests, plus the share of people with `FR_i` below a threshold (for example below 50%).
  - Breakdown by type: "evitar" (avoid) misses are probably felt more than unmet "quiero" (want) requests. Report libre/quiero/evitar separately before blending them.
- Guard against gaming. People who make many low-priority requests can push their own rate down, so priority weighting or a points budget (Alsheddy & Tsang's 100 points) helps normalise.
- Exclude requests that could not be met because of hard constraints such as coverage or legal rest. Otherwise report them separately, as "unmet for coverage reasons", which is more transparent for staff.

### Gaps
- I found no effect sizes linking a given fulfilment percentage to satisfaction or turnover. The evidence is directional.
- I found no vendor documentation (Quinyx, UKG, Allocate/RLDatix HealthRoster) that describes a request-fulfilment fairness report. Searches surfaced only HealthRoster's Roster Analyser KPIs (§4).

## 3. Overtime concentration metrics and evidence on overtime and burnout

### Takeaway
I found no rostering study that measures how concentrated overtime is (top-N share, Lorenz curve). Those are standard inequality tools that apply directly here. The evidence links overtime, and especially mandatory overtime, to burnout and intent to leave, which justifies watching for overtime piling up on a few people.

### Cited Findings
- A 4-year longitudinal study of 1,155 healthcare workers at a Taiwanese university hospital (2021–2024) measured burnout with the Copenhagen Burnout Inventory personal-burnout subscale. Overtime of more than 45 h/month was associated with high burnout, adjusted OR 3.14 (p < 0.001), and with a shorter time to reach high burnout. Limitations: heavy loss to follow-up (29–48%), an observational design, and a COVID-era context. Turnover intention was not measured. — [Chen et al., Healthcare (Basel) 2025;13(15):1859, PMC12345989](https://pmc.ncbi.nlm.nih.gov/articles/PMC12345989/)
- A South Korean cross-sectional survey of acute-care nurses found that only mandatory overtime was significantly related to intent to leave. Staffing, work hours, mandatory overtime and turnover were not significantly associated with burnout. 40.3% reported mandatory overtime. — [Bae 2024, Int J Public Health, PMC11091319](https://www.ncbi.nlm.nih.gov/pmc/articles/PMC11091319/)
- A 12-country European study found that 27% of nurses worked overtime on their last shift. Hospital-level rates ranged from 0% to 80%, so overtime is unevenly distributed, at least between sites. — [Griffiths et al., PMC4196798](https://pmc.ncbi.nlm.nih.gov/articles/PMC4196798/)
- Payroll data from 70 US hospitals (2019–2022) put mean overtime at 0.09 nurse hours per patient day, 63.6% above an estimated safe threshold. The data are hospital-level, not per nurse. — [JAMA Netw Open 2025, PMC11966309](https://pmc.ncbi.nlm.nih.gov/articles/PMC11966309/)
- Colombian context:
  - Ley 2101 of 2021 reduced the private-sector week to 42 h from 15 July 2026.
  - Ley 2466 of 2025 moved the start of night work from 21:00 to 19:00, from late December 2025. Sources differ on the exact date (25 Dec 2025 or 1 Jan 2026).
  - Sunday and holiday surcharges are being phased in: 80% (Jul 2025–Jun 2026), 90% from 1 July 2026, and 100% from 1 July 2027.

  These come from secondary sources, so verify them against the official text. — [Bloomberg Línea](https://www.bloomberglinea.com/latinoamerica/colombia/pago-de-domingos-y-festivos-sube-al-90-desde-hoy-1-de-julio-de-2026-en-colombia/), [Alegra](https://blog.alegra.com/colombia/ley-2466-de-2025/), [Polisura](https://www.polisura.edu.co/reforma-laboral-en-colombia-todo-lo-que-cambio-y-como-te-afecta)

### Inferences
- Concentration metrics to compute from overtime per person (OT_i, hours):
  - Top-N share: `share_topN = Σ_{top N} OT_i / Σ OT_i`. For n = 40, top 10% means N = 4. Read it against the equal-share baseline N/n (10%). For example, "the top 4 people did 46% of overtime".
  - Lorenz curve: sort OT_i in ascending order, then plot the cumulative share of people (x) against the cumulative share of overtime (y). Gini = 1 − 2 × (area under the curve). With 40 points the curve is a short step line, which is readable.
  - Share of staff with any overtime: `#(OT_i > 0)/n`. This tells "everyone does a little" apart from "few do a lot".
  - Per-person threshold flags: hours per month above a fixed line. The 45 h/month threshold used by Chen et al. comes from Japanese and Taiwanese law and research, so for Colombia set the threshold from local policy instead.
- Separate voluntary from assigned overtime if the change log can tell them apart, for example by who initiated a swap or cover. The Korean finding points to mandatory overtime as the turnover risk.
- The app's "who covers most" ranking and the overtime totals can feed the same top-N share and Lorenz view, so one component can serve both (covers and overtime hours).
- Under the Colombian changes, night and Sunday/holiday assignments now cost more and the night window is wider. Night counts computed before and after the 19:00 change are not comparable unless shifts are reclassified.

### Gaps
- I found no study that quantifies overtime concentration among individual nurses, for example "X% of nurses do Y% of overtime".
- I did not confirm the Colombian overtime caps (daily or weekly maximum) from an official source.

## 4. Contracted vs worked hours deviation per person, and how tools show it

### Takeaway
NHS England's e-rostering standards make "planned versus delivered hours (net hours) per WTE" a core KPI. It is the cumulative variance between contracted and delivered hours per roster period, with a target of under 13 hours per WTE. HealthRoster's Roster Analyser shows over- and under-contracted hours as a KPI group. The equivalent here is per-person `worked − contracted`, tracked cumulatively, which is the app's hours bank.

### Cited Findings
- NHS England and NHS Improvement define the "planned versus delivered hours (net hours) per WTE" KPI as the "cumulative variance between the number of planned contracted hours and actual delivered hours per WTE per roster period". Trusts should aim for less than 13 hours per WTE, report it at least monthly, and break it down by team and professional group. The same document says reports on staff availability, sickness and "unused hours" should be available for team leaders to review regularly. — [NHS England, E-rostering the clinical workforce: levels of attainment and meaningful use standards (2019), Appendix 2](https://www.england.nhs.uk/wp-content/uploads/2020/09/E-rostering_meaningful_use_standards.pdf)
- The same standards say that automatically generated rosters "ensure fairness between staff". They also say leave policy should set rules "for consistency and equity" in managing leave requests. — [NHS England meaningful use standards](https://www.england.nhs.uk/wp-content/uploads/2020/09/E-rostering_meaningful_use_standards.pdf)
- The HealthRoster Roster Analyser Summary tab has a "Safety" KPI group on how well staff hours have been used: over- and under-contracted hours, duties above demand and duties assigned to the wrong grade. There is a separate cost-versus-budget group. — [ELFT HealthRoster "Analyse a roster" guide (2026)](https://www.elft.nhs.uk/sites/default/files/2026-05/healthroster_analyse_a_roster.pdf) (search-snippet level)
- NSW Health's example measures include overtime hours and unused contract hours. — [NSW Health example measures](https://www.health.nsw.gov.au:443/Performance/rostering/Documents/example-measures-of-success.pdf) (search-snippet level)

### Inferences
- Per-person formulas:
  - Monthly net deviation: `Δ_i = worked_i − contracted_i` in hours.
  - Relative deviation: `Δ_i / contracted_i`, which compares full-time and part-time staff.
  - Cumulative balance: `B_i(t) = Σ_{months ≤ t} Δ_i`. This should match the app's hours-bank balance, so reuse that value and do not recompute it.
  - Team KPI, NHS-style: mean of `|B_i|` per FTE, or the share of people with `|B_i|` above a threshold. The NHS 13 h/WTE is a reference point, not a Colombian norm.
- Normalise burden counts by contract too. A 0.5-FTE person with 3 nights carries the same relative load as a 1.0-FTE person with 6. Use `x_i / FTE_i` (or `x_i / contracted hours_i`) before computing deviation, Gini or CV, or the part-timers will look "favoured".
- How to show it: a diverging bar per person (worked − contracted, under on the left, over on the right) sorted by value, with an optional ±threshold band. A line per person of the cumulative balance over months, highlighting the selected person, shows drift.

### Gaps
- I found no public documentation from Quinyx or UKG showing how they display contracted-versus-worked deviation or fairness. The vendor pages surfaced were generic marketing.

## 5. Recommended visualisations

### Takeaway
The literature and NHS guidance favour per-person views (deviation bars, cumulative lines) for action and box plots for comparing distributions. A Lorenz curve with a top-N share is the standard picture of concentration. With about 40 people, show every person: a dot or strip plot beats a summary box alone.

### Cited Findings
- Martin et al. use box plots of the fairness index to compare objective functions across runs. — [Martin et al. preprint](https://people.cs.nott.ac.uk/pszeo/docs/publications/fairnessNurseRosteringCoop.pdf)
- The Gini coefficient is geometrically tied to the Lorenz curve. Nurse-workforce equity studies routinely report Gini for distribution across regions. — [Distribution of nursing workforce using Gini (ResearchGate)](https://www.researchgate.net/publication/370558990_Distribution_of_nursing_workforce_in_the_world_using_Gini_coefficient); [Regional inequities in nursing workforce, Italy](https://doi.org/10.3390/nursrep15070235)
- NHS standards require net-hours KPIs broken down by team and professional group and reported monthly, which suggests per-team small multiples over time. — [NHS England meaningful use standards](https://www.england.nhs.uk/wp-content/uploads/2020/09/E-rostering_meaningful_use_standards.pdf)

### Inferences
Suggested charts, each computable from roster, requests and change log:

| Question | Chart | Data |
|---|---|---|
| Who is above or below the team for nights, Sundays and holidays? | Diverging bar per person of `x_i/FTE_i − mean`, sorted, ±1 MAD band | Rolling 3–12 months |
| Is the distribution fair overall, and is it improving? | One line per category of Gini or CV by month (3 lines: nights, Sundays, holidays) | Monthly plus rolling |
| Is overtime or covering concentrated? | Lorenz curve with a "top 4 = X%" label; alternatively a Pareto bar (sorted bars with a cumulative % line) | Monthly overtime hours, number of covers |
| How do categories compare? | Strip or dot plot (one dot per person) per category, with an optional box behind | Per-person counts |
| Are requests met fairly? | Per-person bar of weighted fulfilment % with n requests labelled; team range or Gini as a KPI | Request log |
| Is someone repeatedly unlucky? | Cumulative unmet-request debt per person over months (line per person, top 5 highlighted) | Request log, rolling |
| Under- or over-scheduling? | Diverging bar of worked − contracted per person; cumulative hours-bank line per person | Hours, contract, hours bank |

- Prefer rolling windows over single months for rare categories (holidays), so the charts do not show noise.
- Name the comparison baseline explicitly in the UI: team mean normalised by FTE, and people who were ineligible during the period excluded.

### Gaps
- I found no study that evaluates which charts staff or managers find most understandable for roster fairness. The recommendations above are standard data-visualisation practice, not evidence from rostering research.
