"""Tier 3 of the source cascade (Rule O): each economy's official national portals.

Where FRED (tier 1) and the multilateral aggregators (tier 2) lack an indicator or only have a
frozen mirror, QuFin goes to the country's statistics office or central bank. This registry says
which portals those are, how to authenticate, and what has actually been checked. Nothing here is
a connector: a portal gets one only after its terms and limits are read and recorded in
`docs/data-connections.md` and `docs/licence-register.md` (rules 7 and 28).

Three dates keep the record honest:

- `registered` is when the entry was written (13 Nov 2026), from general knowledge of the portals;
- `terms_checked` is when a person or this project read the supplier's terms (None until then);
- `endpoint_verified` is when a live request to the API succeeded (None until then).

`env_var` names the `.env` setting a `free_key` portal needs. QuFin's naming is used, so the names
are exact; the registration page of each supplier was not looked up.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

AuthType = Literal["keyless", "free_key", "bulk_file"]
REGISTERED = date(2026, 11, 13)


@dataclass(frozen=True)
class Portal:
    name: str
    base_url: str
    auth_type: AuthType
    env_var: str | None = None  # the .env setting, for free_key portals
    terms_checked: date | None = None
    endpoint_verified: date | None = None
    note: str = ""


@dataclass(frozen=True)
class CountrySources:
    iso3: str
    statistics_office: Portal
    central_bank: Portal | None = None
    registered: date = REGISTERED


def _p(
    name: str,
    url: str,
    auth: AuthType,
    env: str | None = None,
    *,
    terms: date | None = None,
    verified: date | None = None,
    note: str = "",
) -> Portal:
    return Portal(name, url, auth, env, terms, verified, note)


_CHECKED = date(2026, 11, 13)
_SOURCES: tuple[CountrySources, ...] = (
    CountrySources(
        "USA",
        _p(
            "BLS, BEA and Census",
            "https://api.bls.gov/publicAPI/v2",
            "free_key",
            "QUFIN_BLS_API_KEY",
            note="BLS key optional; BEA key is QUFIN_BEA_API_KEY; FRED comes first (tier 1)",
        ),
        _p(
            "Federal Reserve (via FRED)",
            "https://api.stlouisfed.org/fred",
            "free_key",
            "QUFIN_FRED_API_KEY",
        ),
    ),
    CountrySources(
        "GBR",
        _p(
            "Office for National Statistics",
            "https://www.ons.gov.uk",
            "keyless",
            terms=_CHECKED,
            verified=_CHECKED,
            note="in use: unemployment, GDP, core CPI, goods trade",
        ),
        _p("Bank of England", "https://www.bankofengland.co.uk/boeapps/database", "keyless"),
    ),
    CountrySources(
        "FRA",
        _p("INSEE", "https://api.insee.fr", "free_key", "QUFIN_INSEE_API_KEY"),
        _p(
            "Banque de France Webstat",
            "https://webstat.banque-france.fr",
            "free_key",
            "QUFIN_BDF_API_KEY",
        ),
    ),
    CountrySources(
        "DEU",
        _p(
            "Destatis GENESIS",
            "https://www-genesis.destatis.de/genesisWS",
            "free_key",
            "QUFIN_DESTATIS_API_KEY",
        ),
        _p("Deutsche Bundesbank", "https://api.statistiken.bundesbank.de", "keyless"),
    ),
    CountrySources(
        "ITA",
        _p("ISTAT", "https://esploradati.istat.it/SDMXWS", "keyless"),
        _p("Banca d'Italia", "https://infostat.bancaditalia.it", "bulk_file"),
    ),
    CountrySources(
        "AUS",
        _p("Australian Bureau of Statistics", "https://data.api.abs.gov.au", "keyless"),
        _p("Reserve Bank of Australia", "https://www.rba.gov.au/statistics", "bulk_file"),
    ),
    CountrySources(
        "CAN",
        _p("Statistics Canada", "https://www150.statcan.gc.ca/t1/wds/rest", "keyless"),
        _p("Bank of Canada Valet", "https://www.bankofcanada.ca/valet", "keyless"),
    ),
    CountrySources(
        "JPN",
        _p("e-Stat", "https://api.e-stat.go.jp", "free_key", "QUFIN_ESTAT_APP_ID"),
        _p("Bank of Japan", "https://www.stat-search.boj.or.jp", "bulk_file"),
    ),
    CountrySources(
        "MEX",
        _p("INEGI", "https://www.inegi.org.mx/app/api", "free_key", "QUFIN_INEGI_TOKEN"),
        _p(
            "Banxico SIE",
            "https://www.banxico.org.mx/SieAPIRest",
            "free_key",
            "QUFIN_BANXICO_TOKEN",
        ),
    ),
    CountrySources(
        "KOR",
        _p("KOSIS", "https://kosis.kr/openapi", "free_key", "QUFIN_KOSIS_API_KEY"),
        _p("Bank of Korea ECOS", "https://ecos.bok.or.kr/api", "free_key", "QUFIN_ECOS_API_KEY"),
    ),
    CountrySources(
        "TUR",
        _p("TurkStat", "https://data.tuik.gov.tr", "bulk_file"),
        _p("CBRT EVDS", "https://evds2.tcmb.gov.tr/service/evds", "free_key", "QUFIN_EVDS_API_KEY"),
    ),
    CountrySources(
        "BRA",
        _p("IBGE SIDRA", "https://apisidra.ibge.gov.br", "keyless"),
        _p(
            "Banco Central do Brasil SGS",
            "https://api.bcb.gov.br",
            "keyless",
            verified=_CHECKED,
            note="in use: unemployment (24369) and goods trade balance (22707); terms not read",
        ),
    ),
    CountrySources(
        "IND",
        _p("MoSPI", "https://mospi.gov.in", "bulk_file"),
        _p("Reserve Bank of India DBIE", "https://data.rbi.org.in", "bulk_file"),
    ),
    CountrySources(
        "ZAF",
        _p("Statistics South Africa", "https://www.statssa.gov.za", "bulk_file"),
        _p("South African Reserve Bank", "https://www.resbank.co.za", "bulk_file"),
    ),
    CountrySources(
        "CHN",
        _p("National Bureau of Statistics", "https://data.stats.gov.cn", "bulk_file"),
        _p("People's Bank of China", "http://www.pbc.gov.cn", "bulk_file"),
    ),
    CountrySources(
        "SGP",
        _p(
            "SingStat Table Builder",
            "https://tablebuilder.singstat.gov.sg",
            "keyless",
            verified=_CHECKED,
            note="in use: unemployment (table M182342); terms not read",
        ),
        _p(
            "Monetary Authority of Singapore",
            "https://eservices.mas.gov.sg/apimg-portal",
            "free_key",
            "QUFIN_MAS_API_KEY",
        ),
    ),
    CountrySources(
        "SAU",
        _p("GASTAT", "https://www.stats.gov.sa", "bulk_file"),
        _p("SAMA", "https://www.sama.gov.sa", "bulk_file"),
    ),
    CountrySources(
        "NOR",
        _p("Statistics Norway", "https://data.ssb.no/api", "keyless"),
        _p("Norges Bank", "https://data.norges-bank.no/api", "keyless"),
    ),
    CountrySources(
        "CHE",
        _p("Federal Statistical Office", "https://www.bfs.admin.ch", "bulk_file"),
        _p("Swiss National Bank", "https://data.snb.ch/api", "keyless"),
    ),
    CountrySources(
        "NZL",
        _p("Stats NZ", "https://api.stats.govt.nz", "free_key", "QUFIN_STATSNZ_API_KEY"),
        _p("Reserve Bank of New Zealand", "https://www.rbnz.govt.nz/statistics", "bulk_file"),
    ),
    CountrySources(
        "ARG",
        _p("INDEC (Series de Tiempo)", "https://apis.datos.gob.ar/series", "keyless"),
        _p("BCRA", "https://api.bcra.gob.ar", "keyless"),
    ),
    CountrySources(
        "CHL",
        _p("Instituto Nacional de Estadisticas", "https://www.ine.gob.cl", "bulk_file"),
        _p(
            "Banco Central de Chile BDE",
            "https://si3.bcentral.cl/SieteRestWS",
            "free_key",
            "QUFIN_BCCH_API_KEY",
        ),
    ),
    CountrySources(
        "COL",
        _p("DANE", "https://www.dane.gov.co", "bulk_file"),
        _p("Banco de la Republica", "https://www.banrep.gov.co", "bulk_file"),
    ),
)
COUNTRY_SOURCES: dict[str, CountrySources] = {c.iso3: c for c in _SOURCES}

# Regional and multilateral portals used where a country has no registered national one.
SUPRANATIONAL: dict[str, Portal] = {
    "ECB": _p(
        "ECB Data Portal",
        "https://data-api.ecb.europa.eu",
        "keyless",
        note="in use for the euro area; terms not read",
    ),
    "UNECE": _p("UNECE Statistical Database", "https://w3.unece.org/PXWeb", "keyless"),
    "WTO": _p("WTO Stats API", "https://api.wto.org", "free_key", "QUFIN_WTO_API_KEY"),
}


def portal_label(iso3: str) -> str:
    """The Tier 3 portal to try for a country, with what is known about it (for the doctor)."""
    entry = COUNTRY_SOURCES.get(iso3)
    if entry is None:
        return "no national portal registered; UNECE and WTO portals"
    names = [entry.statistics_office.name]
    if entry.central_bank is not None:
        names.append(entry.central_bank.name)
    checked = entry.statistics_office.terms_checked
    return f"{' / '.join(names)}; registered {entry.registered}; terms " + (
        f"checked {checked}" if checked else "not yet read"
    )


def free_key_variables() -> dict[str, str]:
    """The `.env` settings the registered free_key portals need, by portal name."""
    portals = [p for c in _SOURCES for p in (c.statistics_office, c.central_bank) if p]
    return {p.name: p.env_var for p in portals if p.auth_type == "free_key" and p.env_var}
