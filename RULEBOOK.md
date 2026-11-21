# QuFin Rule Book (master)

**Version 3.5 — 20 November 2026.** This rule book is the property of QuFin (the QuFin-Web repository). It stands on its own: no rule depends on any tool, vendor or person, and it remains in force whoever or whatever builds or maintains QuFin. Everything that builds, tests or reviews QuFin follows it, and a change that breaks a rule is a defect, however convenient. Each subject is ruled once, in one place. Terms used in more than one rule are defined once, in Part 0. Where two rules ever seem to disagree, the stricter reading applies until the rule book is corrected (rule 26); a disagreement is a defect.

QuFin is a data-extensive trading assistant. Its trading ideas, scores and backtests rest on the data, so the rules below put data integrity first, then comparability, then transparency.

**Related documents:** `private/scorecard-methodology.md` (proprietary, not committed while this repository is public), `private/disclosure-log.md` (private), `docs/assumptions-register.md`, `docs/indicator-names.md`, `docs/data-provenance.md`, `docs/licence-register.md`, `docs/release-calendars.md`, `docs/data-connections.md`, `docs/data-pipeline.md`, `docs/scorecard-versions.md`, `docs/rulebook-paths-waivers.md`.

---

## Preamble — How to read this rule book

Every rule has a **number**, a **title**, a **Purpose** (one sentence stating what the rule ensures), a **Force** (what kind of obligation it imposes), the **Text** (the enforceable content), and a **Cross-references** block (which other rules and which code, tests and docs depend on it or are depended on by it).

**Force is one of three values:**

- **Mandatory** — a defect if broken; no exception without a Rule 26 change.
- **Conditional (<conditions>)** — mandatory where the named conditions hold; no exception without a Rule 26 change.
- **Informational** — a definition, convention or note; not independently enforceable, but relied on by rules that are.

A Force may carry a scope in parentheses where a rule applies only inside part of the book: the scorecard rules S1–S9 are `Mandatory (within the scorecard mechanism)`, which means Mandatory wherever the scorecard is computed.

Rules are numbered **1–38** with gaps at 5, 13, 14, 17 and 19 (retired; see Appendix A). The scorecard correction mechanism is a **sub-series S1–S9**, scoped to Part 4 because the private methodology quotes it as a unit; each S-rule follows the same Force, cross-reference and change procedure as any numbered rule. No new prefixes are introduced: any future rule is a number.

Where two rules seem to disagree, the stricter reading applies until the book is corrected (Rule 26). A disagreement is a defect.

