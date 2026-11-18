"""Queueing, running and retrying jobs.

- `enqueue()` records the job (in its own transaction) and hands it to the worker; in inline
  mode (development, tests) it runs it straight away instead.
- A job is claimed with a single UPDATE, so a message delivered twice still runs once.
- `recover()` (every few minutes) re-sends jobs whose message was lost and requeues jobs left
  "running" by a worker that stopped.
"""

import logging
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, text, update
from sqlalchemy.exc import IntegrityError

from app.core.config import get_settings
from app.core.db import SessionLocal
from app.core.models import utcnow
from app.jobs.models import Job
from app.jobs.registry import HANDLERS

log = logging.getLogger(__name__)

STUCK_AFTER = timedelta(minutes=15)  # longer than any job should take
LOST_AFTER = timedelta(minutes=2)    # a queued job nobody picked up


def backoff(attempt: int) -> timedelta:
    """30 s, 2 min, 8 min, 32 min, … capped at 2 hours."""
    return timedelta(seconds=min(30 * 4 ** (attempt - 1), 7200))


def enqueue(kind: str, payload: dict[str, Any] | None = None, *,
            organization_id: uuid.UUID | None = None, dedupe_key: str | None = None) -> uuid.UUID:
    """Record a job and start it. With a dedupe_key, an identical job already waiting or
    running is reused instead."""
    if kind not in HANDLERS:
        raise ValueError(f"Unknown job kind {kind!r}")
    spec = HANDLERS[kind]
    with SessionLocal() as db:
        job = Job(kind=kind, payload=payload or {}, organization_id=organization_id,
                  dedupe_key=dedupe_key, max_attempts=spec.max_attempts)
        db.add(job)
        try:
            db.commit()
        except IntegrityError:
            db.rollback()
            existing = db.scalar(select(Job.id).where(Job.dedupe_key == dedupe_key,
                                                      Job.status.in_(("queued", "running"))))
            if existing:
                return existing
            raise
        job_id = job.id
    try:
        dispatch(job_id)
    except Exception:  # noqa: BLE001 - the queue being down mustn't break the request
        # The job is recorded; recover() sends it once the queue is back.
        log.exception("Couldn't hand job %s (%s) to the queue; it will be retried", job_id, kind)
    return job_id


def dispatch(job_id: uuid.UUID, countdown: float = 0) -> None:
    if get_settings().jobs_mode == "inline":
        if countdown == 0:
            run(job_id)
        return  # inline retries wait for the next recover() (none run in development)
    from app.worker import run_job

    run_job.apply_async(args=[str(job_id)], countdown=countdown)


def run(job_id: uuid.UUID) -> str | None:
    """Run one attempt of a job. Returns its new status, or None if it wasn't ready to run
    (already taken, finished, or waiting for a retry)."""
    with SessionLocal() as db:
        claimed = db.execute(
            update(Job).where(Job.id == job_id, Job.status == "queued",
                              Job.run_after <= text("now()"))
            .values(status="running", attempts=Job.attempts + 1, started_at=utcnow(),
                    finished_at=None)
            .returning(Job.kind, Job.payload, Job.attempts, Job.max_attempts)
        ).first()
        db.commit()
        if claimed is None:
            return None
        kind, payload, attempt, max_attempts = claimed
        spec = HANDLERS.get(kind)
        try:
            if spec is None:
                raise LookupError(f"No handler for job kind {kind!r}")
            with SessionLocal() as work:
                spec.run(work, payload)
                work.commit()
        except Exception as exc:  # noqa: BLE001 - every failure is recorded and retried
            error = f"{type(exc).__name__}: {exc}"[:1000]
            give_up = attempt >= max_attempts
            log.warning("Job %s (%s) attempt %s/%s failed: %s", job_id, kind, attempt,
                        max_attempts, error)
            values: dict[str, Any] = {"last_error": error}
            if give_up:
                values |= {"status": "dead", "finished_at": utcnow()}
                if spec and spec.scrub:
                    values["payload"] = spec.scrub(payload)
            else:
                values |= {"status": "queued", "run_after": utcnow() + backoff(attempt)}
            db.execute(update(Job).where(Job.id == job_id).values(**values))
            db.commit()
            if not give_up:
                dispatch(job_id, countdown=backoff(attempt).total_seconds())
            return values["status"]
        values = {"status": "succeeded", "finished_at": utcnow(), "last_error": None}
        if spec.scrub:
            values["payload"] = spec.scrub(payload)
        db.execute(update(Job).where(Job.id == job_id).values(**values))
        db.commit()
        return "succeeded"


def recover() -> int:
    """Requeue jobs a stopped worker left running, and re-send queued jobs nobody picked up.
    Safe to run any time: claiming makes a second delivery harmless."""
    now = utcnow()
    with SessionLocal() as db:
        # Each kind has its own time limit (a long crawl isn't stuck after 15 minutes).
        running = db.execute(select(Job.id, Job.kind, Job.started_at, Job.attempts,
                                    Job.max_attempts)
                             .where(Job.status == "running",
                                    Job.started_at < now - STUCK_AFTER)).all()
        stuck = [r for r in running
                 if r.started_at < now - getattr(HANDLERS.get(r.kind), "stuck_after", STUCK_AFTER)]
        give_up = [r.id for r in stuck if r.attempts >= r.max_attempts]
        freed = [r.id for r in stuck if r.attempts < r.max_attempts]
        if give_up:
            db.execute(update(Job).where(Job.id.in_(give_up))
                       .values(status="dead", finished_at=now,
                               last_error="Stopped while running, with no attempts left."))
        if freed:
            db.execute(update(Job).where(Job.id.in_(freed))
                       .values(status="queued", run_after=now,
                               last_error="Stopped while running; tried again."))
        due = freed + list(db.scalars(select(Job.id).where(
            Job.status == "queued", Job.run_after <= now - LOST_AFTER)))
        db.commit()
    for job_id in due:
        dispatch(job_id)
    return len(due)


def retry(job_id: uuid.UUID) -> bool:
    """Give a dead job another round of attempts (staff, from the command line)."""
    with SessionLocal() as db:
        done = db.execute(update(Job).where(Job.id == job_id, Job.status == "dead")
                          .values(status="queued", attempts=0, run_after=utcnow(),
                                  finished_at=None)).rowcount
        db.commit()
    if done:
        dispatch(job_id)
    return bool(done)
