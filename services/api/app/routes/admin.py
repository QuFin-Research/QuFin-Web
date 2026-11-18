"""Admin and data-scientist endpoints: coverage, scorecard freshness and the data refresh button.

Everything here needs a signed-in user with the `admin` or `data_scientist` role (set with
`QUFIN_ADMIN_EMAILS` and `QUFIN_DATA_SCIENTIST_EMAILS`, see `core/auth.py`). Starting a refresh is
admin-only: it makes requests to outside sources, so it is limited to one run at a time and one
per `refresh_min_interval_seconds`.
"""

import threading
import time
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Request
from sqlalchemy.orm import sessionmaker

from app.core.auth import Admin, AppSettings, DbSession, Staff
from app.core.clock import Today
from app.jobs import admin_status, refresh
from app.schemas.admin import AdminStatus, CoverageSummary, JobRun, RefreshRequest
from app.stores.jobs import JobStore

router = APIRouter(prefix="/v1/admin", tags=["admin"])


def _next_allowed(jobs: JobStore, settings: AppSettings, now: datetime) -> datetime | None:
    last = jobs.last_started(refresh.JOB)
    if last is None or settings.refresh_min_interval_seconds == 0:
        return None
    allowed = last + timedelta(seconds=settings.refresh_min_interval_seconds)
    return allowed if allowed > now else None


@router.get("/coverage", response_model=CoverageSummary)
def get_coverage(_user: Staff, session: DbSession, today: Today) -> CoverageSummary:
    """Countries and indicators missing, from the stored series (see docs: coverage matrix)."""
    return admin_status.coverage_summary(session, today)


@router.get("/status", response_model=AdminStatus)
def get_status(
    _user: Staff, session: DbSession, today: Today, settings: AppSettings
) -> AdminStatus:
    """Shown at sign-in and beside the scorecard: coverage headline, whether the scorecard is
    being kept up to date, and the last refresh run."""
    now = datetime.now(UTC)
    jobs = JobStore(session)
    stale = timedelta(seconds=settings.refresh_run_timeout_seconds)
    running = jobs.running(stale, now)
    last = running or next(iter(jobs.recent(1)), None)
    return AdminStatus(
        scorecard=admin_status.scorecard_status(session, today, last, now),
        coverage=admin_status.coverage_summary(session, today, now, top=0).headline,
        last_run=last,
        running=running is not None,
        next_refresh_allowed_at=_next_allowed(jobs, settings, now),
    )


@router.get("/jobs", response_model=list[JobRun])
def list_jobs(
    _user: Staff, session: DbSession, limit: Annotated[int, Query(ge=1, le=50)] = 10
) -> list[JobRun]:
    return JobStore(session).recent(limit)


@router.get("/jobs/{run_id}", response_model=JobRun)
def get_job(_user: Staff, session: DbSession, run_id: str) -> JobRun:
    run = JobStore(session).get(run_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Unknown run")
    return run


@router.post("/jobs/refresh", response_model=JobRun, status_code=202)
def start_refresh(
    _body: RefreshRequest,
    request: Request,
    user: Admin,
    session: DbSession,
    today: Today,
    settings: AppSettings,
) -> JobRun:
    """Load what the sources have published since, for the series that are due. Returns at
    once; poll `/v1/admin/jobs/{id}`. One run at a time, and not more often than the interval."""
    now = datetime.now(UTC)
    jobs = JobStore(session)
    if jobs.running(timedelta(seconds=settings.refresh_run_timeout_seconds), now) is not None:
        raise HTTPException(status_code=409, detail="A refresh is already running")
    if (allowed := _next_allowed(jobs, settings, now)) is not None:
        wait = int((allowed - now).total_seconds()) + 1
        raise HTTPException(
            status_code=429,
            detail=f"The last refresh started recently; try again in {wait} s",
            headers={"Retry-After": str(wait)},
        )
    steps = refresh.plan(session, settings, today)
    run = jobs.start(refresh.JOB, user.email, now)
    jobs.set_steps(run.id, refresh.summarize_steps(steps))
    factory = sessionmaker(session.get_bind(), expire_on_commit=False)
    executor = getattr(request.app.state, "refresh_executor", refresh.subprocess_executor)
    args = (run.id, factory, steps, executor, settings.refresh_step_timeout_seconds)
    options = {
        "sleep": getattr(request.app.state, "refresh_sleep", time.sleep),
        "budget_seconds": settings.refresh_run_timeout_seconds * 0.9,
    }
    if getattr(request.app.state, "refresh_inline", False):
        refresh.execute(*args, **options)  # tests: run in the request, no thread
    else:
        threading.Thread(target=refresh.execute, args=args, kwargs=options, daemon=True).start()
    return jobs.get(run.id) or run
