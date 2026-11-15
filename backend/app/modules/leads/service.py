"""Website leads: consultation requests, contact messages and newsletter sign-ups."""

import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.email import send_email
from app.core.models import utcnow
from app.core.security import generate_token, hash_token
from app.modules.leads.models import Lead, NewsletterSubscriber
from app.modules.leads.schemas import ConsultationIn, ContactIn, NewsletterIn, SpamChecks

log = logging.getLogger(__name__)

# The wording shown beside the newsletter checkbox. Stored with each subscriber as their
# consent record (CASL). If you change it, change the website too (config/forms.ts).
NEWSLETTER_CONSENT_TEXT = (
    "Yes, email me Outlogik's newsletter with marketing tips and news about our services. "
    "I can unsubscribe at any time."
)

SERVICE_LABELS = {
    "seo": "SEO",
    "social-media-management": "Social Media Management",
    "website-analytics-reporting": "Website Analytics & Reporting",
    "content-marketing": "Content Marketing",
    "not-sure": "Not sure yet",
}
BUDGET_LABELS = {
    "under-1k": "Under $1,000 a month",
    "1k-2.5k": "$1,000 to $2,500 a month",
    "2.5k-5k": "$2,500 to $5,000 a month",
    "5k-plus": "Over $5,000 a month",
    "not-sure": "Not sure yet",
}
TOPIC_LABELS = {
    "general": "General question",
    "existing-client": "I'm an existing client",
    "partnerships": "Partnerships",
    "press": "Press",
}


def spam_reason(body: SpamChecks) -> str | None:
    if body.nickname.strip():
        return "honeypot"
    if body.elapsed_ms < get_settings().form_min_seconds * 1000:
        return "too_fast"
    return None


def _clean(value: str | None) -> str | None:
    return value or None


def create_consultation(db: Session, body: ConsultationIn, ip: str | None,
                        user_agent: str | None) -> Lead:
    details = {
        "services": list(dict.fromkeys(body.services)),
        "budget": body.budget,
        "preferred_contact": _clean(body.preferred_contact),
    }
    lead = _store(db, "consultation", body, details=details, ip=ip, user_agent=user_agent,
                  website=_clean(body.website), phone=_clean(body.phone),
                  message=_clean(body.message))
    return lead


def create_contact(db: Session, body: ContactIn, ip: str | None,
                   user_agent: str | None) -> Lead:
    return _store(db, "contact", body, details={"topic": body.topic}, ip=ip,
                  user_agent=user_agent, message=body.message)


def _store(db: Session, kind: str, body: ConsultationIn | ContactIn, *, details: dict,
           ip: str | None, user_agent: str | None, website: str | None = None,
           phone: str | None = None, message: str | None = None) -> Lead:
    reason = spam_reason(body)
    lead = Lead(
        kind=kind, status="spam" if reason else "new", spam_reason=reason,
        name=body.name, email=body.email, company=_clean(body.company), website=website,
        phone=phone, message=message, details=details,
        attribution=body.attribution.model_dump(exclude_none=True), ip=ip, user_agent=user_agent,
    )
    db.add(lead)
    db.commit()
    if reason:
        log.info("Website %s marked as spam (%s)", kind, reason)
    else:
        _notify_team(lead)
        _acknowledge(lead)
    return lead


def _summary(lead: Lead) -> str:
    d = lead.details
    lines = [f"Name: {lead.name}", f"Email: {lead.email}"]
    for label, value in [("Company", lead.company), ("Website", lead.website),
                         ("Phone", lead.phone)]:
        if value:
            lines.append(f"{label}: {value}")
    if lead.kind == "consultation":
        lines.append("Services: " + ", ".join(SERVICE_LABELS[s] for s in d.get("services", [])))
        if d.get("budget"):
            lines.append(f"Budget: {BUDGET_LABELS[d['budget']]}")
        if d.get("preferred_contact"):
            lines.append(f"Best time to reach them: {d['preferred_contact']}")
    else:
        lines.append(f"Topic: {TOPIC_LABELS[d.get('topic', 'general')]}")
    if lead.message:
        lines += ["", "Message:", lead.message]
    a = lead.attribution
    source = ", ".join(f"{k}={v}" for k, v in a.items() if k.startswith("utm_"))
    lines += ["", f"Sent from: {a.get('page', 'unknown page')}"]
    if a.get("landing_page"):
        lines.append(f"First page of the visit: {a['landing_page']}")
    if a.get("referrer"):
        lines.append(f"Referred by: {a['referrer']}")
    if source:
        lines.append(f"Campaign: {source}")
    return "\n".join(lines)


