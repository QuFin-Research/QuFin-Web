"""Job runs: one row per manual or scheduled data refresh, so the admin panel can say what ran."""

import json
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, Index, String, Text, select
from sqlalchemy.orm import Mapped, Session, mapped_column

from app.schemas.admin import JobRun, JobStep
from app.stores.db import Base, as_utc

RUNNING = "running"
SUCCEEDED = "succeeded"
FAILED = "failed"
INTERRUPTED = "interrupted"  # the process stopped before the run finished


class JobRunRow(Base):
    __tablename__ = "job_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    job: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(12))
    requested_by: Mapped[str] = mapped_column(String(254))
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_job_runs_started", "started_at"),)


def _run(row: JobRunRow) -> JobRun:
    return JobRun(
        id=row.id,
        job=row.job,
        status=row.status,  # type: ignore[arg-type]
        requested_by=row.requested_by,
        started_at=as_utc(row.started_at),
        finished_at=as_utc(row.finished_at) if row.finished_at else None,
        steps=[JobStep(**s) for s in json.loads(row.steps_json)],
        error=row.error,
    )


class JobStore:
    def __init__(self, session: Session) -> None:
        self.session = session

    def start(self, job: str, requested_by: str, now: datetime | None = None) -> JobRun:
        row = JobRunRow(
            id=str(uuid.uuid4()),
            job=job,
            status=RUNNING,
            requested_by=requested_by,
            started_at=now or datetime.now(UTC),
        )
        self.session.add(row)
        self.session.commit()
        return _run(row)

    def running(self, stale_after: timedelta, now: datetime | None = None) -> JobRun | None:
        """The run in progress. A run older than `stale_after` is marked interrupted: the
        server that started it can no longer be running it."""
        now = now or datetime.now(UTC)
        rows = self.session.scalars(select(JobRunRow).where(JobRunRow.status == RUNNING)).all()
        live = None
        for row in rows:
            if now - as_utc(row.started_at) > stale_after:
                row.status, row.finished_at = INTERRUPTED, now
                row.error = "The run did not finish: the server stopped or it ran too long"
            else:
                live = row
        self.session.commit()
        return _run(live) if live else None

    def set_steps(self, run_id: str, steps: list[JobStep]) -> None:
        row = self.session.get(JobRunRow, run_id)
        if row is not None:
            row.steps_json = json.dumps([s.model_dump(by_alias=False, mode="json") for s in steps])
            self.session.commit()

    def finish(
        self, run_id: str, status: str, error: str | None = None, now: datetime | None = None
    ) -> None:
        row = self.session.get(JobRunRow, run_id)
        if row is not None:
            row.status, row.error = status, error
            row.finished_at = now or datetime.now(UTC)
            self.session.commit()

    def get(self, run_id: str) -> JobRun | None:
        row = self.session.get(JobRunRow, run_id)
        return _run(row) if row else None

    def recent(self, limit: int = 10) -> list[JobRun]:
        rows = self.session.scalars(
            select(JobRunRow).order_by(JobRunRow.started_at.desc()).limit(limit)
        )
        return [_run(r) for r in rows]

    def last_started(self, job: str) -> datetime | None:
        row = self.session.scalars(
            select(JobRunRow)
            .where(JobRunRow.job == job)
            .order_by(JobRunRow.started_at.desc())
            .limit(1)
        ).first()
        return as_utc(row.started_at) if row else None
