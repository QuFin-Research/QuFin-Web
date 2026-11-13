# Assumptions register

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
| World Bank unemployment is an annual modelled ILO estimate | Judgement | For the euro area members Eurostat publishes monthly unemployment; rule K says the monthly series should replace the annual: **not yet done** |
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
| Eurostat monthly unemployment (`une_rt_m`, SA, total, percent of labour force) for 17 EU members | Verified | Replaces the World Bank's annual figure for Austria, Belgium, Croatia, Cyprus, Estonia, Finland, Greece (Eurostat code EL), Ireland, Latvia, Lithuania, Luxembourg, the Netherlands, Portugal, Romania, Slovakia, Slovenia and Spain (rule K, rule M); the 17 World Bank series were removed |
| Bulgaria and Malta keep the World Bank's annual unemployment | Fail-fast | Probed fine, but the load answered HTTP 307 (a redirect) for both on 13 Nov 2026; not retried. Tiers checked: 1 (FRED not probed), 2 (Eurostat 307). Retry later |
| Switzerland monthly unemployment | Not available | OECD answered 404 on 13 Nov 2026 (tier 2). Tier 1 (FRED) not probed; tier 3 (Swiss Federal Statistical Office) registered, terms unread |
| Chile and Colombia are in the taxonomy (87 countries) | Done | Added at the owner's request beyond the 85-country list; currency, central bank and emerging-market flag unverified like the other 50. The policy rates come from the BIS (`BIS_CBPOL_CL` to October 2026, from 1997; `BIS_CBPOL_CO` from 1995) and monthly unemployment from the OECD (Chile to August 2026 from 1990, Colombia to September 2026 from 2007). Their CPI was not asked for and is not loaded |
