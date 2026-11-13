"""The tier 3 registry (Rule O): the 23 national portals, the supranational ones, honest dates."""

from datetime import date

from app.data.country_sources import (
    COUNTRY_SOURCES,
    REGISTERED,
    SUPRANATIONAL,
    free_key_variables,
    portal_label,
)
from app.data.taxonomy import COUNTRY_BY_ISO3

NATIONAL = [
    "USA",
    "GBR",
    "FRA",
    "DEU",
    "ITA",
    "AUS",
    "CAN",
    "JPN",
    "MEX",
    "KOR",
    "TUR",
    "BRA",
    "IND",
    "ZAF",
    "CHN",
    "SGP",
    "SAU",
    "NOR",
    "CHE",
    "NZL",
    "ARG",
    "CHL",
    "COL",
]


def test_all_23_national_portals_and_the_three_regional_ones_are_registered():
    assert set(COUNTRY_SOURCES) == set(NATIONAL) and len(NATIONAL) == 23
    assert set(SUPRANATIONAL) == {"ECB", "UNECE", "WTO"}
    assert all(iso3 in COUNTRY_BY_ISO3 for iso3 in COUNTRY_SOURCES)


def test_every_portal_has_an_https_address_a_known_auth_type_and_a_key_name_when_it_needs_one():
    portals = [
        p for c in COUNTRY_SOURCES.values() for p in (c.statistics_office, c.central_bank) if p
    ]
    portals += list(SUPRANATIONAL.values())
    for p in portals:
        assert p.base_url.startswith(("https://", "http://")), p.name
        assert p.auth_type in {"keyless", "free_key", "bulk_file"}, p.name
        assert (p.env_var is not None) == (p.auth_type == "free_key"), p.name
        if p.env_var:
            assert p.env_var.startswith("QUFIN_") and p.env_var.isupper(), p.name


def test_no_terms_are_claimed_checked_that_were_not_read():
    """Only the ONS terms were read (13 Nov 2026); other dates stay empty until someone reads."""
    checked = {
        c.iso3: c.statistics_office.terms_checked
        for c in COUNTRY_SOURCES.values()
        if c.statistics_office.terms_checked
    }
    assert checked == {"GBR": date(2026, 11, 13)}
    assert all(c.registered == REGISTERED == date(2026, 11, 13) for c in COUNTRY_SOURCES.values())


def test_the_portals_in_use_say_so_and_carry_a_verification_date():
    assert COUNTRY_SOURCES["BRA"].central_bank.endpoint_verified == date(2026, 11, 13)
    assert COUNTRY_SOURCES["SGP"].statistics_office.endpoint_verified == date(2026, 11, 13)
    assert COUNTRY_SOURCES["GBR"].statistics_office.endpoint_verified == date(2026, 11, 13)


def test_the_label_names_the_portals_and_whether_terms_were_read():
    assert "Office for National Statistics" in portal_label("GBR")
    assert "checked 2026-11-13" in portal_label("GBR")
    assert "not yet read" in portal_label("DEU") and "Destatis" in portal_label("DEU")
    assert "UNECE" in portal_label("ISL")  # no national portal registered


def test_the_free_key_portals_name_their_env_settings():
    keys = free_key_variables()
    assert keys["Banxico SIE"] == "QUFIN_BANXICO_TOKEN" and keys["e-Stat"] == "QUFIN_ESTAT_APP_ID"
    assert len(set(keys.values())) == len(keys)  # one setting per portal
