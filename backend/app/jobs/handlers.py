"""The job kinds. Imported by app.worker and app.jobs.service users, so they're registered
before anything is queued."""

from datetime import timedelta
from typing import Any

from sqlalchemy import delete, or_
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import deliver
from app.core.models import utcnow
from app.jobs.models import Job
from app.jobs.registry import handler
from app.jobs.service import recover
from app.modules.auth.models import EmailVerificationToken, PasswordResetToken, UserSession


def _email_scrub(payload: dict[str, Any]) -> dict[str, Any]:
    # Keep who it was for; drop the text, which may hold a sign-in or reset link.
    return {"to": payload.get("to"), "subject": payload.get("subject")}


@handler("email.send", max_attempts=6, scrub=_email_scrub)
def send_email_job(db: Session, payload: dict[str, Any]) -> None:
    if "body" not in payload:
        raise ValueError("The email's text was already removed; send it again from the app.")
    deliver(payload["to"], payload["subject"], payload["body"])


@handler("jobs.recover", max_attempts=1)
def recover_job(db: Session, payload: dict[str, Any]) -> None:
    recover()


FINISHED_JOBS_KEPT = timedelta(days=30)
USED_TOKENS_KEPT = timedelta(days=7)


@handler("maintenance.cleanup", max_attempts=3)
def cleanup_job(db: Session, payload: dict[str, Any]) -> None:
    """Delete what's no longer needed: expired or idle sessions, used or expired one-time
    tokens, and finished jobs older than 30 days."""
    s = get_settings()
    now = utcnow()
    db.execute(delete(UserSession).where(or_(
        UserSession.expires_at < now,
        UserSession.last_seen_at < now - timedelta(minutes=s.session_idle_timeout_minutes))))
    for model in (PasswordResetToken, EmailVerificationToken):
        db.execute(delete(model).where(or_(
            model.expires_at < now - USED_TOKENS_KEPT,
            model.used_at < now - USED_TOKENS_KEPT)))
    db.execute(delete(Job).where(Job.status.in_(("succeeded", "dead")),
                                 Job.finished_at < now - FINISHED_JOBS_KEPT))


AUDIT_TIME = timedelta(minutes=50)  # a crawl stops itself at 40 minutes


@handler("audit.run", max_attempts=2, stuck_after=AUDIT_TIME)
def audit_job(db: Session, payload: dict[str, Any]) -> None:
    import uuid

    from app.modules.audits.service import run

    run(db, uuid.UUID(payload["audit_id"]))


@handler("audits.schedule", max_attempts=1)
def audits_schedule_job(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.audits.service import schedule_due

    schedule_due(db)


@handler("integrations.sync", max_attempts=4, stuck_after=timedelta(minutes=20))
def integration_sync_job(db: Session, payload: dict[str, Any]) -> None:
    import uuid

    from app.modules.integrations.sync import sync_source

    sync_source(db, uuid.UUID(payload["source_id"]))


@handler("integrations.sync_all", max_attempts=1)
def integration_sync_all_job(db: Session, payload: dict[str, Any]) -> None:
    from app.modules.integrations.sync import sync_all

    sync_all(db)
