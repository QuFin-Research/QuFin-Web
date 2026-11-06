# QuFin Rule Book

**This rule book is the property of QuFin (the QuFin-Web repository).** It stands on its own: no rule
depends on any tool, vendor or person, and it remains in force whoever or whatever builds or maintains
QuFin. Everything that builds, tests or reviews QuFin follows it, and a change that breaks a rule is a
defect, however convenient. Rules are numbered and keep their numbers; the code, tests and docs refer
to them as "rule N" ("S1" to "S9" for the scorecard correction mechanism).

QuFin is a data-extensive trading assistant. Its trading ideas, scores and backtests rest on the
data, so the rules below put data integrity first, then comparability, then transparency.

Contents: Part 1 data integrity (rules 1-19) | Part 2 comparison, change measures and weights (rules
20-23) | Part 3 scorecard correction mechanism (S1-S9) | Part 4 ownership, documentation and conduct (rules 24-27) |
Change log. Related documents: `private/scorecard-methodology.md` (proprietary, not committed while this repository is public), `docs/assumptions-register.md`,
`docs/indicator-names.md`, `docs/data-provenance.md`, `docs/licence-register.md`,
`docs/release-calendars.md`.

## Part 1. Data integrity rules (non-negotiable)

QuFin's trading ideas rest on this data, so these rules apply to every data source and every
series, existing or new:

1. **No series without a live release schedule.** Before adding a series to a catalog, check
   on the source that it is still published: its latest observation fits its frequency and
   usual release lag, and it is not marked discontinued. Run
   `uv run python -m app.cli check-data` after ingesting and include its result in the PR.
2. **Every ingest ends with the release check.** `ingest-fred`, `ingest-cftc` and `check-data`
   exit non-zero when any series is overdue, discontinued or needs review. Never silence or
   bypass that, and never widen the grace periods to make a failure pass.
3. **Unusable data stays out.** The API reports `freshness.usable` on every series. Signals,
   scorecards and backtests must skip series where it is false, never fill them with the last
   value as if it were current.
4. **Name the real source and its dates.** Every series records who produces it (e.g. the
   University of Michigan, not FRED) and its release. When an aggregator such as FRED
   publishes later than the source (licensing), declare it in the catalog (`fred_delay_days`,
   `delay_note`). A FRED delay notice without a declared delay, or a declared delay FRED no
   longer reports, fails the check as "review".
5. **Late data weighs less.** Scorecards weight each series by `timeliness.weight`, which halves
   for every 60 days between the end of a period and the day QuFin can read it. Fresh data
   (daily rates, weekly claims) keeps full weight.
6. **Point in time only.** Backtests read data as it was published (`asOf`), never revised
   values before their release date.
7. **Check the licence before relying on a series commercially.** Some sources restrict use in
   a product sold to others, whatever channel the data arrives through. The University of
   Michigan survey (UMCSENT) is free only for research or strictly internal use; a platform,
   dashboard or investment advisory needs a licence from umsurvey@umich.edu. Moody's data
   (BAA10Y) carries a similar proprietary notice. Record such limits in the catalog.
8. **Every number states its origin.** Each data endpoint returns `data` ("live" or "sample")
   or `freshness`; `tests/test_provenance.py` fails otherwise. Sample numbers are labelled on
   every page whether or not the user is signed in, and nothing invented (signals, alerts,
   notifications) is ever shown as if it were real. See `docs/data-provenance.md`.
9. **Release dates come from the source's real calendar**, including holidays, shutdowns and
   incidents (`app/data/cot_calendar.py` for the CFTC). Where a date is not published, derive
   it from the source's stated rule and mark it derived; when in doubt, err late, never early.
10. **Verify meaning at the source before scoring.** For every scored indicator, confirm its
    definition, sign, units and adjustment from the producer's own notes, and record the reason
    in `app/data/scorecard_catalog.py`. Growth is scored in real terms only (nominal dollars
    read inflation as growth).
11. **Flag partial coverage.** A contract or series that covers only part of its market (e.g.
    NYMEX Brent, while most Brent trades on ICE) carries a caveat that the API and page show.
12. **Assumptions are listed and checked, not trusted.** Before adding or changing any data
    path, list every assumption (mapping, sign, unit, release timing, licence, coverage),
    verify each against the primary source, and report any that could not be verified. Record every judgement in
    `docs/assumptions-register.md` with its status (verified, convention, design choice,
    unverified); a judgement with no row there is a defect.
13. **Measure change in the right units, and never change a change.** Quantities and price
    indexes change in percent; rates, spreads, ratios and indexes that can be zero or negative
    change in their own units (points). Each catalog series declares its `change` kind, and a
    series the source already publishes as a change or growth rate is marked
    `published_as_change` (read the source's notes, not just the units: WEI's units say
    "Index" but it is a GDP growth rate). The release check fails a percent change or y/y on
    such a series. Changes are taken within one vintage, never across vintages.
