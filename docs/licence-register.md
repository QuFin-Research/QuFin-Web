# Data licence register

Every source QuFin uses or plans to use, with what we may do with it (backlog task P0-14, rule 7
in `RULEBOOK.md`). "Free to download" is not "free to show to paying customers": a
source moves to **In use** only when its redistribution terms allow display in a paid product,
or a licence is signed.

**Status:** In use · Planned · Needs licence · Excluded. **Last reviewed:** 4 Nov 2026.
Rows marked *to confirm* have not yet been checked against the publisher's terms page.

## In use

| Source | Data | Redistribution in a paid product | Attribution | Cost | Notes |
|---|---|---|---|---|---|
| FRED / ALFRED API (St. Louis Fed) | 43 US series with vintages | Depends on each series' copyright; public-domain US government series are fine | "Source: Federal Reserve Bank of St. Louis, FRED" plus the original agency | Free (API key) | Check each series' notes: copyrighted series below |
| US government agencies via FRED (BLS, BEA, Census, Fed Board, ETA, EIA) | Prices, jobs, output, rates, claims, gasoline | Public domain | Name the agency | Free | — |
| University of Michigan Surveys of Consumers (via FRED, UMCSENT) | Consumer sentiment | **Not allowed** without a licence: free only for research or strictly internal use (CC-BY-NC-ND) | Copyright notice required | Licence on request (umsurvey@umich.edu) | In use under the owner's decision while the licence is checked; FRED shows it 1 month late |
| Moody's via FRED (BAA10Y, Baa yield) | Credit spread | Proprietary, licensed to FRED: *to confirm* before commercial display | "Moody's" | Unknown | Spread calculated by FRED from Moody's Baa yield and H.15 |
| Federal Reserve Banks of Chicago (NFCI), Philadelphia (survey), St. Louis (STLFSI4) | Financial conditions, new orders, stress | Free reuse with attribution: *to confirm* per bank | Name the bank | Free | — |
| Lewis-Mertens-Stock Weekly Economic Index (WEI) | Weekly activity | *to confirm* | Authors and FRED | Free | Published as a growth rate |
| Fed H.10 daily FX (via FRED: DEXUSEU, DEXUSUK, DEXJPUS, DEXUSAL, DEXUSNZ, DEXCAUS, DEXSZUS) | Daily reference FX rates, 7 pairs | Public domain | "Board of Governors of the Federal Reserve System" | Free | Noon buying rates in New York, published weekly; reference prices, not tradable quotes |
| EIA spot prices (via FRED: DCOILWTICO, DCOILBRENTEU, DHHNGSP) | WTI, Brent, Henry Hub daily | Public domain | "U.S. Energy Information Administration" | Free | Spot reference prices |
| EIA API v2 (Weekly Petroleum Status Report) | 12 weekly oil series: crude, Cushing and SPR stocks, production, refinery use, product stocks, imports, exports, demand | Public domain (US government work) | "Source: U.S. Energy Information Administration" | Free (API key) | Not on FRED; EIA serves no vintages, so QuFin records revisions as it sees them |
| ECB Data Portal (SDMX API) | Euro area: deposit facility rate, HICP headline and core (Eurostat), M3 | Reuse with attribution (ECB statistics reuse policy); *to confirm* commercial terms for Eurostat-produced HICP | "Source: ECB Data Portal" (and Eurostat for HICP) | Free, keyless | No vintages, so QuFin records revisions as it sees them; ECB reference FX rates not loaded (EUR/USD already from Fed H.10) |
| Treasury Fiscal Data API (Bureau of the Fiscal Service) | Debt to the Penny (daily), average interest rates, interest expense on the public debt (monthly) | Public domain (US government work) | "Source: U.S. Treasury, Fiscal Data" | Free, keyless | Not on FRED at these frequencies; no vintages, so QuFin records revisions as it sees them |
| OECD Data Explorer (SDMX API) | Composite leading indicators (7 countries), business confidence (13), consumer confidence (8) | OECD data is published under CC BY 4.0 (OECD terms since July 2024): *to confirm* for commercial display; confidence series are national surveys (e.g. GfK for the UK) republished by the OECD, so their producers' terms also apply: *to confirm* | "Source: OECD" plus the national producer | Free, keyless (rate-limited per hour) | US CLI taken from FRED (live with vintages); US confidence left out (ISM and Michigan inputs) |
| CFTC Commitments of Traders (Public Reporting API) | Positioning, 15 contracts: Traders in Financial Futures (currencies, US Dollar Index, crypto) and legacy (commodities) | Public domain | "Source: CFTC" | Free | — |

## Planned (Phase 1 connectors)

| Source | Data | Redistribution | Cost |
|---|---|---|---|
| BLS, BEA, Census | US primary releases | Public domain | Free (BLS, BEA keys) |
| Eurostat | Euro-area macro beyond the ECB's copies | Reuse with attribution | Free |
| IMF, World Bank, BIS | Cross-country macro, policy rates, REER | Reuse with attribution, *to confirm* (IMF has commercial-use limits on some data) | Free |
| Central banks and statistics offices (BoE, ONS, BoC, StatCan, RBA, ABS, RBNZ, Stats NZ, BoJ, SNB, …) | National macro | Most allow reuse with attribution; *to confirm* each | Free |
| FRED H.10 daily FX, ECB reference rates | Daily FX reference prices | Public domain (H.10); ECB: reuse with attribution | Free |
| Crypto exchange public APIs (via CCXT) | Crypto prices | Exchange terms apply to redistribution: *to confirm* | Free |
| GDELT 2.0, Geopolitical Risk Index, Economic Policy Uncertainty | Geopolitics, uncertainty | GDELT free; GPR and EPU: *to confirm* | Free |

## Needs a licence (quotes: backlog P0-15)

| Source | Data | Why |
|---|---|---|
| ISM, NAHB, Conference Board (LEI, consumer confidence), S&P Global PMIs, ZEW, sentix | Premium surveys | Proprietary; removed from or never on FRED |
| Economic calendar consensus (Trading Economics, FXStreet, Finnhub, Econoday, LSEG) | Consensus forecasts | Proprietary; release dates themselves are free from official calendars |
| Intraday FX, metals and futures prices (OANDA, Polygon, Twelve Data, Tiingo, Databento) | Prices | Paid for intraday and for redistribution |
| ICE (BofA bond indexes, ICE Brent COT) | Credit indexes, Brent positioning | FRED keeps only 3 years of ICE data; ICE's own COT is not in the CFTC data |
| ACLED | Conflict data | Commercial licence |

## Excluded

| Source | Why |
|---|---|
| Cboe VIX (on FRED) | Cboe copyright; licence needed |
| Coinbase bitcoin and ether (on FRED: CBBTCUSD, CBETHUSD) | "Reproduction of Coinbase data in any form is prohibited except with the prior written permission of Coinbase" |
| LBMA gold and silver | Withdrawn from FRED; licensed price feed needed |
| Forex Factory, Investing.com, Yahoo Finance, Trading Economics web pages | Terms forbid scraping; design references only |
| S&P 500 on FRED | 10 years only and no vintages; licensed price source instead |
