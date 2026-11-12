# Data connections

How QuFin connects to every data source: where it goes, how it authenticates, how it behaves under
failure, and how each number gets from the publisher to the dashboard. Keep this file current: a
connector pull request updates its row here (rule 27 in `RULEBOOK.md`). No secret ever appears in
this file; keys are named by the setting that holds them.

## 1. The mechanism, common to every source

1. **Official APIs only.** QuFin reads the publisher's own published API (or an official aggregator
   such as FRED). It does not scrape web pages. Sites that forbid scraping are used for names only.
2. **One shared base** (`app/connectors/base.py`, class `HttpSource`). Every connector subclasses it
   and adds only the endpoints and the parsing:
   - HTTPS `GET` through `httpx`, with the operating system's certificate store (`truststore`).
   - Up to 3 retries with exponential backoff (1 s, 2 s, 4 s) on network errors, HTTP 429 and 5xx,
     honouring the publisher's `Retry-After` (seconds or an HTTP date, at most 120 s). BLS uses `POST`
     with the same retry policy.
   - Every response body is saved untouched to the **raw zone** before it is parsed.
   - Errors never echo the request URL, so a key in a query string cannot leak into a log.
3. **Raw zone** (`app/stores/raw_zone.py`, folder `QUFIN_RAW_DIR`, git-ignored). Layout
   `<source>/<YYYY-MM-DD>/<name>-<HHMMSS>-<sha256>.<ext>`, written once and never overwritten, with a
   line per file in `manifest.jsonl` (path, checksum, size, time). Any stored number can be traced
   to the exact response it came from. Credentials never reach it.
4. **Parse and validate**, then store **point in time** (`macro_observations`: every value with the
   dates it was valid; CFTC reports in their own tables). Where the source serves no history of
   revisions (EIA, ECB, OECD, Treasury, BLS), a changed value is stored as a new vintage from the day
   QuFin sees it, and a new period is dated by its release (rule 6).
5. **Release dates** come from the publisher's real calendar where one exists (FRED release dates,
   the CFTC schedule), otherwise from its stated rule, erring late (rule 9).
6. **The release check** (`python -m app.cli check-data`) tests every series against its schedule,
   the duplicated-data check and the unit and currency declarations (rules 1-3, 16, 23). Every
   `ingest-*` command ends with it and exits non-zero on a failure.
7. **Keys** live in `services/api/.env` (git-ignored), loaded as settings with the `QUFIN_` prefix
   (`app/core/config.py`). Blank means not set. A secret scan (gitleaks) runs on every pull request.

## 2. The sources