14. **Prefer the earliest honest read.** Where a weekly or daily series measures the same
    thing as a monthly one, carry it too; the scorecard averages it into the current month as
    soon as each week lands, and its momentum part (3-month change) catches turns before the
    level does.
15. **Every hot query is indexed; nothing aggregates a data table on a page load.** Data grows
    with every country and series, so a full scan gets slower with each one added. Each read a
    page or job relies on is listed in `tests/test_query_plans.py`, which fails if the planner
    scans a data table; a new read is added there with the index that serves it, in a
    migration. Summaries a page needs (coverage, counts, latest period) are stored at ingest,
    not computed per request. Bulk loads end with `ANALYZE` so the planner picks the right
    index. Indexes belong to the table, so rows for series added later are indexed on insert.

16. **No duplicated indicators or data, at any cost.** A country has at most one series per
    concept (`app/data/indicator_concepts.py`), and a series that can be derived exactly from
    stored ones is not stored (`REDUNDANT`, e.g. the 10y-2y spread from the two yields).
    `tests/test_indicator_concepts.py` fails otherwise. The release check (`check-data`) also
    compares every stored series with every other, from any source: two that carry the same
    values, or the same values in other units, both fail as "review" until one is removed.
17. **FRED/ALFRED first, at least for the US.** Use an agency's own API (BLS, BEA, EIA, ...)
    only for a leading indicator FRED does not carry, or a lagging one that is mandatory to
    gauge an economy, currency, country or asset; record the reason in `NON_FRED_ALLOWED`. An
    agency API may also be used as a release-time fast lane for a FRED series, stored as a
    vintage of the same series and reconciled against FRED, never as a second series.
18. **Every series has a human-readable name, shared across countries.** Each maps to a
    concept with a name and a one-sentence plain explanation; indices use their standard name
    with the acronym first ("CPI – Consumer Price Index", "PPI – Producer Price Index"); the same concept key
    matches the indicator in every country (US and UK unemployment are both
    `unemployment_rate`, "Unemployment Rate"). The API returns the name and the official
    title; pages show the name, with the official title, source code and publisher in a
    tooltip. A series without a name fails the tests. Never choose a name from memory: read what FRED, Trading
    Economics and the Forex Factory calendar call the indicator and record the survey in
    `docs/indicator-names.md`. Every series also has a business-cycle tag
    (`app/data/cycle_classification.py`, with a reason); the catalog refuses a series without one.

19. **One global name for every indicator, in every country and every layer.** An indicator is
    known by its globally recognised name and acronym (CPI, PPI, GDP, NFP, PMI, ...), never by a
    country's local name for it: the euro area's HICP and the UK's CPIH are both "CPI". Series
    from every country map to the same concept, and that name is used everywhere QuFin names
    things: database, API (`name`, `concept`, `acronym`), charts, comparisons, scorecards,
    backtests, alerts and docs. The local name appears only in the official title and tooltip.
    Acronyms and their full names are listed in `ACRONYMS` (`app/data/indicator_concepts.py`),
    local aliases in `LOCAL_ALIASES`; add the acronym there before using it, and add a country's
    series to the existing concept rather than inventing a new name. Tests enforce the format.

## Part 2. Comparison, change measures and weights

20. **QuFin controls whether the scorecard mechanism is shown or hidden.** The mechanism
    (indicators, directions, weights, formulas, assumptions) is QuFin's proprietary recipe. It is
    always documented in full, internally, in plain words (`private/scorecard-methodology.md`, kept out
    of version control while the repository is public), so QuFin
    can explain and defend every score. Whether users see it is QuFin's decision, made with one
    switch (`QUFIN_SCORECARD_MECHANISM`: `show` or `hide`, default `hide`) that can be changed at
    any time, and the recipe may be disclosed to a person or organisation on request. When hidden,
    the API and dashboard leave out weights, sub-scores and method text. **Never hidden, whichever
    way the switch is set:** that a score comes from a model and is not advice, where the data comes
    from and whether it is live or sample (rule 8), how fresh it is, the confidence in each score,
    and the releases still to come (S6). Every change to the mechanism or to a weight is recorded in
    the methodology's change log with the reason, takes effect only after the bias gate (S7) and a
    point-in-time backtest, and never silently alters a past score. A modelling assumption (for
    example that hot inflation supports a currency) is documented as an assumption, not a fact.
21. **Indicator weights are earned, never assumed equal.** An indicator's weight in a pillar reflects
    how much it matters: its market impact, its predictive power, how reliable it is (revisions,
    noise) and how timely it is. Equal weights are a defect, and so are weights nobody can explain.
    Each weight has a recorded basis (its "weight card"), kept internally and shown to users only when the mechanism is shown; weights come from the
    mechanism in the methodology, are estimated only from data available at the time (no
    look-ahead), are capped so that no single indicator dominates a pillar, and are recalibrated on
    a fixed schedule with the before and after recorded. Until the mechanism is approved and
    calibrated, any interim weight is labelled interim wherever it is shown.