**Cross-references.** Every rule's cross-reference block names its implementation file and its test file. **The `Depends on:` line is hand-maintained and must list, exactly, every rule, §0.1 term, §0.2 value and §0.3 principle that the rule's Purpose or Text cites, either by number or by name.** A rule body cites a rule only by its number (`rule N`), by its S-number (`S<N>`, where N is 1–9; a range `S1–S9` in a rule body expands to `S1, S2, S3, S4, S5, S6, S7, S8, S9` in that rule's `Depends on:` line), by its Part 0 term (§0.1), value (§0.2) or principle (§0.3) by name, or by the exact title of the rule. The implementation name (e.g., `check-data`) is **not** a citation of the rule that describes it; the rule number must appear alongside it. **The `Referenced by:` line is generated** by `scripts/build_rule_index.py` from the union of every other rule's `Depends on:` line; it never appears in a rule body — it appears only in Appendix B. `tests/test_rulebook.py` fails if a rule body cites a rule not in its `Depends on:`, or if a `Depends on:` entry is not cited in the body.

**Part 0 is binding. §0.1 definitions, §0.2 normative values and §0.3 principles are constraints equivalent in force to Mandatory rules.** A rule that cites them depends on them. A change to §0.1 or §0.3 is a Rule 26 change, recorded in the change log as `0.1 (term: <name>)` or `0.3 (principle: <n>)`. A change to a §0.2 value is a Rule 26 change, recorded as `0.2 (value: <name>)`.

**Path resolution.** Every implementation and test path cited in a rule's cross-reference block is **relative to the repository root**. The path `app/…` means `services/api/app/…`; the path `tests/…` means `services/api/tests/…`; the path `migrations/…` means `services/api/migrations/…`; `apps/web/…`, `docs/…` and `scripts/…` are as written. `private/…` paths live in a private repository and are not resolved by the test, because they do not exist in a public checkout.

**Rule 25 applies to this document.** The rule book, its change log and its appendices are documents covered by Rule 25; no rule-book entry may name an AI assistant or code-generation tool.

Appendix A is the permanent record of every retired and renumbered rule. Appendix B is the **generated** cross-reference index. Appendix C is the change log. Appendix D exists only while the v2.4 → v3.4 migration is in flight, and is deleted after one release cycle.

---

## Part 0. Definitions and principles

### 0.1 Terms

- **Due date** of a series: the scheduled date on the source's real release calendar (rule 9) where one is published, otherwise the end of its latest stored period, plus one period, plus its median release lag, plus any declared aggregator delay (rule 4). The calendar takes priority over the median lag where both are available, and a calendar-derived due date is marked derived as rule 9 says. The median is taken over the releases first seen in the trailing three years (`LAG_WINDOW`, `app/jobs/check_data.py`); where fewer than three releases have been observed, the fallback is the source's own stated lag rule (one release interval), recorded in the catalog.
- **Grace period:** days allowed after the due date before a series is overdue: daily 5, weekly and biweekly 7, monthly 14, quarterly 30, semi-annual 45, annual 60 (`GRACE_DAYS`, `app/domain/freshness.py`).
- **Status:** `overdue` when today is past the due date by more than the grace period, or nothing is stored; `discontinued` when the source marks it so; `review` when a check needs a person to decide (a duplicate under rule 16, a delay notice that does not match the declared delay under rule 4, a change taken on a `published_as_change` series under rule 22, a frozen upstream series under rule 36); otherwise `ok`.
- **Usable** (`freshness.usable`): the status is `ok`. Nothing else is usable.
- **Timeliness weight:** `0.5 ^ (days after period end until QuFin can read it / 60)`, and 0 when not usable (`HALF_LIFE_DAYS`, `app/domain/freshness.py`).
- **Score scale:** indicator scores, pillar scores and overall scores are on one scale, -3 to +3 (S1, S2).
- **Data table:** a table that grows with observations, vintages or bars (for example `macro_observations`). Tables that grow only with the catalog (countries, concepts, sources, job runs) are metadata tables.
- **Hot query:** a read that a page load, an API request or a scheduled job makes.
- **Source decision:** the source chosen for a country-indicator pair under rule 38, with the date it took effect. Each pair's decisions form its source history. A **provisional** source decision is the first one for a new pair, made before a release cycle has been measured (rule 38); it is a source decision like any other: the source serves and is scored, and scores record it (rule 20).
- **Staging:** where the candidate sources for a pair are loaded and timed. Staged series are never served or scored, and the duplicate check skips them. Staged series are discarded, not retired, when a provisional decision is confirmed or a measured winner replaces it: they were never served or scored, so no as-of read refers to them. A staged candidate that wins promotion does not discard its observations; they promote into the active series (rule 38).
- **Retired series:** the stored history of a pair's previous source after a source change. It is read only for as-of dates before the change (rule 16).
- **Catalog version:** the state of the catalog declarations (source decision, change kind, adjustment, variant, unit) a value or score was computed with.
- **Scorecard recipe:** the parameters of the scorecard mechanism (rule 20): which indicators enter each pillar, their directions, their weights and weight cards, the calibration, and the modelling assumptions. It lives in `private/scorecard-methodology.md` and is governed by rule 20 and S1–S9. The correction mechanism itself (S1–S9) is public and is not part of the recipe.
- **Native source** of an economy: the source closest to where its data originates, in this order. First the original producer (the national statistics office, central bank or agency). Then the aggregator that belongs to the economy's own country or bloc: Eurostat for the European Union, the euro area, the EFTA economies and the candidate economies it serves, and FRED for the United States. Then a global aggregator: FRED (for every non-US economy), the IMF, the World Bank, the BIS or the OECD. FRED is the aggregator of the United States only; for every other economy it is a global aggregator. An economy without a bloc aggregator (for example Japan, Canada or Australia) has a tie-break order of original producer, then a global aggregator. It is used only to break a tie (rule 38), and not at all for a pair covered by rule 38's *Bloc aggregator first*.

### 0.2 Normative values

The values below are normative: a rule that cites them depends on them, and a change to a value here is a Rule 26 change, recorded in the change log as `0.2 (value: <name>)`.

| Name | Value | Home |
|---|---|---|
| `HALF_LIFE_DAYS` | 60 | `app/domain/freshness.py` |
| `GRACE_DAYS` (daily) | 5 | `app/domain/freshness.py` |
| `GRACE_DAYS` (weekly, biweekly) | 7 | `app/domain/freshness.py` |
| `GRACE_DAYS` (monthly) | 14 | `app/domain/freshness.py` |
| `GRACE_DAYS` (quarterly) | 30 | `app/domain/freshness.py` |
| `GRACE_DAYS` (semi-annual) | 45 | `app/domain/freshness.py` |
| `GRACE_DAYS` (annual) | 60 | `app/domain/freshness.py` |
| `LAG_WINDOW` | trailing 3 years | `app/jobs/check_data.py` |
| `MOMENTUM_WEIGHT` | 0.5 | `app/domain/scorecard.py` |
| `MAX_MEAN_BIAS` | ±0.25 score points | `app/jobs/scorecard.py` |
| `DEFAULT_OBSERVATION_START` | 1990-01-01 | `app/data/macro_catalog.py` |
| `DUPLICATE_FINGERPRINT_TOLERANCE` | 1e-6 (relative) | `app/domain/duplicates.py` |
| `DUPLICATE_MIN_FINGERPRINTS` | 12 (effective: `min(12, max(DUPLICATE_MIN_FINGERPRINTS_FLOOR, periods − 1))`) | `app/domain/duplicates.py` |
| `DUPLICATE_MIN_FINGERPRINTS_FLOOR` | 4 | `app/domain/duplicates.py` |
| `DUPLICATE_MIN_SHARED_PERIODS` | 20 | `app/domain/duplicates.py` |
| `DUPLICATE_MIN_DISTINCT_VALUES` | 5 | `app/domain/duplicates.py` |
| `DUPLICATE_MATCH_SHARE` | 0.95 | `app/domain/duplicates.py` |
| `DUPLICATE_CHECK_TIMEOUT_SECONDS` | 600 | `app/jobs/check_data.py` |
| `INGEST_RUN_TIME_BUDGET_SECONDS` | 14400 | `app/core/config.py` (`refresh_run_timeout_seconds`) |
| `DISCOVERY_SWEEP_TIME_BUDGET_SECONDS` | 21600 | `app/jobs/ingest.py` |
| `ZSCORE_WINDOW_YEARS_STANDARD` | 10 | `app/domain/scorecard.py` |
| `ZSCORE_WINDOW_YEARS_ANNUAL` | 20 | `app/domain/scorecard.py` |
| `ZSCORE_MIN_OBSERVATIONS_MONTHLY` | 36 | `app/domain/scorecard.py` |
| `ZSCORE_MIN_OBSERVATIONS_QUARTERLY` | 16 | `app/domain/scorecard.py` |
| `ZSCORE_MIN_OBSERVATIONS_SEMIANNUAL` | 8 | `app/domain/scorecard.py` |
| `ZSCORE_MIN_OBSERVATIONS_ANNUAL` | 8 | `app/domain/scorecard.py` |

### 0.3 Principles

1. **Data integrity first, then comparability, then transparency.** A rule that trades one for another is a defect unless the trade-off is explicitly ruled.
2. **No number without provenance.** Every value carries its source, its release date and its point-in-time position.
3. **Fresher is worth more.** The scorecard's timeliness weight (Part 0, §0.1) prices lateness into every score; no source-selection or scorecard rule may silently reverse that. The one explicit exception is rule 38's *Bloc aggregator first*, which trades freshness for comparability across the economies Eurostat serves (rule 23); the lateness is priced into every score like any other source's.
4. **Reference stability.** Rules keep their numbers. A number whose rule was merged into another is listed in Appendix A, so an old reference still leads to the rule that now holds it.
5. **Owner approves rule changes.** A rule changes only by a reviewed pull request that the QuFin owner merges, with a change-log entry.

---

## Part 1. Data integrity rules

These rules apply to every data source and every series, existing or new.

### Rule 1. No series without a live release schedule

**Purpose:** Prevent discontinued or frozen series from entering the catalog, so no score or backtest rests on data that is no longer published.

**Force:** Mandatory.

**Text:** Before adding a series to a catalog, check on the source that it is still published: its latest observation fits its frequency and usual release lag, and it is not marked discontinued. Run the release check (rule 2) after ingesting and include its result in the PR (rule 26).

**Cross-references:**
- Depends on: 2, 26
- Implementation: `app/jobs/check_data.py`
- Tests: `tests/test_freshness.py`, `tests/test_admin_api.py`

### Rule 2. Every ingest run ends with the release check

**Purpose:** Every run either confirms the catalog is live or names the series that failed, so a stale series never silently blocks others and never silently enters use.

**Force:** Mandatory.

**Text:** Each `ingest-*` command runs the release check (rule 1), or, when a refresh chains several commands, one final check runs after the last (`QUFIN_DEFER_RELEASE_CHECK`). The ingest commands and the release check exit non-zero when any series is overdue, discontinued or needs review. A run keeps what it loaded correctly: series that loaded are committed, the run is marked failed, and the report names each failing series, so one stale series never blocks the others; rule 3 keeps the failing ones out of use. Downstream jobs (scorecards, backtests, alerts) do not wait for a successful run: they read the committed series whose `freshness.usable` is true. Staged series (Part 0, §0.1) that fail their own freshness check are reported in the run report without failing the production ingest exit code; staged series never enter the production `freshness.usable` set. Never silence or bypass that, and never widen the grace periods (Part 0, §0.1) to make a failure pass.

**Cross-references:**
- Depends on: 0.1, 1, 3
- Implementation: `app/jobs/check_data.py`, `app/jobs/refresh.py`
- Tests: `tests/test_freshness.py`, `tests/test_admin_api.py`

### Rule 3. Unusable data stays out

**Purpose:** Ensure no rule, score or signal uses a value the freshness check has marked unusable.

**Force:** Mandatory.

**Text:** The API reports `freshness.usable` on every series. Signals, scorecards and backtests must skip series where it is false, never fill them with the last value as if it were current.

**Cross-references:**
- Depends on: 0.1
- Implementation: `app/domain/freshness.py`
- Tests: `tests/test_freshness.py`

### Rule 4. Name the real source and its dates

**Purpose:** Make provenance explicit, so a series is always attributed to its producer and never to a republisher, and any aggregator delay is visible.

**Force:** Mandatory.

**Text:** Every series records who produces it (e.g. the University of Michigan, not FRED) and its release (rule 9). When an aggregator (FRED or any other) publishes later than the source (licensing), declare it in the catalog (for FRED: `fred_delay_days`, `delay_note`). A delay notice without a declared delay, or a declared delay the aggregator no longer reports, fails the check as `review` (Part 0, §0.1).

**Cross-references:**
- Depends on: 0.1, 9
- Implementation: `app/data/macro_catalog.py`
- Tests: `tests/test_provenance.py`

### Rule 6. Point in time only; vintages are kept and served

**Purpose:** Guarantee that backtests and scores see only what was available at the time, and that charts are honest about which vintage they display.

**Force:** Mandatory.

**Text:** Backtests read data as it was published (`asOf`), never revised values before their release date (rule 9). Wherever the source provides revisions (FRED/ALFRED), the store keeps every vintage and chart endpoints serve them. Charts show the current vintage by default: the whole series as the source publishes it today, one vintage for every period, never the latest value of each period stitched from different vintages; the chart states the vintage date and the source of the current vintage (rule 4), marks the date of any source change (rule 38), and earlier vintages stay available. Where the source keeps none, QuFin records each value as first seen, a flash and its final separately, dated by the real release (rule 9); history from before the first load carries no vintages and is labelled so.

**Cross-references:**
- Depends on: 4, 9, 38
- Implementation: `app/stores/macro.py`
- Tests: `tests/test_record_latest.py`, `tests/test_macro_api.py`

### Rule 7. Check the licence before relying on a series commercially

**Purpose:** Prevent QuFin from shipping a series in a commercial product whose licence restricts commercial use.

**Force:** Mandatory.

**Text:** Some sources (rule 4) restrict use in a product sold to others, whatever channel the data arrives through. The University of Michigan survey (UMCSENT) is free only for research or strictly internal use; a platform, dashboard or investment advisory needs a licence from umsurvey@umich.edu. Moody's data (BAA10Y) carries a similar proprietary notice. Record such limits in the catalog.

**Cross-references:**
- Depends on: 4
- Implementation: `docs/licence-register.md`
- Tests: —

### Rule 8. Every number states its origin

**Purpose:** Ensure no user ever mistakes sample data for live data, or an invented number for a computed one.

**Force:** Mandatory.

**Text:** Each endpoint that returns an observed value (rule 10), or anything computed from one (a change, score, signal or backtest), returns `data` ("live" or "sample") or `freshness` (Part 0, §0.1); metadata endpoints (country, concept and source lists, calendars) need not; `tests/test_provenance.py` fails otherwise. Sample numbers are labelled on every page whether or not the user is signed in, and nothing invented (signals, alerts, notifications) is ever shown as if it were real. See `docs/data-provenance.md`.

**Cross-references:**
- Depends on: 0.1, 10
- Implementation: `app/schemas/base.py`
- Tests: `tests/test_provenance.py`

### Rule 9. Release dates come from the source's real calendar

**Purpose:** Ground the due-date calculation in the source's published schedule, never in guesswork, and err late when a date is unknown.

**Force:** Mandatory.

**Text:** Release dates come from the source's real calendar, including holidays, shutdowns and incidents (`app/data/cot_calendar.py` for the CFTC). Where a date is not published, derive it from the source's stated rule and mark it derived; when in doubt, err late, never early. A derived date gives way to the real time as soon as it is known: the source's own update timestamp, or QuFin's first sight of the value (rule 38).

**Cross-references:**
- Depends on: 38
- Implementation: `app/data/cot_calendar.py`, `app/jobs/build_calendar.py`
- Tests: `tests/test_cot_calendar.py`

### Rule 10. Verify meaning at the source before scoring

**Purpose:** Prevent a wrong definition, sign, unit or adjustment from entering a score.

**Force:** Mandatory.

**Text:** For every scored indicator, confirm its definition, sign, units and adjustment from the producer's own notes (rule 4), and record the reason in `app/data/scorecard_catalog.py`. Activity growth (output, spending, sales, income) is scored in real terms only, deflated where the source publishes it nominal (nominal dollars read inflation as growth). Prices, inflation, rates and money are scored as published.

Activity growth series are stored and scored in real terms. Where an eligible source publishes only a nominal series, the source choice under rule 38 proceeds as written (the nominal series is stored, not rejected), and QuFin **deflates it at scoring time using the reference CPI concept for the same economy** (rule 18). The deflated series is derived, not stored (rule 16); the deflator's vintage is the one current at the observation's release (rule 6); and the choice of deflator is recorded in `docs/assumptions-register.md` (rule 12).

**Deflation of a nominal activity series.** The reference CPI is the country's `consumer_prices` concept (rule 18), chosen under rule 38. (a) **Frequency:** the nominal series is aggregated to the CPI's frequency before deflation (rule 30's period-end / period-average / period-sum rules apply); the CPI is never up-sampled. (b) **Adjustment:** an SA nominal series is deflated with an SA CPI where the CPI source publishes one; an NSA nominal series with an NSA CPI; a mixed pair carries rule 29's notice. (c) **Unusable or missing deflator:** if the reference CPI is missing (rule 37) or unusable under rule 3, the derived real series is unusable and drops out of every score (S2). (d) **Pending deflator:** if a nominal observation is released before the CPI for the same period, the derived real series is not scored until the CPI lands; an estimate of the CPI is admitted only under S5.

**Cross-references:**
- Depends on: 3, 4, 6, 12, 16, 18, 29, 30, 37, 38, S2, S5
- Implementation: `app/data/scorecard_catalog.py`
- Tests: `tests/test_scorecard.py`

### Rule 11. Flag partial coverage

**Purpose:** Make a series' partial market coverage visible, so no user mistakes a partial contract for the whole market.

**Force:** Mandatory.

**Text:** A contract or series (rule 4) that covers only part of its market (e.g. NYMEX Brent, while most Brent trades on ICE) carries a caveat that the API and page show.

**Cross-references:**
- Depends on: 4
- Implementation: `app/data/macro_catalog.py`
- Tests: —

### Rule 12. Assumptions are listed and checked, not trusted

**Purpose:** Make every judgement visible and verifiable, so no assumption silently enters a data path.

**Force:** Mandatory.

**Text:** Before adding or changing any data path, list every assumption (mapping, sign, unit, release timing, licence, coverage), verify each against the primary source (rule 4), and report any that could not be verified. Record every judgement in `docs/assumptions-register.md` with its status (verified, convention, design choice, unverified); a judgement with no row there is a defect.

**Cross-references:**
- Depends on: 4
- Implementation: `docs/assumptions-register.md`
- Tests: —

### Rule 15. Every hot query on a data table is indexed; nothing aggregates a data table on a page load

**Purpose:** Keep response times bounded as the catalog grows, and prevent page latency from degrading as countries and series are added.

**Force:** Mandatory.

**Text:** (Both terms: Part 0, §0.1.) Data grows with every country and series, so a full scan gets slower with each one added. Each hot query is listed in `tests/test_query_plans.py`, which fails if the planner scans a data table; a metadata table may be scanned; a new read is added there with the index that serves it, in a migration. Summaries a page needs (coverage, counts, latest period) are stored at ingest, not computed per request. Bulk loads end with `ANALYZE` so the planner picks the right index. Indexes belong to the table, so rows for series added later are indexed on insert.

**Cross-references:**
- Depends on: 0.1
- Implementation: `tests/test_query_plans.py`, `migrations/`
- Tests: `tests/test_query_plans.py`

### Rule 16. No duplicated indicators or data, at any cost

**Purpose:** Prevent the same indicator from being stored twice (in different sources, units or frequencies), so a comparison never silently double-counts or contradicts itself.

**Force:** Mandatory.

**Text:** A country has at most one series per concept (`app/data/indicator_concepts.py`), and a series that can be derived exactly from stored ones is not stored. **A series is `REDUNDANT` (and not stored) only when it is an algebraic identity of stored series at the same frequency (e.g. the 10y-2y spread from the two yields), or a pure calendar aggregation of a higher-frequency series from the same producer where the producer applies no additional weighting, business-day adjustment or seasonal factor. A source-published aggregate that differs from such a computation for business-day, weighting or calendar reasons is a distinct official measure and is stored.**

A country-indicator pair is served from one source at a time; rule 38 says which. When the source changes, the new source loads its full history (rule 33), and the previous source's history becomes a retired series (Part 0, §0.1): kept read-only for as-of reads before the change, never served as current and never spliced into the new series. `tests/test_indicator_concepts.py` fails otherwise. The release check (rule 2) also compares every stored series with every other, from any source: two that carry the same values, or the same values in other units, both fail as `review` (Part 0, §0.1) until one is removed. Two exemptions, and only these: a retired series is not compared with the later series of its own pair (they are expected to match), and staged series are not compared. A retired series is still compared with every other pair's series.

**Pre-filter and comparison.** The pre-filter (rule 15's cost concern) uses `DUPLICATE_FINGERPRINT_TOLERANCE` on consecutive-period ratios. The **full comparison** uses the same tolerance after unit normalisation and after the source's native rounding — **never bit-for-bit equality**. Two series are duplicates when they share at least `DUPLICATE_MIN_SHARED_PERIODS` periods holding at least `DUPLICATE_MIN_DISTINCT_VALUES` distinct values, and at least `DUPLICATE_MATCH_SHARE` of the shared periods carry equal values, or values in one fixed ratio (the same data in other units). Two series become candidates for full comparison when their consecutive-period ratios match within tolerance in at least `min(DUPLICATE_MIN_FINGERPRINTS, max(DUPLICATE_MIN_FINGERPRINTS_FLOOR, periods − 1))` periods (`periods` is the number of usable observations of the shorter of the two series), or when they carry equal values in at least `DUPLICATE_MIN_SHARED_PERIODS × DUPLICATE_MATCH_SHARE` shared periods (the same data on different period grids, such as a daily series and a monthly one that repeats its month-end value); a series with fewer than `DUPLICATE_MIN_FINGERPRINTS_FLOOR` usable observations is compared with all others as before, never pre-filtered. The pre-filter only chooses pairs and never reports a duplicate; its tests check that it finds every pair the full comparison finds. The check has `DUPLICATE_CHECK_TIMEOUT_SECONDS` to finish; if it cannot, it fails — it is never skipped.

**Cross-references:**
- Depends on: 0.1, 0.2, 2, 15, 33, 38
- Implementation: `app/data/indicator_concepts.py`, `app/domain/duplicates.py`
- Tests: `tests/test_indicator_concepts.py`, `tests/test_duplicates.py`

### Rule 18. Every series has one human-readable, global name, shared across countries

**Purpose:** Keep every page, chart and API response naming an indicator the same way, so a user can compare countries without translating local vocabulary.

**Force:** Mandatory.

**Text:** An indicator is known by its globally recognised name and acronym (CPI, PPI, GDP, NFP, PMI, …), never by a country's local name: the euro area's HICP and the UK's CPIH are both shown as "CPI". One name does not make two measures the same: where national definitions differ (HICP, CPIH and a national CPI differ in coverage, for example owner-occupiers' housing), the series records its `variant`, the tooltip shows it, and a comparison across variants carries a notice, as rule 29 does for adjustment (rules 10 and 23). Each series maps to a concept with a name and a one-sentence plain explanation; indices use their standard name with the acronym first ("CPI – Consumer Price Index"); the same concept key matches the indicator in every country (US and UK unemployment are both `unemployment_rate`, "Unemployment Rate"), and a country's series joins the existing concept rather than a new name. That name is used everywhere QuFin names things: database, API (`name`, `concept`, `acronym`), charts, comparisons, scorecards, backtests, alerts and docs. The API returns the name and the official title; pages show the name, with the official title, local name, source code (rule 4) and publisher in a tooltip. Acronyms and their full names are listed in `ACRONYMS`, local aliases in `LOCAL_ALIASES` (`app/data/indicator_concepts.py`); add the acronym there before using it. A series without a name fails the tests. Never choose a name from memory: read what at least two independent public references call the indicator (currently FRED, Trading Economics and the Forex Factory calendar) and record the survey in `docs/indicator-names.md`. Where they disagree, the name most of them use wins; with no majority, the producer's own English name wins. Any disagreement is recorded in the survey. This is a one-off look-up by a person, not automated collection, so rule 28's connector requirements do not apply to it; naming a reference is provenance, not attribution (rule 25). Every series also has a business-cycle tag (`app/data/cycle_classification.py`, with a reason); the catalog refuses a series without one.

**Cross-references:**
- Depends on: 4, 10, 23, 25, 28, 29
- Implementation: `app/data/indicator_concepts.py`
- Tests: `tests/test_indicator_concepts.py`

---

## Part 2. Source selection and frequency

Source selection (rules 29–38) governs **how a source is chosen**; all other rules apply to the source it picks. The rules in this Part extend and never loosen the rules in Parts 0, 1, 3, 4 and 5.

### Rule 29. Seasonal adjustment is declared and preferred

**Purpose:** Make every series' adjustment state visible, and prefer SA where the data allows it — without forcing SA where the source publishes none.

**Force:** Mandatory.

**Text:** Every series carries its adjustment as `SA`, `NSA`, or not applicable (`OTHER`, with the source's text and the reason: an annual series, a market price, or an adjustment other than seasonal). Rule 38 picks the source; this rule picks the variant within it: `SA` where the chosen source publishes it, otherwise `NSA`. A comparison across countries or indicators prefers `SA` series, and never mixes `SA` with `NSA` silently: a mix is shown with an explicit notice. Where the source chosen under rule 38 publishes only NSA, the series is NSA; a slower SA source is not substituted unless the owner records a source decision for it under rule 38 (Changing source). A flash admitted under S5 is treated as the first release (rule 38); the final figure replaces it under S5 and rule 6.

**Cross-references:**
- Depends on: 0.1, 6, 38, S5
- Implementation: `app/domain/harmonize.py`, `app/data/macro_catalog.py`
- Tests: `tests/test_harmonize.py`

### Rule 30. One frequency when countries are compared

**Purpose:** Make cross-country comparisons valid by forcing every country to the same frequency before anything is drawn or computed.

**Force:** Conditional (only when two or more countries on one indicator are compared).

**Text:** Two or more countries on one indicator are evaluated at the same frequency (rule 23): the lowest common one among the selected series. Daily and weekly series are aggregated down before anything is drawn or any change is computed (rule 22), and a series is never up-sampled. The aggregation depends on what the series is: period end for a stock or level, period average for a rate or index, period sum for a flow.

**Cross-references:**
- Depends on: 22, 23
- Implementation: `app/domain/harmonize.py`
- Tests: `tests/test_harmonize.py`

### Rule 31. Charting limits

**Purpose:** Keep charts readable and API responses bounded, by capping what a single chart may plot.

**Force:** Mandatory.

**Text:** Mode 1 plots one indicator for at most 10 countries; mode 2 plots several indicators for one country, as actual values on separate axes (rule 23), or in each series' **declared change view** where that view exists (percent change, change in points, or change in own units — rule 22). A `published_as_change` series is shown only as published. The cap, the frequency alignment (rule 30) and both computations are enforced in the API; the web app renders the selectors and the result.

**Cross-references:**
- Depends on: 22, 23, 30
- Implementation: `app/routes/studio.py`
- Tests: `tests/test_studio.py`

### Rule 32. The frequency filter shows only what is possible

**Purpose:** Prevent a user from selecting a frequency no selected series supports, and explain why it is unavailable.

**Force:** Mandatory.

**Text:** Both the user and admin dashboards offer a frequency filter (rule 30: daily, weekly, monthly, quarterly, semi-annual, annual) and a metric mode. The filter allows only frequencies shared by every selected series, and states in words why a frequency is unavailable (rule 31).

**Cross-references:**
- Depends on: 30, 31
- Implementation: `app/domain/harmonize.py`, `apps/web/src/features/macro/components/studio-view.tsx`
- Tests: `tests/test_studio.py`, `apps/web/src/features/macro/lib/studio.test.ts`

### Rule 33. Deep history: every series from 1990

**Purpose:** Give every series the same comparison window, so indicators across countries line up over the same dates — while accepting that a source whose history is genuinely shallower is not padded from a second source.

**Force:** Mandatory.

**Text:** Every series, new or existing, loads the deepest history its source holds, targeting `1990-01-01` (`DEFAULT_OBSERVATION_START`), so all series share one start and indicators compare over the same dates (owner instruction, 13 Nov 2026). A source whose history begins after `1990-01-01` is loaded from its first available observation; a source whose first observation is after `2000-01-01` is accepted but recorded in the coverage report as shallow; a source whose history begins before `1990-01-01` is truncated to `1990-01-01`. The default start is `DEFAULT_OBSERVATION_START` in the catalog, so a routine run does not trim it. This holds for a new source after a source change too (rule 16 says how its overlap with the retired series is handled). A series whose source begins later keeps its own first date, stated in the coverage report; it is never spliced with older values from a second source (rule 16).

**Cross-references:**
- Depends on: 0.1, 0.2, 16
- Implementation: `app/data/macro_catalog.py`
- Tests: —

### Rule 34. Universal country and indicator cross-matrix

**Purpose:** Ensure every newly added indicator is probed across every country, and every valid series is available once its eligibility is verified — without waiting for the full source-decision cycle once the eligibility PR is merged.

**Force:** Mandatory.

**Text:** QuFin's active country universe is the list in `COUNTRIES` (`app/data/taxonomy.py`; 87 economies and blocs on 18 Nov 2026), and its indicator universe is `Master_Taxonomy_169`. Whenever an indicator is added, the ingestion engine probes every country across the candidate sources of rule 37 and places every responding candidate into staging (Part 0, §0.1). **No candidate is served — even provisionally — until its eligibility prerequisites are verified and committed by a reviewed pull request (rule 26):** licence (rule 7), permitted machine access (rule 28), definition, unit, adjustment and variant (rules 10, 12, 18, 29), live release schedule (rules 1 to 3, 37), global name (rule 18), and business-cycle tag (rule 18). Once those are merged, rule 38's provisional and measured decisions proceed as written, with the deepest history each source holds from `1990-01-01` (rule 33). "Valid" is as rules 1 to 3 define it: a series that is not published live stays out, and the sweep keeps to every supplier's limits (rule 28).

**The cross-matrix sweep runs as an asynchronous background discovery job, not inside the blocking scheduled ingestion window.** Its progress is recorded per country, and a sweep that exceeds `DISCOVERY_SWEEP_TIME_BUDGET_SECONDS` (Part 0, §0.2) marks remaining countries as `discovery-pending` (never failed) for the next run.

**Cross-references:**
- Depends on: 0.1, 0.2, 1, 2, 3, 7, 10, 12, 18, 26, 28, 29, 33, 37, 38
- Implementation: `app/data/taxonomy.py`, `app/jobs/coverage_matrix.py`, `app/data/probes.py`, `app/jobs/discover.py`
- Tests: `tests/test_taxonomy.py`, `tests/test_coverage_matrix.py`, `tests/test_discover.py`

### Rule 35. Release-calendar precision and a resilient retry policy

**Purpose:** Maximize data freshness without ever turning retries into a way round a supplier's limit.

**Force:** Mandatory.

**Text:** Every ingested series tracks its official `next_release_at` timestamp, and the scheduler triggers ingestion at the release window, so models train on the freshest data. When an upstream portal answers HTTP 429, 502, 503 or 504, or times out, there are two layers of retry:
- *Within a request:* up to 3 retries after 2, 4 and 8 seconds (exponential, `2^n`), or after the supplier's `Retry-After` where it gives one, up to 120 seconds (`app/connectors/base.py`).
- *Across attempts (a capped ladder):* a feed that still fails for a transient reason (a timeout, a network error, a 5xx) is tried again after the other sources have had their turn, about 15 seconds, 60 seconds, 5 minutes, 15 minutes and 1 hour later, each wait varied at random by up to 20% so retries do not arrive in step; after the last step the feed is marked degraded. The ladder may use at most 90% of `INGEST_RUN_TIME_BUDGET_SECONDS` (Part 0, §0.2), so that the release check (rule 2), which runs last, still fits.

Rule 28 governs where it differs: a `Retry-After` longer than a step is honoured, and a 403 or a 429 that outlasts the retries stops requests to that supplier for the run, so neither layer can become a way round a limit.

**Cross-references:**
- Depends on: 0.2, 2, 28
- Implementation: `app/connectors/base.py`, `app/jobs/refresh.py`
- Tests: `tests/test_connector_framework.py`, `tests/test_admin_api.py`

### Rule 36. A self-running database health and integrity engine ("QuFin Doctor")

**Purpose:** Catch structural corruption (orphaned rows, null corruption, tag drift, frozen upstream) before it reaches a score, and repair it where it is safe to do so.

**Force:** Mandatory.

**Text:** QuFin keeps a fast, deterministic command line check with automatic repair, `uv run python -m app.cli doctor --fix`, that runs after every ingestion job and in continuous integration. It verifies and, where it can do so safely, repairs: (a) no duplicate country-indicator mapping (rule 16); staged series are exempt as in rule 16; (b) no orphaned vintage rows and no null or NaN corruption; (c) strictly increasing dates; (d) the `SA` and `NSA` tags are accurate; (e) release-schedule freshness (rule 2); and (f) upstream series that have frozen are quarantined or flagged.

**A repair to a database row is restricted to:** (i) deleting an orphaned vintage row whose parent series no longer exists (after backup); (ii) deleting a corrupted row whose vintage dates are reversed (start after end), whose value is null, NaN or not finite, **so the next ingest re-fetches a clean value from the source — never imputing or rewriting a numeric value**; (iii) reporting a series as `review` (Part 0, §0.1) when its upstream source has frozen: the status is computed by the release check (rule 2), so the doctor stores nothing for it; (iv) re-deriving a series' canonical code from its stored frequency and adjustment (a label computed from stored fields, never a data value). **No other mutation is permitted.** Series the catalog no longer lists are reported, never removed by the doctor; removing them is the separate, explicit command `prune-stale --yes`, which backs up first. A repair to **catalog metadata** (SA/NSA tag, change kind, source decision, concept, variant) is never applied by `doctor --fix`; it fails loudly and requires a reviewed PR that updates the catalog and `docs/assumptions-register.md` (rule 12), under Rule 26's process and Rule 29's variant rule. A repair never deletes data without a backup and a report line saying what was done.

**Cross-references:**
- Depends on: 0.1, 2, 12, 16, 26, 29
- Implementation: `app/jobs/doctor.py`
- Tests: `tests/test_doctor.py`

### Rule 37. Candidate sources, and no silent gaps

**Purpose:** State the universe of candidate sources for every pair, and record every gap that cannot be filled — so no pair is silently missing.

**Force:** Mandatory.

**Text:** For every `(country, indicator)` pair in the taxonomy the candidates are all of these, with no ranking by tier (rule 38 alone chooses, and its tie-break is the only place a native source, Part 0, §0.1, is preferred):
- FRED/ALFRED;
- the multilateral aggregators: BIS, IMF, OECD, Eurostat, ECB and the World Bank;
- the country's official statistics office, central bank, agency or government open-data portal, each registered in `app/data/country_sources.py` with the date its terms and limits were read (rules 7 and 28), and, for the remaining economies, the UNECE and WTO statistical portals.

For a pair covered by rule 38's *Bloc aggregator first*, Eurostat is the only candidate while it is eligible and publishing; when it is ineligible, does not publish the indicator or is in an outage, every candidate of this rule is a candidate again.

A frozen mirror (for example FRED's `*PROINDMISMEI` and `*CPICORMINMEI` series) is not a candidate: it fails the live-schedule rules 1 to 3. A pair may stay unpopulated only if no candidate has an active, current feed; each such pair is listed with the candidates checked and the date, so no gap is silent.

**Cross-references:**
- Depends on: 0.1, 1, 2, 3, 7, 28, 38
- Implementation: `app/data/country_sources.py`
- Tests: `tests/test_country_sources.py`

### Rule 38. Bloc aggregator first, then earliest and most frequent source

**Purpose:** Choose exactly one source for each country-indicator pair, on objective and testable measures, so the same input always yields the same choice.

**Force:** Mandatory.

**Text:** For every economy and every indicator, existing and to come, the source is chosen from the candidates of rule 37, whatever the source is: an aggregator, an agency or the original producer. No source is preferred for what it is, except in *Bloc aggregator first* and in the tie-break below.

*Eligibility first.* A candidate is eligible only if all of these hold; an ineligible source is never chosen, however early it is:
- its licence allows QuFin's use (rule 7);
- it offers permitted machine access, an official API or bulk download, within its limits (rule 28);
- its definition, unit, adjustment and variant are verified at the source (rules 10, 12, 18, 29);
- it has a live release schedule and is not a frozen mirror (rules 1 to 3, 37).

*Bloc aggregator first.* For a pair of an economy that Eurostat serves (the European Union, the euro area, the EFTA economies and the candidate economies it covers) and that Eurostat publishes, Eurostat serves the pair whenever it is eligible, however early any other candidate is, an original producer or a global aggregator included, so that the bloc is read on one definition (rule 23; Part 0, §0.3, principle 3). Earliest and frequency are not measured for such a pair and nothing is staged for it, except in an outage. The quarterly check of such a pair confirms that Eurostat is still eligible and publishing. Where Eurostat does not publish the indicator for the economy, or is ineligible, the pair is chosen by the paragraphs below as before. This paragraph covers Eurostat's economies only: for every other economy, the United States included, the measures decide.

*An outage.* While Eurostat is overdue for such a pair, the pair has no usable series (rule 3) and drops out of every score (S2); no substitute is spliced in. If the outage lasts more than one release cycle past the grace period (Part 0, §0.1), the other candidates of rule 37 are staged and timed, and the owner may approve a source change by the procedure of *Changing source*. When Eurostat has published again for one release cycle, the pair returns to it by the same procedure.

Among eligible candidates, two measures decide:
(a) *Earliest.* The source that makes each new observation available first is better. It is measured on the same observation: the time from the end of the period to the moment QuFin can first read it, from the source's own update timestamp where it gives one and from QuFin's first sight of it otherwise, over at least one release cycle. A flash or provisional figure counts as a release when the source flags it as such, and follows S5 until the final figure lands.
(b) *Frequency.* The more often the source releases the indicator, the better: hourly, daily, weekly, monthly, quarterly, semi-annual, annual, in that order. The same measure at a lower frequency is derived by aggregation (rule 30), not stored (rule 16); a different measure is a different concept.

The best source meets both: it is the earliest and it releases at least as often as every other candidate. Where no source meets both, the earliest release wins. In practice this is usually the original producer, since aggregators republish after a lag (rule 4), but the rule does not assume it. Where eligible candidates publish different adjustments, a comparison shows rule 29's notice.

*Ties.* If two or more sources are equal on both measures, the most native source wins (Part 0, §0.1): the original producer, then the aggregator of the economy's own country or bloc, then a global aggregator. For the United States it is FRED rather than the IMF or the World Bank (an economy Eurostat serves does not reach this paragraph for a pair Eurostat publishes). Sources equally native are ranked by the latest period at the probe recorded for the decision (rule 12): the fresher observation wins; if still tied, the source code in ascending order wins. The outcome never depends on load order. Nativeness only breaks a tie: it never outweighs eligibility, earliest or frequency.

*New pairs.* A pair covered by *Bloc aggregator first* is served from Eurostat from the start and nothing is staged for it. For any other pair, "earliest" needs one release cycle to measure, so a new pair is served at first from the eligible candidate with the most recent period at the probe (frequency, then nativeness, breaks a tie): a provisional source decision (Part 0, §0.1), served and scored. The other eligible candidates are staged (Part 0, §0.1) and timed for one release cycle. If the measured winner is the provisional source, the decision is confirmed; otherwise the winner replaces it as a source change, below.

*Changing source.* Each decision is recorded in `docs/assumptions-register.md` with the candidates, the latest period, update timestamp and frequency of each, and the date checked. It is checked again at least once a quarter, and whenever the chosen source falls overdue or another one overtakes it. **When the chosen source falls overdue, the pair is not served from a substitute until the new source decision is recorded by a reviewed pull request (rules 12 and 26) that updates `docs/assumptions-register.md` and the catalog source history; until that PR merges, the pair has no usable series under rule 3.** A change takes effect from a stated date and is a new source decision: from that date the new source serves the pair with its full history (rules 33 and 16); reads as of an earlier date use the retired series, so past scores and backtests do not change (rules 6 and 20). **If the new source supplies no vintages for periods before the effective date, those pre-switch periods are stamped with their derived release dates under rule 9, capped at the date first loaded by QuFin, and labelled un-vintage-stamped under rule 6; a backtest after the effective date never treats pre-load history as known before its release window.** **When the measured winner replaces a provisional decision, the staged observations, first-sight timestamps and vintage history promote into the active series; they are not discarded and re-fetched.**

The chosen source is read as published (rule 6).

**Cross-references:**
- Depends on: 0.1, 0.3, 1, 2, 3, 4, 6, 7, 9, 10, 12, 16, 18, 20, 23, 26, 28, 29, 30, 33, 37, S2, S5
- Implementation: `app/domain/source_selection.py`, `app/stores/source_decisions.py`, `app/data/source_baseline.py`, `app/data/candidates.py`, `app/jobs/ingest_staged.py`, `app/stores/candidates.py`, `app/domain/measurement.py`, `app/jobs/measure_candidates.py`, `app/jobs/decide_sources.py`, `app/jobs/promote.py`
- Tests: `tests/test_source_selection.py`, `tests/test_source_decisions.py`, `tests/test_staged.py`, `tests/test_measurement.py`, `tests/test_decide_sources.py`

---

## Part 3. Change measures and comparison

### Rule 20. QuFin controls whether the scorecard mechanism is shown or hidden

**Purpose:** Protect the proprietary recipe while guaranteeing the correction mechanism, the data provenance and the freshness of every score are public.

**Force:** Mandatory.

**Text:** The correction mechanism (S1–S9) is public: it is how QuFin keeps scores honest, and it stays in this rule book. The recipe is proprietary: which indicators enter each pillar, their directions, their weights and weight cards (rule 21), the calibration, and the modelling assumptions. The recipe is always documented in full, internally, in plain words (`private/scorecard-methodology.md`, kept out of version control while the repository is public), so QuFin can explain and defend every score. Whether users see it is QuFin's decision, made with one switch (`QUFIN_SCORECARD_MECHANISM`: `show` or `hide`, default `hide`) that can be changed at any time, and the recipe may be disclosed to a person or organisation on request, **by the QuFin owner's written decision, recorded in a private disclosure log (`private/disclosure-log.md`) with the recipient, date, scope, and any confidentiality terms. The disclosure log is separate from the methodology's version change log, because disclosure is an access-control event, not a version change.**

The methodology and its change log are versioned in a private repository; each version's commit hash, date, owner approval and S7 result are recorded in the public `docs/scorecard-versions.md`, so every change can be audited without disclosing the recipe. When hidden, the API and dashboard leave out the recipe: weights, sub-scores and method text. **Never hidden, whichever way the switch is set:** that a score comes from a model and is not advice, where the data comes from (rule 4) and whether it is live or sample (rule 8), how fresh it is, the confidence in each score, and the releases still to come (S6). Every change to the recipe or to a weight is recorded in the methodology's change log with the reason, takes effect only after the bias gate (S7), a point-in-time backtest and the QuFin owner's approval, and never silently alters a past score: every score records the scorecard version and the catalog version (Part 0, §0.1, provisional source decisions included (rule 38)) it was computed with, and a score computed under an earlier version stays as it was shown. A modelling assumption (for example that hot inflation supports a currency) is documented as an assumption, not a fact.

**Cross-references:**
- Depends on: 0.1, 4, 8, 21, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9
- Implementation: `app/domain/scorecard.py`, `private/scorecard-methodology.md`, `private/disclosure-log.md`, `docs/scorecard-versions.md`
- Tests: `tests/test_scorecard.py`

### Rule 21. Indicator weights are earned, never assumed equal

**Purpose:** Ensure no indicator's influence on a pillar is assumed rather than earned, and each weight has a recorded justification.

**Force:** Mandatory.

**Text:** An indicator's weight in a pillar reflects how much it matters: its market impact, its predictive power, how reliable it is (revisions, noise) and how timely it is. Equal weights between indicators are a defect unless their weight cards show those inputs are equal, and weights nobody can explain are always a defect. (The equal split of each indicator's own score between level and momentum in S1 is how one indicator is scored, not a weight between indicators.) Each weight has a recorded basis (its "weight card"), kept internally and shown to users only when the mechanism is shown (rule 20); weights come from the mechanism in the methodology, are estimated only from data available at the time (no look-ahead), are capped so that no single indicator dominates a pillar, and are recalibrated on a fixed schedule with the before and after recorded. The cap and the schedule are stated as numbers in the methodology; a weight with no stated cap or schedule counts as interim. Until the mechanism is approved and calibrated, any interim weight is labelled interim wherever it is shown.

**Cross-references:**
- Depends on: 20, S1
- Implementation: `private/scorecard-methodology.md`
- Tests: `tests/test_scorecard.py`

### Rule 22. Change is measured in the right units, only where admissible, and never changed twice

**Purpose:** Prevent a rate from being treated as a level (or a count as a percentage), and prevent a change from being computed twice on a series that is already a change.

**Force:** Mandatory.

**Text:** Each catalog series declares how it changes (`change` kind), from its definition and units, not by habit:
- *Percent change* (PoC): strictly positive quantities, counts, amounts and price or volume indexes: employment, claims and benefit claims, orders, sales, production, prices, money and balance-sheet totals, debt amounts, exchange rates, commodity prices.
- *Change in points* (percentage points, index points, or basis points): rates, yields, spreads, ratios, shares (for example % of GDP), and diffusion or sentiment indexes, which can be zero, negative or already bounded.
- *Change in own units* (an amount, not a percentage): series that can cross zero, such as the trade balance, current account and budget balance.
- *No change taken*: a series the source already publishes as a change or growth rate is marked `published_as_change` and shown as published, never changed again. Read the source's notes, not just the units: WEI's units say "Index" but it is a GDP growth rate. The release check (rule 2) fails a percent change or y/y on such a series.

Changes are taken within one vintage (rule 6), never across vintages. A percent change whose old or new value is zero or negative is not computed: it is returned empty, never as zero, and a series where that happens is re-declared in points or own units by a catalog change in a pull request (rule 26); tests cover both cases. The change kind is part of the catalog version (Part 0, §0.1), so a score computed under the earlier declaration stays recorded with it (rule 20). Every chart and table offers the **actual value** and the **change** (percent or points, as declared) of any series over the chosen display frequency: a week, month, quarter, half year or year earlier. **For a series whose declared change kind is percent change, change in points, or change in own units, the change view is always available; for a series marked `published_as_change`, only the actual (as-published) view is available; for a series with no declared change kind, the actual only.** Claims and other benefit-claim series are scored and charted on their percent change, with the actual counts shown beside it. A new series is not added until its change kind is declared and tested.

**Cross-references:**
- Depends on: 0.1, 2, 6, 20, 26
- Implementation: `app/domain/changes.py`
- Tests: `tests/test_changes.py`

### Rule 23. Only compare what has a common basis

**Purpose:** Prevent invalid comparisons (a count beside a rate, USD beside GBP), so every chart the user sees is meaningful.

**Force:** Mandatory.

**Text:** Two series are compared, overlaid, ranked or combined only when they share a unit and currency, or have first been put on a common basis: (a) percent or point changes (rule 22); (b) standardised scores against each series' own history (S1); (c) ratios to a common denominator (for example % of GDP); (d) indexes rebased to 100 at a common date; or (e) conversion to one currency at a stated exchange rate and date, with the rate's source shown (purchasing-power parity for levels where that is the point). The US GDP in dollars is never put beside the UK GDP in pounds, and a count is never put beside a rate on one scale. Each series records its unit and currency (rule 18); the dashboard states the basis of every comparison and refuses an overlay that has none. Scorecards compare countries only through standardised scores, never through raw values. Frequency alignment is rule 30.

**Cross-references:**
- Depends on: 18, 22, 30, S1
- Implementation: `app/domain/comparison.py`, `app/routes/taxonomy.py`
- Tests: `tests/test_comparison.py`

---

## Part 4. Scorecard correction mechanism

A delayed or missing indicator must make a score **less certain, never more bullish or bearish**. Score and confidence are separate outputs (`app/domain/scorecard.py`).

### S1. Score each indicator point in time

**Purpose:** Score each indicator against its own published history, catching turns (via momentum) before the level moves.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Score each indicator point in time against its own history as published then (rule 6): a z-score over the lookback window (`ZSCORE_WINDOW_YEARS_STANDARD` for monthly or higher, quarterly and semi-annual series; `ZSCORE_WINDOW_YEARS_ANNUAL` for annual series — both Part 0, §0.2), clipped to -3..+3, flipped where higher means weaker, on two parts: where it stands and its prior-period momentum, averaged equally (`MOMENTUM_WEIGHT` = 0.5; this is how one indicator is scored, not an indicator weight under rule 21). A daily or weekly series is averaged into the current month as each value lands, so its momentum part catches turns before the monthly level does.

**Minimum sample by frequency.** A z-score requires at least the following usable observations in the lookback window, by frequency: monthly or higher, `ZSCORE_MIN_OBSERVATIONS_MONTHLY`; quarterly, `ZSCORE_MIN_OBSERVATIONS_QUARTERLY`; semi-annual, `ZSCORE_MIN_OBSERVATIONS_SEMIANNUAL`; annual, `ZSCORE_MIN_OBSERVATIONS_ANNUAL`, all in Part 0, §0.2. The floor applies to both the level and the momentum z-score distributions. A series below its floor is unscorable (weight 0 under S2).

**Momentum.** Momentum is the change from the prior observation at the series' native frequency (three months for monthly or higher, one quarter for quarterly, one half year for semi-annual, one year for annual), taken in the series' declared change kind (rule 22): the annualised percent change for a series changed in percent, the difference for one changed in points or in its own units. It is z-scored separately against the same lookback window as the level and averaged with the level z-score under `MOMENTUM_WEIGHT`.

**Cross-references:**
- Depends on: 0.2, 6, 21, 22, S2
- Implementation: `app/domain/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S2. Rescaled weighted average per pillar

**Purpose:** Compute a pillar score that prices lateness into every indicator's contribution, and never treats a missing value as neutral.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** `score = Σ wᵢ·sᵢ / Σ wᵢ` over usable indicators (rule 3), with `wᵢ` = base importance × timeliness weight. The timeliness weight (`timeliness.weight`, Part 0, §0.1) halves for every 60 days between the end of a period and the day QuFin can read it; fresh data (daily rates, weekly claims) keeps full weight. Overdue, discontinued, missing or unscorable indicators drop out (weight 0); the only exception is a labelled estimate admitted under S5. Never count missing data as zero (a plain sum pulls scores toward neutral: strong economies underrated, weak ones overrated), and never carry an old value forward at full weight.

**Cross-references:**
- Depends on: 0.1, 3, S5
- Implementation: `app/domain/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S3. Confidence is reported separately

**Purpose:** Keep confidence independent of the score, so a missed release can reduce certainty without changing direction.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Confidence is `Σ wᵢ / Σ base importance` (using the S2 weights). It never changes the score.

**Cross-references:**
- Depends on: S2
- Implementation: `app/domain/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S4. Caution goes into position size, not into the view

**Purpose:** Ensure a lower-confidence score does not become a directional signal; instead, it shrinks the trade's size.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Size trade ideas by confidence (S3): the share of a normal position a trade idea may take is the confidence of the score it rests on, from 0 (none) to 1 (full), and for a currency pair the confidence of the weaker side (S8). The score itself is never changed. The API carries it as `sizeFactor` beside `overallConfidence`.

**Cross-references:**
- Depends on: S3, S8
- Implementation: `app/domain/scorecard.py`, `app/jobs/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S5. Fix delays at the source where the licence allows it

**Purpose:** Allow a labelled estimate to stand in for a missing release, without ever carrying an old value forward as if it were current.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Fix delays at the source where the licence allows it, rather than living with them. An estimate for a missing release, and a flash or provisional figure a source itself flags, may enter a score only if labelled as an estimate, at a reduced weight stated in the methodology (rule 20), and replaced when the final figure lands (rule 29). An estimate is a new value with its own method and date, so it may stand in for an overdue series (Part 0, §0.1); the series' last real value is never carried forward in its place (rule 3).

**A non-source estimate** (a nowcast produced by a QuFin model or a third party, not a flash the source publishes) may stand in only if all of the following hold: its method is documented and registered as verified or design choice in `docs/assumptions-register.md` (rule 12); the inputs it uses are themselves eligible (rule 38) and current under rules 1 and 3; the owner has approved it for live scores; and it is labelled `estimate:<method-id>` in the API response so rule 8's provenance is preserved. Without all four, an overdue series is dropped (weight 0 under S2), not estimated.

**Cross-references:**
- Depends on: 0.1, 1, 3, 8, 12, 20, 29, 38, S2
- Implementation: `app/domain/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S6. Show what is pending

**Purpose:** Tell users which releases are still to come, so they know a score may move and why.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Every live scorecard lists the releases still to come (rule 9), with the source (rule 4) and aggregator dates, so users know the score may move and why.

**Cross-references:**
- Depends on: 4, 9
- Implementation: `app/routes/market.py`
- Tests: `tests/test_market_api.py`

### S7. Prove there is no bias

**Purpose:** Guarantee the scorecard is not systematically biased by late or missing data, by comparing what users would have seen against complete information.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** `uv run python -m app.cli scorecard-bias` compares the scorecard users would have seen each month with complete information. The mean difference must stay within `MAX_MEAN_BIAS` (Part 0, §0.2), on the -3 to +3 score scale (Part 0, §0.1), for every pillar and overall; if it fails, the scorecard must not be used until the cause is fixed. `tests/test_scorecard.py` enforces the rules above (S1, S2, S3); do not loosen it to make a change pass.

**Cross-references:**
- Depends on: 0.1, 0.2, S1, S2, S3
- Implementation: `app/jobs/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S8. A currency pair is only as certain as its less certain side

**Purpose:** Ensure a stale side of a pair cannot make the pair look decisive.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Use `pair_confidence(base, quote)` (the minimum of the two sides' confidence (S3)), so a stale side cannot make a pair look decisive.

**Cross-references:**
- Depends on: S3
- Implementation: `app/domain/scorecard.py`
- Tests: `tests/test_scorecard.py`

### S9. Never mix live and sample scorecards

**Purpose:** Prevent a user from comparing a live score with a sample one.

**Force:** Mandatory (within the scorecard mechanism).

**Text:** Never mix live and sample scorecards in one ranking; sample data is always labelled (rule 8).

**Cross-references:**
- Depends on: 8
- Implementation: `app/routes/market.py`
- Tests: `tests/test_market_api.py`

---

## Part 5. Ownership, documentation and conduct

### Rule 24. The rule book and QuFin's code belong to QuFin

**Purpose:** Make the rule book the single, self-contained contract, with no hidden tool, vendor or assistant dependency, and acknowledge the one governed exception (the scorecard recipe) explicitly.

**Force:** Mandatory.

**Text:** The rule book is kept in this repository, in plain text, and is the only place rules are defined. The one governed exception is the scorecard recipe (rule 20): its parameters (indicators per pillar, directions, weights, calibration) live in the private methodology, under the rules that rule 20 and S1–S9 set here. Instruction files for any development tool may exist only as a pointer to it and must add no rule of their own. No rule may require a particular development tool, assistant or hosting vendor. The commands, settings, files and libraries the rules name are the current implementation (Part 0, §0.2): replaceable, with the rule book updated in the same pull request (rule 26). The data sources the rules name are provenance (rule 4), chosen and replaced under rules 37 and 38, not dependencies of the rules.

**Cross-references:**
- Depends on: 0.1, 0.2, 4, 20, 26, 37, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9
- Implementation: —
- Tests: —

### Rule 25. No tool or assistant attribution anywhere

**Purpose:** Keep the repository free of assistant credits while preserving data-source attribution where it is provenance.

**Force:** Mandatory.

**Text:** Code, comments, commit messages, pull request descriptions, documents and releases carry no mention of, credit to or footer from any AI assistant or code-generation tool. A build, test, lint or package tool (for example `uv` or `pytest`) may be named where a rule or a command needs it. Names of data sources and licensed vendors are recorded where the data comes from (rule 4); that is provenance, not attribution. **This rule applies to the rule book, its change log and its appendices; no rule-book entry may name an AI assistant or code-generation tool.**

**Cross-references:**
- Depends on: 4
- Implementation: —
- Tests: `tests/test_no_attribution.py`, `tests/test_rulebook.py`

### Rule 26. Changing the rule book needs the owner's approval and a log entry

**Purpose:** Make every rule change auditable, and prevent a rule from being loosened to make a change pass.

**Force:** Mandatory.

**Text:** A rule changes only by a reviewed pull request that the QuFin owner merges. The change log below records the date, the rule and the reason. Rules are never loosened to make a change pass. S1–S9 are changed by the same procedure as any other rule (owner-approved pull request and change log entry), and the scorecard recipe they govern (rule 20) changes only with the additional approvals rule 20 requires (S7 bias gate, point-in-time backtest and owner approval). A change to a value in Part 0, §0.2 is a rule change recorded as `0.2 (value: <name>)`. A change to a §0.1 term is recorded as `0.1 (term: <name>)`; a change to a §0.3 principle is recorded as `0.3 (principle: <n>)`. Where another rule requires a reviewed pull request for a data-path change (rules 1, 22, 34 and 38: a catalog entry, a re-declared change kind, an eligibility verification or a source decision), the QuFin owner merges that pull request too, and it is recorded in `docs/assumptions-register.md` (rule 12); it is not a rule change and needs no change-log entry.

**Cross-references:**
- Depends on: 0.1, 0.2, 0.3, 1, 12, 20, 22, 34, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9
- Implementation: —
- Tests: —

### Rule 27. Every data connection and process is documented

**Purpose:** Prevent an undocumented connector from merging, and keep the pipeline's behaviour legible from the repository alone.

**Force:** Mandatory.

**Text:** `docs/data-connections.md` records, for every source (rule 4), what QuFin takes, the address and protocol, how it authenticates (by the name of the setting, never the secret), its rate limits, its release calendar, the command that loads it and where its licence is recorded (rule 7). `docs/data-pipeline.md` records how data is ingested and retrieved. A connector is not merged until its row is there (rule 28), and a change to either process updates the document in the same pull request.

**Cross-references:**
- Depends on: 4, 7, 28
- Implementation: `docs/data-connections.md`, `docs/data-pipeline.md`
- Tests: —

### Rule 28. Respect every data supplier's policy

**Purpose:** Make a ban an incident, not a risk: every connector is designed and operated so it does not cause one, and stops if one occurs.

**Force:** Mandatory.

**Text:** Every crawler, agent and connector is built and run so that it is never banned. A refusal or ban is an incident: the connector stops, the owner is told, and it resumes only once the cause is fixed. Before a connector is written, the supplier's (rule 4) terms of use, API documentation and published limits (requests per period, series or rows per request, concurrent connections, bulk-download rules, required identification or attribution) are read on the supplier's own site, and what was found is recorded with the date read in `docs/data-connections.md` (rule 27) for rate limits and `docs/licence-register.md` (rule 7) for licence. The connector is then built to those limits, not to what happens to work:
- It stays inside the stated limits with margin. Where the supplier states none, it makes the fewest and smallest requests that do the job: several series per request where the API allows, bulk files rather than many small calls, no more history than is needed, and pauses between requests.
- It uses the official API or bulk download only, never page scraping where an API exists, and identifies itself with a descriptive `User-Agent`.
- It honours `Retry-After`, backs off on 429 and 5xx, and when the supplier refuses (403 or 429 that outlasts the retries) it stops asking for that run instead of retrying into a ban.
- It runs no more often than the data changes: a monthly series is not fetched hourly.
- A need that the supplier's limits cannot meet goes to the owner, to change the plan or the source. It is never met by rotating addresses or keys, splitting traffic to hide it, or any other way round a limit.
- A connector is not merged until its row in `docs/data-connections.md` (rule 27) states the limits and how the code keeps within them, and tests show the identification and the stop on refusal.

**Cross-references:**
- Depends on: 4, 7, 27
- Implementation: `app/connectors/base.py`, `docs/data-connections.md`, `docs/licence-register.md`
- Tests: `tests/test_connector_framework.py`

---

## Appendix A. Historical numbering

Permanent record of every retired and renumbered rule.

| Old | Type | Now | What happened |
|---|---|---|---|
| 5 | Retired | S2 | Merged into S2 (late data weighs less). |
| 13 | Retired | 22 | Merged into 22 (change units). |
| 14, A, K | Retired | 38 (b) | Merged into Rule 38 frequency measure. |
| 17, H, M | Retired | 38, 16 | Merged into Rule 38 and Rule 16. |
| 19 | Retired | 18 | Merged into 18 (one global name). |
| C | Retired | 6 | Merged into 6 (vintages). |
| E | Retired | 22 | Merged into 22 (PoC). |
| B | Renumbered | 29 | Letter rule, same substance. |
| D | Renumbered | 30 | Letter rule, same substance. |
| F | Renumbered | 31 | Letter rule, same substance. |
| G | Renumbered | 32 | Letter rule, same substance. |
| I | Renumbered | 33 | Letter rule, same substance. |
| J | Renumbered | 34 | Letter rule, same substance. |
| L | Renumbered | 35 | Letter rule, same substance. |
| N | Renumbered | 36 | Letter rule, same substance. |
| O | Renumbered | 37 | Letter rule, same substance. |
| P | Renumbered | 38 | Letter rule, same substance. |

**Rule-number gaps:** 5, 13, 14, 17 and 19 are retired (see above). No rule will ever be assigned those numbers again.

Any old reference (`rule P`, `rule S5`, `rule 1-28`) resolves through this table, or through the S-rule's own number if it is still active.

---

## Appendix B. Cross-reference index

**Generated** by `scripts/build_rule_index.py` from the `Depends on:` lines of the rule bodies; do
not edit it by hand. `tests/test_rulebook.py` fails if it differs from the script's output, or if a
rule body cites a rule that is not in its `Depends on:` line. Rule bodies hold no `Referenced by:`
blocks; this appendix is their sole home.

| Rule | Depends on | Referenced by | Implementation | Tests |
|---|---|---|---|---|
| 1 | 2, 26 | 2, 26, 34, 37, 38, S5 | `app/jobs/check_data.py` | `tests/test_freshness.py`, `tests/test_admin_api.py` |
| 2 | 0.1, 1, 3 | 1, 16, 22, 34, 35, 36, 37, 38 | `app/jobs/check_data.py`, `app/jobs/refresh.py` | `tests/test_freshness.py`, `tests/test_admin_api.py` |
| 3 | 0.1 | 2, 10, 34, 37, 38, S2, S5 | `app/domain/freshness.py` | `tests/test_freshness.py` |
| 4 | 0.1, 9 | 6, 7, 10, 11, 12, 18, 20, 24, 25, 27, 28, 38, S6 | `app/data/macro_catalog.py` | `tests/test_provenance.py` |
| 6 | 4, 9, 38 | 10, 22, 29, 38, S1 | `app/stores/macro.py` | `tests/test_record_latest.py`, `tests/test_macro_api.py` |
| 7 | 4 | 27, 28, 34, 37, 38 | `docs/licence-register.md` | — |
| 8 | 0.1, 10 | 20, S5, S9 | `app/schemas/base.py` | `tests/test_provenance.py` |
| 9 | 38 | 4, 6, 38, S6 | `app/data/cot_calendar.py`, `app/jobs/build_calendar.py` | `tests/test_cot_calendar.py` |
| 10 | 3, 4, 6, 12, 16, 18, 29, 30, 37, 38, S2, S5 | 8, 18, 34, 38 | `app/data/scorecard_catalog.py` | `tests/test_scorecard.py` |
| 11 | 4 | — | `app/data/macro_catalog.py` | — |
| 12 | 4 | 10, 26, 34, 36, 38, S5 | `docs/assumptions-register.md` | — |
| 15 | 0.1 | 16 | `tests/test_query_plans.py`, `migrations/` | `tests/test_query_plans.py` |
| 16 | 0.1, 0.2, 2, 15, 33, 38 | 10, 33, 36, 38 | `app/data/indicator_concepts.py`, `app/domain/duplicates.py` | `tests/test_indicator_concepts.py`, `tests/test_duplicates.py` |
| 18 | 4, 10, 23, 25, 28, 29 | 10, 23, 34, 38 | `app/data/indicator_concepts.py` | `tests/test_indicator_concepts.py` |
| 20 | 0.1, 4, 8, 21, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9 | 21, 22, 24, 26, 38, S5 | `app/domain/scorecard.py`, `private/scorecard-methodology.md`, `private/disclosure-log.md`, `docs/scorecard-versions.md` | `tests/test_scorecard.py` |
| 21 | 20, S1 | 20, S1 | `private/scorecard-methodology.md` | `tests/test_scorecard.py` |
| 22 | 0.1, 2, 6, 20, 26 | 23, 26, 30, 31, S1 | `app/domain/changes.py` | `tests/test_changes.py` |
| 23 | 18, 22, 30, S1 | 18, 30, 31, 38 | `app/domain/comparison.py`, `app/routes/taxonomy.py` | `tests/test_comparison.py` |
| 24 | 0.1, 0.2, 4, 20, 26, 37, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9 | — | — | — |
| 25 | 4 | 18 | — | `tests/test_no_attribution.py`, `tests/test_rulebook.py` |
| 26 | 0.1, 0.2, 0.3, 1, 12, 20, 22, 34, 38, S1, S2, S3, S4, S5, S6, S7, S8, S9 | 1, 22, 24, 34, 36, 38 | — | — |
| 27 | 4, 7, 28 | 28 | `docs/data-connections.md`, `docs/data-pipeline.md` | — |
| 28 | 4, 7, 27 | 18, 27, 34, 35, 37, 38 | `app/connectors/base.py`, `docs/data-connections.md`, `docs/licence-register.md` | `tests/test_connector_framework.py` |
| 29 | 0.1, 6, 38, S5 | 10, 18, 34, 36, 38, S5 | `app/domain/harmonize.py`, `app/data/macro_catalog.py` | `tests/test_harmonize.py` |
| 30 | 22, 23 | 10, 23, 31, 32, 38 | `app/domain/harmonize.py` | `tests/test_harmonize.py` |
| 31 | 22, 23, 30 | 32 | `app/routes/studio.py` | `tests/test_studio.py` |
| 32 | 30, 31 | — | `app/domain/harmonize.py`, `apps/web/src/features/macro/components/studio-view.tsx` | `tests/test_studio.py`, `apps/web/src/features/macro/lib/studio.test.ts` |
| 33 | 0.1, 0.2, 16 | 16, 34, 38 | `app/data/macro_catalog.py` | — |
| 34 | 0.1, 0.2, 1, 2, 3, 7, 10, 12, 18, 26, 28, 29, 33, 37, 38 | 26 | `app/data/taxonomy.py`, `app/jobs/coverage_matrix.py`, `app/data/probes.py`, `app/jobs/discover.py` | `tests/test_taxonomy.py`, `tests/test_coverage_matrix.py`, `tests/test_discover.py` |
| 35 | 0.2, 2, 28 | — | `app/connectors/base.py`, `app/jobs/refresh.py` | `tests/test_connector_framework.py`, `tests/test_admin_api.py` |
| 36 | 0.1, 2, 12, 16, 26, 29 | — | `app/jobs/doctor.py` | `tests/test_doctor.py` |
| 37 | 0.1, 1, 2, 3, 7, 28, 38 | 10, 24, 34, 38 | `app/data/country_sources.py` | `tests/test_country_sources.py` |
| 38 | 0.1, 0.3, 1, 2, 3, 4, 6, 7, 9, 10, 12, 16, 18, 20, 23, 26, 28, 29, 30, 33, 37, S2, S5 | 6, 9, 10, 16, 20, 24, 26, 29, 34, 37, S5 | `app/domain/source_selection.py`, `app/stores/source_decisions.py`, `app/data/source_baseline.py`, `app/data/candidates.py`, `app/jobs/ingest_staged.py`, `app/stores/candidates.py`, `app/domain/measurement.py`, `app/jobs/measure_candidates.py`, `app/jobs/decide_sources.py`, `app/jobs/promote.py` | `tests/test_source_selection.py`, `tests/test_source_decisions.py`, `tests/test_staged.py`, `tests/test_measurement.py`, `tests/test_decide_sources.py` |
| S1 | 0.2, 6, 21, 22, S2 | 20, 21, 23, 24, 26, S7 | `app/domain/scorecard.py` | `tests/test_scorecard.py` |
| S2 | 0.1, 3, S5 | 10, 20, 24, 26, 38, S1, S3, S5, S7 | `app/domain/scorecard.py` | `tests/test_scorecard.py` |
| S3 | S2 | 20, 24, 26, S4, S7, S8 | `app/domain/scorecard.py` | `tests/test_scorecard.py` |
| S4 | S3, S8 | 20, 24, 26 | `app/domain/scorecard.py`, `app/jobs/scorecard.py` | `tests/test_scorecard.py` |
| S5 | 0.1, 1, 3, 8, 12, 20, 29, 38, S2 | 10, 20, 24, 26, 29, 38, S2 | `app/domain/scorecard.py` | `tests/test_scorecard.py` |
| S6 | 4, 9 | 20, 24, 26 | `app/routes/market.py` | `tests/test_market_api.py` |
| S7 | 0.1, 0.2, S1, S2, S3 | 20, 24, 26 | `app/jobs/scorecard.py` | `tests/test_scorecard.py` |
| S8 | S3 | 20, 24, 26, S4 | `app/domain/scorecard.py` | `tests/test_scorecard.py` |
| S9 | 8 | 20, 24, 26 | `app/routes/market.py` | `tests/test_market_api.py` |

---

## Appendix C. Change log

Fixed columns: **Date | Rules touched | Change | Reason | Approved by**. The Rules-touched cell uses a canonical format: numbered rules only (`1-4, 6, 10`), S-rules (`S1-S9` as a group when all touched, or `S2, S5` individually), Part 0 terms/values (`0.1 (term: <name>)`, `0.2 (value: <name>)`, `0.3 (principle: <n>)`), or appendices (`A (renumbering)`, `B (index)`, `C (standardisation)`, `D (migration)`).

| Date | Rules touched | Change | Reason | Approved by |
|---|---|---|---|---|
| 6 Nov 2026 | 1-19, S1-S9 | Moved into this rule book from the API folder; wording unchanged. | Consolidation. | Owner |
| 6 Nov 2026 | 20-26 | Added: show/hide control of the scorecard mechanism, earned weights, percent-change admissibility, common basis for comparison, ownership, no attribution, rule changes. | Initial scope. | Owner |
| 6 Nov 2026 | 12 | Judgements are recorded in `docs/assumptions-register.md`. | Traceability. | Owner |
| 6 Nov 2026 | 18, 19 | Names come from the data and calendar sites, not memory; one global name and acronym per indicator. | Cross-country consistency. | Owner |
| 6 Nov 2026 | 27 | Added: every data connection is documented in `docs/data-connections.md`. | Auditability. | Owner |
| 6 Nov 2026 | 27 | Widened: ingestion and retrieval are documented in `docs/data-pipeline.md`. | Auditability. | Owner |
| 12 Nov 2026 | 28 | Added: every connector follows its supplier's published limits and policies and must never be banned. | Legal / commercial risk. | Owner |
| 12 Nov 2026 | A, B, C, D, E, F, G, H | Added Part 5: earliest signal, seasonal adjustment, vintages, one frequency per comparison, `PoC`, chart limits, frequency filter, FRED first. | Initial Part 5 scope. | Owner |
| 13 Nov 2026 | H, I | H: UK fallback to the ONS where FRED lacks a current SA series with vintages. Added I: every series loads from 1990. | Coverage decisions. | Owner |
| 13 Nov 2026 | J-N | Added: 85-country and 169-indicator cross-matrix, highest frequency first, release-calendar precision with a retry ladder (rule 28 governs), FRED first with authentic fallbacks, and the QuFin Doctor health engine. | Operational scope. | Owner |
| 13 Nov 2026 | O | Added: three-tier source cascade (FRED, multilateral aggregators, official national portals) and no silent gaps. | Source breadth. | Owner |
| 13 Nov 2026 | J | The country universe is 87: the 85 of the QuFin Country List plus Chile and Colombia. | Coverage correction. | Owner |
| 18 Nov 2026 | P (17, H, M, O) | Added: the earliest and most frequent source wins for every economy; supersedes the FRED-first order. | Source-selection policy change. | Owner |
| 18 Nov 2026 | 1-28, S1-S9, A-P | Consolidated into a master rule book: duplicate rules merged (5, 13, 14, 17, 19, A, C, E, H, K, M retired into S2, 22, P, 16, 18, 6), conflicts resolved, retired numbers listed; no rule's substance dropped except the FRED-first order. | Single-authority book. | Owner |
| 18 Nov 2026 | 0, 2, 6, 16, 18, 20, 21, 22, 24, I, J, P | Second cross-verification: a new source loads from 1990 and only its own retired series is exempt from the duplicate check; recipe acknowledged as rule 24's one exception, versioned privately with hashes in `docs/scorecard-versions.md`; provisional decision, staging, retired series and catalog version defined; J serves the provisional choice and stages the rest; owner decides disclosure; equal weights allowed when weight cards show equal inputs; change-kind re-declaration versioned; naming tie-break; charts mark source changes; downstream jobs read usable series after a failed run; release-lag window stated. | Internal consistency. | Owner |
| 19 Nov 2026 | 0, O, P | Rule P tie-break: the most native source wins (the original producer, then the aggregator of the economy's own country or bloc, such as Eurostat for the European Union or FRED for the United States, then a global aggregator), which also keeps the sources of a bloc uniform; Part 0 defines native source. | Owner instruction. | Owner |
| 20 Nov 2026 | 0.1, 0.2, 0.3, 1-4, 6-12, 15, 16, 18, 20-38, S1-S9, A (renumbering), B (index), C (standardisation), D (migration) | v3.0 consolidation. Renumbered letter rules into numbers 29–38 (Appendix A); introduced Preamble, Purpose lines, Force tags, Cross-references blocks; added Part 0 §0.1 terms (scorecard recipe, staging lifecycle, FRED as global aggregator for non-US, non-bloc economies) and §0.2 normative values; added Appendix B (generated cross-reference index) and Appendix D (migration map); standardised change log (Appendix C); corrected Rule 38's bloc-uniformity claim (the stated tie-break does not deliver it) and made the equally-native tie deterministic; marked "most likely the original producer" as a note, not a rule; added NSA-only and flash consequences to Rule 29; fixed Rule 33's shallow-source wording and aligned Rule 34 with it; added Rule 26's S-rule change sentence; removed the "(non-negotiable)" labels from Part headings (Force tags replace them). | Multi-sequence numbering was historically necessary but produced ambiguity; a single sequence plus a scoped S-sub-series is clearer and cheaper to maintain; the window to do this cheaply is now, before external consumers exist. | Owner (Rule 26 review) |
| 20 Nov 2026 | 0.1, 0.2, 0.3, 1-4, 6-12, 15, 16, 18, 20-38, S1-S9, A (renumbering), B (index), C (standardisation), D (migration) | v3.1 amendment: resolved 17 findings from an independent audit. Rule 34 now probes and stages only; serving requires human-verified eligibility PR. Rule 22 and Rule 31 restrict the change view to admissible change kinds. Preamble declares Part 0 binding and defines path resolution; §0.1 "Due date" prefers calendar and defines fallback. §0.2 gains six values. Rule 16 defines pre-filter tolerances, minimum fingerprints, full comparison and the exact "REDUNDANT" test. Rule 20 separates disclosure log from methodology change log. Rules 2, 36, 38 add staging exemptions and clarify source-change lifecycle and as-of boundary. Rule 10 defines real-vs-nominal. Rule 34 runs as async sweep; Rule 35 uses INGEST_RUN_TIME_BUDGET_SECONDS. Rule 36 restricts --fix to database hygiene. Rule S5 requires estimate method registration and owner approval. Rule S1 defines minimum sample, frequency-specific momentum and input series. Preamble and Appendix B move Referenced by to generated output; rule bodies keep Depends on only. Appendix C 20 Nov row reformatted; Appendix D cleanup instruction fixed. | Independent rulebook audit surfaced production-blocking and governance-blocking issues; adopting the fixes before the v3.0 PR merges. | Owner (Rule 26 review) |
| 20 Nov 2026 | 0.1, 0.2, 0.3, 1-4, 6-12, 15, 16, 18, 20-38, S1-S9, A (renumbering), B (index), C (standardisation), D (migration) | v3.2 amendment: resolved eight findings from a second independent audit. (1) Restored the Depends on / body citation invariant across 15 rules. (2) Removed the assistant name from Appendix C per Rule 25; Rule 25 now explicitly covers the rule book itself. (3) Rule 10 gained a deflation paragraph defining frequency alignment, SA/NSA matching, unusable-deflator fallback and pending-deflator handling. (4) Rule 36's row-repair rules are now exhaustive. (5) Rule 16's full comparison now uses DUPLICATE_FINGERPRINT_TOLERANCE (never bit-for-bit) and DUPLICATE_MIN_FINGERPRINTS_FLOOR avoids O(N²) for shallow series. (6) Rule 38's pre-switch release dates now fall back to derived dates (rule 9) capped at first-load, with un-vintage-stamped label. (7) S1's ZSCORE_MIN_OBSERVATIONS split into frequency-specific floors; momentum defined as prior-period arithmetic difference at native frequency. (8) Rules 12 and 23 dependency chains closed. | Second independent audit found architecture, governance and scoring defects; adopting all eight before v3.1 is used. | Owner (Rule 26 review) |
| **20 Nov 2026** | **0.2, 10, Preamble, S1, A (renumbering), B (index), C (standardisation), D (migration)** | **v3.3 amendment: resolved three findings from a third independent audit. (F1) Rule S1's lookback window is now frequency-aware via §0.2 `ZSCORE_WINDOW_YEARS_STANDARD` (10) and `ZSCORE_WINDOW_YEARS_ANNUAL` (20); all three S1 paragraphs reference the same window; the observation floor explicitly applies to both level and momentum distributions. (F2) Preamble's citation grammar declares `S<N>` (N in 1–9) and the range `S1–S9` as valid shorthand that expands to the nine S-rules in `Depends on:`; Rule S1's `Depends on:` now includes S2 (S1 cites it in text). (F3) Rule 10 clause (c) now covers a country where the reference CPI is missing (rule 37) as well as unusable (rule 3); Rule 10's `Depends on:` includes 37. Also fixed during application: Rule 38's `Depends on:` now includes 26 (its Text cites "rules 12 and 26"); Rule 26's `Referenced by:` was correct and no longer mismatched. Appendix B is marked provisional and must be regenerated via `scripts/build_rule_index.py` before merge.** | **Third independent audit found three residual defects in v3.2; adopting them plus two hand-verification fixes.** | **Owner (Rule 26 review)** |
| 20 Nov 2026 | Preamble, 0.2 (value: INGEST_RUN_TIME_BUDGET_SECONDS), 0.2 (value: DUPLICATE_MIN_SHARED_PERIODS), 0.2 (value: DUPLICATE_MIN_DISTINCT_VALUES), 0.2 (value: DUPLICATE_MATCH_SHARE), 1-4, 6-12, 16, 18, 22-38, S1-S9, B (index) | v3.4 amendment, checked against the code and by a mechanical test of the citation invariant. (1) Seven `Depends on:` lines did not match their bodies (rules 10, 24, 33, 36, 37, 38, S2) and rule 29 and rule 26 gained citations; Appendix B is now generated by `scripts/build_rule_index.py` and tested by `tests/test_rulebook.py`. (2) 36 of the 62 implementation and test paths cited did not exist; each now names the file that does, and the Preamble's path resolution maps `migrations/…` to `services/api/migrations/…` and exempts `private/…`. (3) §0.2 now names the constants the code holds, in the files that hold them; `INGEST_RUN_TIME_BUDGET_SECONDS` is 14400, because the retry ladder of rule 35 takes 4875 seconds and could never fit in 1800; three values rule 16 needs are added. Values the code does not yet hold are listed in `docs/rulebook-paths-waivers.md`. (4) Rule 16 defines when two series are duplicates and keeps the second kind of candidate (equal values on different period grids), so the pre-filter finds every pair the full comparison finds. (5) Rule 26 says who approves a data-path change; rule 29's owner decision now has the procedure of rule 38; rule 36 reports instead of setting a status; rule 38's tie-break uses the probe recorded for the decision; rule 10 names the `consumer_prices` concept; rule 25 says what a tool is; S1's momentum is taken in the change kind of rule 22; the Preamble allows a scoped Force. | The v3.3 text could not be adopted as written: it cited files and values the code does not have, and contradicted rules 22 and 36 and the code. | Owner (Rule 26 review pending) |
| 20 Nov 2026 | 0.1 (term: native source), 0.3 (principle: 3), 37, 38, B (index) | v3.5 amendment: **Bloc aggregator first.** For a pair of an economy Eurostat serves (the European Union, the euro area, the EFTA economies and the candidate economies it covers) and that Eurostat publishes, Eurostat serves the pair whenever it is eligible, however early any other candidate is. Earliest and frequency are not measured for such a pair and nothing is staged for it. An outage has no substitute spliced in: the pair drops out of scores (rule 3, S2) and the owner may approve a change by the procedure of Changing source after one release cycle. The United States and every other economy keep the measures. Rule 37 lets every candidate back in where Eurostat is ineligible, does not publish the indicator or is in an outage. The tie-break sentence that let an original producer break the uniformity of a bloc is removed. | One definition, one revision schedule and one release pattern for a bloc make cross-country comparison valid (rule 23); the 32 provisional decisions of 19 Nov 2026 no longer wait for a measurement, and 32 staged series are no longer loaded. | Owner (Rule 26 review pending) |

---

## Appendix D. Migration map (v2.4 → v3.4)

One-off appendix. Lists every changed reference, so a reviewer can verify the move is complete. Deleted after one release cycle; from that point, Appendix A is the permanent record.

### Rule references

| v2.4 reference | v3.4 reference |
|---|---|
| `rule P` | `rule 38` |
| `rule O` | `rule 37` |
| `rule B` | `rule 29` |
| `rule D` | `rule 30` |
| `rule F` | `rule 31` |
| `rule G` | `rule 32` |
| `rule I` | `rule 33` |
| `rule J` | `rule 34` |
| `rule L` | `rule 35` |
| `rule N` | `rule 36` |
| `rules 1-28` (as a set) | `the active rules in Parts 1, 3, 4, 5` |
| `Part 5` (sources) | `Part 2` (sources) |
| `Part 5 B, D, F, G, I, J, L, N, O, P` | `Part 2 rules 29–38` |
| `Part 3` (scorecard) | `Part 4` (scorecard) |
| `Part 4` (governance) | `Part 5` (governance) |

### Code, test and doc references to update

**Path convention:** all paths below are relative to the repository root, as the Preamble now says. `app/…` = `services/api/app/…`; `tests/…` = `services/api/tests/…`.

| File | What to search for | Replacement |
|---|---|---|
| `app/**/*.py` | `rule P`, `rule O`, `rule B`, `rule I`, `rule J`, `rule L`, `rule N`, `rule D`, `rule F`, `rule G` | Respective new numbers |
| `tests/**/*.py` | Same; plus test names containing `rule_P`, `rule_O`, etc. | `rule_38`, `rule_37`, etc. |
| `apps/web/src/**/*.ts(x)` | Same rule references in comments / docstrings | — |
| `apps/web/tests/**/*.ts` | Same | — |
| `docs/assumptions-register.md` | "Selected under rule P" / "rule O" | `rule 38` / `rule 37` |
| `docs/data-connections.md` | `rule 28` (unchanged), any `rule P` / `rule O` | Renumbered |
| `docs/data-pipeline.md` | Any rule letter references | Renumbered |
| `private/scorecard-methodology.md` | `rule P`, `rule O`, `rule B`, `rule I`, `rule D` | Renumbered |
| Any open PR / issue | Same | Rebase onto the v3.4 consolidation PR |

### Files to add

- `tests/test_rulebook.py` — verifies every rule body's `Depends on:` matches the exact set of rule/S-rule/§0.1-term/§0.2-value/§0.3-principle citations in its Text and Purpose (per the Preamble's citation grammar); verifies every Appendix A entry has a Type; verifies no rule body uses a retired letter; verifies `scripts/build_rule_index.py` regenerates Appendix B identically; verifies every `Implementation:` and `Tests:` path resolves on disk, or is waived in `docs/rulebook-paths-waivers.md` with a target PR number; verifies Rule 25 against `RULEBOOK.md` itself.
- `scripts/build_rule_index.py` — generates Appendix B's `Referenced by:` column from the union of every rule body's `Depends on:` line.
- `docs/scorecard-versions.md` — commit-hash index of the private methodology versions (from rule 20).
- `private/disclosure-log.md` — recipient, date, scope, confidentiality terms for every external disclosure of the scorecard recipe (from rule 20). Private; not committed.
- `docs/rulebook-paths-waivers.md` — explicit list of files referenced in rule bodies but not yet created, each with a target PR number. The migration PR creates this file; `tests/test_rulebook.py` fails if a path is neither present nor waived.

### Files to update but not renumber

- `README.md` — no change to rule references (it doesn't cite rule numbers).
- `docs/indicator-names.md` — no rule references (only naming).
- `docs/data-provenance.md` — references to rule 8 (unchanged number).

### After the release cycle

- Delete this Appendix D only after one release cycle has passed and no external reference remains.
- Rule 26's change log becomes the sole record of the transition (Appendix C).

---

*End of QuFin Rule Book v3.5.*