| Source | What QuFin takes | Protocol and address | Authentication | Command | Series |
|---|---|---|---|---|---|
| **FRED / ALFRED** (St. Louis Fed) | US macro and market series with full revision history | REST `https://api.stlouisfed.org/fred`: `/series`, `/series/observations` (real-time periods 1776-07-04 to 9999-12-31 for every vintage), `/series/vintagedates`, `/series/release`, `/release/sources` | Key in the query: `QUFIN_FRED_API_KEY` | `ingest-fred` | 75 |
| **EIA** (US Energy Information Administration) | 12 weekly petroleum series (stocks, production, trade, demand) not on FRED | REST `https://api.eia.gov/v2/seriesid/PET.<id>.W`, paged by `length` and `offset`, newest first | Key in the query: `QUFIN_EIA_API_KEY` | `ingest-eia` | 12 |
| **CFTC** Commitments of Traders | Weekly positioning: Traders in Financial Futures for 10 financial contracts, legacy report for 5 commodities | Socrata open data `https://publicreporting.cftc.gov/resource/gpe5-46if.json` (financial) and `.../6dca-aqww.json` (legacy), SoQL `$where`, `$order`, `$limit`, `$offset` | None | `ingest-cftc` | 15 contracts |
| **ECB** Data Portal | Euro area policy rate, HICP, core HICP, M3 | SDMX 2.1 REST `https://data-api.ecb.europa.eu/service/data/<flow>/<key>?format=jsondata` | None | `ingest-ecb` | 4 |
| **OECD** Data Explorer | Composite leading indicator, business and consumer confidence for 14 economies | SDMX 2.1 REST `https://sdmx.oecd.org/public/rest/data/<flow>/<key>?format=jsondata` (section 3) | None | `ingest-oecd` | 34 |
| **IMF** (International Liquidity) | Official reserves excluding gold, in US dollars, for the 9 economies FRED does not carry (FRED's copies are used for 12 more) | SDMX 2.1 REST `https://api.imf.org/external/sdmx/2.1/data/IMF.STA,IL,13.0.1/<area>.RXF11_REVS.USD.M?format=jsondata`; JSON only with `Accept: application/vnd.sdmx.data+json`, and the body starts with a byte-order mark; one series per request with a pause; no release dates (derived, `app/data/imf_calendar.py`) | None | `ingest-imf` | 9 |
| **BLS** (US Bureau of Labor Statistics) | The Employment Cost Index (total compensation, civilian workers, seasonally adjusted), which FRED does not carry | REST `POST https://api.bls.gov/publicAPI/v2/timeseries/data/` with a JSON body (`seriesid`, `startyear`, `endyear`); history fetched in year windows (10 years keyless, 20 with a key) | Optional key: `QUFIN_BLS_API_KEY` (keyless works within 25 queries a day; 50 requests per 10 seconds) | `ingest-bls` | 1 |
| **BIS** (Bank for International Settlements) Data Portal | Central bank policy rates (21 economies), nominal and real effective exchange rates (24), credit-to-GDP ratio and gap (23), for economies FRED carries late or not at all | SDMX REST API v2 `https://stats.bis.org/api/v2/data/dataflow/BIS/<flow>/1.0/<key>` (flows `WS_CBPOL`, `WS_EER`, `WS_CREDIT_GAP`), SDMX-JSON requested in the `Accept` header; one request per measure returns every economy | None | `ingest-bis` | 115 |
| **US Treasury** Fiscal Data | Debt to the Penny, average interest rates, interest expense | REST `https://api.fiscaldata.treasury.gov/services/api/fiscal_service/v2/accounting/od/...`, filters `record_date:gte:<date>`, paged | None | `ingest-treasury` | 3 |

Total: 253 macro series and 15 positioning contracts (268 sources), each checked by `check-data`.

Not connected yet: World Bank and central-bank batch 1 (backlog P1-23 and P1-24).
A BEA key exists in the local `.env` but has no connector: FRED carries those series
(rule 17). BLS is connected only for the Employment Cost Index; JOLTS job openings stay on FRED
(`JTSJOL`), because the same series from BLS would be a duplicate (rules 16 and 17). The licence status of every source is in `docs/licence-register.md`.

The ECB, OECD and every later SDMX source share one parser, `app/connectors/sdmx.py`: it reads
SDMX-JSON, turns periods (day, month `2026-10` or the IMF's `2026-M10`, quarter, year) into dates, and returns each series with its
attributes (units, scale) exactly as the publisher states them.

## 2b. Supplier limits and how QuFin keeps within them (rule 28)

What each supplier publishes was read on its own site on 12 Nov 2026 (pages named below). "Not
stated" means the pages read gave no number; QuFin then keeps its own conservative gap. Every
connector sends the `User-Agent` `QuFin-data-client/1.0 (+https://github.com/QuFin-Research/QuFin-Web)`,
waits at least `min_interval` between requests (`app/connectors/base.py`, set per connector), honours
`Retry-After`, and after a 403 or 429 that outlasts its retries asks for nothing more in that run.

| Source | What the supplier states | QuFin's gap and sizes | Source of the statement |
|---|---|---|---|
| FRED / ALFRED | Per-minute limit **not stated**; the terms let the Bank set bandwidth or transaction limits. `limit` up to 100,000 observations per request; vintage dates per request capped (2,000 for JSON). Each application should use its own key | 0.6 s; page 100,000; 1,900 vintages per request | fred.stlouisfed.org/docs/api (series_observations, overview, api_key) and /legal |
| BLS API v2 | 500 queries a day (registered), 50 series per query, 20 years per query, 50 requests per 10 s; BLS may block a user who tries to exceed or circumvent limits. Unregistered v1: 25 a day, 25 series, 10 years | 0.5 s; windows of 20 years with a key, 10 without; one series per run today | bls.gov/developers (api_faqs, termsOfService) |
| EIA API v2 | 5,000 rows per request. No official rate limit; informal guidance of under 5 requests a second and about 9,000 an hour avoids throttling. Bulk files at eia.gov/opendata/bulk refreshed twice daily. EIA may block use that exceeds or circumvents its limits | 0.5 s; page 5,000 | eia.gov/opendata (faqs, terms-of-service) |
| US Treasury Fiscal Data | No limit stated; default page size 100, no maximum stated; no key | 0.5 s; page 10,000 (**maximum not verified**) | fiscaldata.treasury.gov/api-documentation |
| CFTC (Socrata) | CFTC states none. Socrata: requests without an app token share one pool per IP address and get HTTP 429 when throttled; no numbers. `$limit` maximum not found | 0.5 s; page 5,000; no app token yet | dev.socrata.com/docs/app-tokens.html; publicreportinghub.cftc.gov |
| BIS | No numeric limit; the terms let the BIS limit or suspend an IP address at any time without notice. Bulk CSV and SDMX files at data.bis.org/bulkdownload | 1 s; one request per measure (5 a run); run at most daily | data.bis.org/help/legal, /bulkdownload |
| OECD | **Not verified** (the pages could not be read on 12 Nov 2026). Observed: HTTP 429 after about 70 requests in a row | 3 s; one series per request | observation recorded in section 3 |
| ECB | **Not verified** (the ECB pages returned HTTP 503 on 12 Nov 2026) | 1 s | none yet |
| IMF | No numeric limit on the IMF API page; the page points to a portal account for the API explorer and does not say whether data queries need a key | 1 s; one request per run of series | data.imf.org/en/Resource-Pages/IMF-API |

**Open work (rule 28):** read the OECD, ECB and IMF limit pages and replace "not verified"; find the
Treasury and CFTC page-size maximums; consider an app token for the CFTC and bulk files for EIA if
load grows. Runs of any connector stay at most as frequent as its data changes.

## 3. Worked example: the OECD

**What the OECD is for:** leading indicators and confidence surveys for countries FRED does not carry
reliably (FRED's copies of OECD data are mostly stale).

**Address and key.** One request fetches one series:

```
https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/<REF_AREA>.M.<MEASURE>.IX..AA.IX..H?format=jsondata&startPeriod=2026-05-01
```

- Dataflow `OECD.SDD.STES,DSD_STES@DF_CLI,` (agency, dataflow, latest version).
- The key lists the dataflow's dimensions in order: `REF_AREA . FREQ . MEASURE . UNIT_MEASURE .
  ACTIVITY . ADJUSTMENT . TRANSFORMATION . TIME_HORIZ . METHODOLOGY`. QuFin fixes frequency `M`
  (monthly), unit `IX` (index), adjustment `AA` (amplitude adjusted, long-term average = 100),
  transformation `IX` and methodology `H`, leaves activity and time horizon empty, and varies only
  the area (`USA`, `JPN`, `KOR` ...) and the measure: `LI` (composite leading indicator), `BCICP`
  (business confidence), `CCICP` (consumer confidence).
- **Tested live on 6 Nov 2026:** `USA.M.LI.IX..AA.IX..H` returned HTTP 200, content type
  `application/vnd.sdmx.data+json`, 8.9 kB, latest value 101.0 for September 2026.

**Authentication:** none. **No release dates:** the API serves none, so QuFin dates each month the
15th of the second month after it (next weekday), `app/data/oecd_calendar.py`: late for most series,
never early for the slow ones.

**How QuFin behaves, and why** (`app/jobs/ingest_oecd.py`):

- **One fully specified key per request.** The OECD returns broken, partial histories for queries
  that cover several series (checked 6 Nov 2026), so they are never used.
- **A pause of 3 seconds between requests**, because the OECD limits requests per hour (it answered
  HTTP 429 after about 70 in a row). A full load of 34 series fits, but a repeated load may have to
  wait for the limit to reset.
- **A completeness check:** every month from the first to the last must be present; a gap means a
  broken or partial response and the series is rejected, not stored.
- **Declared units:** the series is stored with the OECD's own units, adjustment and frequency, and
  the unit and currency declaration is verified against them at every load (rule 23).
- A changed value is stored as a new vintage; `check-data` then confirms the latest month fits the
  schedule.

**By hand:** open the address above in a browser, or run
`curl "https://sdmx.oecd.org/public/rest/data/OECD.SDD.STES,DSD_STES@DF_CLI,/USA.M.LI.IX..AA.IX..H?format=jsondata&startPeriod=2026-05-01"`.

## 4. Running a load

```
cd services/api
uv run python -m app.cli ingest-fred        # also: ingest-eia, ingest-cftc, ingest-ecb, ingest-oecd, ingest-treasury
uv run python -m app.cli check-data         # release, duplicate and unit checks of every source
```

Each command accepts series ids and `--start`, prints what changed per series, then prints the
release check and exits non-zero if any series is overdue, discontinued or needs review.

## 5. Adding a connector

1. Verify the series at the publisher: dataflow and key, latest observation, release schedule, units
   and currency, whether it is live, and the licence for use in a paid product (rules 1, 7, 12).
2. Subclass `HttpSource` (or `SdmxClient` for SDMX sources); parse; write the ingest job; derive the
   release dates from the publisher's calendar or stated rule (rule 9).
3. Declare each series in the catalog: global name and acronym (rule 19), cycle with a reason,
   change kind (rule 22), unit and currency (rule 23). No duplicate of a series already stored
   (rules 16, 17).
4. Record every judgement in `docs/assumptions-register.md`, the licence in
   `docs/licence-register.md`, the calendar in `docs/release-calendars.md`, and the row here.
5. Load live, run `check-data`, and put its result in the pull request.
