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