22. **Percent change (PoC) is used only where it is admissible, and users can see both views.** Each
    catalog series declares how it changes, from its definition and units, not by habit:
    - *Percent change* (PoC): strictly positive quantities, counts, amounts and price or volume
      indexes: employment, claims and benefit claims, orders, sales, production, prices, money
      and balance-sheet totals, debt amounts, exchange rates, commodity prices.
    - *Change in points* (percentage points, index points): rates, yields, spreads, ratios, shares
      (for example % of GDP), and diffusion or sentiment indexes, which can be zero, negative or
      already bounded.
    - *Change in own units* (an amount, not a percentage): series that can cross zero, such as the
      trade balance, current account and budget balance.
    - *No change taken*: a series the source already publishes as a change or growth rate (rule 13:
      never a change of a change); it is shown as published.
    Every chart and table offers the **actual value** and the **change** (percent or points, as
    declared) of any series, so users compare either; for a series with a declared change kind
    the change view is always available, and for one with none the actual only. Claims and other
    benefit-claim series are scored and charted on their percent change, with the actual counts
    shown beside it. A new series is not added until its change kind is declared and tested.
23. **Only compare what has a common basis.** Two series are compared, overlaid, ranked or combined
    only when they share a unit and currency, or have first been put on a common basis: (a)
    percent or point changes; (b) standardised scores against each series' own history; (c)
    ratios to a common denominator (for example % of GDP); (d) indexes rebased to 100 at a common
    date; or (e) conversion to one currency at a stated exchange rate and date, with the rate's
    source shown (purchasing-power parity for levels where that is the point). The US GDP in
    dollars is never put beside the UK GDP in pounds, and a count is never put beside a rate on one
    scale. Each series records its unit and currency; the dashboard states the basis of every
    comparison and refuses an overlay that has none. Scorecards compare countries only through
    standardised scores, never through raw values.

## Part 3. Scorecard correction mechanism (non-negotiable)

A delayed or missing indicator must make a score **less certain, never more bullish or
bearish**. Score and confidence are separate outputs (`app/domain/scorecard.py`):

S1. **Score each indicator point in time** against its own history as published then: a
   z-score over ten years, clipped to -3..+3, flipped where higher means weaker, on two
   parts averaged equally: where it stands and its 3-month momentum (`MOMENTUM_WEIGHT`).
S2. **Rescaled weighted average per pillar:** `score = Σ wᵢ·sᵢ / Σ wᵢ` over usable
   indicators, with `wᵢ` = base importance × timeliness weight. Overdue, discontinued, missing
   or unscorable indicators drop out (weight 0). Never count missing data as zero (a plain
   sum pulls scores toward neutral: strong economies underrated, weak ones overrated), and
   never carry an old value forward at full weight.
S3. **Confidence is reported separately:** `Σ wᵢ / Σ base importance`. It never changes the
   score.
S4. **Caution goes into position size, not into the view.** Size trade ideas by confidence.
S5. **Fix delays at the source where the licence allows it**, rather than living with them.
   An estimate for a missing release may be added only if it is labelled as an estimate,
   at reduced weight, and replaced when the real figure lands.
S6. **Show what is pending:** every live scorecard lists the releases still to come, with the
   source and FRED dates, so users know the score may move and why.
S7. **Prove there is no bias:** `uv run python -m app.cli scorecard-bias` compares the
   scorecard users would have seen each month with complete information. The mean difference
   must stay within ±0.25 for every pillar and overall; if it fails, the scorecard must not
   be used until the cause is fixed. `tests/test_scorecard.py` enforces the rules above; do
   not loosen it to make a change pass.
S8. **A currency pair is only as certain as its less certain side:** use
   `pair_confidence(base, quote)` (the minimum), so a stale side cannot make a pair look
   decisive.
S9. **Never mix live and sample scorecards** in one ranking; sample data is always labelled.

## Part 4. Ownership, documentation and conduct

24. **The rule book and QuFin's code belong to QuFin.** The rule book is kept in this repository, in
    plain text, and is the only place rules are defined. Instruction files for any development tool
    may exist only as a pointer to it and must add no rule of their own. No rule, test, data file or
    process may depend on a particular tool or vendor, so QuFin can change any of them at any time.
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

## Change log

| Date | Rule | Change |
|---|---|---|
| 6 Nov 2026 | 1-19, S1-S9 | Moved into this rule book from the API folder; wording unchanged |
| 6 Nov 2026 | 20-26 | Added: show/hide control of the scorecard mechanism, earned weights, percent-change admissibility, common basis for comparison, ownership, no attribution, rule changes |
| 6 Nov 2026 | 12 | Judgements are recorded in `docs/assumptions-register.md` |
| 6 Nov 2026 | 18, 19 | Names come from the data and calendar sites, not memory; one global name and acronym per indicator |
| 6 Nov 2026 | 27 | Added: every data connection is documented in `docs/data-connections.md` |
| 6 Nov 2026 | 27 | Widened: ingestion and retrieval are documented in `docs/data-pipeline.md` |
