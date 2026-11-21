"""Candidate sources: series that publish a pair another series serves (rules 37 and 38).

A candidate is loaded without being served (`staged`, Part 0) so its release timing can be measured
against the series that serves the pair, over a release cycle. It is not in the catalog: nothing
refreshes it as a served series, the API never returns it, and the duplicate check and the scorecard
leave it out. If it wins, a reviewed pull request adds it to the catalog and records the source
decision (rules 26 and 38).

The registry holds the pairs the measures still decide: the United States and every economy
Eurostat does not serve. Slice 1 staged 32 IMF consumer price series for the pairs moved to
Eurostat's HICP on 19 Nov 2026; rule 38's *Bloc aggregator first* (v3.5) makes Eurostat the source
of those pairs whatever the IMF's timing, so they were removed. Candidates are added here as other
pairs are measured.
"""

from dataclasses import dataclass

from app.data.gap_ids import HICP_GEO
from app.data.indicator_concepts import SERIES_CONCEPTS
from app.domain.source_selection import Producer

PREFIX = "CAND_"


@dataclass(frozen=True)
class Candidate:
    id: str  # CAND_<SOURCE>_<MEASURE>_<AREA>: never a catalog id
    country: str  # ISO 3166 alpha-2
    concept: str
    source: str
    producer: Producer  # how native it is for this economy (Part 0)
    area: str  # the source's own area code
    serves: str  # the series serving the pair now
    flow: str  # the source's dataset
    key: str  # the source's series key (FRED: the series id)
    months: int = 1  # months in a period: 1 monthly, 3 quarterly
    # A gap candidate has nothing to be timed against (`serves` is empty) and describes
    # itself; one that is timed copies its description from the series it serves.
    title: str = ""
    units: str = ""
    adjustment: str = ""
    dimension: str = ""
    cycle: str = ""
    frequency: str = "Monthly"


CANDIDATES: tuple[Candidate, ...] = (
    # The United States' commercial property prices: the BIS serves the pair (provisional since
    # 19 Nov 2026); FRED's copy of the IMF's financial soundness indicator is the rival (rule 38).
    Candidate(
        id="CAND_FRED_CPP_US",
        country="US",
        concept="commercial_property_prices",
        source="fred",
        producer="bloc",
        area="US",
        serves="BIS_CPP_US",
        flow="",
        key="COMREPUSQ159N",
        months=3,
    ),
)

# FRED serves these United States series, chosen under the retired rule 17 (FRED first). The BLS is
# the original producer of each; its own series (ids checked live on 21 Nov 2026) is the candidate.
# FRED series id -> (BLS series id, months in a period).
_BLS_RIVALS: dict[str, tuple[str, int]] = {
    "PAYEMS": ("CES0000000001", 1),  # all employees, total nonfarm
    "UNRATE": ("LNS14000000", 1),  # unemployment rate
    "UEMPMEAN": ("LNS13008275", 1),  # average weeks unemployed
    "AWHMAN": ("CES3000000007", 1),  # average weekly hours, manufacturing
    "CPIAUCSL": ("CUSR0000SA0", 1),  # CPI, all items
    "CPILFESL": ("CUSR0000SA0L1E", 1),  # CPI, all items less food and energy
    "CUSR0000SAS": ("CUSR0000SAS", 1),  # CPI, services
    "PPIFIS": ("WPSFD4", 1),  # PPI, final demand
    "JTSJOL": ("JTS000000000000000JOL", 1),  # job openings
    "JTSQUR": ("JTS000000000000000QUR", 1),  # quits rate
    "ECIALLCIV": ("CIS1010000000000I", 3),  # employment cost index, civilian (quarterly)
}
CANDIDATES = (
    *CANDIDATES,
    *(
        Candidate(
            id=f"{PREFIX}BLS_{fred_id}_US",
            country="US",
            concept=SERIES_CONCEPTS[("US", fred_id)],
            source="bls",
            producer="original",
            area="US",
            serves=fred_id,
            flow="",
            key=bls_id,
            months=months,
        )
        for fred_id, (bls_id, months) in _BLS_RIVALS.items()
    ),
)

