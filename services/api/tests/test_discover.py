"""Rule 34: the discovery probe reports what each source publishes and stores nothing."""

# Fixtures imported from test_macro_api are used by name, which ruff reads as redefinition.
# ruff: noqa: F811

import time
from datetime import date
from types import SimpleNamespace

from app.connectors.eurostat import EurostatError
from app.connectors.sdmx import SdmxError
from app.data.probes import PROBES, Probe
from app.jobs import discover
from app.stores.macro import MacroStore
from tests.test_macro_api import db_session  # noqa: F401  (fixture)

TODAY = date(2026, 11, 21)
OECD = Probe("money_supply", "oecd", "m", flow="F", key=".M.X")
EUROSTAT = Probe("core_consumer_prices", "eurostat", "c", dataset="ds", filters={"freq": "M"})


class FakeOecd:
    def __init__(self, result=None, error=None):
        self.result, self.error = result, error

    def _data(self, flow, key, start):
        if self.error:
            raise self.error
        return self.result


def fake_series(area_last):
    """parse_all is exercised elsewhere; here it is replaced by ready-made series."""
    return [
        SimpleNamespace(
            dimensions={"REF_AREA": area}, observations=[(date(2026, 1, 1), 1.0), (last, 2.0)]
        )
        for area, last in area_last.items()
    ]


def test_an_oecd_wildcard_answers_for_every_economy_and_maps_the_euro_area(monkeypatch):
    monkeypatch.setattr(
        discover,
        "parse_all",
        lambda *a: fake_series({"JPN": date(2026, 9, 1), "EA20": date(2026, 2, 1), "ZZZ": TODAY}),
    )
    found = discover.probe_oecd(FakeOecd({}), OECD, {"money_supply": {"JPN"}}, TODAY)
    by = {f.iso3: f for f in found}
    assert by["JPN"].status == "published" and by["JPN"].current and by["JPN"].held
    assert by["EMU"].status == "published" and not by["EMU"].current  # February is behind
    assert by["USA"].status == "absent" and not by["USA"].bloc_first
    assert len(found) == len(
        {f.iso3 for f in found}
    )  # one finding per economy, unknown areas dropped


def test_an_oecd_404_means_nothing_matches_and_any_other_error_fails_every_economy():
    absent = discover.probe_oecd(
        FakeOecd(error=SdmxError("oecd returned 404: Not Found")), OECD, {}, TODAY
    )
    assert {f.status for f in absent} == {"absent"}
    failed = discover.probe_oecd(FakeOecd(error=SdmxError("oecd returned 429")), OECD, {}, TODAY)
    assert {f.status for f in failed} == {"failed"} and failed[0].detail


class FakeEurostat:
    def __init__(self, last=date(2026, 10, 1), missing=(), broken=()):
        self.last, self.missing, self.broken = last, missing, broken

    def series(self, dataset, filters, start, **kwargs):
        self.kwargs = kwargs
        if filters["geo"] in self.missing:
            raise EurostatError("Eurostat returned no observations")
        if filters["geo"] in self.broken:
            raise EurostatError("The selection holds more than one series")
        return SimpleNamespace(observations=[(self.last, 1.0)])


def test_eurostat_is_asked_for_each_economy_it_serves_and_would_serve_them_first():
    found = discover.probe_eurostat(
        FakeEurostat(missing=("AL",), broken=("IS",)), EUROSTAT, {}, TODAY, time.monotonic() + 60
    )
    by = {f.iso3: f for f in found}
    assert by["DEU"].status == "published" and by["DEU"].current and by["DEU"].bloc_first
    assert by["ALB"].status == "absent" and by["ISL"].status == "failed"
    assert len(found) == 36  # the economies Eurostat serves


def test_residential_property_probe_uses_eurostats_quarterly_total_hpi():
    probe = next(
        p for p in PROBES if p.concept == "residential_property_prices" and p.source == "eurostat"
    )
    assert probe.dataset == "prc_hpi_q"
    assert probe.filters == {"freq": "Q", "purchase": "TOTAL", "unit": "I15_Q"}
    assert probe.quarterly
    client = FakeEurostat(last=date(2026, 4, 1))
    found = discover.probe_eurostat(client, probe, {}, TODAY, time.monotonic() + 60)
    assert len(found) == 36 and client.kwargs == {"quarterly": True}


def test_a_sweep_out_of_time_marks_the_rest_pending_not_failed():
    found = discover.probe_eurostat(FakeEurostat(), EUROSTAT, {}, TODAY, time.monotonic() - 1)
    assert {f.status for f in found} == {"pending"}


