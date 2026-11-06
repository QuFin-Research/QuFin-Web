# Ingestion and retrieval

How data gets into QuFin (ingestion) and how it gets out to the dashboard, the API and the backtests
(retrieval). This is QuFin's own description of its processes and is the property of QuFin
(rule 24 in `RULEBOOK.md`). It describes what exists today and marks what is still planned. Source
by source connection details are in `docs/data-connections.md`; where each number on a page comes
from is in `docs/data-provenance.md`. A change to either process updates this file (rule 27).

## 1. The path of one number

```
publisher's API
  -> connector      (fetch, retries, raw copy saved)
  -> parser         (series, periods, units as published)
  -> validation     (complete, units declared, no duplicates, schedule)
  -> point-in-time store   (every value with the dates it was known)
  -> API            (as published on any date, changes, freshness, names)
  -> dashboard, scorecard, backtests
```

Example: the US unemployment rate (`UNRATE`). FRED serves every published value of every month with
the dates each was current. The connector saves that response untouched in the raw zone, the parser
turns it into dated values, the store keeps each revision as its own row, and
`GET /v1/macro/series/UNRATE?asOf=2026-09-10` returns the series exactly as the public knew it that
day. The same call without `asOf` returns the latest values. The dashboard draws the chart from it.

## 2. Ingestion

**Trigger.** A command per source (`python -m app.cli ingest-fred`, `ingest-eia`, `ingest-cftc`,
`ingest-ecb`, `ingest-oecd`, `ingest-treasury`), run by hand today. *Planned:* a scheduler (Dagster,
backlog P1-07 to P1-10) running each source on its release calendar, with alerts when a load fails
or a series is late.

**Steps, in order**

1. **Fetch** through the shared connector base: official API only, HTTPS, retries with backoff,
   rate-limit pauses where the source needs them, errors that never reveal a key.
2. **Keep the raw response** in the raw zone before anything reads it. It is written once, never
   overwritten, and listed with its checksum in `manifest.jsonl`, so any stored number can be traced
   to the exact bytes it came from.
3. **Parse** into dated values plus the units, frequency and adjustment as the publisher states
   them. SDMX sources (ECB, OECD, later IMF and BIS) share one parser.
4. **Validate** before storing: the series must be complete over its range, the source's units must
   match the unit kind and currency QuFin declared (rule 23), and the data must not duplicate
   another stored series (rule 16).
5. **Store point in time.** A row is one value of one period together with `realtime_start` and
   `realtime_end`, the first and last day that value was the published one. A revision closes the
   old row and opens a new one. Sources that serve their whole revision history (FRED/ALFRED) are
   stored as served. Sources that serve only current values (EIA, ECB, OECD, Treasury) are stored by
   comparing with what QuFin already holds: a new period is dated by its release, a changed value
   becomes a new row from the day QuFin sees it. Nothing is ever overwritten.
6. **Store the description** of each series: source and publisher, official title, units, unit kind
   and currency, frequency, seasonal adjustment, country, pillar, business-cycle tag, the release it
   belongs to and any delay notice, plus its first period, last period and row count, so no page has
   to count a table to show them (rule 15).
7. **Finish with the release check** (`check-data`): every series against its release schedule,
   the duplicate check and the unit declarations. A load that leaves any series overdue,
   discontinued or needing review exits with a failure. Bulk loads also refresh the database
   statistics so the planner keeps using the indexes.

**Where it is stored.** Local SQLite today (`services/api/qufin.db`), with versioned migrations
(`migrations/versions`) so the schema is reproducible. *Planned:* Postgres with TimescaleDB, and an
object-store raw zone with versioning (backlog P1-03, P1-05).

## 3. Retrieval

**The API** (FastAPI, `/v1`), organised by what it serves:

| Endpoint | What it returns |
|---|---|
| `GET /macro/series` | every macro series: names, units, cycle, source, release status, timeliness, latest changes |
| `GET /macro/series/{id}` | one series; `asOf` gives it as published on that date, `start` and `end` limit the range |
| `GET /macro/series/{id}/revisions` | every value a period has had and when each was published |
| `GET /positioning`, `/positioning/{symbol}` | CFTC positioning with the COT index; `asOf` respects release dates |
| `GET /scorecards/countries` | country scores with confidence and pending releases; `asOf` for any past date |
| `GET /scorecards/methodology` | what QuFin tells users about the scorecard (shown or hidden, rule 20) |
| `GET /assets`, `/assets/{symbol}` | market snapshots and detail (sample data until a licensed price feed exists) |
| `POST /backtests` | runs a backtest through the API |
| `/decisions`, `/auth/...` | the user's decision journal, sign-up, sign-in, sign-out |

**Point-in-time reads.** Every read of data that gets revised takes an `asOf` date. The store answers
it with a range filter on `realtime_start` and `realtime_end`, so a backtest or scorecard sees only
what had been published by then, never a later revision (rule 6).

**What is computed when asked, not stored.** Changes over one, three and twelve months, taken within
a single vintage, so a revision never appears as a move; percent for quantities, points for rates,
none for series already published as a change (rules 13, 22). Daily and weekly series are compared as
28-day averages. Freshness and timeliness weight per series (rules 3, 5). Display names,
acronyms, explanations and cycle tags come from the catalog, not the database, so a rename or re-tag
needs no reload. The scorecard is computed from the store at the requested date.

**Every response states its origin.** Each data endpoint returns `data` (`live` or `sample`) or
`freshness`; a test fails if a new endpoint does not (rule 8). Whether the scorecard recipe is
included is QuFin's choice, a setting; origin, freshness, confidence and pending releases are always
included.

**Speed.** Each read a page relies on is served by an index and listed in a test that fails if the
planner scans a data table (rule 15).

**Access.** Accounts use a server-side session cookie (`SameSite=Lax`), an explicit list of allowed
origins, and an origin check on every request that changes data.

**The dashboard** (`apps/web`, Next.js) reads only this API, through one client and TanStack Query.
Without the API it shows sample data, labelled as sample on every page. The Macro page can show a
series as actual values or as its change over a year (rule 22).

## 4. Not built yet

- Scheduling and alerting (Dagster), Postgres/TimescaleDB, the object-store raw zone.
- A multi-series chart endpoint that puts series on a common basis (rule 23) and converts currencies
  at a stated rate and date.
- Per-person or per-organisation disclosure of the scorecard recipe (today one setting for all).
- Connectors for the IMF, BIS, World Bank and central banks (backlog P1-21 to P1-24).