def _notify_team(lead: Lead) -> None:
    recipients = get_settings().lead_notification_recipients
    if not recipients:
        return
    what = "consultation request" if lead.kind == "consultation" else "contact message"
    subject = f"New {what} from {lead.name}"
    for to in recipients:
        send_email(to, subject, f"A new {what} arrived through the website.\n\n{_summary(lead)}\n")


def _acknowledge(lead: Lead) -> None:
    if lead.kind == "consultation":
        subject = "We've received your consultation request"
        body = (
            f"Hi {lead.name},\n\nThanks for booking a free consultation with Outlogik. "
            "We'll reply to arrange a time that suits you.\n\n"
            "If you didn't make this request, you can ignore this email.\n\nOutlogik\n"
        )
    else:
        subject = "We've received your message"
        body = (
            f"Hi {lead.name},\n\nThanks for getting in touch with Outlogik. "
            "We'll reply as soon as we can.\n\n"
            "If you didn't send this message, you can ignore this email.\n\nOutlogik\n"
        )
    send_email(lead.email, subject, body)


# --- newsletter -------------------------------------------------------------------------------

def subscribe(db: Session, body: NewsletterIn, ip: str | None) -> None:
    """Start (or restart) double opt-in. The response is the same whatever the address's state,
    so the form can't be used to find out who is subscribed."""
    if spam_reason(body):
        log.info("Newsletter sign-up ignored as spam")
        return
    s = get_settings()
    sub = db.scalar(select(NewsletterSubscriber).where(NewsletterSubscriber.email == body.email))
    if sub is not None and sub.status == "confirmed":
        return
    now = utcnow()
    confirm = generate_token()
    unsubscribe = generate_token()
    if sub is None:
        sub = NewsletterSubscriber(email=body.email)
        db.add(sub)
    sub.status = "pending"
    sub.consent_text = NEWSLETTER_CONSENT_TEXT
    sub.consent_at = now
    sub.confirmed_at = None
    sub.unsubscribed_at = None
    sub.confirm_token_hash = hash_token(confirm)
    sub.confirm_token_expires_at = now + timedelta(hours=s.newsletter_confirm_token_hours)
    sub.unsubscribe_token_hash = hash_token(unsubscribe)
    sub.attribution = body.attribution.model_dump(exclude_none=True)
    sub.ip = ip
    db.commit()
    site = s.site_url.rstrip("/")
    send_email(body.email, "Please confirm your subscription to Outlogik's newsletter", (
        "Hi,\n\nPlease confirm that you'd like to receive Outlogik's newsletter:\n"
        f"{site}/newsletter/confirm?token={confirm}\n\n"
        f"The link works for {s.newsletter_confirm_token_hours} hours. If you didn't ask to "
        "subscribe, ignore this email and you won't hear from us.\n\n"
        f"You agreed to: \"{NEWSLETTER_CONSENT_TEXT}\"\n\n"
        f"Unsubscribe at any time: {site}/newsletter/unsubscribe?token={unsubscribe}\n\n"
        "Outlogik\n"
    ))


def confirm(db: Session, token: str) -> bool:
    sub = db.scalar(select(NewsletterSubscriber).where(
        NewsletterSubscriber.confirm_token_hash == hash_token(token)))
    if sub is None or sub.status != "pending" or sub.confirm_token_expires_at < utcnow():
        return False
    sub.status = "confirmed"
    sub.confirmed_at = utcnow()
    sub.confirm_token_hash = None
    sub.confirm_token_expires_at = None
    db.commit()
    return True


def unsubscribe(db: Session, token: str) -> bool:
    sub = db.scalar(select(NewsletterSubscriber).where(
        NewsletterSubscriber.unsubscribe_token_hash == hash_token(token)))
    if sub is None:
        return False
    if sub.status != "unsubscribed":
        sub.status = "unsubscribed"
        sub.unsubscribed_at = utcnow()
        sub.confirm_token_hash = None
        sub.confirm_token_expires_at = None
        db.commit()
    return True