def test_the_sweep_reports_held_pairs_limits_to_concepts_and_stores_nothing(
    db_session, monkeypatch
):
    monkeypatch.setattr(discover, "parse_all", lambda *a: fake_series({"JPN": TODAY}))
    clients = {"oecd": FakeOecd({}), "eurostat": FakeEurostat(), "bis": FakeBis()}
    before = len(MacroStore(db_session).list_series(("staged", "live")))
    only_money = discover.sweep(clients, db_session, ["money_supply"], TODAY)
    assert {f.concept for f in only_money} == {"money_supply"}
    everything = discover.sweep(clients, db_session, None, TODAY)
    assert {f.concept for f in everything} == {p.concept for p in PROBES}
    assert discover.sweep({}, db_session, None, TODAY) == []  # no client, no probe
    assert len(MacroStore(db_session).list_series(("staged", "live"))) == before


def test_the_report_counts_current_behind_absent_and_new():
    findings = [
        discover.Finding("c", "oecd", "AAA", "published", TODAY, current=True),
        discover.Finding("c", "oecd", "BBB", "published", date(2025, 1, 1)),
        discover.Finding("c", "oecd", "CCC", "published", TODAY, current=True, held=True),
        discover.Finding("c", "oecd", "DDD", "absent"),
        discover.Finding("c", "eurostat", "EEE", "pending"),
    ]
    summary = discover.summarize(findings)["c"]
    assert summary["oecd"] == {
        "current": 2, "behind": 1, "absent": 1, "pending": 0, "failed": 0, "new": 1,
    }  # fmt: skip
    assert summary["eurostat"]["pending"] == 1
    text = discover.format_report(findings)
    assert "nothing was stored" in text and "1 pending" in text


def test_the_findings_are_written_to_csv(tmp_path):
    path = tmp_path / "out.csv"
    discover.write_csv([discover.Finding("c", "oecd", "AAA", "published", TODAY, True)], path)
    head, row = path.read_text(encoding="utf-8").splitlines()[:2]
    assert head.startswith("concept,source,iso3,status") and row.startswith("c,oecd,AAA,published")


BIS = Probe("household_credit_to_gdp", "bis", "h", flow="WS_TC", key="Q..H", months=18)


class FakeBis:
    def __init__(self, series=(), error=None):
        self.series, self.error, self.asked = series, error, []

    def many(self, flow, key, start, version):
        self.asked.append((flow, key, version))
        if self.error:
            raise self.error
        return list(self.series)


def test_a_bis_wildcard_maps_two_letter_areas_and_gives_a_quarter_a_longer_window():
    series = [
        SimpleNamespace(dimensions={"REF_AREA": area}, observations=[(date(2026, 1, 1), 1.0)])
        for area in ("US", "XM", "ZZ")
    ]
    client = FakeBis(series)
    found = discover.probe_bis(client, BIS, {"household_credit_to_gdp": {"USA"}}, TODAY)
    by = {f.iso3: f for f in found}
    assert by["USA"].status == "published" and by["USA"].current and by["USA"].held
    assert by["EMU"].status == "published"  # the BIS's XM is the euro area
    assert by["JPN"].status == "absent" and client.asked == [("WS_TC", "Q..H", "1.0")]
    assert not discover._finding(Probe("x", "bis", "n"), "USA", {}, date(2026, 1, 1), TODAY).current


def test_a_bis_error_fails_every_economy_without_stopping_the_sweep():
    found = discover.probe_bis(FakeBis(error=SdmxError("bis returned 500")), BIS, {}, TODAY)
    assert {f.status for f in found} == {"failed"}


def test_every_bis_probe_leaves_the_economy_open_and_names_a_known_concept():
    from app.data.indicator_concepts import CONCEPTS

    bis = [p for p in PROBES if p.source == "bis"]
    assert len(bis) >= 15
    for p in bis:
        assert "{" not in p.key and p.concept in CONCEPTS and p.flow


def test_a_quarterly_eurostat_probe_asks_for_a_quarter_and_a_longer_window():
    quarterly = Probe(
        "real_gdp", "eurostat", "g", dataset="namq_10_gdp", filters={"freq": "Q"}, months=18,
        quarterly=True,
    )  # fmt: skip
    client = FakeEurostat(last=date(2026, 7, 1))
    found = discover.probe_eurostat(client, quarterly, {}, TODAY, time.monotonic() + 60)
    assert client.kwargs == {"quarterly": True}
    assert all(f.current for f in found if f.status == "published")  # 2026 Q3 within 345 days


def test_the_macro_flow_probes_name_trade_the_current_account_and_real_gdp():
    probes = [
        p for p in PROBES if p.concept in ("real_gdp", "current_account_to_gdp", "trade_balance")
    ]
    assert {(p.concept, p.source) for p in probes} >= {
        ("real_gdp", "oecd"), ("real_gdp", "eurostat"), ("current_account_to_gdp", "oecd"),
        ("current_account_to_gdp", "eurostat"), ("trade_balance", "oecd"),
    }  # fmt: skip
    for p in probes:
        assert p.months and (p.source != "oecd" or p.key.count(".") >= 7)
