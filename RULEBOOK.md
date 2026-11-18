# QuFin Rule Book (master)

**This rule book is the property of QuFin (the QuFin-Web repository).** It stands on its own: no rule
depends on any tool, vendor or person, and it remains in force whoever or whatever builds or maintains
QuFin. Everything that builds, tests or reviews QuFin follows it, and a change that breaks a rule is a
defect, however convenient. Each subject is ruled once, in one place. Rules keep their numbers; the
code, tests and docs refer to them as "rule N" ("S1" to "S9" for the scorecard correction mechanism).
Active numbers are not contiguous: a number whose rule was merged into another is listed in *Retired
numbers* at the end, so an old reference still leads to the rule that now holds it. Where two rules
ever seem to disagree, the stricter reading applies until the rule book is corrected (rule 26); a
disagreement is a defect. Terms used in more than one rule are defined once, in Part 0.

QuFin is a data-extensive trading assistant. Its trading ideas, scores and backtests rest on the
data, so the rules below put data integrity first, then comparability, then transparency.

Contents: Part 0 definitions | Part 1 data integrity | Part 2 comparison, change measures and weights (20-23) | Part 3
scorecard correction mechanism (S1-S9) | Part 4 ownership, documentation and conduct (24-28) | Part 5
sources, frequency, history and coverage (B, D, F, G, I, J, L, N, O, P) | Retired numbers | Change log.
Related documents: `private/scorecard-methodology.md` (proprietary, not committed while this repository
is public), `docs/assumptions-register.md`, `docs/indicator-names.md`, `docs/data-provenance.md`,
`docs/licence-register.md`, `docs/release-calendars.md`.

## Part 0. Definitions

Named commands, settings, files and tables are the current implementation of a rule. The rule binds
the behaviour; when the implementation is renamed or replaced, the rule book is updated in the same
pull request (rule 24). The numbers below live in the named file, which is their single home.

- **Due date** of a series: the end of its latest stored period, plus one period, plus its median
  release lag, plus any declared aggregator delay (rule 4). The median is taken over the releases
  first seen in the trailing three years (`LAG_WINDOW`, `app/jobs/check_data.py`), so a source
  that changes its timing is followed within that window.
- **Grace period:** days allowed after the due date before a series is overdue: daily 5, weekly and
  biweekly 7, monthly 14, quarterly 30, semi-annual 45, annual 60 (`GRACE_DAYS`,
  `app/domain/freshness.py`).
- **Status:** `overdue` when today is past the due date by more than the grace period, or nothing
  is stored; `discontinued` when the source marks it so; `review` when a check needs a person to
  decide (a duplicate under rule 16, a delay notice that does not match the declared delay under
  rule 4, a change taken on a `published_as_change` series under rule 22, a frozen upstream series
  under rule N); otherwise `ok`.
- **Usable** (`freshness.usable`): the status is `ok`. Nothing else is usable.
- **Timeliness weight:** `0.5 ^ (days after period end until QuFin can read it / 60)`, and 0 when
  not usable (`HALF_LIFE_DAYS`, `app/domain/freshness.py`).
- **Score scale:** indicator scores, pillar scores and overall scores are on one scale, -3 to +3
  (S1, S2).
- **Data table:** a table that grows with observations, vintages or bars (for example
  `macro_observations`). Tables that grow only with the catalog (countries, concepts, sources,
  job runs) are metadata tables.
- **Hot query:** a read that a page load, an API request or a scheduled job makes.
- **Source decision:** the source chosen for a country-indicator pair under rule P, with the date
  it took effect. Each pair's decisions form its source history. A **provisional** source decision
  is the first one for a new pair, made before a release cycle has been measured (rule P); it is a
  source decision like any other: the source serves and is scored, and scores record it (rule 20).
- **Staging:** where the candidate sources for a pair are loaded and timed. Staged series are never
  served or scored, and the duplicate check skips them.
- **Retired series:** the stored history of a pair's previous source after a source change. It is
  read only for as-of dates before the change (rule 16).
- **Catalog version:** the state of the catalog declarations (source decision, change kind,
  adjustment, variant, unit) a value or score was computed with.

## Part 1. Data integrity rules (non-negotiable)

These rules apply to every data source and every series, existing or new:

1. **No series without a live release schedule.** Before adding a series to a catalog, check
   on the source that it is still published: its latest observation fits its frequency and
   usual release lag, and it is not marked discontinued. Run
   `uv run python -m app.cli check-data` after ingesting and include its result in the PR.
