"""H1-5: background jobs: recording, retries, giving up, duplicates, recovery, the worker,
email on the queue, and nightly cleanup."""

import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core import email
from app.core.config import get_settings
from app.core.models import utcnow
from app.jobs import service
from app.jobs.handlers import cleanup_job
from app.jobs.models import Job
from app.jobs.registry import HANDLERS, handler
from app.models import EmailVerificationToken, PasswordResetToken, User, UserSession
from tests.conftest import register

CALLS: list[dict] = []
FAILURES = {"left": 0}

if "test.record" not in HANDLERS:
    @handler("test.record", max_attempts=3, scrub=lambda p: {"kept": p.get("kept")})
    def _record(db, payload):
        CALLS.append(payload)

    @handler("test.flaky", max_attempts=3)
    def _flaky(db, payload):
        if FAILURES["left"] > 0:
            FAILURES["left"] -= 1
            raise RuntimeError("mail server said no")
        CALLS.append(payload)


@pytest.fixture(autouse=True)
def _reset():
    CALLS.clear()
    FAILURES["left"] = 0
    yield


def job(db, job_id):
    db.expire_all()
    return db.get(Job, job_id)


def make_due(db, job_id):
    j = job(db, job_id)
    j.run_after = utcnow() - timedelta(seconds=1)
    db.commit()


# --- running --------------------------------------------------------------------------------

def test_a_job_runs_and_is_recorded(db):
    job_id = service.enqueue("test.record", {"kept": "a", "secret": "b"})
    assert CALLS == [{"kept": "a", "secret": "b"}]
    j = job(db, job_id)
    assert j.status == "succeeded" and j.attempts == 1 and j.finished_at is not None
    # Sensitive content is removed once it's done.
    assert j.payload == {"kept": "a"}


def test_failures_are_retried_with_a_growing_wait(db):
    FAILURES["left"] = 1
    job_id = service.enqueue("test.flaky", {"n": 1})
    j = job(db, job_id)
    assert j.status == "queued" and j.attempts == 1
    assert j.last_error == "RuntimeError: mail server said no"
    assert timedelta(seconds=25) < j.run_after - utcnow() <= timedelta(seconds=30)
    # Not before its time…
    assert service.run(job_id) is None
    # …then it succeeds.
    make_due(db, job_id)
    assert service.run(job_id) == "succeeded"
    assert job(db, job_id).last_error is None and CALLS == [{"n": 1}]


def test_backoff():
    assert [service.backoff(n).total_seconds() for n in (1, 2, 3, 4, 5, 6)] == [
        30, 120, 480, 1920, 7200, 7200]


def test_a_job_gives_up_after_its_attempts(db):
    FAILURES["left"] = 99
    job_id = service.enqueue("test.flaky", {"n": 2})
    for _ in range(2):
        make_due(db, job_id)
        service.run(job_id)
    j = job(db, job_id)
    assert j.status == "dead" and j.attempts == 3 and j.finished_at is not None
    # A person can give it another round.
    FAILURES["left"] = 0
    assert service.retry(job_id)
    assert job(db, job_id).status == "succeeded"
    assert not service.retry(job_id)  # only dead jobs can be retried


def test_a_job_runs_once_even_if_delivered_twice(db, monkeypatch):
    monkeypatch.setattr(service, "dispatch", lambda *a, **kw: None)
    job_id = service.enqueue("test.record", {"kept": "x"})
    assert service.run(job_id) == "succeeded"
    assert service.run(job_id) is None
    assert len(CALLS) == 1


def test_the_same_work_isnt_queued_twice(db, monkeypatch):
    monkeypatch.setattr(service, "dispatch", lambda *a, **kw: None)
    first = service.enqueue("test.record", {"kept": 1}, dedupe_key="report:42")
    second = service.enqueue("test.record", {"kept": 2}, dedupe_key="report:42")
    assert first == second
    service.run(first)
    # Once finished, the same work can be queued again.
    assert service.enqueue("test.record", {"kept": 3}, dedupe_key="report:42") != first


def test_unknown_kinds_are_refused():
    with pytest.raises(ValueError):
        service.enqueue("no.such.job")


# --- recovery and the queue -----------------------------------------------------------------

