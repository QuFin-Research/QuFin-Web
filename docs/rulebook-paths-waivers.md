# Rule book waivers

`RULEBOOK.md` is binding (Preamble, Part 0). Where the code does not yet do what a rule says, the gap
is written here so nobody discovers it by accident. `services/api/tests/test_rulebook.py` fails
if a path cited in a rule's cross-references does not exist and is not listed in the first table,
or if a Part 0, section 0.2 value is not held by the code and is not listed in the second.

A waiver is not an exception to the rule. It is a record that the code is behind the book, with
what closing the gap needs. Closing a gap that changes how a score is computed is a change of the
scorecard recipe (rule 20): it needs the bias gate (S7), a point-in-time backtest, a new scorecard
version in `docs/scorecard-versions.md` and the owner's approval.

## 1. Paths cited by a rule and not yet created

| Path | Rule | Why | Target |
|---|---|---|---|

None. Every path in the rule book's cross-references exists, except those under `private/`, which
live in a private repository and are not resolved by the test.

## 2. Part 0, section 0.2 values the code does not yet hold

| Name | Rule book value | The code today | Why it is waived |
|---|---|---|---|
| `ZSCORE_MIN_OBSERVATIONS_QUARTERLY` | 16 | 12 (`MIN_HISTORY["Q"]`) | Raising it drops quarterly indicators with 12 to 15 observations from every score: a recipe change (rule 20) |
| `ZSCORE_MIN_OBSERVATIONS_SEMIANNUAL` | 8 | no separate floor; a semi-annual series is scored like a quarterly one | Same |
| `ZSCORE_MIN_OBSERVATIONS_ANNUAL` | 8 | no separate floor; an annual series is scored like a quarterly one | Same |
| `ZSCORE_WINDOW_YEARS_ANNUAL` | 20 | none: every series uses `ZSCORE_WINDOW_YEARS_STANDARD` (10) | Same |
| `DISCOVERY_SWEEP_TIME_BUDGET_SECONDS` | 21600 | none: no discovery job exists (section 3, rule 34) | The job is not built |

## 3. Behaviour a rule requires and the code does not do yet

| Rule | What the rule book requires | What the code does today | What closing it needs |
|---|---|---|---|
| S1 | Semi-annual and annual series have their own z-score window and floor; momentum is one half year or one year back | Semi-annual and annual series are scored on the quarterly settings, with momentum taken three months back, so they rarely have a momentum score | A recipe change (rule 20): bias gate, backtest, new scorecard version, owner approval |
| 34 | Every new indicator is probed across every country by an asynchronous background discovery job; candidates go to staging | Candidates are found and verified by hand and recorded in the register; there is no discovery job and no staged load | Build the job; record progress per country |
| 38, Part 0 | Staged observations, first-sight timestamps and vintages promote into the active series when a candidate wins | A series can be marked `staged` and is then never served; nothing loads staged series or promotes them | A staging loader and a promotion step |
| 38 | The source is measured and chosen by the rule's own order | `app/domain/source_selection.py` makes the choice from measured inputs, but nothing measures first-read lags or records the probe; decisions are made by a person from the register and stored with `source-decision` | A measurement job that records first-read time per candidate, and a command that runs `choose()` |
| 36 | `doctor --fix` makes only the three repairs of items (i) to (iii) | It also removes stored series the catalog no longer lists (except the retired predecessors) and re-derives canonical codes that no longer match a series' frequency or adjustment | The owner's decision: add those two repairs to rule 36, or make the doctor report them only |
| 36 (iii) | A frozen upstream series is reported as `review` | The doctor reports it as a `frozen or overdue` error; the status itself is computed by the release check | None; the rule text now says "reporting" |
| S4 | Trade ideas are sized by confidence | The scorecard computes confidence and `pair_confidence`; no module sizes a trade idea from it | Build the sizing step |
| 2 | Staged series that fail their freshness check are reported without failing the run | There are no staged series loaded, so there is nothing to report | Comes with the staging loader |
| 7, 11, 12, 27, 33 | Each rule's behaviour is checked by a test | They have no automated test: they are documents or catalog conventions (`Tests: —` in their cross-references) | A test per rule where one can be written |
