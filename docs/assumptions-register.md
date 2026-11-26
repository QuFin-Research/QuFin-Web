# Assumptions register

> From 20 Nov 2026 the rule book numbers every rule. Sections written before then cite rules by their old letters (B, D, F, G, I, J, L, N, O, P and the retired A, C, E, H, K, M); Appendix A of `RULEBOOK.md` maps each to its number.


Every judgement QuFin's data and scorecard rest on, with what has and has not been checked
against the producer (rule 12 in `RULEBOOK.md`). Audit of 6 Nov 2026. Add a row
whenever a judgement is added; a judgement without a row is a defect.

**Status:** *Verified* = read at the producer or its aggregator this audit. *Convention* = standard
analyst practice with no producer statement. *Design choice* = QuFin's own modelling choice, not a
fact; unvalidated until the backtest gate (Blueprint, Phase 3). *Unverified* = could not be checked.

## 1. Scored series: sign, transform, units and adjustment

`polarity` +1 = higher reading means a stronger pillar, -1 = weaker. Units and seasonal
adjustment are FRED's own metadata for the series; the sign is **verified** only where the
producer's notes say what a higher reading means, otherwise it is **convention**.

| Series | Name | Pillar sign | Transform | Units (FRED) | SA | Sign basis |
|---|---|---|---|---|---|---|
| GDPC1 | GDP – Real Gross Domestic Product | +1 | yoy | Billions of Chained 2017 Dollars | SAAR | FRED notes read; definition confirmed |
| INDPRO | Industrial Production | +1 | yoy | Index 2017=100 | SA | FRED notes read; definition confirmed |
| RRSFS | Real Retail Sales | +1 | yoy | Millions of 1982-84 CPI Adjusted Dollars | SA | FRED notes read; definition confirmed |
| W875RX1 | Real Personal Income excl. Transfers | +1 | yoy | Billions of Chained 2017 Dollars | SAAR | FRED notes read; definition confirmed |
| PERMIT | Building Permits | +1 | yoy | Thousands of Units | SAAR | FRED notes read; definition confirmed |
| HSN1F | New Home Sales | +1 | yoy | Thousands | SAAR | no producer notes: convention |
| PCEC96 | PCE – Real Personal Consumption Expenditures | +1 | yoy | Billions of Chained 2017 Dollars | SAAR | FRED notes read; definition confirmed |
| NOCDFSA066MSFRBPHI | Philadelphia Fed New Orders Index | +1 | level | Index | SA | FRED notes read; definition confirmed |
| WEI | WEI – Weekly Economic Index | +1 | level | Index | NSA | FRED notes read; definition confirmed |
| CPIAUCSL | CPI – Consumer Price Index | +1 | yoy | Index 1982-1984=100 | SA | FRED notes read; definition confirmed |
| CPILFESL | Core CPI – Consumer Price Index ex Food and Energy | +1 | yoy | Index 1982-1984=100 | SA | FRED notes read; definition confirmed |
| PCEPILFE | Core PCE – PCE Price Index ex Food and Energy | +1 | yoy | Index 2017=100 | SA | FRED notes read; definition confirmed |
| CUSR0000SAS | Services CPI – Consumer Price Index, Services | +1 | yoy | Index 1982-1984=100 | SA | no producer notes: convention |
| T10YIE | 10-Year Breakeven Inflation Rate | +1 | level | Percent | NSA | FRED notes read; definition confirmed |
| GASREGW | Retail Gasoline Price | +1 | yoy | Dollars per Gallon | NSA | FRED notes read; definition confirmed |
| PPIFIS | PPI – Producer Price Index | +1 | yoy | Index Nov 2009=100 | SA | no producer notes: convention |
| UNRATE | Unemployment Rate | -1 | level | Percent | SA | FRED notes read; definition confirmed |
| PAYEMS | NFP – Nonfarm Payrolls | +1 | yoy | Thousands of Persons | SA | FRED notes read; definition confirmed |
| ICSA | Initial Jobless Claims | -1 | level | Number | SA | FRED notes read; definition confirmed |
| AWHMAN | Average Weekly Hours, Manufacturing | +1 | level | Hours | SA | FRED notes read; definition confirmed |
| UEMPMEAN | Average Duration of Unemployment | -1 | level | Weeks | SA | no producer notes: convention |
| CCSA | Continuing Jobless Claims | -1 | level | Number | SA | FRED notes read; definition confirmed |
| TEMPHELPS | Temporary Help Services Employment | +1 | yoy | Thousands of Persons | SA | no producer notes: convention |
| JTSJOL | JOLTS Job Openings | +1 | yoy | Level in Thousands | SA | FRED notes read; definition confirmed |
| JTSQUR | JOLTS Quits Rate | +1 | level | Rate | SA | no producer notes: convention |
| FEDFUNDS | Policy Interest Rate | +1 | level | Percent | NSA | FRED notes read; definition confirmed |
| DGS2 | 2-Year Government Bond Yield | +1 | level | Percent | NSA | FRED notes read; definition confirmed |
| DFII10 | 10-Year Real Yield (TIPS) | +1 | level | Percent | NSA | FRED notes read; definition confirmed |
| T10Y3M | Yield Curve (10-Year minus 3-Month) | -1 | level | Percent | NSA | FRED notes read; definition confirmed |
| M2SL | Broad Money Supply (M2, M3) | -1 | yoy | Billions of Dollars | SA | FRED notes read; definition confirmed |
| WALCL | Central Bank Balance Sheet | -1 | yoy | Millions of U.S. Dollars | NSA | FRED notes read; definition confirmed |
| UMCSENT | Michigan Consumer Sentiment Index | +1 | level | Index 1966:Q1=100 | NSA | FRED notes read; definition confirmed |
| NFCI | NFCI – Chicago Fed National Financial Conditions Index | -1 | level | Index | NSA | producer states: positive = tighter than average |
| BAA10Y | Baa Corporate Bond Spread | -1 | level | Percent | NSA | FRED notes read; definition confirmed |
| STLFSI4 | STLFSI – St. Louis Fed Financial Stress Index | -1 | level | Index | NSA | FRED notes read; definition confirmed |

Checked by script against stored metadata: no percent change is taken of a rate or diffusion
index; no growth series is scored in nominal terms (rule 10); every `yoy` series is a quantity or
price index. Found: initial and continuing claims (`ICSA`, `CCSA`) were scored as levels; since 6 Nov 2026 they
are scored on their percent change over a year, as rule 22 requires. The WEI is not seasonally
adjusted at the source but is scored as published (it is scaled to GDP growth).

## 2. Modelling choices (not facts)

| Choice | Where | Status |
|---|---|---|
| Hot inflation counts as *strength* in the Inflation pillar, tight policy as strength in Policy: each pillar "supports the currency" | `scorecard_catalog.py` | Design choice: true when markets price hikes, wrong in stagflation. Unvalidated; stated in the methodology as an assumption |
| Every indicator has equal importance (1.0) | `ScoreSpec.importance` | **Known defect** (rule 21): replacement mechanism proposed in `private/scorecard-methodology.md`, awaiting QuFin approval |
| Scored against the series' own 10-year history, clipped at +-3, flipped where higher is weaker | `scorecard.py` | Design choice |
| Each indicator is level plus 3-month momentum, averaged equally (`MOMENTUM_WEIGHT` 0.5) | `scorecard.py` | Design choice; bias gate only proves no look-ahead bias |
| Timeliness weight halves every 60 days of delay | `freshness.py` | Design choice |
| Currencies, 2y and real yields, credit spreads, M2, commodity prices lead the cycle; central-bank rates, fiscal series and inventories lag | `cycle_classification.py` | Convention, reason per series in the file; arguable either way |
| Sign of quits, new home sales and temporary-help employment (higher = stronger) | `scorecard_catalog.py` | Convention: FRED carries no notes for them |

## 3. Business-cycle tags

The Conference Board classifies its own composite-index components. **Its component lists could not
be read from conference-board.org: the site blocks automated access and your own browser too (6 Nov
2026).** The lists below come from a search summary and the catalog's own header, so every
"Conference Board" basis is *unverified* until someone opens the Technical Notes PDF.

| Series | Name | Cycle | Basis |
|---|---|---|---|
| AWHMAN | Average Weekly Hours, Manufacturing | leading | Conference Board component (list unverified) |
| ICSA | Initial Jobless Claims | leading | Conference Board component (list unverified) |
| ACOGNO | Consumer Goods Orders | leading | Conference Board component (list unverified) |
| NEWORDER | Core Capital Goods Orders | leading | Conference Board component (list unverified) |
| NOCDFSA066MSFRBPHI | Philadelphia Fed New Orders Index | leading | Proxy for a Conference Board component: stands in for ISM new orders (licensed) |
| GACDISA066MSFRBNY | Empire State Manufacturing Index | leading | QuFin convention (not a Conference Board component) |
| BACTSAMFRBDAL | Dallas Fed Manufacturing Index | leading | QuFin convention (not a Conference Board component) |
| PERMIT | Building Permits | leading | Conference Board component (list unverified) |
| HOUST | Housing Starts | leading | QuFin convention (not a Conference Board component) |
| OECD_CCI_CHE, _SWE, _DNK, _CZE, _HUN, _KOR | CCI – Consumer Confidence (OECD, amplitude adjusted) | leading | OECD convention: published with its composite leading indicators; household expectations precede spending. Verified live and gap-free at the OECD, one series per request, 7 Nov 2026 (latest Aug 2026 for CH, Sep 2026 for the rest) |
| HSN1F | New Home Sales | leading | QuFin convention (not a Conference Board component) |
| TEMPHELPS | Temporary Help Services Employment | leading | QuFin convention (not a Conference Board component) |
| JTSJOL | JOLTS Job Openings | leading | QuFin convention (not a Conference Board component) |
| JTSQUR | JOLTS Quits Rate | leading | QuFin convention (not a Conference Board component) |
| T10YFF | 10-Year Yield minus Policy Rate | leading | Conference Board component (list unverified) |
| T10Y3M | Yield Curve (10-Year minus 3-Month) | leading | QuFin convention (not a Conference Board component) |
| NFCI | NFCI – Chicago Fed National Financial Conditions Index | leading | Proxy for a Conference Board component: stands in for the Leading Credit Index |
| STLFSI4 | STLFSI – St. Louis Fed Financial Stress Index | leading | QuFin convention (not a Conference Board component) |
| UMCSENT | Michigan Consumer Sentiment Index | leading | Proxy for a Conference Board component: stands in for average consumer expectations |
| GDPC1 | GDP – Real Gross Domestic Product | coincident | QuFin convention (not a Conference Board component) |
| WEI | WEI – Weekly Economic Index | coincident | QuFin convention (not a Conference Board component) |
| INDPRO | Industrial Production | coincident | Conference Board component (list unverified) |
| RRSFS | Real Retail Sales | coincident | Proxy for a Conference Board component: stands in for manufacturing and trade sales |
| W875RX1 | Real Personal Income excl. Transfers | coincident | Conference Board component (list unverified) |
| PCEC96 | PCE – Real Personal Consumption Expenditures | coincident | QuFin convention (not a Conference Board component) |
| PI | Personal Income | coincident | QuFin convention (not a Conference Board component) |
| PAYEMS | NFP – Nonfarm Payrolls | coincident | Conference Board component (list unverified) |
| UEMPMEAN | Average Duration of Unemployment | lagging | Conference Board component (list unverified) |
| UNRATE | Unemployment Rate | lagging | QuFin convention (not a Conference Board component) |
| CCSA | Continuing Jobless Claims | lagging | QuFin convention (not a Conference Board component) |
| ISRATIO | Inventories-to-Sales Ratio | lagging | Conference Board component (list unverified) |
| ULCMFG | ULC – Unit Labor Costs | lagging | Proxy for a Conference Board component: Conference Board uses nonfarm business; this is the manufacturing sector |
| CUSR0000SAS | Services CPI – Consumer Price Index, Services | lagging | Conference Board component (list unverified) |
| CPILFESL | Core CPI – Consumer Price Index ex Food and Energy | lagging | QuFin convention (not a Conference Board component) |
| BUSLOANS | C&I Loans – Commercial and Industrial Loans | lagging | Conference Board component (list unverified) |
| TOTALSL | Consumer Credit | lagging | Proxy for a Conference Board component: Conference Board uses installment credit to personal income; this is the level |
| CPIAUCSL | CPI – Consumer Price Index | lagging | QuFin convention (not a Conference Board component) |

The other 45 series are QuFin convention with a one-line reason each in
`app/data/cycle_classification.py`.

