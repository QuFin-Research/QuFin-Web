from app.data.sample import ASSETS, HISTORY_DAYS


def test_list_assets_returns_a_snapshot_per_asset(client):
    res = client.get("/v1/assets")
    assert res.status_code == 200
    body = res.json()
    assert [s["asset"]["symbol"] for s in body] == [a.symbol for a in ASSETS]
    first = body[0]
    assert set(first) == {"data", "asset", "lastPrice", "changePct", "regime", "signal", "hitRate"}
    assert all(s["data"] == "sample" for s in body)  # never presented as market data
    assert set(first["asset"]) == {"symbol", "name", "assetClass", "precision"}
    assert set(first["signal"]) == {"time", "probUp", "direction", "conviction", "horizonDays"}
    assert first["signal"]["time"] == "2026-10-30"


def test_hit_rates_stay_realistic(client):
    # The sample model has a modest edge; anything near 90% would be a red flag.
    for snapshot in client.get("/v1/assets").json():
        assert 0.45 < snapshot["hitRate"] < 0.65


def test_asset_detail(client):
    res = client.get("/v1/assets/XAUUSD")
    assert res.status_code == 200
    body = res.json()
    assert body["asset"]["symbol"] == "XAUUSD"
    assert len(body["candles"]) == len(body["signals"]) == HISTORY_DAYS
    assert body["candles"][-1]["close"] == body["lastPrice"]
    assert body["signals"][-1] == body["signal"]
    assert len(body["drivers"]) == 5
    contributions = [abs(d["contribution"]) for d in body["drivers"]]
    assert contributions == sorted(contributions, reverse=True)
    for candle in body["candles"]:
        assert candle["low"] <= min(candle["open"], candle["close"])
        assert candle["high"] >= max(candle["open"], candle["close"])


def test_asset_detail_is_case_insensitive(client):
    assert client.get("/v1/assets/eurusd").json()["asset"]["symbol"] == "EURUSD"


def test_unknown_asset_is_404(client):
    res = client.get("/v1/assets/DOGEUSD")
    assert res.status_code == 404
    assert res.json() == {"detail": "Unknown symbol"}


def test_malformed_symbol_is_rejected(client):
    assert client.get("/v1/assets/EUR-USD").status_code == 422
    assert client.get("/v1/assets/" + "A" * 13).status_code == 422


def test_country_scores(client):
    res = client.get("/v1/scorecards/countries")
    assert res.status_code == 200
    body = res.json()
    assert len(body) == 10
    overall = [c["overall"] for c in body]
    assert overall == sorted(overall, reverse=True)
    for country in body:
        assert set(country["scores"]) == {"growth", "inflation", "labour", "policy", "sentiment"}
        assert all(-3 <= v <= 3 for v in country["scores"].values())
