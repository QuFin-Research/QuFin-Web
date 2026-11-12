"""Consumer prices and unemployment for the countries the US series do not cover (P1-23).

The two indicators every country comparison starts with, each in the form that can be compared
across countries (rule 22/23):

- consumer prices as the annual rate of change the statistics office's own index implies
  (published as a change, so it is never changed again; the US stores the index and is compared
  on its year-on-year change, see `COMPARED_AS`);
- unemployment as a percentage of the labour force, seasonally adjusted, on the OECD's
  harmonised definition (International Labour Organization, ages 15 and over), never a head count.

Consumer prices come from the IMF Consumer Price Index dataflow (one source and one definition for
every country: the national index's year-on-year change) and unemployment from the OECD's
harmonised monthly series (one fully specified request per series; the OECD returns broken partial
histories for multi-series queries). Both are keyless and were checked live on 12 Nov 2026.
Kept apart from the catalog so the cycle classification, concepts and tests can use it too.

Left out, and why:

- the United States and the euro area: their CPI and unemployment are already stored (CPIAUCSL,
  UNRATE and the ECB's HICP); a second copy would be duplicated data (rule 16);
- unemployment for countries without a monthly harmonised series: only quarterly or annual rates
  exist for them, which would sit next to monthly ones on the same page; they come with the
  national-source batch (P1-24).
"""

from dataclasses import dataclass
from typing import Literal

Indicator = Literal["UNE"]

# OECD (and IMF) area code -> QuFin country code, for the countries this batch adds.
ISO3_TO_ISO2: dict[str, str] = {
    "DEU": "DE",
    "FRA": "FR",
    "ITA": "IT",
    "GBR": "GB",
    "JPN": "JP",
    "CAN": "CA",
    "AUS": "AU",
    "KOR": "KR",
    "MEX": "MX",
    "TUR": "TR",
    "POL": "PL",
    "CHE": "CH",
    "SWE": "SE",
    "DNK": "DK",
    "NOR": "NO",
    "CZE": "CZ",
    "HUN": "HU",
    "NZL": "NZ",
    "ARG": "AR",
    "IDN": "ID",
    "IND": "IN",
    "BRA": "BR",
    "CHN": "CN",
    "ZAF": "ZA",
    "RUS": "RU",
    "SAU": "SA",
    "KWT": "KW",
    "QAT": "QA",
    "BHR": "BH",
    "OMN": "OM",
    "ARE": "AE",
    "SGP": "SG",
    "HKG": "HK",
}

# Who publishes what, as live on 12 Nov 2026 (one request per area, 2000 onwards, no missing
# months). Areas absent from a tuple were checked and are not available from that source.
# IMF CPI: every candidate except New Zealand (the IMF answers 400: New Zealand publishes its CPI
# quarterly), Qatar (latest month August 2025) and the United Arab Emirates (December 2025):
# without a live release schedule a series stays out (rule 1). Australia's monthly CPI only
# began in late 2024, so it has 17 months. Kuwait loaded but the release check marked it overdue
# (latest month June 2026, due 30 Sept): it joins when the IMF catches up.
IMF_CPI_AREAS: tuple[str, ...] = tuple(
    a for a in ISO3_TO_ISO2 if a not in {"NZL", "QAT", "ARE", "KWT"}
)
# OECD unemployment (monthly, seasonally adjusted, ILO definition). Not available monthly for
# Switzerland, New Zealand, Argentina, Indonesia, India, Brazil, China, South Africa, Russia, the
# Gulf states, Singapore or Hong Kong (the OECD answers 404); Turkey's series starts in 2005.
# The United Kingdom loaded but the release check marked it overdue (latest month July 2026, due
# 15 Oct: the OECD's copy of the ONS release runs a month behind its other countries): it joins
# when the OECD catches up.
OECD_UNE_AREAS: tuple[str, ...] = (
    "DEU", "FRA", "ITA", "JPN", "CAN", "AUS", "KOR", "MEX", "TUR", "POL", "SWE", "DNK",
    "NOR", "CZE", "HUN",
)  # fmt: skip


@dataclass(frozen=True)
class OecdMacro:
    indicator: Indicator
    area: str  # OECD / ISO3 area code


UNE_FLOW = "OECD.SDD.TPS,DSD_LFS@DF_IALFS_UNE_M,"
# REF_AREA.MEASURE.UNIT_MEASURE.TRANSFORMATION.ADJUSTMENT.SEX.AGE.ACTIVITY.FREQ
# Unemployment rate, percent of the labour force, seasonally adjusted, both sexes, 15 and over.
UNE_KEY = "{area}.UNE_LF_M.PT_LF_SUB._Z.Y._T.Y_GE15._Z.M"

# IMF Consumer Price Index dataflow: all items, year-on-year percent change, monthly.
IMF_CPI_FLOW = "IMF.STA,CPI,5.0.0"
IMF_CPI_KEY = "{area}.CPI._T.YOY_PCH_PA_PT.M"

OECD_MACRO: dict[str, OecdMacro] = {f"OECD_UNE_{a}": OecdMacro("UNE", a) for a in OECD_UNE_AREAS}
IMF_CPI: dict[str, str] = {f"IMF_CPI_{a}": a for a in IMF_CPI_AREAS}

MACRO_COUNTRY: dict[str, str] = {
    sid: ISO3_TO_ISO2[spec.area] for sid, spec in OECD_MACRO.items()
} | {sid: ISO3_TO_ISO2[area] for sid, area in IMF_CPI.items()}
