# Data provenance

Where every number in QuFin comes from. Keep this table current: a new page, card or endpoint
gets a row before it ships (rule 8 in `services/api/CLAUDE.md`).

Every badge and note follows the `data` origin the API returns (or the offline mock's "sample"), so labels change by themselves when a source goes live; a missing origin counts as sample.

| Page / surface | Numbers | Origin | How it is labelled |
|---|---|---|---|
| All dashboard pages | — | — | Red banner while prices and signals are sample data, signed in or not |
| Account menu | — | — | "Prices and signals: sample data" while the API reports sample prices |
| Overview: KPIs | High-conviction count, hit rate, assets covered | **Sample** (generator) | Badge on each market KPI |
| Overview: Decisions logged | Count of the user's journal entries | User input | None (not market data) |
| Overview: Today's signals | Direction, probability, conviction, price, change | **Sample** | Badge on card |
| Overview: Macro scorecard | Pillar scores, confidence, pending releases | **Live** (FRED/ALFRED, point in time) | "Live · as of" badge; falls back to labelled sample without macro data |
| Markets | Prices, signals, regimes, hit rates | **Sample** | Banner |
| Asset page: chart | Daily prices, signal markers | **Sample** | Badge on card |
| Asset page: signal and drivers | Probability, conviction, drivers | **Sample** | Badge on card |
| Asset page: your decision | Rule backtest of the plan | **Sample** prices and signals | Badge and description |
| Journal | Decisions (user input), marks to latest close, backtest summary | User input + **sample** prices | Badge when any decision was logged on sample data; each decision stores its origin |
| Backtest lab | Equity curve, statistics | **Sample** | Banner and in-card note, from the result's origin |
| Macro data | Series, vintages, revisions, release status, weight, 1m/3m/1y change | **Live** (FRED/ALFRED) | Source, release dates and status per series; changes in % or points per the series' kind |
| Macro data: Markets | Daily reference prices: 7 FX pairs (Fed H.10), WTI, Brent, Henry Hub (EIA) | **Live** (FRED/ALFRED), reference prices, not tradable quotes | "markets" group; not scored; asset prices elsewhere stay sample until wired |
| Macro data: Energy | 12 weekly oil series (stocks, production, refinery use, trade, demand) | **Live** (EIA API v2, Weekly Petroleum Status Report) | "energy" group; not scored; release dates derived from EIA's weekly rule; revisions stored as vintages from the day QuFin sees them |
| Macro data: euro area | Deposit facility rate, HICP headline and core (annual rates), M3 | **Live** (ECB Data Portal; HICP produced by Eurostat) | Country EA, same concept names as the US; not scored (no mixed-country scorecard yet); release dates derived, erring late |
| Macro data: OECD members | Composite leading indicator, business and consumer confidence (index, long-term average 100) | **Live** (OECD Data Explorer, from national sources) | Own country codes (GB, JP, …), same concept names as the US; not scored; release dates derived, erring late |
| Positioning | COT net, % OI, COT index; asset managers' net for financial futures | **Live** (CFTC Traders in Financial Futures for 10 financial contracts, legacy report for 5 commodities; each contract from one report only) | Report, group (leveraged funds or non-commercial) and release dates; caveats on partial contracts (Brent) and the US Dollar Index (no licensed price) |
| Notifications | — | None yet | Empty until real event sources exist (invented alerts removed) |

## Verified assumptions (1 November 2026)

| Assumption | Source checked | Result |
|---|---|---|
| CFTC contract codes map to the intended markets | CFTC market names in the data | All 11 correct; Brent is NYMEX "Last Day" only → caveat added |
| USDJPY sign flip | CME yen futures quote USD per JPY | Correct: long JPY = short USDJPY |
| COT release = report + 3 days | CFTC release schedule and special announcements | **Wrong for 71 reports** (holidays, 2018-19 and 2025 shutdowns, 2023 ION incident) → real calendar in `cot_calendar.py`; every load also re-derives stored release dates, so older databases are corrected |
| Scorecard signs (NFCI, T10Y3M, BAA10Y, Philly Fed, unemployment, claims) | FRED series notes | Correct |
| Growth indicators in real terms | FRED units | **Three were nominal** (RSAFS, PI, NEWORDER) → real RRSFS and W875RX1 scored; NEWORDER unscored |
| No series is changed twice | FRED units and notes of all 43 series | None published as a change, except WEI ("Index" units, but scaled to GDP growth per its notes): declared `published_as_change`, scored as published |
| VIX as an early sentiment read | FRED notes | Copyright Cboe: not added (licence needed) |
| BLS and BEA leading/lagging indicators missing on FRED | FRED API (4 Nov 2026) | None missing: temp help, JOLTS openings and quits, PPI final demand, real PCE, trade balance, current account, budget balance and debt/GDP are all on FRED with vintages; no direct BLS or BEA connector needed |
| EIA weekly petroleum status on FRED | FRED API | Not on FRED (crude, Cushing, SPR, production, refinery use, product stocks and demand): EIA API v2 is the source for oil, verified with the key |
| Duplicated data in the catalog | Series definitions | Removed four exactly derivable series: DGS10 (= DFII10 + T10YIE), T10Y2Y, MPRIME (= fed funds + 3), RSAFS (= RRSFS × CPI) |
| Regional Fed manufacturing surveys (P1-17) | FRED API and series notes (5 Nov 2026) | Empire State (GACDISA066MSFRBNY) and Dallas (BACTSAMFRBDAL) headline indexes live on FRED, SA, added as leading, not scored yet (rule 10). Philadelphia stays as its new-orders series: its headline would be a second read of the same survey (rule 16). Richmond and Kansas City manufacturing surveys are **not on FRED**; their banks publish spreadsheets only: gap, not loaded |
| Treasury fiscal series not on FRED (P1-14) | FRED API and Fiscal Data API (5 Nov 2026) | FRED has debt only quarterly and no Treasury average rates or monthly interest expense: daily Debt to the Penny, average rate on marketable debt and monthly interest expense loaded from Fiscal Data. Interest expense has no total row: its lines are summed, and FY2024 sums to $1,133.0 billion, matching Treasury's published total. No duplicate of GFDEGDQ188S (a ratio to GDP) |
| Euro area series (P1-18, P1-19) | ECB Data Portal API (6 Nov 2026) | All four live: deposit rate to 5 Nov, HICP to Oct (flash), M3 to Sep. HICP is published as an annual rate: declared `published_as_change`, never re-changed. ECB reference FX rates skipped: EUR/USD would duplicate Fed H.10 (rule 16). Shared concept names made country-neutral ("Broad Money Supply": M2 in the US, M3 in the euro area) |
| OECD leading indicators and confidence (P1-20) | OECD API, one series per request (6 Nov 2026) | **Multi-series OECD queries return broken partial histories** (a few scattered months per series): never used; each series is fetched alone and a monthly gap fails the load. Liveness checked series by series: 28 live; stale ones left out (Canadian and Norwegian business confidence); 6 consumer confidence series not yet verified (API rate limit) and left out. US CLI from FRED (USALOLITOAASTSAM, live with vintages), not the OECD API (rule 17) |
| University of Michigan licence | Michigan usage agreement | Commercial use needs a licence; kept for now by the owner's decision |

Not verified: exact release dates for the 2018-19 shutdown weeks (derived from the CFTC's
stated catch-up rule) and the times of day of late releases (treated as end of day).