2. **Every ingest run ends with the release check.** Each `ingest-*` command runs it, or, when a
   refresh chains several commands, one final `check-data` runs after the last
   (`QUFIN_DEFER_RELEASE_CHECK`). The ingest commands and `check-data` exit non-zero when any
   series is overdue, discontinued or needs review. A run keeps what it loaded correctly: series
   that loaded are committed, the run is marked failed, and the report names each failing series,
   so one stale series never blocks the others; rule 3 keeps the failing ones out of use.
   Downstream jobs (scorecards, backtests, alerts) do not wait for a successful run: they read the
   committed series whose `freshness.usable` is true. Never
   silence or bypass that, and never widen the grace periods (Part 0) to make a failure pass.
3. **Unusable data stays out.** The API reports `freshness.usable` on every series. Signals,
   scorecards and backtests must skip series where it is false, never fill them with the last
   value as if it were current.
4. **Name the real source and its dates.** Every series records who produces it (e.g. the
   University of Michigan, not FRED) and its release. When an aggregator (FRED or any other)
   publishes later than the source (licensing), declare it in the catalog (for FRED:
   `fred_delay_days`, `delay_note`). A delay notice without a declared delay, or a declared delay
   the aggregator no longer reports, fails the check as "review".
6. **Point in time only; vintages are kept and served.** Backtests read data as it was published
   (`asOf`), never revised values before their release date. Wherever the source provides
   revisions (FRED/ALFRED), the store keeps every vintage and chart endpoints serve them. Charts
   show the current vintage by default: the whole series as the source publishes it today, one
   vintage for every period, never the latest value of each period stitched from different
   vintages; the chart states the vintage date and the source of the current vintage, marks the
   date of any source change (rule P), and earlier vintages stay available. Where the
   source keeps none, QuFin records each value as first seen, a flash and its final separately,
   dated by the real release (rule 9); history from before the first load carries no vintages and
   is labelled so.
7. **Check the licence before relying on a series commercially.** Some sources restrict use in
   a product sold to others, whatever channel the data arrives through. The University of
   Michigan survey (UMCSENT) is free only for research or strictly internal use; a platform,
   dashboard or investment advisory needs a licence from umsurvey@umich.edu. Moody's data
   (BAA10Y) carries a similar proprietary notice. Record such limits in the catalog.
8. **Every number states its origin.** Each endpoint that returns an observed value, or anything
   computed from one (a change, score, signal or backtest), returns `data` ("live" or "sample")
   or `freshness`; metadata endpoints (country, concept and source lists, calendars) need not; `tests/test_provenance.py` fails otherwise. Sample numbers are labelled on
   every page whether or not the user is signed in, and nothing invented (signals, alerts,
   notifications) is ever shown as if it were real. See `docs/data-provenance.md`.
9. **Release dates come from the source's real calendar**, including holidays, shutdowns and
   incidents (`app/data/cot_calendar.py` for the CFTC). Where a date is not published, derive
   it from the source's stated rule and mark it derived; when in doubt, err late, never early.
   A derived date gives way to the real time as soon as it is known: the source's own update
   timestamp, or QuFin's first sight of the value (rule P).
10. **Verify meaning at the source before scoring.** For every scored indicator, confirm its
    definition, sign, units and adjustment from the producer's own notes, and record the reason
    in `app/data/scorecard_catalog.py`. Activity growth (output, spending, sales, income) is
    scored in real terms only, deflated where the source publishes it nominal (nominal dollars read
    inflation as growth). Prices, inflation, rates and money are scored as published.
11. **Flag partial coverage.** A contract or series that covers only part of its market (e.g.
    NYMEX Brent, while most Brent trades on ICE) carries a caveat that the API and page show.
12. **Assumptions are listed and checked, not trusted.** Before adding or changing any data
    path, list every assumption (mapping, sign, unit, release timing, licence, coverage),
    verify each against the primary source, and report any that could not be verified. Record
    every judgement in `docs/assumptions-register.md` with its status (verified, convention,
    design choice, unverified); a judgement with no row there is a defect.
15. **Every hot query on a data table is indexed; nothing aggregates a data table on a page load.**
    (Both terms: Part 0.) Data grows with every country and series, so a full scan gets slower with
    each one added. Each hot query is listed in `tests/test_query_plans.py`, which fails if the
    planner scans a data table; a metadata table may be scanned; a new read is added there with the index that serves it, in a
    migration. Summaries a page needs (coverage, counts, latest period) are stored at ingest,
    not computed per request. Bulk loads end with `ANALYZE` so the planner picks the right
    index. Indexes belong to the table, so rows for series added later are indexed on insert.
