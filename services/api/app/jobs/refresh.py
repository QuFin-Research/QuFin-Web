"""Data refresh: load what the sources have published since, for the series that are due.

The admin panel's "Run refresh" button and a scheduler both start this. It does not reload the
whole catalog (hundreds of requests to sources that ask us to be gentle, rule 28): it asks only
for series whose next release has arrived or that are overdue, one ingest command per source, in
a fixed order that is only a run order, not a source preference (rule 38): FRED first because most
series come from it, then the agencies and aggregators. Each command is the same CLI
command a person would run, in its own process, so a crash or a slow source cannot take the API
down, and each ends with the release check as always (rule 2).

A step that fails for a transient reason (a timeout, a network error, a 5xx) is retried on the
capped ladder of rule 35, after the other sources have had their turn: about 15 s, 60 s, 5 min,
15 min and 1 h later, each wait varied by up to 20% so retries do not arrive in step. A step still
failing after the last rung is marked degraded. A supplier that refuses (403, 429) is never
retried or asked again in the run (rule 28). The release check runs last.

A run is recorded in `job_runs` step by step, so the panel can show progress and what failed.

Each ingest command normally ends with the release check and the doctor, about three minutes
each. A refresh runs its commands with those deferred (`QUFIN_DEFER_RELEASE_CHECK=1`) and
finishes with one `check-data` step, so the run still ends with the release check (rule 2).
"""

import os
import random
import re
import subprocess
import sys
import time
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal

from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings
from app.data.macro_catalog import BY_ID
from app.jobs.check_data import LAG_WINDOW, macro_status
from app.jobs.ingest_staged import staging_due
from app.schemas.admin import JobStep
from app.stores.jobs import FAILED, SUCCEEDED, JobStore
from app.stores.macro import MacroStore

JOB = "refresh"
CHECK_COMMAND = "check-data"
STAGING_COMMAND = "ingest-staged"
DEFER_ENV = "QUFIN_DEFER_RELEASE_CHECK"
API_DIR = Path(__file__).resolve().parents[2]
CHUNK = 100  # series ids per command: a command line has a length limit

# Source -> the CLI command that ingests it, in the order they run.
SOURCE_COMMAND: dict[str, str] = {
    "fred": "ingest-fred",
    "ecb": "ingest-ecb",
    "eurostat": "ingest-eurostat",
    "ons": "ingest-ons",
    "bis": "ingest-bis",
    "oecd": "ingest-oecd",
    "imf": "ingest-imf",
    "worldbank": "ingest-worldbank",
    "bcb": "ingest-bcb",
    "singstat": "ingest-singstat",
    "bls": "ingest-bls",
    "eia": "ingest-eia",
    "treasury": "ingest-treasury",
}
# Sources that need a free API key, and the setting that holds it.
KEY_SETTING = {"fred": "fred_api_key", "bls": "bls_api_key", "eia": "eia_api_key"}

StepOutcome = Literal["ok", "overdue", "failed", "degraded"]

# Rule 35: the waits before each retry of a failing feed, in seconds, and the random variation.
RETRY_LADDER = (15, 60, 300, 900, 3600)
RETRY_JITTER = 0.2
_REFUSED = re.compile(r"returned (403|429)|refused an earlier request")
_TRANSIENT = re.compile(r"timed out|returned (408|5\d\d)|request failed|kept failing")


@dataclass(frozen=True)
class Step:
    command: str
    source: str
    series_ids: tuple[str, ...]
    skip_reason: str | None = None


@dataclass(frozen=True)
class StepResult:
    status: StepOutcome
    detail: str


Executor = Callable[[Step, int], StepResult]


def plan(session: Session, settings: Settings, today: date) -> list[Step]:
    """The commands a refresh would run: only series that are due or overdue, grouped by source."""
    store = MacroStore(session)
    releases = store.first_releases(today - LAG_WINDOW)
    due: dict[str, list[str]] = defaultdict(list)
    for s in store.list_series():
        if s.meta.id not in BY_ID:
            continue
        fresh = macro_status(s.meta, s.last_period, releases.get(s.meta.id, {}), today).freshness
        if not fresh.usable or (fresh.next_due is not None and fresh.next_due <= today):
            due[s.meta.source].append(s.meta.id)
    steps: list[Step] = []
    known = [s for s in SOURCE_COMMAND if s in due]
    for source in [*known, *sorted(set(due) - set(SOURCE_COMMAND))]:
        ids = sorted(due[source])
        command = SOURCE_COMMAND.get(source)
        skip = None
        if command is None:
            skip = f"no ingest command for {source}"
        elif source in KEY_SETTING and getattr(settings, KEY_SETTING[source]) is None:
            skip = f"no {source.upper()} API key configured"
        for i in range(0, len(ids), CHUNK):
            steps.append(Step(command or "-", source, tuple(ids[i : i + CHUNK]), skip))
    if staging_due(session, today):
        steps.append(Step(STAGING_COMMAND, "staging", ()))
    if any(step.skip_reason is None for step in steps):
        steps.append(Step(CHECK_COMMAND, "release check", ()))
    return steps


