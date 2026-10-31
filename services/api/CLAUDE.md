# CLAUDE.md — QuFin API

See [README.md](./README.md) for setup, endpoints and layout.

## Data integrity rules (non-negotiable)

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
    verify each against the primary source, and report any that could not be verified.
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

## Scorecard correction mechanism (non-negotiable)

A delayed or missing indicator must make a score **less certain, never more bullish or
bearish**. Score and confidence are separate outputs (`app/domain/scorecard.py`):

1. **Score each indicator point in time** against its own history as published then: a
   z-score over ten years, clipped to -3..+3, flipped where higher means weaker, on two
   parts averaged equally: where it stands and its 3-month momentum (`MOMENTUM_WEIGHT`).
2. **Rescaled weighted average per pillar:** `score = Σ wᵢ·sᵢ / Σ wᵢ` over usable
   indicators, with `wᵢ` = base importance × timeliness weight. Overdue, discontinued, missing
   or unscorable indicators drop out (weight 0). Never count missing data as zero (a plain
   sum pulls scores toward neutral: strong economies underrated, weak ones overrated), and
   never carry an old value forward at full weight.
3. **Confidence is reported separately:** `Σ wᵢ / Σ base importance`. It never changes the
   score.
4. **Caution goes into position size, not into the view.** Size trade ideas by confidence.
5. **Fix delays at the source where the licence allows it**, rather than living with them.
   An estimate for a missing release may be added only if it is labelled as an estimate,
   at reduced weight, and replaced when the real figure lands.
6. **Show what is pending:** every live scorecard lists the releases still to come, with the
   source and FRED dates, so users know the score may move and why.
7. **Prove there is no bias:** `uv run python -m app.cli scorecard-bias` compares the
   scorecard users would have seen each month with complete information. The mean difference
   must stay within ±0.25 for every pillar and overall; if it fails, the scorecard must not
   be used until the cause is fixed. `tests/test_scorecard.py` enforces the rules above; do
   not loosen it to make a change pass.
8. **A currency pair is only as certain as its less certain side:** use
   `pair_confidence(base, quote)` (the minimum), so a stale side cannot make a pair look
   decisive.
9. **Never mix live and sample scorecards** in one ranking; sample data is always labelled.
