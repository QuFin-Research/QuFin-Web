"""Admin and data-scientist views: roles, coverage, scorecard freshness, and the refresh button."""

# Fixtures imported from conftest and test_macro_api are used by name.

from collections.abc import Iterator
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr
from sqlalchemy.orm import Session, sessionmaker

from app.core.clock import today as today_dependency
from app.core.config import Settings
from app.jobs import admin_status, refresh
from app.main import create_app
from app.stores.db import create_all, get_session, make_engine
from app.stores.jobs import JobStore
from app.stores.macro import MacroStore, SeriesMeta, Vintage
from tests.conftest import PASSWORD

TODAY = date(2026, 10, 25)  # September's figures are due (the usual lag is 20 days)
OPEN = date(9999, 12, 31)
ADMIN, SCIENTIST, PLAIN = "boss@example.com", "ds@example.com", "trader@example.com"


class Recorder:
    """Stands in for the ingest commands: no network, no subprocess."""

    def __init__(self, status="ok"):
        self.status = status
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def __call__(self, step, _timeout):
        self.calls.append((step.command, step.series_ids))
        return refresh.StepResult(self.status, "1 of 1 on schedule")


@pytest.fixture
def factory_and_app():
    engine = make_engine("sqlite://")
    create_all(engine)
    factory = sessionmaker(engine, expire_on_commit=False)

    def session_override() -> Iterator[Session]:
        with factory() as session:
            yield session

    settings = Settings(
        _env_file=None,
        auto_migrate=False,
        admin_emails=f" {ADMIN.upper()} ",  # case and spaces do not matter
        data_scientist_emails=SCIENTIST,
        fred_api_key=SecretStr("test"),
        refresh_min_interval_seconds=600,
    )
    application = create_app(settings)
    application.dependency_overrides[get_session] = session_override
    application.dependency_overrides[today_dependency] = lambda: TODAY
    application.state.refresh_inline = True
    application.state.refresh_executor = Recorder()
    return factory, application


@pytest.fixture
def app(factory_and_app):
    return factory_and_app[1]


def signed_in(app, email):
    client = TestClient(app)
    client.__enter__()
    res = client.post("/v1/auth/sign-up", json={"email": email, "password": PASSWORD})
    assert res.status_code == 201, res.text
    return client


@pytest.fixture
def admin(app):
    return signed_in(app, ADMIN)


@pytest.fixture
def scientist(app):
    return signed_in(app, SCIENTIST)


@pytest.fixture
def plain(app):
    return signed_in(app, PLAIN)


def store_series(factory, series_id="UNRATE", frequency="Monthly", last_month=9, source="fred"):
    with factory() as session:
        MacroStore(session).replace_series(
            SeriesMeta(
                id=series_id,
                source=source,
                title=f"{series_id} (test)",
                units="Percent",
                frequency=frequency,
                seasonal_adjustment="Seasonally Adjusted",
                country="US",
                dimension="labour",
                last_updated=None,
                cycle="lagging",
            ),
            [
                Vintage(date(2026, m, 1), date(2026, m, 1) + timedelta(days=20), OPEN, 4.0 + m / 10)
                for m in range(1, last_month + 1)
            ],
        )
        session.commit()


# --- roles -----------------------------------------------------------------------------------


def test_the_server_decides_the_role_from_its_settings(admin, scientist, plain):
    assert admin.get("/v1/auth/me").json()["role"] == "admin"
    assert scientist.get("/v1/auth/me").json()["role"] == "data_scientist"
    assert plain.get("/v1/auth/me").json()["role"] == "user"


def test_a_sign_up_cannot_ask_for_a_role(app):
    with TestClient(app) as client:
        res = client.post(
            "/v1/auth/sign-up",
            json={"email": "x@example.com", "password": PASSWORD, "role": "admin"},
        )
    assert res.status_code == 422


def test_admin_emails_are_split_and_lowercased():
    s = Settings(_env_file=None, admin_emails="A@x.com, b@x.com ,")
    assert s.admin_emails == ["a@x.com", "b@x.com"]
    assert Settings(_env_file=None).admin_emails == []  # nobody by default


@pytest.mark.parametrize("path", ["/v1/admin/status", "/v1/admin/coverage", "/v1/admin/jobs"])
def test_the_admin_views_need_a_staff_role(app, plain, path):
    with TestClient(app) as anonymous:
        assert anonymous.get(path).status_code == 401
    assert plain.get(path).status_code == 403


def test_only_an_admin_may_start_a_refresh(scientist, plain, admin):
    assert plain.post("/v1/admin/jobs/refresh", json={}).status_code == 403
    assert scientist.post("/v1/admin/jobs/refresh", json={}).status_code == 403
    assert admin.post("/v1/admin/jobs/refresh", json={}).status_code == 202


