# ADR 0003: Orchestration and scheduling

**Status:** Accepted; Dagster pending (1 Nov 2026)

## Context
Data arrives two ways: on fixed rhythms (daily FRED sweeps, monthly OECD) and at exact release
moments (US CPI 08:30 ET). Both need retries, lineage, freshness checks and alerts (Blueprint
section 03).

## Decision
- **Now:** idempotent command-line jobs (`python -m app.cli ingest-fred | ingest-cftc |
  check-data | scorecard-bias`). Each ends with the release-schedule check and exits non-zero on
  overdue, discontinued or unreviewed data, so any scheduler can alert on it.
- **Next (P1-07 to P1-10):** Dagster, with each dataset a software-defined asset: cron schedules
  for fixed rhythms, release-calendar sensors for market-moving releases, asset checks for
  quality, and alerts on failure or freshness breaches. The jobs above become the assets' bodies.

## Consequences
Until Dagster runs, loads are started by hand or by an external scheduler; the exit codes make
failures visible either way.
