# Data provenance

Where every number in QuFin comes from. Keep this table current: a new page, card or endpoint
gets a row before it ships (rule 8 in `services/api/CLAUDE.md`).

| Page / surface | Numbers | Origin | How it is labelled |
|---|---|---|---|
| All dashboard pages | — | — | Red banner while prices and signals are sample data, signed in or not |
| Account menu | — | — | "Prices and signals: sample data" |
| Overview: KPIs | High-conviction count, hit rate, decisions | **Sample** (generator) | Badge on each KPI |
| Overview: Today's signals | Direction, probability, conviction, price, change | **Sample** | Badge on card |
| Overview: Macro scorecard | Pillar scores, confidence, pending releases | **Live** (FRED/ALFRED, point in time) | "Live · as of" badge; falls back to labelled sample without macro data |
| Markets | Prices, signals, regimes, hit rates | **Sample** | Page description and banner |
| Asset page: chart | Daily prices, signal markers | **Sample** | Badge on card |
| Asset page: signal and drivers | Probability, conviction, drivers | **Sample** | Badge on card |
| Asset page: your decision | Rule backtest of the plan | **Sample** prices and signals | Badge and description |
| Journal | Decisions (user input), marks to latest close, backtest summary | User input + **sample** prices | Badge when any decision was logged on sample data; each decision stores its origin |
| Backtest lab | Equity curve, statistics | **Sample** | Page description and in-card note |
| Macro data | Series, vintages, revisions, release status, weight | **Live** (FRED/ALFRED) | Source, release dates and status per series |
| Positioning | COT net, % OI, COT index | **Live** (CFTC legacy futures) | Report and release dates; caveat on partial contracts (Brent) |
| Notifications | — | None yet | Empty until real event sources exist (invented alerts removed) |

## Verified assumptions (1 November 2026)

| Assumption | Source checked | Result |
|---|---|---|
| CFTC contract codes map to the intended markets | CFTC market names in the data | All 11 correct; Brent is NYMEX "Last Day" only → caveat added |
| USDJPY sign flip | CME yen futures quote USD per JPY | Correct: long JPY = short USDJPY |
| COT release = report + 3 days | CFTC release schedule and special announcements | **Wrong for 71 reports** (holidays, 2018-19 and 2025 shutdowns, 2023 ION incident) → real calendar in `cot_calendar.py` |
| Scorecard signs (NFCI, T10Y3M, BAA10Y, Philly Fed, unemployment, claims) | FRED series notes | Correct |
| Growth indicators in real terms | FRED units | **Three were nominal** (RSAFS, PI, NEWORDER) → real RRSFS and W875RX1 scored; NEWORDER unscored |
| University of Michigan licence | Michigan usage agreement | Commercial use needs a licence; kept for now by the owner's decision |

Not verified: exact release dates for the 2018-19 shutdown weeks (derived from the CFTC's
stated catch-up rule) and the times of day of late releases (treated as end of day).
