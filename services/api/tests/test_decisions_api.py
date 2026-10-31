import uuid


def decision_body(**overrides):
    body = {
        "symbol": "EURUSD",
        "direction": "long",
        "entry": 1.08,
        "stop": 1.07,
        "target": 1.1,
        "riskPct": 1,
        "maxHoldDays": 10,
        "signalProbUp": 0.58,
        "backtest": {"trades": 42, "winRate": 0.52, "avgR": 0.11},
        "note": "Rate differential widening",
    }
    return body | overrides


def test_decision_lifecycle(client):
    assert client.get("/v1/decisions").json() == []

    first = client.post("/v1/decisions", json=decision_body())
    assert first.status_code == 201
    created = first.json()
    assert uuid.UUID(created["id"])
    assert created["createdAt"].endswith(("Z", "+00:00"))
    assert created["backtest"] == {"trades": 42, "winRate": 0.52, "avgR": 0.11}

    second = client.post(
        "/v1/decisions",
        json=decision_body(
            symbol="wti", direction="short", entry=78, stop=80, target=74, backtest=None
        ),
    ).json()
    assert second["symbol"] == "WTI"

    listed = client.get("/v1/decisions").json()
    assert [d["id"] for d in listed] == [second["id"], created["id"]]
    assert listed[1] == created

    assert client.delete(f"/v1/decisions/{created['id']}").status_code == 204
    assert [d["id"] for d in client.get("/v1/decisions").json()] == [second["id"]]
    assert client.delete(f"/v1/decisions/{created['id']}").status_code == 404


def test_decision_validation(client):
    without_note = decision_body()
    del without_note["note"]
    cases = [
        decision_body(stop=1.09),  # stop above entry on a long
        decision_body(target=1.07),  # target below entry on a long
        decision_body(direction="short"),  # levels are for a long
        decision_body(entry=0),
        decision_body(entry="NaN"),
        decision_body(riskPct=25),
        decision_body(signalProbUp=1.5),
        decision_body(maxHoldDays=0),
        decision_body(note="x" * 2001),
        decision_body(backtest={"trades": -1, "winRate": 0.5, "avgR": 0}),
        decision_body(id="client-chosen"),
        without_note,
    ]
    for body in cases:
        assert client.post("/v1/decisions", json=body).status_code == 422, body
    assert client.get("/v1/decisions").json() == []


def test_decision_for_unknown_symbol(client):
    res = client.post("/v1/decisions", json=decision_body(symbol="DOGEUSD"))
    assert res.status_code == 422


def test_delete_requires_a_uuid(client):
    assert client.delete("/v1/decisions/not-a-uuid").status_code == 422