## 4. Source attributes set by hand

**EIA weekly petroleum series** (WCESTUS1, W_EPC0_SAX_YCUOK_MBBL, WCSSTUS1, WCRFPUS2, WPULEUS3, WGTSTUS1, WDISTUS1, WCRIMUS2, WCREXUS2, WRPUPUS2, WGFUPUS2, WDIUPUS2): QuFin labels all twelve *Not Seasonally Adjusted*.
EIA never marks any of them seasonally adjusted, but it also never states that they are not, so
the label is an **inference** (status: *unverified*). Units were checked on EIA's series pages.
EIA revises weekly figures only if substantive, in the next release (WPSR Appendix B), which is
why QuFin stores a changed value as a new vintage from the day it sees it.

EIA's definition of *product supplied*: Approximately represents consumption of petroleum products; 'implied' demand from disappearance out of the primary supply chain (WPSR Appendix B). Source: https://www.eia.gov/dnav/pet/TblDefs/pet_cons_wpsup_tbldef2.asp (also https://www.eia.gov/petroleum/supply/weekly/pdf/appendixb.pdf)
So the demand series labelled *Product Supplied* are implied demand, not measured sales.

Also set by hand and not independently checked: the Treasury series are labelled not seasonally
adjusted; ECB adjustment flags come from the series key (N or Y), which is the ECB's own code.

## 4a. Unit kind and currency (rule 23)

Every series records a unit kind and an ISO currency. **Derived:** read by `classify`
(`app/domain/units.py`) from the units the source itself states (FRED `units`, ECB UNIT and
UNIT_MULT, OECD measure, EIA and Treasury field definitions), at every ingest and in migration
0009's backfill. **Declared:** the reviewed table `app/data/series_units.py`, one row per catalog
series, first derived and then checked. The release check marks a series "review" when the two
disagree; a test fails on a missing or `unknown` declaration. On 7 Nov 2026 all 110 catalog series
derived to a known kind, matching their declarations.

| Judgement | Status | Basis |
|---|---|---|
| An unqualified "Dollars" is USD only for a US series; for any other country it is unknown | Design choice | The units text does not name the currency; never guessed |
| FRED "Rate" (JOLTS quits) is a percent rate | Verified | FRED notes: the quits rate is quits as a percent of employment |
| "Percentage change" (ECB HICP annual rate) is a percent rate | Verified | ECB UNIT; the series is published as a change (rule 13) |
| "Percent of GDP" is a ratio, not a rate | Design choice | A share of a denominator; compares only with other % of GDP |
| An FX rate "A to One B" is a price per unit in currency A | Verified | FRED H.10 units; e.g. CAD per USD for DEXCAUS |
| USD conversion uses only the seven catalogued FRED H.10 pairs: EUR, GBP, JPY, CAD, AUD, CHF and NZD | Verified | `DEXUSEU`, `DEXUSUK`, `DEXJPUS`, `DEXCAUS`, `DEXUSAL`, `DEXSZUS`, `DEXUSNZ`; each is already declared in the macro catalog |
| Inverse quotes are inverted per observation before averaging; monthly/quarterly flows are summed in native currency before applying the display-period average FX rate; stocks use the period-end rate | Design choice | Rule 23 and `app/domain/currency.py`; preserves the chosen aggregation order and avoids averaging an inverse quote incorrectly |
| Catalog currencies without one of those FX pairs are not converted or fetched implicitly; they return no converted points and are logged as Rule 37 gaps | Unverified | No eligible USD rate is catalogued for AED, ARS, BRL, CLP, CNY, COP, CZK, DKK, HUF, INR, MKD, MXN, MYR, NOK, PLN, SAR, SEK, SGD, TRY or ZAR; candidate sources have not yet been checked |
| Barrels, barrels per day, hours and weeks are `other` (physical or time units) | Design choice | The seven unit kinds have no physical-quantity kind |
| Same scale needs the same kind, currency and scale-free unit: real (chained or CPI-adjusted) dollars never beside nominal, $/barrel never beside $/gallon | Design choice | `comparable()`; rescaling millions to billions is allowed |
| An index shares a scale only with the same stated base; a plain "Index" (diffusion, standardised) never does | Design choice | Rebase or standardise first (rule 23 b, d) |
| A count shares a scale only when the units say what is counted ("Persons", "Units"); "Number" or "Thousands" never does | Design choice | Claims, home sales and job openings are not one quantity |

## 4b. Official reserves (P1-21)

| Judgement | Status | Basis |
|---|---|---|
| Reserves excluding gold (IMF RXF11_REVS) rather than total reserves, so gold price swings do not read as reserve changes | Design choice | Standard IFS "total reserves minus gold" |
| FRED's copies (TRESEG..M052N) are used where live: 12 economies, with ALFRED vintages; the IMF API only for the 9 FRED lacks | Verified | FRED API, 7 Nov 2026 (rule 17); no economy loaded twice |
| IMF values are in units of the currency; the SCALE attribute ("Millions") is a display hint and nothing is rescaled | Verified | UK July to September 2026: the IMF API value equals FRED's (millions) times one million exactly |
| FRED's unqualified "Dollars" is US dollars | Verified | FRED names every other currency ("Domestic Currency", "Canadian Dollars"); the IMF's UNIT for these series is USD |
| Left out: China (last June 2026) and Hong Kong (last February 2024) as behind schedule; the US (not a gauge of the dollar); the euro area (members report separately) | Verified | FRED and IMF API, 7 Nov 2026 |
| Reserves are coincident | Convention | They move with current balance-of-payments flows and central bank intervention |
| IMF release dates: the last weekday of the second month after each month | Design choice | No published dates; latest month on 7 Nov 2026 was September for most economies, August for the rest (rule 9: err late) |
| Name "Foreign Exchange Reserves" | Verified | Trading Economics page title; FRED's "Reserves Excluding Gold" in the official title |

## 4c. Employment Cost Index (BLS)

