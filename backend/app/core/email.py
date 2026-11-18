"""Outgoing email: queued as a background job (app/jobs), then sent by SMTP (Mailpit in
development), logged to the console, or kept in an in-memory outbox for tests."""

import logging
import smtplib
from dataclasses import dataclass
from email.message import EmailMessage

from app.core.config import get_settings

log = logging.getLogger(__name__)


@dataclass
class SentEmail:
    to: str
    subject: str
    body: str


outbox: list[SentEmail] = []


def send_email(to: str, subject: str, body: str) -> None:
    """Queue an email. It's sent by a background job, retried if the mail server fails, and
    its text is erased from the job record once sent (it may contain a sign-in link)."""
    from app.jobs.service import enqueue

    enqueue("email.send", {"to": to, "subject": subject, "body": body})


def deliver(to: str, subject: str, body: str) -> None:
    """Send now. Raises if the mail server fails, so the job is retried."""
    settings = get_settings()
    if settings.email_backend == "memory":
        outbox.append(SentEmail(to, subject, body))
        return
    if settings.email_backend == "console":
        log.info("Email to %s: %s\n%s", to, subject, body)
        return

    msg = EmailMessage()
    msg["From"] = settings.email_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
        if settings.smtp_starttls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password or "")
        smtp.send_message(msg)