def subprocess_executor(step: Step, timeout: int) -> StepResult:
    """Run one ingest command. Exit 1 with a release report is a finished run that found series
    still overdue (the source has not published); anything else non-zero is a failure."""
    cmd = [sys.executable, "-m", "app.cli", step.command, *step.series_ids]
    ingest = step.command not in (CHECK_COMMAND, STAGING_COMMAND)
    env = {**os.environ, DEFER_ENV: "1"} if ingest else dict(os.environ)
    try:
        done = subprocess.run(  # noqa: S603 - fixed argv, ids come from the catalog
            cmd, capture_output=True, text=True, timeout=timeout, cwd=API_DIR, env=env, check=False
        )
    except subprocess.TimeoutExpired:
        return StepResult("failed", f"timed out after {timeout} s")
    lines = [ln for ln in (done.stdout + "\n" + done.stderr).splitlines() if ln.strip()]
    if step.command == STAGING_COMMAND:
        summary = next((ln for ln in reversed(lines) if ln.startswith("staged:")), "")
        # Staged series are measured, not relied on: a failure is reported, never failing the run.
        return StepResult("ok" if done.returncode == 0 else "overdue", summary[:300])
    if ingest:
        failed = [ln for ln in lines if "FAILED" in ln]
        loaded = len(step.series_ids) - len(failed)
        detail = f"{loaded} of {len(step.series_ids)} series loaded"
        if done.returncode == 0:
            return StepResult("ok", detail)
        detail += f"; {failed[0][:150]}" if failed else ""
        return StepResult("failed", detail if failed else " | ".join(lines[-3:])[:300])
    report = next((ln for ln in reversed(lines) if "on schedule" in ln), "")
    if done.returncode == 0:
        return StepResult("ok", report[:300])
    if done.returncode == 1 and report:
        return StepResult(
            "overdue", report[:300]
        )  # some series are overdue: the sources have not published
    return StepResult("failed", " | ".join(lines[-3:])[:300] or f"exit {done.returncode}")


def summarize_steps(steps: Sequence[Step]) -> list[JobStep]:
    return [
        JobStep(
            command=s.command,
            source=s.source,
            series=len(s.series_ids),
            status="skipped" if s.skip_reason else "pending",
            detail=s.skip_reason or "",
        )
        for s in steps
    ]


def refused(result: StepResult) -> bool:
    """The supplier said no (403 or 429): asking again risks a ban (rule 28)."""
    return result.status == "failed" and bool(_REFUSED.search(result.detail))


def transient(result: StepResult) -> bool:
    """A failure that may pass: worth a retry on the ladder (rule 35)."""
    return (
        result.status == "failed" and not refused(result) and bool(_TRANSIENT.search(result.detail))
    )


def ladder_wait(rung: int, rng: random.Random) -> float:
    """Seconds before retry number `rung` (0-based): the ladder step, varied by the jitter."""
    return RETRY_LADDER[rung] * (1 + rng.uniform(-RETRY_JITTER, RETRY_JITTER))


def execute(
    run_id: str,
    factory: sessionmaker[Session],
    steps: Sequence[Step],
    executor: Executor = subprocess_executor,
    step_timeout: int = 1800,
    *,
    sleep: Callable[[float], None] = time.sleep,
    rng: random.Random | None = None,
    budget_seconds: float | None = None,
) -> None:
    """Run the steps in order, saving progress after each; retry transient failures on the ladder
    of rule 35; run the release check last. Never raises: a run that cannot finish is recorded as
    failed. `budget_seconds` caps the time the ladder may take."""
    progress = summarize_steps(steps)
    rng = rng or random.Random()  # noqa: S311 - jitter, not security
    started = time.monotonic()
    try:
        with factory() as session:
            jobs = JobStore(session)

            def put(i: int, status: str, detail: str | None = None) -> None:
                update = {"status": status} | ({} if detail is None else {"detail": detail})
                progress[i] = progress[i].model_copy(update=update)
                jobs.set_steps(run_id, progress)

            def attempt(i: int) -> StepResult:
                put(i, "running")
                result = executor(steps[i], step_timeout)
                put(i, result.status, result.detail)
                return result

            ingest = [i for i, s in enumerate(steps) if s.command != CHECK_COMMAND]
            checks = [i for i, s in enumerate(steps) if s.command == CHECK_COMMAND]
            failed = 0
            retry: list[int] = []
            blocked: set[str] = set()  # sources that refused: not asked again this run
            for i in ingest:
                step = steps[i]
                if step.skip_reason:
                    continue
                if step.source in blocked:
                    put(i, "failed", "the supplier refused earlier in this run; not asking again")
                    failed += 1
                    continue
                result = attempt(i)
                if refused(result):
                    blocked.add(step.source)
                if transient(result):
                    retry.append(i)
                else:
                    failed += result.status == "failed"
            for rung in range(len(RETRY_LADDER)):
                if not retry:
                    break
                wait = ladder_wait(rung, rng)
                if (
                    budget_seconds is not None
                    and time.monotonic() - started + wait > budget_seconds
                ):
                    break
                for i in retry:
                    put(i, "running", f"retry {rung + 1} of {len(RETRY_LADDER)} in {wait:.0f} s")
                sleep(wait)
                retry = [i for i in retry if transient(attempt(i))]
            for i in retry:  # still failing after the last rung, or out of time
                put(i, "degraded", f"still failing after the retries; {progress[i].detail}")
                failed += 1
            for i in checks:
                if not steps[i].skip_reason:
                    failed += attempt(i).status == "failed"
            jobs.finish(
                run_id,
                FAILED if failed else SUCCEEDED,
                f"{failed} of {len(steps)} steps failed" if failed else None,
                datetime.now(UTC),
            )
    except Exception as exc:
        with factory() as session:
            JobStore(session).finish(run_id, FAILED, f"{type(exc).__name__}: {exc}"[:300])
