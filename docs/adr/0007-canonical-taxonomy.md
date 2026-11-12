# ADR 0007: Canonical taxonomy, point-in-time reads by code, economic calendar

**Status:** Accepted (12 Nov 2026)

## Context
The macro store held 253 series under their sources' own ids (`UNRATE`, `BIS_CBPOL_GB`,
`HICP.M.U2.N.000000.4D0.ANR`). The dashboard listed them flat, the same indicator name appeared
once per country, and nothing recorded which pillar a series informs except a coarse `dimension`
that filed surveys under growth and the dollar under sentiment. The platform needs one naming scheme
in the style of Haver and Macrobond, two ways to read the data (by indicator and by country), and a
release calendar.

## Decision
- **One store, not two.** ADR 0002's `macro_series` and `macro_observations` already are the
  bitemporal store (`period` is valid time, `realtime_start` to `realtime_end` is transaction
  time). They are extended, not duplicated: a second observation table would double 1.08 million
  rows and risk the duplicates rules 15 and 16 forbid. Mapping to the usual names:
  `dim_series_metadata` = `macro_series`, `fact_macro_observations` = `macro_observations`.
- **Canonical code** `<ISO3>.<PILLAR>.<INDICATOR>.<FREQ>.<ADJ>` on every series
  (`USA.LABOR.UNEMPLOYMENT_RATE.M.SA`), derived from the catalog (`app/data/taxonomy.py`), unique in
  the database, stored with the series at every ingest. The source id stays the key everywhere else
  (connectors, tests, existing API paths); the code is an alias, not a replacement.
- **Eight pillars:** GROWTH, INFLATION, LABOR, MONETARY, SURVEYS, CONSUMPTION, TRADE, FISCAL.
  ENERGY and MARKETS are reference classes: stored and shown, never scored. Each series gets its
  pillar from its concept where the old dimension was wrong, else from its dimension. This replaces
  the pillar list in ADR 0005 (which had financial conditions and merged consumption and trade);
  the owner chose the new list on 12 Nov 2026. The live scorecard still scores its five pillars,
  shown under the new names, until it is re-mapped (separate change).
- **`dim_country_taxonomy`**: ISO3 and ISO2, currency, central bank, G7, G20, GCC and emerging
  market flags, filled from the taxonomy by `sync-taxonomy`. The euro area has no ISO code and is
  `EMU`.
- **Point-in-time reads** by code (`app/stores/point_in_time.py`): `get_latest_series`,
  `get_point_in_time_series(code, as_of_timestamp)` and `compute_macro_pillar_scores`. A vintage is
  dated, not timed, so one dated D counts as known from the start of D+1: a timestamp during D could
  precede the release. A day given to the API (`asOf=2026-09-10`) means "through that day", as the
  existing series endpoint does.
- **`fact_economic_calendar`** holds release date, previous value (as known then), first print,
  and consensus and surprise **empty until a licensed consensus feed exists**. Trading Economics and
  Forex Factory consensus is proprietary and scraping it breaks rule 28. The calendar covers
  weekly to annual series; daily rates are not releases.
- **Medallion layout.** Bronze is the raw zone (`data/raw`, `QUFIN_RAW_DIR`, immutable and
  checksummed; the folder keeps its name so no stored manifest breaks). Silver is the database
  tables above. Gold is derived tables filled at ingest (rule 15), not files; today the calendar and
  the per-series coverage, with the scorecard's z-scores still computed on read.

## Consequences
- The by-indicator and by-country dashboard views read `/v1/macro/indicators` and
  `/v1/macro/countries`; the page change is a separate step.
- A source that words its adjustment differently loads its data uncoded, with a warning, and
  `sync-taxonomy` fails until the wording is added to `ADJUSTMENTS`.
- Saudi Arabia has two series until the central-bank connectors (backlog P1-24).
- Only the United States has pillar scores; every other country reads "not scored yet".