def test_a_refresh_needs_a_json_body(admin):
    res = admin.post(
        "/v1/admin/jobs/refresh", content="x=1", headers={"Content-Type": "text/plain"}
    )
    assert res.status_code == 422


# --- coverage and status ---------------------------------------------------------------------


def test_coverage_reports_countries_and_indicators_missing(scientist):
    body = scientist.get("/v1/admin/coverage").json()
    h = body["headline"]
    assert h["countries"] == 87 and h["countriesWithGaps"] == 87  # nothing stored in the test
    assert h["have"] == 0 and h["applicable"] == h["unusable"] + h["gap"]
    assert h["coveragePct"] == 0
    gaps = [row["gap"] for row in body["byIndicator"]]
    assert gaps == sorted(gaps, reverse=True) and len(gaps) == 15
    assert len(body["byCountry"]) == 15 and body["globalIndicators"] >= 31


def test_coverage_counts_a_stored_series_as_held(factory_and_app, scientist):
    store_series(factory_and_app[0])
    h = scientist.get("/v1/admin/coverage").json()["headline"]
    assert h["have"] == 1 and h["applicable"] == h["have"] + h["unusable"] + h["gap"]


def test_status_says_the_scorecard_is_stale_when_nothing_is_stored(scientist):
    body = scientist.get("/v1/admin/status").json()
    assert body["scorecard"]["state"] == "stale"
    assert body["lastRun"] is None and body["running"] is False
    assert body["nextRefreshAllowedAt"] is None
    assert body["coverage"]["applicable"] > 0


def test_scorecard_is_updated_when_every_scored_series_is_current(factory_and_app):
    store_series(factory_and_app[0])
    with factory_and_app[0]() as session:
        now = datetime(2026, 10, 20, tzinfo=UTC)
        status = admin_status.scorecard_status(session, TODAY, None, now)
    assert status.state == "updated" and status.overdue_series == []
    assert status.latest_period == date(2026, 9, 1) and status.scored_series == 1


def test_scorecard_is_partial_then_stale_as_scored_series_go_overdue(factory_and_app):
    factory = factory_and_app[0]
    store_series(factory, "UNRATE")
    store_series(factory, "GDPC1", frequency="Quarterly", last_month=1)  # three quarters behind
    now = datetime.now(UTC)
    with factory() as session:
        status = admin_status.scorecard_status(session, TODAY, None, now)
    assert status.state == "partial" and status.usable_series == 1
    assert status.overdue_series == ["GDPC1"]
    store_series(factory, "INDPRO", last_month=2)  # eight months behind
    with factory() as session:
        status = admin_status.scorecard_status(session, TODAY, None, now)
    assert status.state == "stale" and len(status.overdue_series) == 2  # most are overdue


def test_scorecard_is_stale_when_no_data_has_been_loaded_for_a_week(factory_and_app):
    store_series(factory_and_app[0])
    with factory_and_app[0]() as session:
        later = datetime.now(UTC) + timedelta(days=9)
        status = admin_status.scorecard_status(session, TODAY, None, later)
    assert status.state == "stale" and "9 days" in status.reason


# --- the refresh button ----------------------------------------------------------------------


def test_a_refresh_runs_only_the_due_series_one_command_per_source(factory_and_app, admin, app):
    store_series(factory_and_app[0])  # last period September, due on 22 October
    with factory_and_app[0]() as session:
        settings = app.state.settings
        assert refresh.plan(session, settings, date(2026, 10, 20)) == []  # not due yet
    res = admin.post("/v1/admin/jobs/refresh", json={})
    assert res.status_code == 202
    run = admin.get(f"/v1/admin/jobs/{res.json()['id']}").json()
    assert run["status"] == "succeeded" and run["requestedBy"] == ADMIN
    # One command per source, then the one release check that ends the run (rule 2).
    assert app.state.refresh_executor.calls == [("ingest-fred", ("UNRATE",)), ("check-data", ())]
    assert [(s["source"], s["series"], s["status"]) for s in run["steps"]] == [
        ("fred", 1, "ok"),
        ("release check", 0, "ok"),
    ]


def test_a_source_without_its_key_is_skipped_and_said_so(factory_and_app):
    factory, application = factory_and_app
    application.state.settings.fred_api_key = None
    store_series(factory)
    with factory() as session:
        [step] = refresh.plan(session, application.state.settings, TODAY)
    assert step.skip_reason == "no FRED API key configured"


def test_a_failed_step_fails_the_run_and_the_panel_can_say_which(factory_and_app, admin, app):
    app.state.refresh_executor = Recorder("failed")
    store_series(factory_and_app[0])
    run = admin.post("/v1/admin/jobs/refresh", json={}).json()
    assert run["status"] == "failed" and run["error"] == "2 of 2 steps failed"
    assert run["steps"][0]["status"] == "failed"
    status = admin.get("/v1/admin/status").json()
    assert status["lastRun"]["status"] == "failed"
    assert "The last refresh failed" in status["scorecard"]["reason"]


