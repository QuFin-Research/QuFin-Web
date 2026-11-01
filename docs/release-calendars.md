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
| United States | BLS | BLS release schedule | To confirm |
| United States | BEA | BEA release schedule | To confirm |
| United States | Census | Economic indicators calendar | To confirm |
| United States | Federal Reserve Board | H.4.1, H.8, H.15, G.17, G.19 statistical release dates; FOMC calendar | To confirm |
| United States | EIA | Weekly Petroleum Status Report schedule | To confirm |
| Euro area | ECB | Statistical calendar; monetary policy meeting calendar | To confirm |
| Euro area | Eurostat | Euro indicators release calendar | To confirm |
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