16. **No duplicated indicators or data, at any cost.** A country has at most one series per
    concept (`app/data/indicator_concepts.py`), and a series that can be derived exactly from
    stored ones is not stored (`REDUNDANT`, e.g. the 10y-2y spread from the two yields, or a
    monthly figure from a stored daily one). A country-indicator pair is served from one source at
    a time; rule P says which. When the source changes, the new source loads its full history
    (rule I), and the previous source's history becomes a retired series (Part 0): kept read-only
    for as-of reads before the change, never served as current and never spliced into the new
    series. `tests/test_indicator_concepts.py` fails otherwise. The release check (`check-data`)
    also compares every stored series with every other, from any source: two that carry the same
    values, or the same values in other units, both fail as "review" until one is removed. Two
    exemptions, and only these: a retired series is not compared with the later series of its own
    pair (they are expected to match), and staged series are not compared. A retired series is
    still compared with every other pair's series. A cheap pre-filter picks the pairs that need a
    full comparison, so the cost does not grow with the square of the data: it keeps series that
    share the same ratio between consecutive periods (the same data in any unit) and series that
    share the same value in the same period (the same data on different period grids), and a
    series with too few usable fingerprints is compared with all. The pre-filter only chooses
    pairs and never reports a duplicate; its tests check that it finds every pair the full
    comparison finds. A check that cannot finish in its time budget fails, it is never skipped.
