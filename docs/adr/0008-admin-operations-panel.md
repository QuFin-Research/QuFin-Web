# ADR 0008: Admin operations panel

Status: Accepted (17 Nov 2026). Deviation from ADR 0003 (jobs stay command-line; the panel only starts them).

## Context

Admins and data scientists had to run `doctor` and `coverage-matrix` by hand to learn how much data
was missing, and nothing told them whether the scorecard behind a country was being kept up to date.
Loading new data needed a terminal. The sidebar already marked the data-health page `role: 'admin'`,
but the API had no roles at all, so that marker enforced nothing, and a button that makes the server
call outside data sources cannot rest on it.

## Decision

1. **Roles are server settings.** `QUFIN_ADMIN_EMAILS` and `QUFIN_DATA_SCIENTIST_EMAILS` (comma
   separated, empty by default) give an address its role on every request. The role is returned by
   `/v1/auth/me` for the interface to hide what a user cannot use; it is never stored and a sign-up
   cannot ask for one. `require_staff` (admin or data scientist) guards the views; `require_admin`
   guards starting a run.
2. **One status call.** `GET /v1/admin/status` returns the coverage headline, whether the scorecard is
   `updated`, `partial` or `stale`, and the last run. The dashboard shell asks for it only for staff,
   so a banner (and one toast per browser session) greets them at every sign-in and on every page; the
   scorecard card carries a `Backend:` badge with the reason. `GET /v1/admin/coverage` adds the tables
   (indicators and countries missing the most) for the data-health page.
3. **Scorecard state is derived, never invented.** `updated`: every scored indicator is current.
   `partial`: some are overdue, they are left out and confidence falls (the scorecard's own rule).
   `stale`: most are overdue, or nothing has been loaded for seven days. A failed last run is added to
   the reason.
4. **The Run button starts the same commands a person would run.** `POST /v1/admin/jobs/refresh`
   plans one `ingest-<source>` command per source, only for series that are due or overdue (FRED
   first as a run order only, not a source preference, rule 38), runs each in its own process with a timeout, and records every step in
   `job_runs` so the panel can poll `GET /v1/admin/jobs/{id}`. A process per step means a slow source
   cannot take the API down and each step still ends with the release check (rule 2).
5. **Guards.** One run at a time (`409`), at most one start per `QUFIN_REFRESH_MIN_INTERVAL_SECONDS`
   (default 10 minutes, `429` with `Retry-After`: rule 28 asks us to be gentle with sources), a run
   older than `QUFIN_REFRESH_RUN_TIMEOUT_SECONDS` is marked interrupted, a source whose key is not set
   is skipped and said so. The request needs a JSON body and the API's existing origin check applies,
   so a cross-site form cannot start a run.
6. **Coverage reads the same hot path as `GET /v1/macro/series`** (stored series plus the first-release
   map), so it adds no new table scan (rule 15).

## Consequences

- Nobody has admin rights until the settings name them; on a deployment this is a conscious step.
- A refresh started from the web runs in a thread of the API process and survives only as long as the
  process; a restart leaves a `running` row that the next call marks interrupted. When ADR 0003's
  scheduler arrives it should call the same `refresh` job; the panel then shows its runs too.
- Every ingest command ends with the full release check and the doctor, about three minutes on a
  1,000-series database, so a run of six sources would spend most of its time checking six times. A
  refresh therefore runs its ingest commands with those deferred (`QUFIN_DEFER_RELEASE_CHECK=1`, read by
  `app/cli.py`; a person running one command sees no change) and ends with one `check-data` step: the
  run still ends with the release check (rule 2), once. Found by running the button against the real
  database: with a 90 s step limit every step was stopped.
- `ingest-fred` re-reads each due series' full vintage history, so a FRED step with dozens of daily
  series is slow. An incremental FRED load would fix it but must not replace a series with a short
  window: not done.
- The panel shows what is stored and declared. Derived-not-stored indicators and removed series have no
  status yet.
