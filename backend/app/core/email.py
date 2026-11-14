"""Outgoing email. SMTP (Mailpit in development), console, or an in-memory outbox for tests."""

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
    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=10) as smtp:
            if settings.smtp_starttls:
                smtp.starttls()
            if settings.smtp_username:
                smtp.login(settings.smtp_username, settings.smtp_password or "")
            smtp.send_message(msg)
    except OSError:
        # Delivery problems must not break the request (or reveal anything to the caller).
        # A background queue with retries arrives with Celery in a later step.
        log.exception("Failed to send email to %s", to)