18. **Every series has one human-readable, global name, shared across countries.** An indicator is
    known by its globally recognised name and acronym (CPI, PPI, GDP, NFP, PMI, ...), never by a
    country's local name: the euro area's HICP and the UK's CPIH are both shown as "CPI". One name
    does not make two measures the same: where national definitions differ (HICP, CPIH and a
    national CPI differ in coverage, for example owner-occupiers' housing), the series records its
    `variant`, the tooltip shows it, and a comparison across variants carries a notice, as rule B
    does for adjustment (rules 10 and 23). Each series maps
    to a concept with a name and a one-sentence plain explanation; indices use their standard
    name with the acronym first ("CPI – Consumer Price Index"); the same concept key matches the
    indicator in every country (US and UK unemployment are both `unemployment_rate`,
    "Unemployment Rate"), and a country's series joins the existing concept rather than a new
    name. That name is used everywhere QuFin names things: database, API (`name`, `concept`,
    `acronym`), charts, comparisons, scorecards, backtests, alerts and docs. The API returns the
    name and the official title; pages show the name, with the official title, local name, source
    code and publisher in a tooltip. Acronyms and their full names are listed in `ACRONYMS`, local
    aliases in `LOCAL_ALIASES` (`app/data/indicator_concepts.py`); add the acronym there before
    using it. A series without a name fails the tests. Never choose a name from memory: read what
    at least two independent public references call the indicator (currently FRED, Trading
    Economics and the Forex Factory calendar) and record the survey in `docs/indicator-names.md`.
    Where they disagree, the name most of them use wins; with no majority, the producer's own
    English name wins. Any disagreement is recorded in the survey.
    This is a one-off look-up by a person, not automated collection, so rule 28's connector
    requirements do not apply to it; naming a reference is provenance, not attribution (rule 25). Every series also has a business-cycle tag
    (`app/data/cycle_classification.py`, with a reason); the catalog refuses a series without one.

## Part 2. Comparison, change measures and weights

20. **QuFin controls whether the scorecard mechanism is shown or hidden.** The correction mechanism
    (S1-S9) is public: it is how QuFin keeps scores honest, and it stays in this rule book. The
    recipe is proprietary: which indicators enter each pillar, their directions, their weights and
    weight cards, the calibration, and the modelling assumptions. The recipe is
    always documented in full, internally, in plain words (`private/scorecard-methodology.md`, kept out
    of version control while the repository is public), so QuFin
    can explain and defend every score. Whether users see it is QuFin's decision, made with one
    switch (`QUFIN_SCORECARD_MECHANISM`: `show` or `hide`, default `hide`) that can be changed at
    any time, and the recipe may be disclosed to a person or organisation on request, by the QuFin
    owner's decision, recorded in the methodology's change log. The methodology and its change log
    are versioned in a private repository; each version's commit hash, date, owner approval and S7
    result are recorded in the public `docs/scorecard-versions.md`, so every change can be audited
    without disclosing the recipe. When hidden,
    the API and dashboard leave out the recipe: weights, sub-scores and method text. **Never hidden, whichever
    way the switch is set:** that a score comes from a model and is not advice, where the data comes
    from and whether it is live or sample (rule 8), how fresh it is, the confidence in each score,
    and the releases still to come (S6). Every change to the recipe or to a weight is recorded in
    the methodology's change log with the reason, takes effect only after the bias gate (S7), a
    point-in-time backtest and the QuFin owner's approval, and never silently alters a past score:
    every score records the scorecard version and the catalog version (Part 0, provisional source
    decisions included) it was computed with, and a score computed under an earlier version stays
    as it was shown. A modelling assumption (for
    example that hot inflation supports a currency) is documented as an assumption, not a fact.
21. **Indicator weights are earned, never assumed equal.** An indicator's weight in a pillar reflects
    how much it matters: its market impact, its predictive power, how reliable it is (revisions,
    noise) and how timely it is. Equal weights between indicators are a defect unless their weight
    cards show those inputs are equal, and weights nobody can explain are always a defect. (The equal split of each indicator's own score between level and momentum
    in S1 is how one indicator is scored, not a weight between indicators.)
    Each weight has a recorded basis (its "weight card"), kept internally and shown to users only when
    the mechanism is shown; weights come from the mechanism in the methodology, are estimated only
    from data available at the time (no look-ahead), are capped so that no single indicator
    dominates a pillar, and are recalibrated on a fixed schedule with the before and after recorded.
    The cap and the schedule are stated as numbers in the methodology; a weight with no stated cap
    or schedule counts as interim.
    Until the mechanism is approved and calibrated, any interim weight is labelled interim wherever
    it is shown.
22. **Change is measured in the right units, only where admissible, and never changed twice.** Each
    catalog series declares how it changes (`change` kind), from its definition and units, not by
    habit:
    - *Percent change* (PoC): strictly positive quantities, counts, amounts and price or volume
      indexes: employment, claims and benefit claims, orders, sales, production, prices, money
      and balance-sheet totals, debt amounts, exchange rates, commodity prices.
    - *Change in points* (percentage points, index points, or basis points): rates, yields,
      spreads, ratios, shares (for example % of GDP), and diffusion or sentiment indexes, which can
      be zero, negative or already bounded.
    - *Change in own units* (an amount, not a percentage): series that can cross zero, such as the
      trade balance, current account and budget balance.
    - *No change taken*: a series the source already publishes as a change or growth rate is marked
      `published_as_change` and shown as published, never changed again. Read the source's notes,
      not just the units: WEI's units say "Index" but it is a GDP growth rate. The release check
      fails a percent change or y/y on such a series.
    Changes are taken within one vintage, never across vintages. A percent change whose old or new
    value is zero or negative is not computed: it is returned empty, never as zero, and a series
    where that happens is re-declared in points or own units by a catalog change in a pull request;
    tests cover both cases. The change kind is part of the catalog version (Part 0), so a score
    computed under the earlier declaration stays recorded with it (rule 20). Every
    chart and table offers the
    **actual value** and the **change** (percent or points, as declared) of any series over the
    chosen display frequency: a week, month, quarter, half year or year earlier. For a series with a
    declared change kind the change view is always available, and for one with none the actual
    only. Claims and other benefit-claim series are scored and charted on their percent change, with
    the actual counts shown beside it. A new series is not added until its change kind is declared
    and tested.
23. **Only compare what has a common basis.** Two series are compared, overlaid, ranked or combined
    only when they share a unit and currency, or have first been put on a common basis: (a)
    percent or point changes; (b) standardised scores against each series' own history; (c)
    ratios to a common denominator (for example % of GDP); (d) indexes rebased to 100 at a common
    date; or (e) conversion to one currency at a stated exchange rate and date, with the rate's
    source shown (purchasing-power parity for levels where that is the point). The US GDP in
    dollars is never put beside the UK GDP in pounds, and a count is never put beside a rate on one
    scale. Each series records its unit and currency; the dashboard states the basis of every
    comparison and refuses an overlay that has none. Scorecards compare countries only through
    standardised scores, never through raw values. Frequency alignment is rule D.

## Part 3. Scorecard correction mechanism (non-negotiable)

A delayed or missing indicator must make a score **less certain, never more bullish or
bearish**. Score and confidence are separate outputs (`app/domain/scorecard.py`):

S1. **Score each indicator point in time** against its own history as published then: a
   z-score over ten years, clipped to -3..+3, flipped where higher means weaker, on two
   parts: where it stands and its 3-month momentum, averaged equally (`MOMENTUM_WEIGHT` = 0.5;
   this is how one indicator is scored, not an indicator weight under rule 21). A daily
   or weekly series is averaged into the current month as each value lands, so its momentum part
   catches turns before the monthly level does.
S2. **Rescaled weighted average per pillar:** `score = Σ wᵢ·sᵢ / Σ wᵢ` over usable
   indicators, with `wᵢ` = base importance × timeliness weight. The timeliness weight
   (`timeliness.weight`, Part 0) halves for every 60 days between the end of a period and the day
   QuFin can read it; fresh data (daily rates, weekly claims) keeps full weight. Overdue,
   discontinued, missing or unscorable indicators drop out (weight 0); the only exception is a
   labelled estimate admitted under S5. Never count missing data as zero (a plain
   sum pulls scores toward neutral: strong economies underrated, weak ones overrated), and
   never carry an old value forward at full weight.
S3. **Confidence is reported separately:** `Σ wᵢ / Σ base importance`. It never changes the
   score.
S4. **Caution goes into position size, not into the view.** Size trade ideas by confidence.
S5. **Fix delays at the source where the licence allows it**, rather than living with them.
   An estimate for a missing release, and a flash or provisional figure a source itself flags, may
   enter a score only if labelled as an estimate, at a reduced weight stated in the methodology,
   and replaced when the final figure lands. An estimate is a new value with its own method and
   date, so it may stand in for an overdue series; the series' last real value is never carried
   forward in its place (rule 3).
S6. **Show what is pending:** every live scorecard lists the releases still to come, with the
   source and aggregator dates, so users know the score may move and why.
S7. **Prove there is no bias:** `uv run python -m app.cli scorecard-bias` compares the
   scorecard users would have seen each month with complete information. The mean difference
   must stay within ±0.25 score points on the -3 to +3 score scale (Part 0) for every pillar and
   overall (`MAX_MEAN_BIAS`); if it fails, the scorecard must not
   be used until the cause is fixed. `tests/test_scorecard.py` enforces the rules above; do
   not loosen it to make a change pass.
S8. **A currency pair is only as certain as its less certain side:** use
   `pair_confidence(base, quote)` (the minimum), so a stale side cannot make a pair look
   decisive.
S9. **Never mix live and sample scorecards** in one ranking; sample data is always labelled.

## Part 4. Ownership, documentation and conduct

24. **The rule book and QuFin's code belong to QuFin.** The rule book is kept in this repository, in
    plain text, and is the only place rules are defined. The one governed exception is the
    scorecard recipe (rule 20): its parameters (indicators per pillar, directions, weights,
    calibration) live in the private methodology, under the rules that rule 20 and S1-S9 set here.
    Instruction files for any development tool
    may exist only as a pointer to it and must add no rule of their own. No rule may require a
    particular development tool, assistant or hosting vendor. The commands, settings, files and
    libraries the rules name are the current implementation (Part 0): replaceable, with the rule
    book updated in the same pull request. The data sources the rules name are provenance (rule 4),
    chosen and replaced under rules O and P, not dependencies of the rules.
25. **No tool or assistant attribution anywhere.** Code, comments, commit messages, pull request
    descriptions, documents and releases carry no mention of, credit to or footer from any
    development tool or assistant. Names of data sources and licensed vendors are recorded where the
    data comes from (rule 4); that is provenance, not attribution.
26. **Changing the rule book needs the owner's approval and a log entry.** A rule changes only by a
    reviewed pull request that the QuFin owner merges. The change log below records the date, the
    rule and the reason. Rules are never loosened to make a change pass.
27. **Every data connection and process is documented.** `docs/data-connections.md` records, for
    every source, what QuFin takes, the address and protocol, how it authenticates (by the name of
    the setting, never the secret), its rate limits, its release calendar, the command that loads
    it and where its licence is recorded. `docs/data-pipeline.md` records how data is ingested and
    retrieved. A connector is not merged until its row is there, and a change to either process
    updates the document in the same pull request.
28. **Respect every data supplier's policy: every crawler, agent and connector is built and run so
    that it is never banned.** A refusal or ban is an incident: the connector stops, the owner is
    told, and it resumes only once the cause is fixed. Before a connector is written, the supplier's terms of use, API documentation and published
    limits (requests per period, series or rows per request, concurrent connections, bulk-download
    rules, required identification or attribution) are read on the supplier's own site, and what was
    found is recorded with the date read in `docs/data-connections.md` (rate limits) and
    `docs/licence-register.md`. The connector is then built to those limits, not to what happens to
    work:
    - It stays inside the stated limits with margin. Where the supplier states none, it makes the
      fewest and smallest requests that do the job: several series per request where the API allows,
      bulk files rather than many small calls, no more history than is needed, and pauses between
      requests.
    - It uses the official API or bulk download only, never page scraping where an API exists, and
      identifies itself with a descriptive `User-Agent`.
    - It honours `Retry-After`, backs off on 429 and 5xx, and when the supplier refuses (403 or 429
      that outlasts the retries) it stops asking for that run instead of retrying into a ban.
    - It runs no more often than the data changes: a monthly series is not fetched hourly.
    - A need that the supplier's limits cannot meet goes to the owner, to change the plan or the
      source. It is never met by rotating addresses or keys, splitting traffic to hide it, or any
      other way round a limit.
    - A connector is not merged until its row in `docs/data-connections.md` states the limits and how
      the code keeps within them, and tests show the identification and the stop on refusal.

## Part 5. Sources, frequency, history and coverage

These rules extend, and never loosen, rules 1-28. Source choice is rule P alone; the other rules here
apply to the source it picks.

B. **Seasonal adjustment is declared and preferred.** Every series carries its adjustment as `SA`,
   `NSA`, or not applicable (`OTHER`, with the source's text and the reason: an annual series, a
   market price, or an adjustment other than seasonal). Rule P picks the source; B picks the
   variant within it: `SA` where the chosen source publishes it, otherwise `NSA`. A comparison across countries or indicators prefers `SA`
   series, and never mixes `SA` with `NSA` silently: a mix is shown with an explicit notice.

D. **One frequency when countries are compared.** Two or more countries on one indicator are
   evaluated at the same frequency: the lowest common one among the selected series. Daily and
   weekly series are aggregated down before anything is drawn or any change is computed, and a
   series is never up-sampled. The aggregation depends on what the series is: period end for a
   stock or level, period average for a rate or index, period sum for a flow.

F. **Charting limits.** Mode 1 plots one indicator for at most 10 countries; mode 2 plots several
   indicators for one country, as actual values on separate axes or as `PoC` (rule 22). The cap,
   the frequency alignment and both computations are enforced in the API; the web app renders the
   selectors and the result.

G. **The frequency filter shows only what is possible.** Both the user and admin dashboards offer
   a frequency filter (daily, weekly, monthly, quarterly, semi-annual, annual) and a metric mode.
   The filter allows only frequencies shared by every selected series, and states in words why a
   frequency is unavailable.

I. **Deep history: every series from 1990.** Every series, new or existing, loads the deepest
   history its source holds from `1990-01-01` (from `2000-01-01` at the least where the source has
   nothing earlier), so all series share one start and indicators compare over the same dates
   (owner instruction, 13 Nov 2026). The default start is `DEFAULT_OBSERVATION_START` in the
   catalog, so a routine run does not trim it. This holds for a new source after a source change
   too (rule 16 says how its overlap with the retired series is handled). A series whose source
   begins later keeps its own first date, stated in the coverage report; it is never spliced with
   older values from a second source (rule 16).

J. **Universal country and indicator cross-matrix.** QuFin's active country universe is the list
   in `COUNTRIES` (`app/data/taxonomy.py`; 87 economies and blocs on 18 Nov 2026), and its
   indicator universe is `Master_Taxonomy_169`. Whenever an indicator is added, the ingestion
   engine probes every country across the candidate sources of rule O; as soon as a valid series
   is available, it serves the provisional choice back to `1990-01-01` (rule I) and stages the
   other eligible candidates (Part 0) until rule P's measured choice replaces the provisional one.
   "Valid" is as rules 1 to 3 define it: a series that is not published live stays out, and the
   sweep keeps to every supplier's limits (rule 28).

L. **Release-calendar precision and a resilient retry policy.** Every ingested series tracks its
   official `next_release_at` timestamp, and the scheduler triggers ingestion at the release
   window, so models train on the freshest data. When an upstream portal answers HTTP 429, 502,
   503 or 504, or times out, there are two layers of retry:
   - *Within a request:* up to 3 retries after 2, 4 and 8 seconds (exponential, `2^n`), or after
     the supplier's `Retry-After` where it gives one, up to 120 seconds (`app/connectors/base.py`).
   - *Across attempts (a capped ladder):* a feed that still fails for a transient reason (a
     timeout, a network error, a 5xx) is tried again after the other sources have had their turn,
     about 15 seconds, 60 seconds, 5 minutes, 15 minutes and 1 hour later, each wait varied at
     random by up to 20% so retries do not arrive in step; after the last step the feed is marked
     degraded. The ladder is bounded by the run's time budget, and the release check runs last.
   Rule 28 governs where it differs: a `Retry-After` longer than a step is honoured, and a 403 or
   a 429 that outlasts the retries stops requests to that supplier for the run, so neither layer
   can become a way round a limit.

N. **A self-running database health and integrity engine ("QuFin Doctor").** QuFin keeps a fast,
   deterministic command line check with automatic repair, `uv run python -m app.cli doctor --fix`,
   that runs after every ingestion job and in continuous integration. It verifies and, where it
   can do so safely, repairs: (a) no duplicate country-indicator mapping (rule 16); (b) no orphaned
   vintage rows and no null or NaN corruption; (c) strictly increasing dates; (d) the `SA` and
   `NSA` tags are accurate; (e) release-schedule freshness (`check-data`, rule 2); and (f) upstream
   series that have frozen are quarantined or flagged. A repair never deletes data without a backup
   and a line in the report saying what was done.

O. **Candidate sources, and no silent gaps.** For every `(country, indicator)` pair in the taxonomy
   the candidates are all of these, with no ranking by tier (rule P alone chooses, and its
   tie-break is the only place the original producer is preferred):
   - FRED/ALFRED;
   - the multilateral aggregators: BIS, IMF, OECD, Eurostat, ECB and the World Bank;
   - the country's official statistics office, central bank, agency or government open-data
     portal, each registered in `app/data/country_sources.py` with the date its terms and limits
     were read (rules 7 and 28), and, for the remaining economies, the UNECE and WTO statistical
     portals.
   A frozen mirror (for example FRED's `*PROINDMISMEI` and `*CPICORMINMEI` series) is not a
   candidate: it fails the live-schedule rules (1 to 3). A pair may stay unpopulated only if no
   candidate has an active, current feed; each such pair is listed with the candidates checked and
   the date, so no gap is silent.

P. **Earliest and most frequent source wins.** For every economy and every indicator, existing and
   to come, the source is chosen from the candidates of rule O, whatever the source is: an
   aggregator, an agency or the original producer.
   *Eligibility first.* A candidate is eligible only if all of these hold; an ineligible source is
   never chosen, however early it is:
   - its licence allows QuFin's use (rule 7);
   - it offers permitted machine access, an official API or bulk download, within its limits
     (rule 28);
   - its definition, unit, adjustment and variant are verified at the source (rules 10, 12, 18, B);
   - it has a live release schedule and is not a frozen mirror (rules 1 to 3, O).
   Among eligible candidates, two measures decide:
   (a) *Earliest.* The source that makes each new observation available first is better. It is
   measured on the same observation: the time from the end of the period to the moment QuFin can
   first read it, from the source's own update timestamp where it gives one and from QuFin's first
   sight of it otherwise, over at least one release cycle. A flash or provisional figure counts as
   a release when the source flags it as such, and follows S5 until the final figure lands.
   (b) *Frequency.* The more often the source releases the indicator, the better: hourly, daily,
   weekly, monthly, quarterly, semi-annual, annual, in that order. The same measure at a lower
   frequency is derived by aggregation (rule D), not stored (rule 16); a different measure is a
   different concept.
   The best source meets both: it is the earliest and it releases at least as often as every other
   candidate. Where no source meets both, the earliest release wins, which is most likely the
   original producer, the source that FRED or an aggregator republishes. If two are equal on both
   measures, the original producer wins. Where eligible candidates publish different adjustments,
   a comparison shows rule B's notice.
   *New pairs.* "Earliest" needs one release cycle to measure, so a new pair is served at first
   from the eligible candidate with the most recent period at the probe (frequency breaks a tie):
   a provisional source decision (Part 0), served and scored. The other eligible candidates are
   staged (Part 0) and timed for one release cycle. If the measured winner is the provisional
   source, the decision is confirmed; otherwise the winner replaces it as a source change, below.
   *Changing source.* Each decision is recorded in `docs/assumptions-register.md` with the
   candidates, the latest period, update timestamp and frequency of each, and the date checked. It
   is checked again at least once a quarter, and whenever the chosen source falls overdue or
   another one overtakes it. A change takes effect from a stated date and is a new source decision:
   from that date the new source serves the pair with its full history (rules I and 16); reads as
   of an earlier date use the retired series, so past scores and backtests do not change (rules 6
   and 20). The chosen
   source is read as published (rule 6).

## Retired numbers

Merged into another rule, so each subject is ruled once. The old number still resolves here.

| Old | Now in | What happened |
|---|---|---|
| 5 | S2 | Late data weighs less: the timeliness weight is part of the scorecard average |
| 13 | 22 | Change units and "never change a change" join the change-measure rule |
| 14, A, K | P (b) | Frequency preference is a source-selection measure; the scorecard use is S1 |
| 17, H, M | P, 16 | FRED first is replaced by earliest and most frequent; one source per pair is rule 16 |
| 19 | 18 | One global name joins the naming rule |
| C | 6 | Vintages joined the point-in-time rule |
| E | 22 | `PoC` beside the actual value joined the change-measure rule |

The tier order of the old rule O is replaced by rule P; its registered portals and its no-silent-gaps
requirement are kept in the new rule O. The UK ONS first fallback of old rule H and the agency
"fast lane" of old rule 17 are replaced by rule P.

## Change log

| Date | Rule | Change |
|---|---|---|
| 6 Nov 2026 | 1-19, S1-S9 | Moved into this rule book from the API folder; wording unchanged |
| 6 Nov 2026 | 20-26 | Added: show/hide control of the scorecard mechanism, earned weights, percent-change admissibility, common basis for comparison, ownership, no attribution, rule changes |
| 6 Nov 2026 | 12 | Judgements are recorded in `docs/assumptions-register.md` |
| 6 Nov 2026 | 18, 19 | Names come from the data and calendar sites, not memory; one global name and acronym per indicator |
| 6 Nov 2026 | 27 | Added: every data connection is documented in `docs/data-connections.md` |
| 6 Nov 2026 | 27 | Widened: ingestion and retrieval are documented in `docs/data-pipeline.md` |
| 12 Nov 2026 | 28 | Added: every connector follows its supplier's published limits and policies and must never be banned (owner instruction) |
| 12 Nov 2026 | A-H | Added Part 5: earliest signal, seasonal adjustment, vintages, one frequency per comparison, `PoC`, chart limits, frequency filter, FRED first (owner instruction) |
| 13 Nov 2026 | H, I | H: UK fallback to the ONS where FRED lacks a current SA series with vintages. Added I: every series loads from 1990 (owner instruction) |
| 13 Nov 2026 | J-N | Added: 85-country and 169-indicator cross-matrix, highest frequency first, release-calendar precision with a retry ladder (rule 28 governs), FRED first with authentic fallbacks, and the QuFin Doctor health engine (owner instruction) |
| 13 Nov 2026 | O | Added: three-tier source cascade (FRED, multilateral aggregators, official national portals) and no silent gaps (owner instruction) |
| 13 Nov 2026 | J | The country universe is 87: the 85 of the QuFin Country List plus Chile and Colombia (owner instruction) |
| 18 Nov 2026 | P (17, H, M, O) | Added: the earliest and most frequent source wins for every economy; supersedes the FRED-first order (owner instruction) |
| 18 Nov 2026 | All | Consolidated into a master rule book: duplicate rules merged (5, 13, 14, 17, 19, A, C, E, H, K, M retired into S2, 22, P, 16, 18, 6), conflicts resolved (2, 4, 6, 9, B, I, J, N, O, S1, S5, S6), retired numbers listed; no rule's substance dropped except the FRED-first order |
| 18 Nov 2026 | 0, 2, 6, 8, 10, 15, 16, 18, 20, 21, 22, 24, 28, B, J, L, O, P, S1, S2, S5, S7 | Cross-verification fixes: Part 0 definitions (due date, grace, status, usable, score scale, data table, hot query, source decision); P eligibility filter, provisional choice and dated source changes; public correction mechanism vs proprietary recipe; owner approval and versioning of scores; CPI variants; S2/S5 estimate exception; zero-denominator changes; `OTHER` adjustment; ingest failure semantics; duplicate-check pre-filter; two-layer retry; narrower 8 and 15; rule 24 scoped to tools, not data sources |
| 18 Nov 2026 | 0, 2, 6, 16, 18, 20, 21, 22, 24, I, J, P | Second cross-verification: a new source loads from 1990 and only its own retired series is exempt from the duplicate check; recipe acknowledged as rule 24's one exception, versioned privately with hashes in `docs/scorecard-versions.md`; provisional decision, staging, retired series and catalog version defined; J serves the provisional choice and stages the rest; owner decides disclosure; equal weights allowed when weight cards show equal inputs; change-kind re-declaration versioned; naming tie-break; charts mark source changes; downstream jobs read usable series after a failed run; release-lag window stated |