def test_overdue_after_a_refresh_is_a_finished_run_not_a_failure(factory_and_app, admin, app):
    app.state.refresh_executor = Recorder("overdue")
    store_series(factory_and_app[0])
    run = admin.post("/v1/admin/jobs/refresh", json={}).json()
    assert run["status"] == "succeeded" and run["steps"][0]["status"] == "overdue"
    assert run["steps"][-1]["source"] == "release check"


def test_a_second_refresh_is_refused_while_one_runs_and_soon_after(factory_and_app, admin):
    factory = factory_and_app[0]
    with factory() as session:
        JobStore(session).start("refresh", "someone@example.com")
    res = admin.post("/v1/admin/jobs/refresh", json={})
    assert res.status_code == 409
    with factory() as session:  # finish it: the interval now applies
        JobStore(session).finish(JobStore(session).recent(1)[0].id, "succeeded")
    res = admin.post("/v1/admin/jobs/refresh", json={})
    assert res.status_code == 429 and int(res.headers["Retry-After"]) > 0
    assert admin.get("/v1/admin/status").json()["nextRefreshAllowedAt"] is not None


def test_a_run_that_never_finished_is_marked_interrupted(factory_and_app):
    with factory_and_app[0]() as session:
        jobs = JobStore(session)
        old = datetime.now(UTC) - timedelta(hours=3)
        jobs.start("refresh", "x@example.com", now=old)
        assert jobs.running(timedelta(hours=2)) is None
        assert jobs.recent(1)[0].status == "interrupted"


def test_executing_a_run_records_progress_even_if_the_executor_raises(factory_and_app):
    factory = factory_and_app[0]
    store_series(factory)
    with factory() as session:
        steps = refresh.plan(session, factory_and_app[1].state.settings, TODAY)
        run = JobStore(session).start("refresh", "x@example.com")

    def broken(_step, _timeout):
        raise RuntimeError("boom")

    refresh.execute(run.id, factory, steps, broken)
    with factory() as session:
        done = JobStore(session).get(run.id)
    assert done.status == "failed" and "boom" in (done.error or "")


# --- the commands a refresh runs --------------------------------------------------------------


class _Done:
    def __init__(self, code, out):
        self.returncode, self.stdout, self.stderr = code, out, ""


def _run_with(monkeypatch, code, out, step):
    seen = {}

    def fake(cmd, **kwargs):
        seen["cmd"], seen["env"] = cmd, kwargs["env"]
        return _Done(code, out)

    monkeypatch.setattr(refresh.subprocess, "run", fake)
    return refresh.subprocess_executor(step, 5), seen


def test_ingest_steps_defer_the_release_check_and_the_final_step_runs_it(monkeypatch):
    step = refresh.Step("ingest-ecb", "ecb", ("A", "B"))
    result, seen = _run_with(monkeypatch, 0, "A  3 new\nB  1 new\n", step)
    assert seen["cmd"][-3:] == ["ingest-ecb", "A", "B"] and seen["env"][refresh.DEFER_ENV] == "1"
    assert result == refresh.StepResult("ok", "2 of 2 series loaded")
    check = refresh.Step("check-data", "release check", ())
    result, seen = _run_with(monkeypatch, 1, "x\n1000 of 1016 on schedule; NOT USABLE: a", check)
    assert refresh.DEFER_ENV not in seen["env"] or seen["env"].get(refresh.DEFER_ENV) != "1"
    assert result.status == "overdue" and "1000 of 1016" in result.detail


def test_an_ingest_that_cannot_load_a_series_is_a_failed_step(monkeypatch):
    step = refresh.Step("ingest-ecb", "ecb", ("A", "B"))
    result, _ = _run_with(monkeypatch, 1, "A  3 new\nB  FAILED: the ECB returned 500\n", step)
    assert result.status == "failed" and result.detail.startswith("1 of 2 series loaded")
    assert "the ECB returned 500" in result.detail


def test_a_slow_step_is_stopped_and_reported(monkeypatch):
    def slow(cmd, **kwargs):
        raise refresh.subprocess.TimeoutExpired(cmd, kwargs["timeout"])

    monkeypatch.setattr(refresh.subprocess, "run", slow)
    result = refresh.subprocess_executor(refresh.Step("ingest-ons", "ons", ("X",)), 7)
    assert result == refresh.StepResult("failed", "timed out after 7 s")


def test_the_cli_skips_its_own_release_check_only_when_the_refresh_defers_it(monkeypatch, capsys):
    from app import cli

    monkeypatch.delenv(cli.DEFER_CHECKS_ENV, raising=False)
    assert not cli._deferred()
    monkeypatch.setenv(cli.DEFER_CHECKS_ENV, "1")
    assert cli._deferred() and cli._release_check(None) == []
    cli._finish_report([])  # prints nothing and does not run the doctor
    assert capsys.readouterr().out == ""
