"""The connector framework, the raw zone and the reference-price catalog."""

import json
from datetime import UTC, datetime

import httpx
import pytest

from app.connectors.base import HttpSource, SourceError
from app.connectors.cftc import CftcClient
from app.connectors.fred import FredClient
from app.data.macro_catalog import BY_ID
from app.data.price_catalog import NO_FREE_SOURCE, PRICE_SERIES
from app.data.scorecard_catalog import SCORED
from app.stores.raw_zone import RawZone

NOW = datetime(2026, 11, 1, 6, 0, 0, tzinfo=UTC)


# --- raw zone -------------------------------------------------------------------------------


def test_raw_zone_keeps_each_payload_once_with_a_checksum(tmp_path):
    zone = RawZone(tmp_path)
    first = zone.save("fred", "UNRATE-observations", b'{"a": 1}', now=NOW)
    assert first.path.read_bytes() == b'{"a": 1}'
    assert first.path.parent == tmp_path / "fred" / "2026-11-01"
    again = zone.save("fred", "UNRATE-observations", b'{"a": 1}', now=NOW)
    assert again.path == first.path  # same bytes, same second: not written twice
    other = zone.save("fred", "UNRATE-observations", b'{"a": 2}', now=NOW)
    assert other.path != first.path  # different content never overwrites
    lines = [json.loads(x) for x in (tmp_path / "manifest.jsonl").read_text().splitlines()]
    assert lines[0]["sha256"] == first.sha256
    assert lines[0]["path"] == "fred/2026-11-01/" + first.path.name


def test_raw_zone_names_are_safe_on_disk(tmp_path):
    saved = RawZone(tmp_path).save("cftc", "088691/../../x", b"[]", now=NOW)
    assert saved.path.resolve().is_relative_to(tmp_path.resolve())


# --- shared HTTP base -------------------------------------------------------------------------


def test_connectors_save_response_bodies_but_never_the_api_key(tmp_path):
    def handler(request):
        return httpx.Response(200, json={"seriess": [{"id": "UNRATE", "title": "U"}]})

    client = FredClient(
        "secret-key-123", transport=httpx.MockTransport(handler), raw=RawZone(tmp_path)
    )
    client.series("UNRATE")
    [saved] = list((tmp_path / "fred").rglob("*.json"))
    assert b"UNRATE" in saved.read_bytes()
    assert b"secret-key-123" not in saved.read_bytes()
    assert b"secret-key-123" not in (tmp_path / "manifest.jsonl").read_bytes()


def test_cftc_pages_are_kept_in_the_raw_zone(tmp_path):
    client = CftcClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json=[])),
        raw=RawZone(tmp_path),
    )
    client.reports("088691", datetime(2026, 1, 1).date())
    assert list((tmp_path / "cftc").rglob("*.json"))


def test_base_retries_then_raises_the_sources_own_error():
    calls = []

    class Demo(HttpSource):
        source = "demo"

    def handler(request):
        calls.append(1)
        return httpx.Response(503)

    with pytest.raises(SourceError, match="demo returned 503"):
        Demo(transport=httpx.MockTransport(handler), sleep=lambda _s: None, max_retries=2).get(
            "https://example.test/x", {}
        )
    assert len(calls) == 3


# --- reference prices -------------------------------------------------------------------------


def test_every_reference_price_is_a_catalog_series_kept_out_of_the_scorecard():
    for symbol, series_id in PRICE_SERIES.items():
        entry = BY_ID[series_id]
        assert entry.dimension == "markets", symbol
        assert entry.market, symbol  # unrevised market data: history before the archive is kept
        assert entry.change == "pct", symbol
        assert series_id not in SCORED, symbol
    assert not set(PRICE_SERIES) & set(NO_FREE_SOURCE)