| Judgement | Status | Basis |
|---|---|---|
| The Employment Cost Index (total compensation, civilian workers, SA, index Dec 2005=100) comes from FRED as `ECIALLCIV` only | Verified | FRED page, 12 Nov 2026: Seasonally Adjusted, Quarterly, Index Dec 2005=100; ingest loaded 149 vintage rows to 2026 Q3. BLS id `CIS1010000000000I` (BLS API v2: 2026 Q3 = 178.574) was removed as a duplicate (Rule H). The earlier note "not on FRED" (7 Nov 2026) was wrong |
| JOLTS job openings come from FRED (`JTSJOL`) only | Verified | The BLS series `JTS000000000000000JOL` carried the same values as `JTSJOL`; `check-data` flagged the duplicate (rule 16) and the BLS copy was removed |
| ECI release dates: 125 days after the first day of the quarter | Design choice | The API serves no release dates; BLS releases ECI near the end of the month after the quarter (about 90 to 120 days after the quarter's first day); 125 days errs late (rule 9) |
| ECI is a lagging indicator | Convention | Wages and benefits follow price inflation with a lag |
| Name "ECI – Employment Cost Index" | Unverified | Not checked against FRED, Trading Economics or the Forex Factory calendar as rule 18 asks |

## 4d. BIS series (P1-22)

| Judgement | Status | Basis |
|---|---|---|
| Policy rates (`WS_CBPOL`, monthly) are the rate at the end of the month | Verified | BIS series title "Monthly - End of period"; the series notes state the instrument for each bank (for Japan, the target for the uncollateralised overnight call rate) |
| Effective exchange rates (`WS_EER`) are monthly averages, broad basket of 64 economies, 2020=100, nominal and real | Verified | BIS attributes COLLECTION "Average of observations through period", TITLE_TS "Broad (64 economies)", UNIT_MEASURE "Index, 2020 = 100"; the load fails if the units text changes |
| BIS effective exchange rates are the same series FRED republishes (RBGBBIS, NBGBBIS, RBXMBIS) | Verified | UK July 2026: FRED 112.04 and BIS 112.24 (real), 111.75 and 111.74 (nominal); euro area 102.55 and 102.53. The small differences are BIS revisions since FRED's last update |
| FRED's BIS copies are stale, so the BIS API is read directly (non-US only, rule 17) | Verified | FRED to July 2026 and the BIS API to September 2026 on 12 Nov 2026; FRED's UK credit-to-GDP ends 2025 Q4, BIS 2026 Q1 |
| The US is left out: FRED carries the dollar indexes and credit with vintages; the euro area is left out of policy rates (ECB deposit rate stored, rule 16); Russia is left out (BIS has had no Russian official data since 28 Feb 2022; coverage list undecided); Singapore and the UAE have no BIS policy rate, the UAE no credit series | Verified | BIS API, 12 Nov 2026; BIS legal page |
| Credit-to-GDP ratio is private non-financial sector credit from all lenders, as percent of GDP; the gap is actual minus trend, in the same units | Unverified | The API's dimension labels say so (TC_BORROWERS "Private non-financial sector", TC_LENDERS "All sectors", CG_DTYPE A and C) but states no unit attribute. FRED's break-adjusted copy differs by about 1% for the UK (132.6 against 131.3 in 2025 Q4): close, not the same variant |
| The credit-to-GDP trend uses a one-sided (backward-looking) HP filter, so the gap is not rewritten by later data | Verified | BIS credit gap statistics page (data.bis.org/topics/CREDIT_GAPS, 12 Nov 2026); revisions of the underlying credit data still become new vintages |
| Dimensions: policy rates and credit in "policy", effective exchange rates in "external" | Design choice | None is scored; revisit when the scorecard moves to eight pillars (ADR 0005) |
| Cycle: policy rates and credit ratio lagging; effective exchange rates and the credit gap leading | Convention | `app/data/cycle_classification.py` gives the reasons; the gap's lead is the BIS's finding for financial stress, not for output |
| Change kinds: rates and credit measures in points, effective exchange rates in percent | Design choice | Rule 22: rates and ratios in points; indexes that stay positive in percent |
| Japan's policy rate has no value for April 2001 to February 2006 and May 2013 to August 2016; nothing else may be missing | Verified | BIS notes "from 4 Apr 2013 to 20 Sep 2016: no policy rate"; the 2001 to 2006 gap is the BIS's own (no values published), reason not stated. Any other gap fails the load (`KNOWN_GAPS`) |
| Release dates: last weekday of the following month (monthly), of the sixth month after the quarter (credit) | Design choice | No dates in the API; the BIS release calendar (2023 onwards) is never earlier than the rule, which is tested against all 73 listed dates (rule 9: err late) |
| Request volume stays well inside any sensible limit; we identify ourselves and stop when refused | Design choice | The BIS publishes no numeric rate limit (terms: it "may limit access"). One run is 5 requests, 1 s apart, with a QuFin `User-Agent`; 429 and 5xx retry with the server's `Retry-After`; a 403 or 429 that outlasts the retries stops the rest of the run. Runs must stay scheduled at most daily |
| BIS licence: free use if cited, not misleading, no extra charge to users, no advice | Verified | https://data.bis.org/help/legal, 12 Nov 2026; recorded in the catalog `licence_note` and `docs/licence-register.md` |
| Names "NEER" and "REER" | Unverified | Standard acronyms and FRED's titles (`docs/indicator-names.md`); Trading Economics and Forex Factory not checked as rule 18 asks |

## 4e. Supplier limits (rule 28)

| Judgement | Status | Basis |
|---|---|---|
| The gaps between requests (`min_interval`) keep every connector below its supplier's stated limit | Verified for BLS, EIA, BIS terms; **Unverified** for FRED, OECD, ECB, IMF, Treasury, CFTC | Table in `docs/data-connections.md` section 2b: FRED, Treasury and CFTC state no number, OECD and ECB pages could not be read on 12 Nov 2026 |
| A 403 or 429 means "stop for this run" | Design choice | Rule 28; a one-off 403 on a single series therefore also stops the rest of that run, which is the safer failure |
| Treasury page size 10,000 and CFTC page size 5,000 are accepted by the suppliers | Unverified | Both load today; neither supplier's page states a maximum |

## 4f. Canonical taxonomy and calendar (ADR 0007)

| Judgement | Status | Basis |
|---|---|---|
| Each series' pillar: its concept's override, else its old dimension (listed in `app/data/taxonomy.py`) | Design choice | Surveys, consumption, financial conditions, the dollar and the employment cost index were filed under the wrong dimension; the overrides move them. Not scored |
| A vintage dated D is known from D+1 (UTC) when a timestamp is asked for | Design choice | Vintages carry dates, not times; a timestamp on D could precede the release (rule 9: err late) |
| The euro area is coded `EMU` | Design choice | ISO has no code for it; the IMF and OECD treat it as an aggregate |
| G7, G20 and GCC flags | Verified, G20 per the G20 website | G20 follows the state participants shown on g20.org on 12 Nov 2026 (owner's screenshot): Argentina, Australia, Brazil, Canada, China, France, Germany, India, Indonesia, Italy, Japan, Mexico, **Poland**, Russia, Saudi Arabia, South Korea, Türkiye, the United Kingdom and the United States. **South Africa is not shown and Poland is**, so the flags follow the site; the EU Council's Nov 2025 summit pages still list South Africa as a member, so this is the current participant list (2026 presidency), not a change in the founding membership. The screenshot was cropped below the United States, so the EU and African Union entries were not seen and the euro-area flag is kept from the Council pages. G7 and GCC memberships are stable public facts |
| The emerging-market flag is "not an IMF advanced economy" | Verified | IMF World Economic Outlook, April 2026, Statistical Appendix, Table B lists the advanced economies (Korea, Czech Republic, Singapore, Hong Kong SAR, Denmark, Sweden, Switzerland, New Zealand, Norway, Australia, the G7 and the euro area among them); every other economy is emerging or developing by the IMF's own definition. Hungary, Poland, China, India, Mexico, Brazil, Türkiye, South Africa, Argentina, Indonesia, Russia and the Gulf states are therefore flagged emerging. The IMF says its classification "is not based on strict criteria" and changes over time: re-read it each April and October |
| Currency per country | Verified | ISO 4217 list one, published 17 Sep 2026 by SIX (the maintenance agency) |
| Central bank per country | Verified for 31 of 34 | The BIS member central banks page (bis.org/about/member_cb.htm, read 12 Nov 2026) gives the official name; Germany, France and Italy show their national central banks (Eurosystem members), the euro area shows the ECB. Qatar Central Bank, Central Bank of Bahrain and Central Bank of Oman are not BIS members: their names come from secondary sources (a central-bank directory and the Arab Monetary Fund governors list), not their own sites |
| OECD amplitude adjustment (`AA`) and working-day adjustment (`SWDA`) keep their own codes | Design choice | They are not plain seasonal adjustment |
| The first print is the calendar's "actual" | Design choice | A later revision is a vintage, not the release figure a consensus is compared with |
| Daily series are left out of the calendar | Design choice | Rates and prices are not scheduled releases |
| Calendar release dates are the stored first-publication dates; scheduled ones use the usual lag | Design choice | Rule 9: derived, erring late; the time of day is empty until recorded |
| Consensus and surprise | Not available | Trading Economics and Forex Factory consensus is proprietary and may not be scraped (rule 28); needs a licensed feed |
| The surprise score is standardised by the spread of that series' own past surprises, from at least 8 | Design choice | Needs consensus history; empty otherwise |

## 4g. Publishers and comparable scales (ADR 0007)

| Judgement | Status | Basis |
|---|---|---|
| `source_name` keeps the producer's wording; `publisher` is the one canonical organisation | Design choice | The same organisation was stored under spellings that differ by a qualifier or punctuation (the IMF, the OECD, the Treasury, the Federal Reserve Board); counts, filters and licence lookups by publisher would split. Aliases are in `app/data/publishers.py` |
| One concept across countries is by design, even where the national series differ (rules 18 and 19) | Rule | A concept is the indicator, not one national series: consumer prices are "CPI" in every country, consumer confidence is "CCI" |
| Five concepts mix scales as stored: consumer prices and core consumer prices (US index level against the euro area's annual rate), consumer confidence (Michigan 1966:Q1=100 against the OECD's long-term average = 100), the leading index (the US series' unit text omits the OECD base) and money supply (dollars against euro) | Verified | Read from the stored units of every series; declared with the basis countries are compared on in `COMPARED_AS` (`app/data/indicator_concepts.py`) |
| The US leading index is the same OECD amplitude-adjusted indicator as the other countries' | Verified | FRED's title for `USALOLITOAASTSAM` says "Amplitude Adjusted"; only its unit text omits the base |
| A concept that mixes scales and is not declared fails `check-data` | Design choice | A country added later with a different scale (the World Bank and central-bank batches, P1-23 and P1-24) cannot pass unnoticed (rule 23) |
| The by-indicator view must compare on the declared basis, never on the stored values of a concept with `sameScale: false` | Design choice | `/v1/macro/indicators` returns `sameScale`, `scaleNote` and `comparedAs` for each indicator |

## 4h. Country comparison: consumer prices and unemployment (P1-23)

| Judgement | Status | Basis |
|---|---|---|
| Countries are compared on year-on-year change (prices) and on the unemployment rate, never on index levels or head counts | Design choice | `app/domain/comparison.py`; `/v1/macro/compare/{concept}`. A concept without a basis in `BASES` is refused (404) |
| The US price index is converted to its year-on-year change from the seasonally adjusted index (`CPIAUCSL`); the others are published as annual rates | Verified | The IMF's own US figure for Sept 2026 is 3.74%; the conversion gives 3.72%. The 0.02-point gap is seasonal adjustment (the IMF series is not seasonally adjusted) |
| IMF consumer prices are each country's national all-items CPI as its statistics office publishes it, not a harmonised index | Verified (dataflow key), not compared with national releases | Key `<ISO3>.CPI._T.YOY_PCH_PA_PT.M`. Definitions differ at the margin (housing, baskets); euro area members' HICP is not used, so Germany's figure is the national CPI |
| OECD unemployment is the ILO definition, ages 15 and over, both sexes, seasonally adjusted | Verified | Key `<ISO3>.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M`; Germany Sept 2026: 4.1% |
| Coverage: 29 countries for prices, 15 for unemployment; the rest are listed on the page as not compared yet | Verified 12 Nov 2026 | New Zealand (quarterly CPI, IMF answers 400), Qatar and the UAE (latest 2025) and Kuwait (June 2026, overdue) are out for prices; the UK (July 2026, overdue) and the 17 countries the OECD does not publish monthly are out for unemployment. Nothing is filled with annual or estimated figures (rule 1) |
| Australia's monthly CPI has 17 months of history | Verified | Monthly CPI began in late 2024; shorter than the 10 years a z-score needs, so it cannot be scored yet |
| The US unemployment change over 12 months is empty for October 2026 | Verified | October 2025 has no value: the BLS did not publish it |
| Request limits of the IMF CPI dataflow and the OECD labour-force flow | Not verified | No limit is published for either; the connectors pace themselves (IMF 1 s, OECD 3 s) and stop on a 403 or 429 (rule 28) |
| Release dates of both flows are derived, erring late | Design choice | Neither API serves release dates (rule 9) |
| FRED's copies of these series were not compared with the direct feeds | Not verified | Rule 17 applies to the US; the other countries are read directly as for the BIS |

## 5. Known mismatches between a series and its textbook definition

- Unit labour costs (`ULCMFG`) is the manufacturing sector; the Conference Board uses nonfarm business.
- Consumer credit (`TOTALSL`) is the level; the Conference Board uses installment credit to personal income.
- Consumer sentiment (`UMCSENT`) is not the Conference Board's consumer expectations.
- The Philadelphia Fed new-orders index and the NFCI stand in for licensed or unavailable components.
- Richmond and Kansas City regional surveys are not on FRED (gap, not loaded).

## 6. Not covered by this audit

- The one-line plain-English explanations of each concept were written by QuFin and not compared line by line with a producer's text.
- Which pillar each series feeds and its importance beyond the sign (see section 2).
- Non-US series beyond the euro area, the BIS, OECD indices, reserves, consumer prices and unemployment: audit each when added.
- Licence status of every source (`docs/licence-register.md` tracks it; several are still *to confirm*).

All five pillars count equally in the overall score (weighted only by confidence): interim, same status as the indicator weights.

## 4i. Comparison studio: frequency harmonisation and PoC (Rules D-G)

| Judgement | Status | Basis |
|---|---|---|
| Compared series are shown at the lowest frequency they share; nothing is up-sampled | Rule D | `app/domain/harmonize.py`, `tests/test_harmonize.py` |
| Down-sampling: stocks and levels at period end, rates, ratios and indexes as the period average, flows as the period sum | Judgement | By unit kind; flows are the listed concepts `FLOW_CONCEPTS` (jobless claims, trade balance, budget balance, interest expense, current account). Seasonally adjusted annual rate series (housing starts, retail sales) are averaged, because summing a monthly annual rate is wrong. The rule applied is returned on every series |
| An unfinished period (a month with three of four weeks) is dropped, never shown as a full period | Judgement | `aggregate` checks that every monthly or quarterly member is present and that the last weekly or daily observation falls within a week (four days for daily) of the period's end |
| PoC is the change from the previous display period (week, month, quarter, half-year or year, per the chosen frequency); a rate or spread changes in points; a series published as a change is shown as published; a zero or negative base gives no percent change | Rules 13, 22, E | `poc()`; basis-point output is not offered, points are shown as `pp` |
| `SA` is a source adjustment text starting "Seasonally"; `NSA` is "Not Seasonally"; anything else (OECD amplitude adjusted) is `OTHER` and never called seasonally adjusted | Rule B | `adjustment_tag` |
| `last_vintage` is the release date of the latest published value of any period, not a revision count | Rule C | Taken from the stored vintages |
| Actual values of different unit kinds are returned with a notice rather than refused | Judgement | Uses the rule 23 unit check |
| The 10-country cap is enforced by the API for countries and for series in an overlay | Rule F | `MAX_COUNTRIES` |


## 4j. Coverage-gap sprints: Germany, France, Italy, Kuwait, Qatar, the UK, housing (13 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The v3 workbook's FRED industrial production (`*PROINDMISMEI`) and core CPI (`*CPICORMINMEI`) are not loaded | Verified | FRED to March 2024 and March 2025 (June 2021 for Japan core): the OECD MEI copies are frozen. Another source is needed (OECD SDMX flows were not probed) |
| UK real GDP `CLVMNACSCAB1GQUK` is not loaded | Verified | FRED marks it DISCONTINUED (last 2020 Q3); the ONS `ABMI` (chained volume level, SA) replaces it. The workbook's `IHYQ` (quarter-on-quarter growth) is derived exactly from `ABMI`, so it is not stored as well (rule 16) |
| UK unemployment from the ONS (`MGSX`, 16 and over, SA, three-month window dated by its last month), not FRED or the OECD | Verified | FRED `LRHUTTTTGBM156S` is SA with vintages but ended June 2026 (updated 15 Oct 2026) and the OECD copy was overdue on 12 Nov 2026; the ONS has July 2026 and the release check passes it |
| UK core CPI is the ONS 12-month rate excluding energy, food, alcohol and tobacco (`DKO8`) | Verified | Series title read from the ONS; published as a change, so never changed again (rule 13) |
| ONS values have no vintages, so each period is dated by a late-erring rule (`ons_calendar.py`) | Unverified | Exact ONS release dates per past period were not read; a UK backtest is conservative, not exact |
| Real GDP of Germany, France, Italy, Japan, Canada is from FRED (`CLVMNACSCAB1GQ{DE,FR,IT}`, `JPNRGDPEXP`, `NGDPRSAXDCCAQ`), SA with vintages | Verified | FRED metadata, 13 Nov 2026; each in its own currency, so compared as growth (`COMPARED_AS`); the US series is an annual-rate level |
| Goods trade balance of Germany, France, Italy, Japan and Canada is a new concept, `merchandise_trade_balance`, in US dollars | Verified | FRED `XTNTVA01{DE,FR,IT,JP,CA}M667S` are goods only (OECD, exchange-rate converted); the US `BOPGSTB` is goods and services, so it is a different concept and not compared with these. The UK series `XTNTVA01GBM667S` was loaded and then removed: it fell overdue on 13 Nov 2026 (FRED posts the OECD's UK figures every second month); replaced by the ONS series `ONS_BOKI` (section 4l) |
| Germany, France and Italy get no policy rate | Verified | The BIS has none for them (the ECB rate, stored for the euro area, applies); effective exchange rates, credit and credit gap are loaded per country |
| Kuwait has a BIS policy rate and IMF reserves; Qatar has IMF reserves only | Verified | BIS policy rate to October 2026 for Kuwait, none for Qatar; IMF reserves to September (Kuwait) and August 2026 (Qatar). Their CPI stays out: Kuwait to June 2026 (overdue), Qatar to August 2025 |
| Residential property prices: BIS nominal index (2010 = 100), 25 economies; the HOUSING pillar is stored and shown, not scored; cycle "leading" (rate-sensitive) | Judgement | Pillar and cycle are QuFin's classification (`cycle_classification.py`). Japan left out: 2025 Q4 against 2026 Q2 for all others, failed the release check. Russia left out (BIS stopped receiving its official data) |
| The US property price index is read from the BIS, not FRED | Verified | FRED's copy `QUSN628BIS` (NSA, with vintages) ended 2026 Q1 while the BIS had 2026 Q2 (13 Nov 2026) |
| Rule I: every series starts in 1990 (extended to the 297 earlier series on 13 Nov 2026) | Verified | Each source was reloaded from 1990-01-01; a series starts later only where its source does (for example FRED GDP 1991 for Germany and 1994 for Japan, the BIS policy rate for the Czech Republic and China, Australian CPI). The BIS has no Japanese policy rate for March 1999 to July 2000, added to the known gaps |
| Not loaded for want of a source: unemployment for Brazil, South Africa, China, India, Saudi Arabia, Singapore; trade balance for Australia and Korea; industrial production and core CPI for the G7 | Gap | No keyless monthly source found; needs a decision on national sources |

## 4k. Rules J to N: where the code stands (13 Nov 2026)

The rules are adopted; the code does not meet them yet. Each line says what is true today.

| Rule | Status today | Gap |
|---|---|---|
| J: 85 countries, 169 indicators | **87 countries in the taxonomy** (85 plus Chile and Colombia); 83 have stored series; 621 series | The 169-indicator taxonomy is not in the catalog; no automatic cross-country sweep exists (the new countries were filled by hand-chosen IMF, World Bank, Eurostat and FRED series); the 50 new countries' attributes are unverified |
| K: highest frequency first | Partly: ECB policy rate daily, US claims weekly. BIS policy rates and effective exchange rates are monthly for countries whose central banks publish daily | No audit of every series against the highest frequency its source offers; no hourly series |
| L: release time and retry ladder | `HttpSource` retries 3 times (2, 4, 8 seconds), honours `Retry-After`, stops after a 403 or 429 (rule 28) | No jitter and no 15 second to 1 hour ladder; no per-series `next_release_at` column (`macro_status` derives it); no scheduler |
| M: FRED first, authentic fallbacks | In force for the US and UK (ONS). Industrial production and core CPI for the G7 are not loaded | Eurostat SDMX, World Bank and the national portals (StatCan, ABS, e-Stat, KOSIS, INEGI, CBRT, GASTAT, Stats SA, NBS) have no connector |
| N: QuFin Doctor | **Built:** `doctor [--fix] [--quick]` checks orphaned vintages, non-finite values, vintage date order and overlap, SA/NSA tags and canonical codes, duplicate country-indicator pairs, stale and missing series, frozen or overdue series, and the 85-country taxonomy; one summary line after every ingest | Not yet run in continuous integration; quarantine of a frozen series is a recommendation (take it out of the catalog), not an automatic step |
| O: three-tier cascade | Tiers 1 and 2 are in use; **tier 3 registry exists** (`country_sources.py`, 23 portals plus ECB, UNECE, WTO) and three national portals are connected: the UK ONS, the Brazilian central bank and SingStat; `doctor --gaps` lists every unpopulated pair with its tier 3 portal | Terms of every portal but the ONS are unread; no other national connector; the 2 countries without data (Isle of Man, Liechtenstein) and the pairs left out for want of a source (Korea trade balance, G7 unemployment for Brazil, South Africa, China, India, Saudi Arabia, Singapore) are not yet listed with the tiers checked |


## 4l. 85-country expansion, doctor, Eurostat and World Bank (13 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The 50 added countries' currency, central bank and emerging-market flag | **Unverified** | Written from general knowledge, not read at each central bank or the IMF (WEO Table B). Bulgaria is entered as euro (adopted 1 Jan 2026); Kosovo uses ISO-like code XKX (the World Bank's) and XK; North Macedonia's name follows the official name, the workbook says "Macedonia"; Andorra, Faroe Islands, Isle of Man, Liechtenstein, Monaco have no central bank of their own and say so; their `em` flag is false by default |
| Every one of the 85 countries has data | **Not met: 2 countries** | Liechtenstein has no current series from the IMF or the World Bank (its only World Bank figure is a 2015 GDP) and the Isle of Man has real GDP to 2023 only, which fails the release check: both need a national source. The other 83 have live series |
| IMF monthly CPI and reserves for the new economies | Verified | Probed live 13 Nov 2026, one series per request; those not current were left out: CPI for Cambodia (April 2026), Cameroon (February 2026), Serbia (December 2025), Malta (loaded, failed the release check); reserves for Bosnia (March 2025), Cameroon and Congo (December 2024), Montenegro (December 2025), Venezuela (June 2018), Iran (none). The IMF has no series for Andorra, Faroe Islands, Isle of Man, Kosovo, Liechtenstein, Monaco and North Korea |
| Spain's reserves come from FRED (`TRESEGESM052N`), not the IMF | Verified | FRED carries it to September 2026 (rule 17); no other new economy has a FRED reserves series |
| Real GDP growth is not stored beside real GDP | Judgement | Rule 16: growth is derived exactly from the level; the comparison studio computes the year-on-year change |
| World Bank consumer prices and reserves are not taken | Judgement | The IMF has monthly CPI for most (rule K) and a second copy would be a duplicate (rule 16); the World Bank's total reserves include gold, the IMF series does not |
| World Bank unemployment is an annual modelled ILO estimate | Judgement | Used only where no monthly series exists; for the 19 EU members Eurostat's monthly series replaced it (rule K) |
| World Bank values are dated 31 December of the following year | Unverified | The World Bank gives no release date per value; a rule that is never early, so a backtest is conservative |
| UK goods trade balance is the ONS `BOKI` (£ millions, SA, to September 2026) | Verified | Series title read at the ONS; released 12 Nov 2026; replaces the FRED mirror that went overdue; compared against the dollar series by standardising (`COMPARED_AS`) |
| Industrial production and core CPI for the euro area, Germany, France, Italy are from Eurostat | Verified | Production to September 2026 from 1990; core HICP (dataset `prc_hicp_minr`, annual rate) to October 2026 from 1997; the old dataset `prc_hicp_midx` ends in December 2025 and FRED's mirrors are frozen. The euro area core HICP is already stored from the ECB, so Eurostat supplies Germany, France and Italy only (rule 16) |
| Industrial production for the euro area uses the 21-member aggregate (`EA21`) | Judgement | Bulgaria joined on 1 Jan 2026; Eurostat's `EA21` is the current composition, back-cast; the ECB's HICP series stored for the euro area is `U2` (changing composition) |
| Australia's goods trade balance is FRED `XTNTVA01AUM667S`; Korea's is not loaded | Verified | FRED to August 2026 for Australia; `XTNTVA01KRM667S` stopped in December 2024 |
| Japanese policy rate has no value for March 1999 to July 2000 | Verified | The BIS API (13 Nov 2026); added to the known gaps |
| The Eurostat API was announced unavailable on Friday 13 November 14:00 to 23:00 | Noted | If a Eurostat load failed on that day, rerun it |


## 4m. Tier 3 registry, national-portal series and fail-fast log (13 Nov 2026)

Each probe was one attempt (no retry loops). Tiers checked are named for every miss (Rule O).

| Judgement | Status | Basis |
|---|---|---|
| `app/data/country_sources.py` registers the 23 national portals and the ECB, UNECE and WTO | Done | Written from general knowledge on 13 Nov 2026, no browsing. Its `terms_checked` date is set only for the ONS, whose terms were read (the brief asked for 2026-11-13 on all entries: not done, because no other terms were read); `endpoint_verified` is set for the ONS, the BCB and SingStat, which were called live |
| Free-key portals and their `.env` names | Listed | `QUFIN_INSEE_API_KEY`, `QUFIN_BDF_API_KEY`, `QUFIN_DESTATIS_API_KEY`, `QUFIN_ESTAT_APP_ID`, `QUFIN_INEGI_TOKEN`, `QUFIN_BANXICO_TOKEN`, `QUFIN_KOSIS_API_KEY`, `QUFIN_ECOS_API_KEY`, `QUFIN_EVDS_API_KEY`, `QUFIN_MAS_API_KEY`, `QUFIN_STATSNZ_API_KEY`, `QUFIN_BCCH_API_KEY`, `QUFIN_WTO_API_KEY`; the US keys `QUFIN_BLS_API_KEY`, `QUFIN_BEA_API_KEY` and `QUFIN_FRED_API_KEY` exist. The names are QuFin's own; the registration pages were not looked up |
| South Africa quarterly unemployment from FRED `LRUNTTTTZAQ156S` | Verified | SA, 2000 Q3 to 2026 Q2, updated 15 Oct 2026; monthly does not exist (tiers 1 checked) |
| Brazil unemployment (BCB SGS 24369) and goods trade balance (22707) | Verified | Both to September 2026. 24369 starts in 2012: windows before it answer 404 "Value(s) not found", handled as empty. Neither is seasonally adjusted. FRED has no Brazilian unemployment; the OECD has no monthly series (tiers 1 and 2 checked on 13 Nov 2026) |
| Singapore unemployment from SingStat table M182342, series 1 | Verified | Called "Total Unemployment Rate, (SA)" in the table, not "Overall" as in the brief; quarterly, 1992 1Q to 2026 3Q. The terms were not read |
| Eurostat monthly unemployment (`une_rt_m`, SA, total, percent of labour force) for 19 EU members | Verified | Replaces the World Bank's annual figure for Austria, Belgium, Bulgaria, Croatia, Cyprus, Estonia, Finland, Greece (Eurostat code EL), Ireland, Latvia, Lithuania, Luxembourg, Malta, the Netherlands, Portugal, Romania, Slovakia, Slovenia and Spain (rule K, rule M); the 19 World Bank series were removed |
| Bulgaria and Malta monthly unemployment from Eurostat | Resolved 15 Nov 2026 | Both loads answered HTTP 307 on 13 Nov 2026, the day Eurostat announced a maintenance window (14:00 to 23:00); not retried then (fail fast). On 14 Nov both endpoints answered 200 with no redirect and both series loaded (321 months, to September 2026). Their World Bank annual unemployment was removed. `base.py` still does not follow redirects, on purpose: a followed redirect can carry an API key to another host and skips the pacing and refusal checks |
| Switzerland monthly unemployment | Not available | OECD answered 404 on 13 Nov 2026 (tier 2). Tier 1 (FRED) not probed; tier 3 (Swiss Federal Statistical Office) registered, terms unread |
| Chile and Colombia are in the taxonomy (87 countries) | Done | Added at the owner's request beyond the 85-country list; currency, central bank and emerging-market flag unverified like the other 50. The policy rates come from the BIS (`BIS_CBPOL_CL` to October 2026, from 1997; `BIS_CBPOL_CO` from 1995) and monthly unemployment from the OECD (Chile to August 2026 from 1990, Colombia to September 2026 from 2007). Their CPI was not asked for and is not loaded |

## 4n. BIS: thirteen further measures (17 Nov 2026)

One request per measure, paced at one second, no refusal. Each key, area list, unit and release lag
was read live first: see `docs/bis-probe-2026-11-17.md`.

| Judgement | Status | Basis |
|---|---|---|
| Use the keyed API for every flow, no bulk reader | Decided | A keyed request is under 1 MB even for the two debt flows whose bulk files are 62.6 and 147 MB; the connector already pages by measure, keeps the raw response and stops on 403 or 429. A reader would add a second ingestion path for no series |
| 385 series added, from 1990 or the BIS's first period | Verified | Household credit 41 economies, government credit 28, debt service ratios 29 / 16 / 16, US-dollar credit to non-banks 11, central bank total assets 45, international debt securities 68, debt securities issued by government 42, non-financial corporations 38 and financial corporations 41, commercial property 7, consumer prices 3. `check-data` after loading: all 385 on schedule |
| Credit to the non-financial sector (total) and to non-financial corporations are not stored | Judgement | Total = private (stored as the credit-to-GDP ratio) + government; corporations = private - households. Both are exactly derivable (rule 16), recorded in `REDUNDANT`. The identities hold only if the credit-gap flow and `WS_TC` share a valuation basis, which was not compared |
| Debt service ratios: private, household and corporate are three indicators | Judgement | A ratio of sums is not a sum of ratios, so none is derivable from the others |
| Central bank total assets are the quarterly series, not monthly | Deviation | The monthly series loaded first and 33 of 48 were marked overdue on 17 Nov: the BIS releases months in March, June, September and December batches, and the release check expects a monthly series monthly. Widening the grace period is not allowed (rule 2), so the quarterly series, which has the BIS's own cadence and reaches 2026 Q2, replaced it. Rule K (highest frequency) is not met for these |
| Central bank total assets join `central_bank_balance_sheet` | Done | Same concept as the Fed's `WALCL` (rule 19), compared as year-on-year change because the amounts are in different currencies (`COMPARED_AS`). The euro area's own ECB balance sheet was not checked for a duplicate |
| International debt securities and debt service ratio units are not published by the BIS | Unverified | No unit attribute in the response. Millions of US dollars (US total 3,104,204 = $3.1 trillion) and percent of income follow the BIS's descriptions; a changed unit would not be caught by the load |
| Commercial property: one series per economy, mixed property types and coverage | Judgement | Seven economies (Germany, Spain, Indonesia's big cities, the Netherlands' offices, Saudi Arabia's retail, Slovenia's and Turkey's offices and retail). Compared as year-on-year change (`COMPARED_AS`). Japan ends two quarters early, Greece is half-yearly, Poland and Portugal annual |
| The United States is left to FRED for every new measure | Resolved for commercial property, otherwise open | Rule 17 was replaced by rule P on 18 Nov 2026: FRED is not preferred for being FRED. US commercial property now comes from the BIS (section 4s). A US debt service ratio and total credit remain unmeasured |
| Consumer prices only for economies no other source covers | Done | New Zealand, Malta and Serbia (monthly, year-on-year, from 1990 or 2007). The IMF came first (rule 16): Chile (442 months) and Colombia (441) loaded from it the same day. Kuwait's BIS series ends in June 2026 and was marked overdue, so it is out. Not in the BIS: Andorra, Cambodia, Cameroon, the Faroe Islands, the Isle of Man, Kosovo, Liechtenstein, Monaco, North Korea, Qatar; the UAE ends in December 2025 |
| Economies with a gap or a stale series are left out | Done | International debt securities: Oman, Congo, Kuwait, Kenya, Liechtenstein, Cambodia, Nigeria (missing quarters), Moldova (ends 2002), Iran (ends 2009). Corporate debt securities: Lithuania, Latvia. Central bank assets: Israel, Indonesia, South Korea (a quarter late), Kuwait (missing quarters) |
| CPMI payments and FMIs | Not requested | Annual, eight tables, not a market indicator; the owner declined it |
| Release dates are derived from the BIS calendar dataflow | Verified | `BIS_REL_CAL`, with dates into 2027, gave the lags used; two new rules in `bis_calendar.py` (`cbta_release`, `cpi_release`), tested |
| Eight older series and two oil series went overdue on 17 Nov | Open | The IMF reserves for Austria, Brunei, Ghana and Uzbekistan, the IMF consumer prices for India, Moldova and Portugal and ONS UK unemployment had no new release; the two FRED oil series (`DCOILWTICO`, `DCOILBRENTEU`) were a few days late and loaded on a refresh the same day |

## 4o. Coverage matrix generated from the database (17 Nov 2026)

`uv run python -m app.cli coverage-matrix --out FILE` replaces the hand-made seed CSV
(`coverage_matrix_seed.csv`, 15 Nov 2026). The seed matched the database exactly on that day (629 of
629 held cells) but could not be used to decide what to ingest next.

| Judgement | Status | Basis |
|---|---|---|
| A gap is only counted where the indicator can exist for the country | Done | Each indicator has a scope from the catalog: `global` (declared for two or more countries), `country_specific` (one country: US jobless claims, JOLTS, Empire State), `commodity` (EIA weekly petroleum supply and demand), `market` (currency pairs, WTI, Brent, Henry Hub). 46 + 12 + 10 of the 99 indicators are not global; their cells for other countries are `NOT_APPLICABLE`. The seed marked 5,712 of its 6,851 gaps (83%) as gaps that are not |
| Coverage is held over global indicators only | Done | 940 usable of 2,697 cells (35%) on 17 Nov 2026, against 8% of the whole grid |
| Source, frequency, first and last period, pillar are per cell, read from the stored series | Done | The seed copied one value to every cell of a concept (Albania's unemployment read "bcb, eurostat, fred, oecd, ons, singstat, worldbank" and "Annual, Monthly, Quarterly"; it is World Bank, annual). Rule K needs the real frequency per cell |
| `OVERDUE` and `NOT_LOADED` are separate from `GAP` | Done | Eight stored series are past their release (usable = false, rule 3); a series declared in the catalog and not stored is `NOT_LOADED` (none on 17 Nov). Both carry the tier 3 portal as `GAP` does |
| `TARGET` is called `HAVE` | Done | The seed's `TARGET` meant "already held", which reads as "to acquire" |
| All 87 taxonomy countries and all declared indicators | Done | The seed had 85 countries (no Isle of Man, Liechtenstein) and lacked the 11 BIS indicators added on 17 Nov |
| "Global" means two or more countries, `doctor --gaps` means eight or more | Open | The doctor's `WIDELY_HELD = 8` hides money supply (2 countries), industrial production (5), core consumer prices (6) and commercial property (7), the four largest real gaps in the matrix. A test checks every pair the doctor lists is a `GAP` or `NOT_LOADED` here; the doctor's threshold was not changed |
| Derived-not-stored indicators and removed series have no status | Open | The matrix reads the database and catalog only; a `DERIVED` or `REMOVED` status would need the reasons kept as data, not in this register |

## 4p. Portugal consumer prices moved from the IMF to FRED (18 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| Seven IMF series were overdue because the IMF had no newer data, not because of the schedule | Verified | Stored data and the live IMF API both ended in July 2026 for IMF reserves of Austria, Brunei, Ghana, Uzbekistan and IMF consumer prices of India, Moldova, Portugal. Peers were current: 29 of 47 reserves series at September and 8 at October; 44 of 70 consumer price series at September and 12 at October. For the four reserves countries the IMF's own SDR series ran to October while the country-reported reserves and gold stopped at July: the countries had not reported |
| The IMF release dates are derived, not published | Judgement | `imf_calendar.py`: the last weekday of the second month after the period; the freshness check adds a 31-day step, the median derived lag (90 days) and 14 days of grace. Typical economies arrive faster (4 to 7 weeks), so the rule is late for them, as rule 9 asks; the seven series are 80 days or more behind it |
| Portugal consumer prices come from FRED `CP0000PTM086NEST` (Eurostat HICP, all items, index 2025 = 100) | Done | Monthly to September 2026, updated by FRED on 16 Oct 2026; loaded from 1990. FRED first (rule H), one source per pair (rule M): `IMF_CPI_PRT` was removed. It is the harmonised index, not Portugal's national CPI. The OECD copies of the national CPI on FRED (`PRTCPIALLMINMEI`) ended in April 2025 |
| India and Moldova consumer prices, and the four reserves series, stay overdue | Open | No fresher keyless source was found (FRED's OECD copies of India's CPI ended in March 2025). They return when the IMF receives the countries' data, or when a national portal is chosen (tier 3 terms unread). Grace periods were not widened (rule 2) |
| US commercial property (open since 17 Nov) | Resolved 19 Nov 2026 | Measured against FRED's `COMREPUSQ159N`: the BIS is earlier (section 4s) |

## 4q. Rulebook compliance: variants, duplicate pre-filter, retry ladder, source history (18 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The IMF and BIS consumer price series are each country's own national CPI, not Eurostat's HICP | Verified for Europe, unverified elsewhere | `series_variants.py` labels all `IMF_CPI_*` and `BIS_CPI_*` series "National CPI". The IMF's CPI dataset holds national indexes (its series attributes do not name the index). On 19 Nov 2026 the last 12 stored months of the year-on-year rate were compared with Eurostat's HICP for the 34 stored IMF and BIS series Eurostat also covers: 33 differ from the HICP by 0.11 to 2.26 points (Germany 0.17, France 0.38, Sweden 2.18, Luxembourg 2.26), so they are not the HICP; Türkiye matches within 0.05 (Eurostat's Turkish figures come from the national office, so it is the same index). The 38 series outside Europe could not be compared this way, so the national basket and treatment of housing are not checked (rule 10). The US, euro area, Portugal, Eurostat core and ONS core series are labelled from the producers' own descriptions |
| The duplicate pre-filter finds every pair the full comparison finds | Design choice, tested | It keeps pairs that share the ratio between consecutive periods (same data, any unit) or the same value in the same period (different period grids). Two series on different period grids that differ only by a unit factor are not matched by either fingerprint, so they are not compared; a series with too few usable fingerprints (mostly zero or empty) is compared with every other series. Seeded random tests compare the filter with the full comparison |
| A refresh waits up to 81 minutes for a failing feed | Design choice | The ladder (15 s, 60 s, 5 min, 15 min, 1 h, each varied by up to 20%) runs after the other sources, so a failing feed never delays them; it is capped by the run budget (90% of `refresh_run_timeout_seconds`, now 4 hours). Only timeouts, network errors and 5xx are retried; a 403 or 429 stops the supplier for the run (rule 28) |
| Retired series stay in the database | Design choice | They are kept read-only for as-of reads before a change (rule 16), at the cost of storage. They are hidden from every list of served series and exempt from the duplicate check only against their own pair's later series |
| A provisional source decision counts as a source decision | Design choice | It serves, is scored, changes the catalog version and is preserved like any other (rule 20) |
| Source decisions so far | Done for Portugal, otherwise open | `source-decision --baseline` records Portugal consumer prices (FRED copy of Eurostat HICP, provisional, from 18 Nov 2026); the IMF series it replaced was deleted, so there is nothing to retire. No other pair has a decision, so each is served by its catalog series. Eurostat HICP for Europe will be the first real change |
| Scores are computed on request, and each distinct live score shown is kept | Done | `score_snapshots` (migration 0015) keeps what a user sees with the mechanism hidden (scores, confidence, pending releases) with both versions; the recipe is never stored. A change to the score for the same date is kept beside the earlier one |

## 4r. Consumer prices of 36 economies move from the IMF, BIS and FRED to Eurostat's HICP (19 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| Eurostat is the earliest eligible source for these economies | Judgement, provisional | Probed on 19 Nov 2026: Eurostat held October 2026 (dataset updated 18 Nov, 11:00 CET) while the series serving the pair stopped at September (August for Iceland, North Macedonia, Malta, Romania). A release cycle has not yet been measured, so each decision is provisional (rule 38) and is confirmed or reversed after the December release |
| Six economies level with Eurostat went to it by the native tie-break | Judgement, provisional | Albania, Belgium, Switzerland, Estonia, Luxembourg and Slovenia: the IMF also had October at the 19 Nov 2026 probe, so the two tied on latest period and frequency, and the real release times of the IMF are unknown (its dates are derived). The tie goes to the more native source (rule 38, Part 0): Eurostat for a European economy, which also keeps the bloc on one source. Re-measured after the December release like the others |
| Eurostat does not serve Bosnia, Moldova, Ukraine | Verified | The API answered that the selection held more than one series for `BA`, `MD`, `UA`; they keep the IMF series |
| Kosovo is a new pair | Done | Eurostat is the only source found; provisional |
| The measure changes from each country's national CPI to the HICP | Judgement | On 19 Nov 2026 the IMF and BIS series differed from the HICP by 0.11 to 2.26 points (section 4q). The HICP excludes owner-occupiers' imputed rents (ECOICOP 04.2) and counts spending in the territory by residents and non-residents. The variant is "HICP, all items"; a comparison with a national CPI shows a notice (rules 10, 18, 23). Scorecards are unaffected: only the US is scored |
| Eurostat's candidate-economy figures may be less comparable | Judgement | Eurostat says it has not fully evaluated Montenegro, North Macedonia, Serbia, Türkiye and Kosovo against the HICP rules; their variant says so |
| History is shorter for some economies | Open, owner's decision | Eurostat's HICP starts in 1997 or later, the series it replaces in 1990 for 28 of the economies. The longest losses: Iceland 1990 to 2016, Norway 1990 to 2001, Switzerland 1990 to 2005, Serbia 1994 to 2006, Albania 2008 to 2016, Malta and most euro economies 1990 to 1997. The earlier history stays in the retired series and is read as of dates before the switch (rule 16); charts of today's series start later. Rule 38 does not weigh history depth, rule 33 wants it: no splicing from a second source is allowed |
| The final figure replaces the flash as a new vintage | Verified in the store | `record_latest` dates a period by its first read (never later than the derived date) and closes the old value when a revision arrives, so flash and final are separate vintages. The flag `e` itself is not stored per observation (open) |
| The derived release date is late for Eurostat | Judgement | `hicp_release` is the last weekday of the month after; the real final is 15 to 18 days after the month (Eurostat metadata, read 19 Nov 2026). A first read earlier than the derived date is used instead, so freshness is judged on the real first read |
| Reuse terms of the HICP dataset | Unverified | The copyright page returned 404 on 19 Nov 2026. The general notice read on 13 Nov 2026 allows commercial reuse with attribution for EU, EFTA and candidate data; no dataset-specific terms were found |
| Retired series are protected from pruning | Done | The doctor and the FRED job's prune keep the 35 predecessors (`PREDECESSORS`), because their history is read as of dates before the switch |
| Order of a switch: decisions first, then the load | Design choice | A retired series gives up its canonical code (the unique index allows one live series per country and indicator), which the new series takes. Run `source-decision --baseline`, then `ingest-eurostat`, in every database. The refresh plan only covers stored series, so the new series must be loaded once by hand |

## 4s. US commercial property prices from the BIS, not FRED (19 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The BIS is earlier than FRED for US commercial property | Verified, provisional | Probed 19 Nov 2026. BIS `WS_CPP` US (whole country, all commercial properties, not seasonally adjusted, price index 2010 = 100): quarterly to 2026 Q2, from 1945 Q4. FRED `COMREPUSQ159N`: quarterly, to 2026 Q1, from 2005, last updated 1 Oct 2026. FRED's own first-seen dates show it receives the data in batches (Q4 2024 and Q1 2025 on 2 Sep 2025, Q2 2025 on 8 Dec 2025, then Q3 2025 to Q1 2026 all on 1 Oct 2026), 184 days or more after the quarter; the BIS had Q2 within 142 days |
| The two are different measures | Judgement | The BIS series is an index level built from CoStar's repeat-sales index since 1996 and appraisal-based series before (source: the Federal Reserve's Financial Accounts, series `FL075035503`). FRED's is the IMF's financial soundness indicator, "Commercial real estate prices", as a percent change from a year ago, and carries the IMF's copyright notice ("reprinted with permission"). Both are quarterly; the series is compared as year-on-year change (`COMPARED_AS`) |
| Frequency is equal, so earliest decides | Verified | Both are quarterly. No tie, so the native tie-break (rule 38, Part 0) is not used |
| The BIS licence allows QuFin's use | Verified | The licence register row for the BIS (attribution, no endorsement, no charge): availability of the series is "All users". The underlying CoStar data is third-party, and the BIS publishes it openly; its own terms for that data were not read separately |
| No vintages | Judgement | The BIS API serves current values only; QuFin records each value as first seen and a revision as a new vintage (rule 6) |
| Recorded as a provisional decision | Done | `source-decision --baseline` records `BIS_CPP_US` for the pair (US, commercial property prices) from 19 Nov 2026; there is no predecessor series, because FRED's was never stored. It is re-measured after the next quarterly release (rule 38) |
| Code that still said FRED first | Done | `NON_FRED_ALLOWED` now records the rule 38 reason for `BIS_CPP_US`; the tests that kept the US out of the BIS accept commercial property and residential property (`BIS_SPP_US`), as measured |

## 4t. The FRED-first checks retired (19 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The code no longer requires US series to come from FRED | Done | `NON_FRED_ALLOWED` became `SOURCE_REASONS`, a record of why a source was chosen, and the two tests that failed any unlisted non-FRED US series are replaced by consistency tests (each reason names a real series, and a BIS series for the US must say why). The wording of old rules 17, H and M in code and docs now points to rule 38 or rule 16 |
| US sources chosen under the retired rule 17 are not re-measured | Open | FRED is still the source of most US series, the Employment Cost Index, FRED's copies of IMF reserves and a few European series (real GDP and trade balance of five economies, and others). They were chosen because FRED was first, not because they were measured earliest. Rule 38 says to re-measure them at least once a quarter; none has been |
| A general check that a native source was considered cannot be written yet | Gap | A test of "every series not from its native source has a reason" would flag 450 European series today: BIS 299, World Bank 80, OECD 34, IMF 28, FRED 9. Most have no Eurostat candidate at all (credit, property prices, annual indicators), so the BIS or the World Bank is the only source. Telling those from real misses needs a table of the candidates that publish each pair (rule 37); it does not exist, so the check stays a record |
| The refresh order still starts with FRED | Design choice | `SOURCE_COMMAND` runs FRED first because most series come from it. It is a run order, not a source preference |


## 4u. Staging, slice 1: timing the IMF against Eurostat's HICP (20 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The 32 IMF consumer price series are staged again so December can be timed on both sides | Design choice | The 36 Eurostat decisions of 19 Nov are provisional until a release cycle is measured (rule 38). The IMF series that served them are retired and read-only, so they cannot be refreshed; each is loaded as `CAND_IMF_CPI_<area>`, a `staged` series, from 1990 |
| A staged series never holds the canonical code, is never served and never compared | Done | `lifecycle` is `staged`; `MacroStore.list_series()` leaves it out, the API answers 404 for it, the scorecard and the duplicate check do not read it, and its canonical code is empty because one live series per country and indicator holds the code |
| The day a period was first read is kept apart from the vintage date | Design choice | `record_latest` dates a period by the earlier of its derived release date and the day it was seen, which understates the lag of a late source. `candidate_sightings` keeps the day itself. Periods present at the first load are `bootstrap`: published before QuFin looked, so they say nothing about timing |
| The refresh loads staged candidates once a day and never fails on them | Design choice | A step `ingest-staged` is planned only when staged series are stored and none was loaded today (rule 28); a failure is reported as `overdue`, not `failed` (rule 2) |
| Candidates exist only for the pairs under provisional decision | Open | The BIS and FRED candidates (Malta and Serbia consumer prices, US commercial property), and every other pair, follow with the candidate table of slice 4 |
| Nothing measures the lag yet | Open | The sightings are kept from the first refresh; slice 2 turns them into a lag per candidate and compares it with the series that serves the pair |

## 4v. Staging, slice 2: how the lag is measured (20 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The lag is the days from the end of the period to the day QuFin first read it | Design choice | Rule 38 (a). The day QuFin first read a value is an upper bound of the day the source published it, because QuFin looks once a day; both sides are measured the same way, so the bias is shared |
| Only periods published after the candidate was first loaded are compared | Design choice | Periods present at the first load are `bootstrap`: nobody knows who published them first |
| A source that has not shown a period yet is later, and is counted | Design choice | If the other side first read the period on or before the day this one was last loaded and this one had nothing, its lag is at least the days since the period ended. The table marks such a lag with a `+`. Without it a silent source would never lose |
| One published period is enough to judge, and every verdict stays provisional | Judgement | Rule 38 says "at least one release cycle" (`MIN_RELEASES`). With one period the median is that period; the decision stays provisional and is re-measured each cycle |
| The verdict compares periods won, the action compares median lags | Design choice | `measure-candidates` shows who was earlier in more periods and runs `choose()` on the median lags and the latest periods: a tie goes to the more native source. It records nothing |
| First real reading, 20 Nov 2026 | Open | Eurostat's October was first read 18 days after the month. The IMF had not shown October for most of the 32 pairs, so each is at least 21 days (a bound); the verdict is "served earlier, confirm" until the IMF publishes and a real lag replaces the bound |

## 4w. Staging, slice 3: from a measurement to a decision (20 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| A lower bound is not a measurement | Design choice | `decide-sources` acts only when at least one period was read on both sides. While the candidate has published nothing the verdict is shown and the action is `wait`; on 20 Nov 2026 all 32 pairs wait |
| Only a confirmation is recorded by a command | Design choice | A replacement changes the source of a pair, which needs a catalog entry: a reviewed pull request that the owner merges and a row here (rules 26 and 38). `--apply` therefore confirms provisional decisions and never replaces one |
| A confirmation holds for one database until it is written in the code | Open | `decide-sources --apply` changes the decision in the database it runs on. A fresh database is built from `app/data/source_baseline.py`, so the owner sets `status` there to make it permanent |
| A winner takes a new series id | Design choice | The series that served the pair before keeps its id, retired, so its history stays readable as of earlier dates; the winner is added to the catalog under an unused id and `promote-candidate` copies the staged values, vintages and first-read days into it in one transaction |
| The staged copy is removed after the move | Design choice | It never served or scored anything, so no as-of read refers to it; keeping it beside the new series would store the same data twice (rule 16) |
| Which pairs are confirmed | Superseded | By section 4x: the Eurostat pairs are confirmed by rule 38's *Bloc aggregator first*, without a measurement |

## 4x. Bloc aggregator first (20 Nov 2026, v3.5)

| Judgement | Status | Basis |
|---|---|---|
| Eurostat serves any pair it publishes for its economies, however early another source is | Owner decision (rule 26 review pending) | Comparability across the bloc (rule 23) outweighs a few days of freshness. The lateness is priced into every score like any source's (S2). The United States and every other economy keep the measures |
| Eurostat's economies are the EU27, the euro area, IS, NO, CH, LI and AL, BA, GE, MD, ME, MK, RS, TR, UA, XK | Design choice | `EUROSTAT_ECONOMIES` in `app/domain/source_selection.py`. Whether Eurostat publishes a given indicator for one of them is checked by the probe, not assumed |
| An outage splices nothing | Design choice | The pair is unusable (rule 3) and drops out of scores (S2). The other candidates are staged and timed after one release cycle past the grace period, and the owner may approve a change (rules 6, 16 and 20 forbid splicing definitions) |
| The 32 staged IMF series are removed | Design choice | Nothing is measured for those pairs, so staged copies would only be stored. `prune-staged --yes` removes them after a backup; they never served or scored anything |
| The 36 Eurostat HICP decisions are confirmed | Design choice | `app/data/source_baseline.py`; `source-decision --baseline` raises a database's provisional ones. The US commercial property decision stays provisional |

## 4y. Staging, slice 4a: FRED's copy against the BIS for US commercial property (20 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| One candidate is registered | Design choice | `CAND_FRED_CPP_US` (FRED `COMREPUSQ159N`, quarterly) is timed against `BIS_CPP_US`, the only pair still decided by measurement. Other pairs and the discovery job (rule 34) come in slice 4b |
| A FRED candidate is dated by its own vintages | Design choice | The first vintage that carried a period is its release date; the value stored is the latest vintage. First-read days (`candidate_sightings`) are still the day QuFin saw the period |
| Quarterly lags count from the end of the quarter | Design choice | `Candidate.months` (3 here) goes to `read_period`, so both lags are measured from the quarter's end and are comparable |
| The first measurement is preliminary | Open | One period was read on both sides on 20 Nov 2026 (BIS 142 days, FRED at least 144): too few to confirm. `decide-sources` waits until the verdict rests on a release cycle |

## 4z. US series chosen under the retired rule 17 are re-measured against the BLS (21 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| Eleven US series FRED serves are timed against the BLS | Design choice | The BLS is their original producer: payrolls, unemployment rate, average weeks unemployed, manufacturing hours, CPI (all items, core, services), PPI final demand, job openings, quits rate and the Employment Cost Index. Each BLS series id was fetched live on 21 Nov 2026. Other FRED series have other original producers (DOL, BEA, the Federal Reserve) with no connector yet, so they wait for slice 4b |
| A BLS candidate is described like the series it is timed against | Design choice | The BLS API returns current values and no vintages; title, units, frequency, adjustment, dimension and cycle come from the stored FRED series. The first-read day of a period is the day it first appears |
| A tie goes to the BLS if the lags are level | Per rule 38 | The original producer outranks the bloc aggregator (FRED) in the tie-break (Part 0). Changing a source is a reviewed pull request and `promote-candidate`, never a command |
| No source decision exists for these pairs yet | Open | `decide-sources` reports "not what serves it" until a baseline decision records FRED as serving each pair. `measure-candidates` is unaffected and shows the lags |
| The measurement needs a release cycle | Open | All 11 were staged on 21 Nov 2026 and have published nothing since. The FRED series are timed from their own vintages; the BLS from the day each period first appears |

## 5a. Discovery probe, report first (21 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The probe stores nothing | Design choice | It reports what each source publishes against what QuFin holds. Staging and serving stay decisions for a reviewed pull request (rules 26, 34, 38) |
| Three indicators, two sources | Design choice | Industrial production, core consumer prices and money supply, against the OECD (one wildcard request answers for every economy) and Eurostat (one request per economy it serves). The keys were checked live on 21 Nov 2026. Other sources and indicators are added as probes in `app/data/probes.py` |
| Eurostat's answer wins for its economies | Per rule 38 | For an economy Eurostat serves, a Eurostat series would serve the pair whatever the OECD shows (Bloc aggregator first) |
| A series is current if its latest period is within 150 days | Design choice | A recent window of eight months is read; this is a screen for the report, not the release check of rule 2 |
| First report, 21 Nov 2026 | Result | Eurostat publishes 33 core CPI and 30 industrial production series QuFin lacks. The OECD adds industrial production for GB, CA, IN, MX, BR and CL, core CPI for AU, and money supply for 10 economies (GB, JP, CA, AU, NO, HU, ZA, KR, IS, CO). Eurostat could not be read for Iceland and Kosovo (the selection holds more than one series). OECD series for 24 other economies are behind schedule and are not counted |
| Eurostat has no money supply | Open | Euro area money comes from the ECB (already held); other Eurostat economies need their central banks or the IMF |

## 5b. Gap candidates staged from the probe's findings (21 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 80 series are staged | Result | From the 21 Nov 2026 probe: Eurostat core consumer prices for 33 economies and industrial production for 30; OECD industrial production for GB, CA, IN, MX, BR and CL, core consumer prices for AU, and broad money for GB, JP, CA, AU, NO, HU, ZA, KR, IS and CO. Each series loaded live on 21 Nov 2026 (to 440 months for most) |
| Staged is not served | Per rule 34 | No gap candidate is served, scored or compared, and coverage stayed at 944 of 2,697 cells. A reviewed pull request that verifies licence, definition and release schedule promotes one (rules 26 and 34) |
| A gap candidate has nothing to time | Design choice | `serves` is empty, so `measure-candidates` and `decide-sources` skip it. For an economy Eurostat serves, Eurostat wins by rule 38 (Bloc aggregator first); no measurement decides it |
| A gap candidate describes itself | Design choice | Title, units, adjustment, dimension and cycle are written in `app/data/candidates.py`. The dimension and cycle of money supply (`policy`, `leading`) and of the OECD series are my classification and need the owner's review before promotion (rule S5-style review of cycle) |
| Only current economies were staged | Design choice | The probe's `current` flag (latest period within 150 days). OECD series that are behind schedule (24 economies) and Eurostat's Iceland and Kosovo industrial production (the selection holds more than one series) are not staged |
| The daily refresh loads them | Open | `ingest-staged` now has 92 candidates, about 4 minutes a day at the suppliers' own pace (Eurostat 2 s, OECD 3 s per series). If that crowds the run, split the staging step from the refresh |

## 5c. Probe extended to BIS and the OECD; its findings staged (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| The probe now covers 21 more indicators | Result | 18 BIS measures (one wildcard request each) and OECD leading index, business confidence, consumer sentiment and unemployment, in `app/data/probes.py`. Commercial property prices (a key per economy) and the IMF (licence open) are not probed |
| A quarter counts as current within 345 days | Design choice | A BIS quarter is dated at its start and published about a quarter and a half later; 150 days would mark every quarterly series behind. A screen for the report, not the release check of rule 2 |
| 145 series are staged | Result | BIS: 135 (effective exchange rates 31 + 31, credit to GDP 17 and its gap 17, policy rate 8, international debt securities 9, central bank balance sheet 4, property prices 5, other debt and credit measures 12). OECD: leading index for CN, business confidence for BR, ZA, ID, IL, CO, consumer confidence for IN, ZA, ID, IL. Each loaded live on 22 Nov 2026 |
| Eurostat's economies are left out where Eurostat also publishes | Per rule 38 | Residential property prices, business and consumer confidence and unemployment are not staged for an economy Eurostat serves (23 property-price, 5 business-confidence, 2 consumer-confidence economies). They wait for a Eurostat probe of those indicators, which is not built |
| Staged is not served | Per rule 34 | Coverage stayed at 944 of 2,697 cells and the live series at 1,018. A reviewed pull request verifies licence, definition and release schedule before one is served (rules 7, 26, 34) |
| BIS limits | Open | The BIS says to cite it, and its terms limit property-price sub-series (see the licence register); the BIS commercial property series stay unstaged. `BisClient` keeps its 1 s interval and stops after a 403 or 429 |
| Classification of the OECD series | Open | Dimension and cycle copy the served OECD series (`growth`/`leading`, `sentiment`/`leading`); the owner reviews them before promotion |
| The daily refresh loads 237 candidates | Open | Several more minutes a day at the suppliers' own pace (not timed). Split the staging step from the refresh if it crowds the run |

## 5d. Eligibility, batch A: 98 BIS series on six served measures (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 98 BIS series become served series | Per rule 34 | Policy rate 7 (ID, IS, IL, MK, MY, RO, RS), nominal and real effective exchange rate 29 each, credit to GDP and its gap 15 each, residential property prices 3 (IL, MY, CO). They are added to the area lists in `app/data/bis_ids.py` (`BATCH_A`), so the catalog, the taxonomy and `ingest-bis` take them from there |
| The measures were already verified | Basis | Key, units, adjustment, cycle and release rule were verified when the measure was added (12 and 17 Nov 2026); batch A only adds economies to them. Each series was staged and loaded over its full history on 22 Nov 2026 with no missing period and the latest period in line with the economies already served (2026-10 monthly, 2026-01 and 2026-04 quarterly) |
| Licence (rule 7) | Open | The BIS terms were read on 12 Nov 2026 and cover these series. The BIS marks some property-price sub-series as proprietary or third-party; the owner confirms before the three new property-price series are relied on commercially |
| The BIS is the only candidate, so it serves from the start | Per rule 38 | Eurostat does not publish effective exchange rates, credit ratios or policy rates, and no other candidate has a current feed for these pairs. Each pair gets a provisional decision dated 22 Nov 2026 (`app/data/source_baseline.py`) until a release cycle is measured |
| Residential property prices of Eurostat's economies are not served | Per rule 38 | 23 economies wait for a Eurostat probe of that indicator |
| 37 staged BIS series are held back | Open | Russia (10): the BIS stopped receiving official data in Feb 2022 and coverage-universe.md marks it undecided. United States (13): FRED may also serve those pairs, so rule 38 times the two first. Missing periods (10): Kuwait, Oman, Kenya, Liechtenstein, Cambodia, Nigeria and the Congo on international debt securities or central bank assets, Latvia and Lithuania on corporate debt securities. A quarter behind (4): Chile's property prices and central bank assets of South Korea, Indonesia and Israel. They stay staged, and the registry keeps them |
| The staged copies of the 98 are pruned | Design choice | Once served, a candidate has done its job. `prune-staged --yes` removes the 98 staged copies (after a backup); their first-read days are lost, since `promote-candidate` handles only candidates that replace a series |
| Scorecard effect | Open | A new series reaches a score only if its indicator is in the private recipe. The owner checks which of these six indicators the recipe uses (rule 20). Past scores keep the catalog version they were computed with |

## 5e. Eligibility, batch B: Eurostat core HICP and production, and OECD survey series (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 72 series become served series | Per rule 34 | Eurostat core HICP for 33 economies and industrial production for 29, and the OECD's leading indicator for China, business confidence for Brazil, South Africa, Indonesia, Israel and Colombia, consumer confidence for India, South Africa, Indonesia and Israel. They are declared in `BATCH_B_CORE` and `BATCH_B_IP` (`gap_ids.py`) and `_OECD_BATCH_B` (`macro_catalog.py`), so the catalog, units, concepts and the existing ingestion take them |
| The measures were already verified | Basis | Eurostat's `prc_hicp_minr` (core) and `sts_inpr_m` (production) are the datasets and filters of the series served for Germany, France, Italy and the euro area since 13 Nov 2026; the OECD keys are the ones of the served survey series. Each new series was staged and loaded over its full history on 22 Nov 2026: no missing month, latest month 2026-10 (core) and 2026-09 (production and OECD surveys) in line with the rest |
| Eurostat's economies are served by Eurostat | Per rule 38 | Eurostat publishes the indicator for them, so each pair has a confirmed decision, "Bloc aggregator first", dated 22 Nov 2026 (`app/data/source_baseline.py`). The OECD pairs are provisional until a release cycle is measured |
| Candidate economies carry a definition notice | Per rules 10 and 23 | Core HICP of Albania, Montenegro, North Macedonia, Serbia, Turkey and Kosovo is marked "candidate economy: comparability not fully evaluated" (`app/data/series_variants.py`), as their headline HICP already is |
| Belgium's production stays staged | Open | Its latest month is 2026-08, a month behind the other 29; it is not served until it catches up (rule 3) |
| 17 OECD series are not in this batch | Open | Industrial production for GB, CA, IN, MX, BR, CL, core CPI for AU and broad money for ten economies stay staged: the OECD loader reads only the leading-indicator, confidence and unemployment flows. They need a generic OECD loader and, for money supply, your classification of dimension and cycle (`policy`, `leading` are my proposal) |
| Licence (rule 7) | Open | Eurostat's reuse decision (CC BY 4.0) and the OECD terms are in the licence register and cover these series; some Eurostat third-party sub-series are restricted. The OECD builds some survey data from licensed sources (the US ones are left out for that reason): the owner confirms the six new economies are not affected |
| The staged copies are pruned | Design choice | `prune-staged --yes` removes the 72 staged copies; their first-read days are lost |
| Scorecard effect | Open | Core CPI, industrial production, leading index and confidence feed a score only if the private recipe uses them (rule 20) |

## 5f. Findings staged: trade balance, current account and real GDP (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 96 series are registered as candidates | Result | From the 21 Nov 2026 probe: Eurostat real GDP for 8 economies, current account for 11 and trade balance for 24; OECD real GDP for 5, current account for 12, goods balance for 19 and goods-and-services balance for 17. Each is for an economy QuFin holds nothing for |
| 52 OECD candidates loaded as staged | Result | Real GDP (5: BRA, COL, EA, NZL, SAU), current account (12: ARG, BRA, CHL, CHN, EA, GBR, IDN, IND, JPN, SAU, USA, ZAF), goods trade balance (18: ARG, CHE, CHL, CHN, EA, IDN, IND, ISL, ISR, KOR, MEX, NOR, NZL, RUS, SAU, TUR, USA, ZAF), money supply (10: AUS, CAN, COL, GBR, HUN, ISL, JPN, KOR, NOR, ZAF), industrial production (6: BRA, CAN, CHL, GBR, IND, MEX), core CPI (1: AUS). Loaded live on 22 Nov 2026 |
| 18 OECD candidates not loaded | Open | The OECD answered 429 after about 70 requests in a row and `OecdClient` stopped for the run (rule 28): Colombia goods trade balance plus all 17 goods-and-services balances (`CAND_OECD_TRADE_COL`, `CAND_OECD_TRADEGS_*`). They load after the hourly limit resets, with `ingest-staged --only <id>` |
| Eligibility — OECD real GDP (5), OECD current account (12) | Open | Rule 7 not met: OECD terms are "to confirm" for commercial display and national survey producers' terms are unverified (`docs/licence-register.md`); data-connections doc says OECD terms "Not verified (pages could not be read on 12 Nov 2026)". Rule 28 met: connector pauses between requests and stops on 429 (`app/connectors/base.py`, `app/jobs/ingest_oecd.py`). Only rule 28 has evidence; rule 7 terms not yet read. |
| Eligibility — OECD money supply (10), industrial production (6), core CPI (1) | Not eligible | The OECD loader reads only leading-indicator, confidence and unemployment data; it does not load money supply, industrial production or core CPI. Money supply also needs dimension and cycle classification (rule 23). |
| Currency and frequency — trade balance (OECD goods 18; Eurostat 24) | Owner decision, 24 Nov 2026 | Eurostat merchandise balance is monthly in millions of euros; OECD goods balance is quarterly in exchange-rate-converted millions of US dollars (`USD_EXC`, USD pass-through under rule 23). Rule 38 decides new pairs from the latest eligible probe; there is no served series against which to run the usual release-lag measurement |
| Stage-before-serving — trade balance | Owner decision, 24 Nov 2026 | Every responding candidate is staged before serving, including Eurostat-bloc pairs. Eurostat still has exclusive priority whenever eligible and publishing; its release lag is not compared in normal operation. The v3.7 Rule 38 amendment is committed; serving still requires the reviewed eligibility PR |
| Eurostat dataset metadata — trade balance | Partially verified, 25 Nov 2026 | The [official API response](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/ei_eteu27_2020_m?freq=M&unit=MIO-EUR-SA&stk_flow=BAL_RT&partner=WORLD&indic=ET-T&geo=AT) identifies monthly EU27 goods trade, source `ESTAT`, `BAL_RT` balance, total goods, world partner, and million-euro seasonally and working-day-adjusted values. The [ESMS metadata](https://ec.europa.eu/eurostat/cache/metadata/en/ei_et_esms.htm) says trade values are FOB for exports and CIF for imports, and describes working-day correction and seasonal adjustment. The [13 Nov release](https://ec.europa.eu/eurostat/web/products-euro-indicators/w/6-13112026-bp) reports euro-area exports of EUR 272.7bn, imports of EUR 283.0bn and a balance of -EUR 10.3bn, confirming exports minus imports. ESMS says monthly aggregate data are supplied within 40 days and first EU/euro-area balances appear around 46 days; the candidate dataset update on 13 Nov included September data (44 days after month-end). Its release calendar derives a later due date, conservatively. Source/agency metadata names Eurostat; no series-level reuse restriction surfaced. The applicability of the general notice's third-party exception is addressed by the owner decision in the eligibility row below |
| Staged state — trade balance | Verified in local store, 25 Nov 2026 | All 24 Eurostat candidates are staged (297 monthly periods each, 2002-01 to 2026-09); 18 OECD goods candidates are staged (82-147 quarterly periods each, latest 2026-Q2 or Q3). All reads are bootstrap sightings, so no post-stage release-lag evidence exists. The registered Colombia OECD goods candidate is not staged. The 18 local OECD staged rows' units and scale were refreshed to millions of exchange-rate-converted USD (1,000,000) on 24 Nov; on 25 Nov the 24 Eurostat rows' adjustment label was corrected to "Seasonally and Working Day Adjusted". Both metadata corrections were backed up; observations and sightings were not changed |
| Eligibility — Eurostat merchandise balance (24) | Owner accepted terms, 25 Nov 2026; PR review pending | Definition, sign, units, adjustment and release timing are supported by the official metadata and release bulletin above; the keyless API is accessible. The owner accepts commercial reuse with attribution for this EU-only set under the general notice; no dataset-specific third-party restriction surfaced. The 24 series are declared in `BATCH_E_TRADE` with external/lagging tags for the reviewed eligibility PR. Staged data remains unpromoted until that PR is reviewed and merged |
| Eligibility — OECD goods balance (18) | Open | OECD terms permit commercial reuse with attribution unless the metadata names third-party owners or restrictions. The public BOP dataflow structure is accessible, but it does not establish per-series ownership or reuse limits. The Argentina Data Explorer selection (`ARG.WXD.G.B.T.Q.USD_EXC.N`) identifies INDEC as the dissemination agency; its displayed source field gives only the quarterly frequency and shows no recommended-use limitation. This is not sufficient to clear Argentina or the other 17 staged economies. No ownership/reuse check is claimed; keep all 18 staged |
| OECD BOP dataflow status | Open | The official `DSD_BOP@DF_BOP` structure ([OECD SDMX API](https://sdmx.oecd.org/public/rest/v1/dataflow/OECD.SDD.TPS/DSD_BOP@DF_BOP/1.1?references=all)) is marked final and describes BPM6 quarterly data in millions of US dollars or national currency, but also has `NonProductionDataflow=true`. The official material checked here does not define that annotation. Confirm its meaning with OECD before treating this dataflow as production-eligible |
| Eligibility — Eurostat real GDP (8) and current account (11) | Done in batch C | Declared in the catalog with confirmed decisions (section 5g). Eurostat's reuse decision (CC BY 4.0) is in the licence register; its trade balance (24) stays open with the currency and frequency decision |
| Eurostat's economies stay with Eurostat | Per rule 38 | The goods-and-services balance of 12 of its economies (EA, DE, FR, IT, CH, NO, SE, DK, CZ, HU, PL, TR) is not staged: Eurostat publishes it in its balance of payments and has not been probed for it |
| Release dates | Design choice | Quarterly series are dated by a rule that errs late (rule 9): the last weekday of the third month after the quarter for Eurostat, the 15th of the fourth month for the OECD (`eurostat_calendar.py`, `oecd_calendar.py`) |
| Classification | Open | Dimension and cycle (`growth`/`coincident` for GDP, `external`/`lagging` for the balances) copy the series already served; the owner reviews them before promotion |

## 5g. Eligibility, batch C: Eurostat real GDP and current account (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 19 series become served series | Per rule 34 | Real GDP for Switzerland, Norway, Sweden, Denmark, Czechia, Hungary, Poland and Turkey (8, `namq_10_gdp`) and the current account for Germany, France, Italy, Switzerland, Norway, Sweden, Denmark, Czechia, Hungary, Poland and Turkey (11, `ei_bpm6ca_q`). Declared in `gap_ids.py` (`BATCH_C_GDP`, `BATCH_C_CA`), so the catalog, units, concepts and cycles take them; `ingest-eurostat` loads them |
| Definitions | Basis | Real GDP is chain linked volumes (2020) in national currency, seasonally and calendar adjusted (the unit kind is an amount in the economy's currency, as the series already served); the current account is the balance with the rest of the world as a percent of GDP. Each series was staged with these exact keys and loaded over its full history with no missing quarter |
| Eurostat serves its economies | Per rule 38 | Each pair has a confirmed decision, "Bloc aggregator first", dated 22 Nov 2026 (`app/data/source_baseline.py`). Eurostat's reuse decision (CC BY 4.0, read 13 Nov 2026) covers EU, EFTA and candidate economies |
| The OECD's 17 series are not served | Open | Real GDP for the Euro Area, New Zealand, Brazil, Saudi Arabia and Colombia, and the current account for the US, Euro Area, UK, Japan, China, India, Brazil, South Africa, Argentina, Indonesia, Saudi Arabia and Chile. Rule 7 is not met: the licence register says *to confirm* and the OECD's terms page refused an automated read (HTTP 403) on 22 Nov 2026; QuFin does not work around that (rule 28). The owner confirms the terms (CC BY 4.0 and any third-party carve-outs for national accounts and balance of payments data); then `OECD_FLOW_SERIES = _OECD_FLOW_READY` in `gap_ids.py` and the decisions are added. The loader (`ingest-oecd`, quarterly check, release rule) is ready and the series stay staged Superseded by section 5h (terms read, series served). |
| Quarterly handling | Design choice | A quarter is dated at its first month; release dates err late (rule 9): the last weekday of the third month after the quarter for Eurostat, the 15th of the fourth month for the OECD. The ingestion checks no quarter is missing |
| The staged copies are pruned | Design choice | `prune-staged --yes` removes the 19 staged copies; their first-read days are lost (`promote-candidate` handles only candidates that replace a series). Accepted by the owner |
| Scorecard effect | Open | Real GDP and the current account feed a score only if the private recipe uses them (rule 20) |

## 5h. Eligibility, batch D: the OECD's real GDP and current account (22 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 17 OECD series become served series | Per rule 34 | Real GDP (Euro Area, New Zealand, Brazil, Saudi Arabia, Colombia) and the current account as a percent of GDP (US, Euro Area, UK, Japan, China, India, Brazil, South Africa, Argentina, Indonesia, Saudi Arabia, Chile): `OECD_FLOW_SERIES` in `gap_ids.py`, so the catalog, units, concepts and cycles take them; `ingest-oecd` loads them quarterly. Each was staged with these keys and loaded over its full history with no missing quarter; each pair has a provisional decision dated 22 Nov 2026 (rule 38) |
| Licence (rule 7): met | Per the OECD's terms | The owner supplied the OECD's terms and conditions (last updated 1 July 2024; the page refused an automated read, HTTP 403, and QuFin did not work around that, rule 28). Section 3: Data may be extracted, copied, adapted, distributed and shared "for any purpose, even for commercial use", with credit, except where the dataset's metadata names third-party owners or further restrictions. The metadata of the two dataflows (`DSD_NAMAIN1@DF_QNA_EXPENDITURE_NATIO_CURR`, `DSD_BOP@DF_BOP`) read through the OECD's API carries no third-party or licence notice |
| Attribution | Per the OECD's terms | "OECD (year), (dataset name), (data source) DOI or URL (accessed on (date))", and the same acknowledgement in any sub-licence QuFin grants. Series record the source name `OECD (from national sources)` and the dataset (`release_name`) |
| Open | Open | The API section of the terms was empty in the copy supplied, so the OECD's API limits are known only from observation (HTTP 429 after about 70 requests in a row; the terms say the OECD may change query limits). The Data Explorer's "source" tab, which names the national source of each dataset, was not read: if a dataset shows a third-party owner, that series is withdrawn |
| Eligibility of money supply, industrial production and core CPI of the OECD (17) | Not eligible | Still no loader (`ingest-oecd` reads leading-indicator, confidence, unemployment, real GDP and current-account flows only) and no classification of dimension and cycle for money supply |
| The staged copies are pruned | Design choice | `prune-staged --yes` removes the 17 staged copies; their first-read days are lost. Accepted by the owner |

## 5i. Eurostat residential house-price index eligibility (25-26 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| 20 residential property-price gaps are eligible for Eurostat | Result | Euro Area (EA21), Austria, Belgium, Bulgaria, Cyprus, Estonia, Spain, Finland, Croatia, Ireland, Iceland, Lithuania, Luxembourg, Latvia, Malta, the Netherlands, Portugal, Romania, Slovenia and Slovakia. These are added to the live catalog by the eligibility PR; the 39 other residential-property gaps are not addressed by this batch |
| Series definition | Verified | Eurostat quarterly dataset `prc_hpi_q`, filtered to `freq=Q`, `purchase=TOTAL`, `unit=I15_Q` and one `geo` per request. The [official EA21 API response](https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data/prc_hpi_q?freq=Q&purchase=TOTAL&unit=I15_Q&geo=EA21&sinceTimePeriod=2026-Q2) identifies the Euro-area HPI level (2015=100) for Q2 2026 |
| Staged data quality | Verified in local store | All 20 candidates were loaded as `staged`, each with a complete quarterly history beginning between 2005 Q1 and 2010 Q1 and running through 2026 Q2. No missing quarter was found within any available history. The staging run does not change served coverage; after the eligibility PR merges, run `ingest-eurostat` to populate the live series and retire stale staged copies |
| Release dating | Derived; calibrated against release calendar | Eurostat's HPI release-calendar event identifies Q2 2026 as published on 1 Oct 2026; the Statistics Explained article says the next update is planned for January 2027. The earlier shared rule dated Q2 as 30 Sep (before release). HPI now uses the 15th day of the fourth month after quarter-end, a conservative buffer against the observed 1 Oct release (15 Oct for Q2); its due-date grace period provides further tolerance for delayed releases |
| Dataset-specific rights | Reviewed; eligible under general policy | The [Eurostat copyright notice](https://ec.europa.eu/eurostat/web/main/help/copyright-notice), checked 25 Nov 2026, authorises commercial reuse of statistical data with source acknowledgement unless data are identified as third-party-owned, an individual notice states conditions, or the geography is outside EU/EFTA/candidate coverage. The HPI API response identifies `SOURCE_INSTITUTIONS` as Eurostat and exposes no ownership/licence restriction annotation; all 20 staged geographies (EA21 and 19 EU/EFTA economies) are within the geographic scope. Cite Eurostat and dataset DOI `10.2908/PRC_HPI_Q` with access date. The [HPI metadata](https://ec.europa.eu/eurostat/statistics-explained/index.php?title=Housing_price_statistics_-_house_price_index) describes the household-purchased residential HPI and its scope |
| Owner acceptance and eligibility | Owner accepted 25 Nov 2026; eligibility PR prepared 26 Nov | The owner accepts commercial reuse with Eurostat attribution and the dataset DOI/access date. The eligibility PR adds live catalog declarations and confirmed source decisions under Rule 34, including units, adjustment, frequency, housing dimension, leading-cycle rationale, source attribution and the HPI release rule. Production serving begins only after merge and successful ingestion/checks |

## 5j. Japan residential house-price source check (25 Nov 2026)

| Judgement | Status | Basis |
|---|---|---|
| An official monthly residential HPI source exists | Verified | Japan's Ministry of Land, Infrastructure, Transport and Tourism (MLIT) publishes a residential property price index based on transaction prices, with national, regional and metropolitan-area series. The [MLIT source page](https://www.mlit.go.jp/totikensangyo/totikensangyo_tk5_000085.html) provides the latest residential-index workbook |
| Current observations are not available | Blocked | The latest release listed is December 2025 / 2025 Q4, published 31 Mar 2026. MLIT says the planned releases for January-June 2026 and July 2026 / 2026 Q2 are delayed because of a calculation-program defect. Do not stage this as a current Japan series until MLIT resumes publication; recheck the source then |