def test_recover_requeues_stuck_jobs_and_resends_lost_ones(db, monkeypatch):
    sent = []
    monkeypatch.setattr(service, "dispatch", lambda job_id, countdown=0: sent.append(job_id))
    stuck = service.enqueue("test.record", {"kept": "stuck"})
    lost = service.enqueue("test.record", {"kept": "lost"})
    hopeless = service.enqueue("test.record", {"kept": "hopeless"})
    long_ago = utcnow() - timedelta(hours=1)
    for job_id, status, attempts in ((stuck, "running", 1), (hopeless, "running", 3)):
        j = db.get(Job, job_id)
        j.status, j.started_at, j.attempts = status, long_ago, attempts
    db.get(Job, lost).run_after = long_ago
    db.commit()
    sent.clear()
    service.recover()
    assert job(db, stuck).status == "queued"
    assert job(db, hopeless).status == "dead"
    assert set(sent) == {stuck, lost}


def test_the_queue_being_down_doesnt_break_the_request(db, monkeypatch):
    def broken(*a, **kw):
        raise ConnectionError("Redis is down")
    monkeypatch.setattr(service, "dispatch", broken)
    job_id = service.enqueue("test.record", {"kept": "later"})
    assert job(db, job_id).status == "queued"  # recover() sends it once the queue is back


def test_queue_mode_hands_jobs_to_the_celery_worker(db, monkeypatch):
    from app.worker import celery, run_job

    monkeypatch.setattr(get_settings(), "jobs_mode", "queue")
    monkeypatch.setitem(celery.conf, "task_always_eager", True)
    calls = []
    original = run_job.apply_async
    monkeypatch.setattr(run_job, "apply_async",
                        lambda *a, **kw: calls.append(kw) or original(*a, **kw))
    job_id = service.enqueue("test.record", {"kept": "via celery"})
    assert calls and job(db, job_id).status == "succeeded"
    assert celery.conf.task_default_queue == get_settings().jobs_queue


def test_scheduled_work_is_recorded_and_never_doubled(db, monkeypatch):
    from app.worker import scheduled

    monkeypatch.setattr(service, "dispatch", lambda *a, **kw: None)
    scheduled("maintenance.cleanup")
    scheduled("maintenance.cleanup")
    rows = db.scalars(select(Job).where(Job.kind == "maintenance.cleanup")).all()
    assert len(rows) == 1 and rows[0].dedupe_key == "schedule:maintenance.cleanup"


# --- email ----------------------------------------------------------------------------------

def test_emails_go_through_the_queue_and_their_text_isnt_kept(client, db):
    register(client, "owner@agency.example.com", org="Agency")  # sends a confirmation email
    assert email.outbox and email.outbox[-1].to == "owner@agency.example.com"
    j = db.scalars(select(Job).where(Job.kind == "email.send")).one()
    assert j.status == "succeeded"
    assert set(j.payload) == {"to", "subject"}  # the link in the body is gone


def test_a_mail_server_failure_is_retried_and_the_request_still_works(client, db, monkeypatch):
    import app.jobs.handlers as handlers

    def down(*a, **kw):
        raise OSError("Connection refused")
    monkeypatch.setattr(handlers, "deliver", down)
    register(client, "owner@agency.example.com", org="Agency")
    j = db.scalars(select(Job).where(Job.kind == "email.send")).one()
    assert j.status == "queued" and j.attempts == 1 and "Connection refused" in j.last_error
    assert "body" in j.payload  # still needed for the retry


# --- nightly cleanup ------------------------------------------------------------------------

def test_cleanup_deletes_only_what_is_no_longer_needed(client, db):
    register(client, "owner@agency.example.com", org="Agency")
    user = db.scalar(select(User))
    now = utcnow()
    old, recent = now - timedelta(days=40), now - timedelta(hours=1)
    db.add_all([
        UserSession(user_id=user.id, token_hash=uuid.uuid4().hex,
                    expires_at=now - timedelta(days=1), last_seen_at=now - timedelta(days=2)),
        PasswordResetToken(user_id=user.id, token_hash=uuid.uuid4().hex,
                           expires_at=now - timedelta(days=10)),
        PasswordResetToken(user_id=user.id, token_hash=uuid.uuid4().hex,
                           expires_at=now + timedelta(hours=1)),
        Job(kind="test.record", status="succeeded", finished_at=old),
        Job(kind="test.record", status="dead", finished_at=recent),
    ])
    db.commit()
    sessions_before = db.query(UserSession).count()

    from app.core.db import SessionLocal

    with SessionLocal() as s:
        cleanup_job(s, {})
        s.commit()

    db.expire_all()
    assert db.query(UserSession).count() == sessions_before - 1  # the signed-in one stays
    assert db.query(PasswordResetToken).count() == 1
    assert db.query(EmailVerificationToken).count() == 1  # sent at sign-up, still valid
    remaining = {(j.status, j.finished_at is not None and j.finished_at < now - timedelta(days=30))
                 for j in db.scalars(select(Job).where(Job.kind == "test.record"))}
    assert remaining == {("dead", False)}