# Gaps the discovery probe found on 21 Nov 2026 (`discover`, rule 34): series a source publishes
# currently for an economy QuFin holds nothing for. Each is loaded as `staged`, never served, until
# a reviewed pull request verifies its eligibility (rules 26 and 34). Eurostat's economies are
# Eurostat's to serve (rule 38, Bloc aggregator first); the OECD fills the others.
_ESTAT_CORE = (
    "AL",
    "AT",
    "BE",
    "BG",
    "CH",
    "CY",
    "CZ",
    "DK",
    "EE",
    "ES",
    "FI",
    "GR",
    "HR",
    "HU",
    "IE",
    "IS",
    "LT",
    "LU",
    "LV",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SE",
    "SI",
    "SK",
    "TR",
    "XK",
)
_ESTAT_IP = (
    "AT",
    "BE",
    "BG",
    "CH",
    "CY",
    "CZ",
    "DK",
    "EE",
    "ES",
    "FI",
    "GR",
    "HR",
    "HU",
    "IE",
    "LT",
    "LU",
    "LV",
    "ME",
    "MK",
    "MT",
    "NL",
    "NO",
    "PL",
    "PT",
    "RO",
    "RS",
    "SE",
    "SI",
    "SK",
    "TR",
)
_OECD_CORE = {"AU": "AUS"}
_OECD_IP = {"GB": "GBR", "CA": "CAN", "IN": "IND", "MX": "MEX", "BR": "BRA", "CL": "CHL"}
_OECD_MONEY = {
    "GB": "GBR",
    "JP": "JPN",
    "CA": "CAN",
    "AU": "AUS",
    "NO": "NOR",
    "HU": "HUN",
    "ZA": "ZAF",
    "KR": "KOR",
    "IS": "ISL",
    "CO": "COL",
}


def _estat_key(geo_filters: dict[str, str]) -> str:
    return ",".join(f"{k}={v}" for k, v in geo_filters.items())


_CORE = {"freq": "M", "unit": "RCH_A", "coicop18": "TOT_X_NRG_FOOD"}
_IP = {"freq": "M", "indic_bt": "PRD", "nace_r2": "B-D", "s_adj": "SCA", "unit": "I21"}
_OECD_FLOW = "OECD.SDD.STES,DSD_STES@"
GAP_CANDIDATES: tuple[Candidate, ...] = (
    *(
        Candidate(
            id=f"{PREFIX}ESTAT_CORE_{iso2}",
            country=iso2,
            concept="core_consumer_prices",
            source="eurostat",
            producer="bloc",
            area=HICP_GEO[iso2],
            serves="",
            flow="prc_hicp_minr",
            key=_estat_key({**_CORE, "geo": HICP_GEO[iso2]}),
            title=f"HICP excluding energy, food, alcohol and tobacco: annual rate, {iso2}",
            units="Percentage change",
            adjustment="Not Seasonally Adjusted",
            dimension="inflation",
            cycle="lagging",
        )
        for iso2 in _ESTAT_CORE
    ),
    *(
        Candidate(
            id=f"{PREFIX}ESTAT_IP_{iso2}",
            country=iso2,
            concept="industrial_production",
            source="eurostat",
            producer="bloc",
            area=HICP_GEO[iso2],
            serves="",
            flow="sts_inpr_m",
            key=_estat_key({**_IP, "geo": HICP_GEO[iso2]}),
            title=f"Production in industry, seasonally and calendar adjusted, {iso2}",
            units="Index, 2021=100",
            adjustment="Seasonally and Calendar Adjusted",
            dimension="growth",
            cycle="coincident",
        )
        for iso2 in _ESTAT_IP
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_CORE_{iso3}",
            country=iso2,
            concept="core_consumer_prices",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow="OECD.SDD.TPS,DSD_PRICES@DF_PRICES_ALL,",
            key=f"{iso3}.M.N.CPI.IX._TXCP01_NRG.N._Z",
            title=f"CPI excluding food and energy, index, {iso2}",
            units="Index",
            adjustment="Not Seasonally Adjusted",
            dimension="inflation",
            cycle="lagging",
        )
        for iso2, iso3 in _OECD_CORE.items()
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_IP_{iso3}",
            country=iso2,
            concept="industrial_production",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow=f"{_OECD_FLOW}DF_INDSERV,",
            key=f"{iso3}.M.PRVM.IX.BTE.Y._Z._Z.N",
            title=f"Production volume, industry excluding construction, {iso2}",
            units="Index",
            adjustment="Seasonally Adjusted",
            dimension="growth",
            cycle="coincident",
        )
        for iso2, iso3 in _OECD_IP.items()
    ),
    *(
        Candidate(
            id=f"{PREFIX}OECD_MONEY_{iso3}",
            country=iso2,
            concept="money_supply",
            source="oecd",
            producer="global",
            area=iso3,
            serves="",
            flow=f"{_OECD_FLOW}DF_MONAGG,",
            key=f"{iso3}.M.MABM.XDC._Z.Y._Z._Z.N",
            title=f"Broad money, national currency, {iso2}",
            units="National currency",
            adjustment="Seasonally Adjusted",
            dimension="policy",
            cycle="leading",
        )
        for iso2, iso3 in _OECD_MONEY.items()
    ),
)
CANDIDATES = (*CANDIDATES, *GAP_CANDIDATES)
CANDIDATE_BY_ID = {c.id: c for c in CANDIDATES}
