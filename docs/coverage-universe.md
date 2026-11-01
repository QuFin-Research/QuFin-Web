# Coverage universe (draft for sign-off)

Backlog task P0-18: the 26 economies and ~40 instruments QuFin covers. **Status: draft.** The
Blueprint fixes the count (26 economies including the euro area) but not the list; the list below
is built from the central banks and statistics offices the Blueprint names. It needs sign-off from
the founder and the Head of Data Science before Phase 1 connectors are scheduled.

## Economies

| # | Economy | Currency | Central bank | Statistics office | Live in QuFin |
|---|---|---|---|---|---|
| 1 | United States | USD | Federal Reserve | BLS, BEA, Census | Yes (43 series) |
| 2 | Euro area | EUR | ECB | Eurostat | No |
| 3 | United Kingdom | GBP | Bank of England | ONS | No |
| 4 | Japan | JPY | Bank of Japan | Statistics Bureau (e-Stat) | No |
| 5 | Canada | CAD | Bank of Canada | Statistics Canada | No |
| 6 | Australia | AUD | RBA | ABS | No |
| 7 | New Zealand | NZD | RBNZ | Stats NZ | No |
| 8 | Switzerland | CHF | SNB | FSO | No |
| 9 | Norway | NOK | Norges Bank | Statistics Norway | No |
| 10 | Sweden | SEK | Riksbank | Statistics Sweden | No |
| 11 | Denmark | DKK | Danmarks Nationalbank | Statistics Denmark | No |
| 12 | Czech Republic | CZK | CNB | CZSO | No |
| 13 | Hungary | HUF | MNB | KSH | No |
| 14 | Poland | PLN | NBP | GUS | No |
| 15 | China | CNY | PBoC | NBS | No |
| 16 | India | INR | RBI | MoSPI | No |
| 17 | Mexico | MXN | Banxico | INEGI | No |
| 18 | Brazil | BRL | BCB | IBGE | No |
| 19 | Turkey | TRY | TCMB | TurkStat | No |
| 20 | South Africa | ZAR | SARB | Stats SA | No |
| 21 | Singapore | SGD | MAS | SingStat | No |
| 22 | Hong Kong | HKD | HKMA | C&SD | No |
| 23 | South Korea | KRW | Bank of Korea | KOSTAT | No |
| 24 | Saudi Arabia | SAR | SAMA | GASTAT | No |
| 25 | United Arab Emirates | AED | CBUAE | FCSC | No |
| 26 | Russia | RUB | CBR | Rosstat | No |

**Decisions needed**
- **Russia:** the Blueprint names the CBR, but sanctions may restrict data use and the rouble is
  hard to trade; replace with another economy (e.g. Israel, Chile or Indonesia) unless there is a
  reason to keep it.
- **Poland and South Korea** are proposed to complete 26; the Blueprint's list does not name them.
- **GCC:** Saudi Arabia and the UAE are included per the Blueprint's note on MENA; others
  (Qatar, Kuwait) can follow.

## Instruments (~40)

| Class | Instruments |
|---|---|
| FX majors | EURUSD, GBPUSD, USDJPY, USDCHF, AUDUSD, USDCAD, NZDUSD |
| FX crosses | EURGBP, EURJPY, GBPJPY, EURCHF, AUDJPY, EURAUD, CADJPY |
| FX minors and exotics | USDNOK, USDSEK, USDDKK, EURPLN, EURHUF, EURCZK, USDMXN, USDBRL, USDTRY, USDZAR, USDCNH, USDINR, USDSGD, USDHKD, USDKRW, USDSAR |
| Metals | XAUUSD, XAGUSD, XPTUSD, copper |
| Energy | WTI, Brent, natural gas |
| Crypto | BTCUSD, ETHUSD |

Today the app covers 11 of these with sample prices and live CFTC positioning; real prices come
first from FRED H.10 and ECB reference rates (P1-25), then a licensed feed.
