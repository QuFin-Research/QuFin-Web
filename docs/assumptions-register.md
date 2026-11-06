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

## 5. Known mismatches between a series and its textbook definition

- Unit labour costs (`ULCMFG`) is the manufacturing sector; the Conference Board uses nonfarm business.
- Consumer credit (`TOTALSL`) is the level; the Conference Board uses installment credit to personal income.
- Consumer sentiment (`UMCSENT`) is not the Conference Board's consumer expectations.
- The Philadelphia Fed new-orders index and the NFCI stand in for licensed or unavailable components.
- Richmond and Kansas City regional surveys are not on FRED (gap, not loaded).

## 6. Not covered by this audit

- The one-line plain-English explanations of each concept were written by QuFin and not compared line by line with a producer's text.
- Which pillar each series feeds and its importance beyond the sign (see section 2).
- Non-US series (only the euro area is loaded): audit each when added.
- Licence status of every source (`docs/licence-register.md` tracks it; several are still *to confirm*).

All five pillars count equally in the overall score (weighted only by confidence): interim, same status as the indicator weights.
