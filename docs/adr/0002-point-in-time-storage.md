# ADR 0002: Point-in-time storage

**Status:** Accepted (1 Nov 2026)

## Context
Backtests and scores must only see what was published on each date. Revised data that traders
never had is the most common reason "AI accuracy" claims fail (Blueprint section 04).

## Decision
- Every observation is stored with the real-time period it was the published value:
  `(series_id, period, realtime_start, realtime_end, value)`, as ALFRED models vintages. A
  revision closes the old row and opens a new one. The Blueprint's
  `(series_id, period, value, vintage_date, release_id, ingested_at)` maps onto this
  (`vintage_date` = `realtime_start`); `release_id` and `ingested_at` are added with the release
  calendar store (P1-09).
- Reads are as-of a date (`/v1/macro/series/{id}?asOf=`); the latest view is the open rows.
- Release dates come from the source's real calendar, including holidays and shutdowns; where
  unpublished they are derived from the source's stated rule and errs late.
- Raw source payloads are kept immutable (raw zone, P1-05) so any number traces to its file.
- SQLite locally; Postgres 16 + TimescaleDB in staging and production (P1-03), same schema via
  Alembic. Every hot query is index-backed (`tests/test_query_plans.py`).

## Consequences
Storage grows with revisions (NFCI alone keeps 414k rows), accepted as the cost of honest
backtests. Interval queries "as published on date D" are the hardest to index; on Postgres a range
type with a GiST index is the planned fix.
