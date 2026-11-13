# Official release calendars

Backlog task P0-21: where each economy publishes its release schedule, for the release-calendar
store and sensors (P1-09). Release dates are free from official sources; consensus forecasts are
not (licence register). **Status:** draft. A calendar is marked **Verified** only after its page or
API has been opened and its format recorded; the rest are the publisher's calendar to locate and
confirm.

| Economy | Publisher | Calendar | Status |
|---|---|---|---|
| United States | CFTC | Commitments of Traders release schedule (cftc.gov, COT release schedule and historical special announcements) | **Verified**: encoded in `services/api/app/data/cot_calendar.py` |
| United States | St. Louis Fed (FRED/ALFRED) | Release dates per series via the `/fred/release/dates` and `/fred/series/release` API | **Verified**: release and source per series stored |
| United States | Treasury (Fiscal Data) | Release calendar API (upcoming and latest only): Debt to the Penny each business day for the previous one; average interest rates and interest expense on the 4th business day of the next month | **Derived** for past dates from that pattern in `services/api/app/data/treasury_calendar.py` (checked 5 Nov 2026) |
| United States | FRED (BLS source) | Employment Cost Index `ECIALLCIV`: end of the month after each quarter (January, April, July, October) | FRED/ALFRED vintage dates, no derivation needed; the BLS lag table in `ingest_bls.py` is kept only for the connector |
| United States | BEA | BEA release schedule | To confirm |
| United States | Census | Economic indicators calendar | To confirm |
| United States | Federal Reserve Board | H.4.1, H.8, H.15, G.17, G.19 statistical release dates; FOMC calendar | To confirm |
| United States | EIA | Weekly Petroleum Status Report: Wednesday after the week ending Friday; a federal holiday Monday to Wednesday moves it one day later | **Derived** from EIA's stated rule in `services/api/app/data/eia_calendar.py` (erring late); dated exceptions to be added as EIA announces them |
| Euro area | ECB | Deposit rate dated each day (announced before it takes effect); M3 on the ECB monetary developments release, about the 28th of the next month, dated the last business day of that month | **Derived** in `services/api/app/data/ecb_calendar.py` (erring late); statistical calendar dates to replace the rule |
| Euro area | Eurostat | HICP flash around the end of the month, final around the 17th-19th of the next: history dated the 20th (next weekday), the newest flash from the day seen | **Derived** in `services/api/app/data/ecb_calendar.py` (erring late) |
| 24 economies | BIS (policy rates, effective exchange rates, credit-to-GDP) | Release calendar at bis.org/statistics/relcal.htm (2023 onwards): policy rates every Thursday of the month after, effective exchange rates on one Thursday between the 15th and 28th, credit 156 to 171 days after each quarter | **Derived** for all history in `services/api/app/data/bis_calendar.py`, erring late: last weekday of the following month (monthly), of the sixth month after the quarter (credit); tested against every listed date in `tests/test_bis.py` |
| United Kingdom | ONS | Labour market (monthly, mid-month), consumer prices (monthly, third week), GDP quarterly national accounts | **Derived** in `services/api/app/data/ons_calendar.py`, erring late: the last weekday of the second month after the period (labour), the next month (CPI), the sixth month from the quarter start (GDP). The ONS release calendar was read for the usual pattern only; exact dates are unverified |
| Euro area, Germany, France, Italy | Eurostat | Industrial production about six weeks after the month (September data on 13 November); final HICP in mid-month after | **Derived** in `services/api/app/data/eurostat_calendar.py`, erring late: last weekday of the second month after (production) and of the month after (HICP). The Eurostat release calendar was read for the usual pattern only |
| 50 economies added with the 85-country list | World Bank | Annual values added through the year as national offices report; 2025 was already present for most on 13 Nov 2026 | **Derived** in `services/api/app/data/worldbank_calendar.py`: each year dated 31 December of the year after, never early |
| 21 economies | IMF (International Liquidity) | No release calendar or dates: each month dated the last weekday of the second month after it; FRED copies use their ALFRED vintage dates | **Derived** in `services/api/app/data/imf_calendar.py` (erring late) |
| OECD members | OECD | Composite leading indicators and confidence: monthly, around mid-month; the API serves no release dates, so each month is dated the 15th of the second month after it (next weekday), late for most series and never early for slower ones | **Derived** in `services/api/app/data/oecd_calendar.py` (erring late) |
| United Kingdom | ONS, Bank of England | ONS release calendar; MPC dates | To confirm |
| Japan | Statistics Bureau, Bank of Japan | e-Stat release schedule; BoJ meeting schedule | To confirm |
| Canada | Statistics Canada, Bank of Canada | The Daily release schedule; BoC rate announcement dates | To confirm |
| Australia | ABS, RBA | ABS release calendar; RBA board meeting dates | To confirm |
| New Zealand | Stats NZ, RBNZ | Stats NZ release calendar; MPS dates | To confirm |
| Switzerland, Norway, Sweden, Denmark | SNB, Norges Bank, Riksbank, Danmarks Nationalbank and statistics offices | Each publisher's release calendar | To confirm |
| Czech Republic, Hungary, Poland | CNB, MNB, NBP and statistics offices | Each publisher's release calendar | To confirm |
| China | NBS, PBoC | NBS release calendar | To confirm |
| India | MoSPI, RBI | MoSPI advance release calendar; MPC dates | To confirm |
| Mexico, Brazil | INEGI, Banxico, IBGE, BCB | Each publisher's release calendar (Banxico SIE and BCB SGS APIs for data) | To confirm |
| Turkey, South Africa | TurkStat, TCMB, Stats SA, SARB | Each publisher's release calendar (TCMB EVDS API for data) | To confirm |
| Singapore, Hong Kong, South Korea | SingStat, MAS, C&SD, HKMA, KOSTAT, Bank of Korea | Each publisher's release calendar | To confirm |
| Saudi Arabia, UAE | GASTAT, SAMA, FCSC, CBUAE | Each publisher's release calendar | To confirm |

Holiday and shutdown rules follow the CFTC example: model the normal rule, list documented
exceptions, derive undocumented dates from the source's stated rule, and err late.
