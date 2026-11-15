import re
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update

from app.core import email
from app.core.config import get_settings
from app.main import app
from app.models import Lead, NewsletterSubscriber
from app.modules.leads.service import NEWSLETTER_CONSENT_TEXT

CONSULT = "/api/v1/public/leads/consultation"
CONTACT = "/api/v1/public/leads/contact"
NEWS = "/api/v1/public/newsletter"


@pytest.fixture
def site():
    """A browser on the public website: sends the site's Origin, no CSRF token, no session."""
    with TestClient(app, base_url="https://testserver",
                    headers={"Origin": get_settings().site_url}) as c:
        yield c


@pytest.fixture
def notify(monkeypatch):
    monkeypatch.setattr(get_settings(), "lead_notification_emails",
                        "sales@outlogik.example.com, ops@outlogik.example.com")


def consultation(**over):
    return {
        "name": "Casey Client", "email": "Casey@Bakery.example.com", "company": "Harbour Bakery",
        "website": "harbourbakery.example.com", "services": ["seo", "content-marketing"],
        "budget": "1k-2.5k", "message": "We want more local customers.",
        "preferred_contact": "Weekday mornings", "elapsed_ms": 20000, "nickname": "",
        "attribution": {"page": "/services/seo", "landing_page": "/?utm_source=newsletter",
                        "referrer": "https://search.example.com/", "utm_source": "newsletter",
                        "utm_medium": "email"},
        **over,
    }


def contact(**over):
    return {"name": "Pat", "email": "pat@example.com", "topic": "partnerships",
            "message": "Hello there", "elapsed_ms": 9000, **over}


# --- consultation and contact ------------------------------------------------------------------

def test_consultation_is_stored_with_attribution(site, db, notify):
    res = site.post(CONSULT, json=consultation())
    assert res.status_code == 201
    assert res.json() == {"received": True}
    lead = db.scalar(select(Lead))
    assert (lead.kind, lead.status) == ("consultation", "new")
    assert lead.email == "casey@bakery.example.com"
    assert lead.details == {"services": ["seo", "content-marketing"], "budget": "1k-2.5k",
                            "preferred_contact": "Weekday mornings"}
    assert lead.attribution["utm_source"] == "newsletter"
    assert lead.attribution["page"] == "/services/seo"
    assert lead.ip and lead.user_agent


def test_consultation_notifies_the_team_and_acknowledges_the_sender(site, notify):
    site.post(CONSULT, json=consultation())
    to = sorted(m.to for m in email.outbox)
    assert to == ["casey@bakery.example.com", "ops@outlogik.example.com",
                  "sales@outlogik.example.com"]
    team = next(m for m in email.outbox if m.to == "sales@outlogik.example.com")
    assert team.subject == "New consultation request from Casey Client"
    for text in ["SEO, Content Marketing", "$1,000 to $2,500 a month", "Weekday mornings",
                 "Sent from: /services/seo", "utm_source=newsletter", "We want more local"]:
        assert text in team.body
    ack = next(m for m in email.outbox if m.to == "casey@bakery.example.com")
    assert "consultation" in ack.subject


def test_no_team_email_until_addresses_are_configured(site, db):
    assert get_settings().lead_notification_recipients == []
    site.post(CONSULT, json=consultation())
    assert [m.to for m in email.outbox] == ["casey@bakery.example.com"]
    assert db.scalar(select(Lead)).status == "new"


def test_budget_and_extra_fields_are_optional(site, db):
    body = consultation()
    for key in ["company", "website", "budget", "message", "preferred_contact", "attribution"]:
        body.pop(key)
    assert site.post(CONSULT, json=body).status_code == 201
    lead = db.scalar(select(Lead))
    assert lead.details["budget"] is None and lead.attribution == {}


@pytest.mark.parametrize("bad", [
    {"services": []}, {"services": ["paid-ads"]}, {"budget": "a-lot"}, {"name": " "},
    {"email": "not-an-email"}, {"message": "x" * 5001}, {"is_admin": True},
])
def test_consultation_is_validated(site, db, bad):
    assert site.post(CONSULT, json=consultation(**bad)).status_code == 422
    assert db.scalar(select(Lead)) is None


def test_contact_message(site, db, notify):
    assert site.post(CONTACT, json=contact()).status_code == 201
    lead = db.scalar(select(Lead))
    assert (lead.kind, lead.details, lead.message) == ("contact", {"topic": "partnerships"},
                                                        "Hello there")
    team = next(m for m in email.outbox if m.to == "sales@outlogik.example.com")
    assert "Topic: Partnerships" in team.body
    assert site.post(CONTACT, json=contact(message="")).status_code == 422


# --- protection --------------------------------------------------------------------------------

@pytest.mark.parametrize("trap, reason", [({"nickname": "bot"}, "honeypot"),
                                          ({"elapsed_ms": 800}, "too_fast")])
def test_spam_is_kept_for_review_but_never_emailed(site, db, notify, trap, reason):
    res = site.post(CONSULT, json=consultation(**trap))
    assert res.status_code == 201  # looks like success, so bots learn nothing
    lead = db.scalar(select(Lead))
    assert (lead.status, lead.spam_reason) == ("spam", reason)
    assert email.outbox == []


@pytest.mark.parametrize("origin", [None, "https://evil.example.com", "http://localhost:4200"])
def test_forms_only_accept_the_website_origin(origin, db):
    headers = {"Origin": origin} if origin else {}
    with TestClient(app, base_url="https://testserver", headers=headers) as c:
        res = c.post(CONSULT, json=consultation())
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "bad_origin"
    assert db.scalar(select(Lead)) is None


def test_extra_origins_can_be_allowed(monkeypatch, db):
    monkeypatch.setattr(get_settings(), "public_form_extra_origins", "https://staging.example.com/")
    with TestClient(app, base_url="https://testserver",
                    headers={"Origin": "https://staging.example.com"}) as c:
        assert c.post(CONTACT, json=contact()).status_code == 201


def test_forms_need_no_csrf_token_but_the_app_still_does(site, client):
    assert site.post(CONTACT, json=contact()).status_code == 201
    # Everything outside /api/v1/public still requires the CSRF token.
    bare = TestClient(app, base_url="https://testserver")
    assert bare.post("/api/v1/auth/login", json={"email": "a@b.co", "password": "x"}
                     ).status_code == 403


def test_rate_limited_per_email_and_per_ip(site):
    for _ in range(3):
        assert site.post(CONTACT, json=contact()).status_code == 201
    res = site.post(CONTACT, json=contact())
    assert res.status_code == 429 and "Retry-After" in res.headers
    for i in range(6):
        site.post(CONTACT, json=contact(email=f"p{i}@example.com"))
    assert site.post(CONTACT, json=contact(email="new@example.com")).status_code == 429


# --- newsletter (CASL double opt-in) ------------------------------------------------------------

def news(**over):
    return {"email": "Reader@Example.com", "consent": True, "elapsed_ms": 5000,
            "attribution": {"page": "/about"}, **over}


def link_token(kind: str) -> str:
    match = re.search(rf"/newsletter/{kind}\?token=([\w-]+)", email.outbox[-1].body)
    assert match, email.outbox[-1].body
    return match.group(1)


def test_newsletter_double_opt_in_and_unsubscribe(site, db):
    assert site.post(NEWS, json=news()).status_code == 202
    sub = db.scalar(select(NewsletterSubscriber))
    assert (sub.email, sub.status) == ("reader@example.com", "pending")
    assert sub.consent_text == NEWSLETTER_CONSENT_TEXT and sub.consent_at
    msg = email.outbox[-1]
    assert msg.to == "reader@example.com"
    assert f"{get_settings().site_url}/newsletter/confirm?token=" in msg.body
    assert NEWSLETTER_CONSENT_TEXT in msg.body

    confirm, unsubscribe = link_token("confirm"), link_token("unsubscribe")
    assert sub.confirm_token_hash != confirm  # only hashes are stored
    assert site.post(f"{NEWS}/confirm", json={"token": confirm}).status_code == 200
    db.refresh(sub)
    assert sub.status == "confirmed" and sub.confirmed_at
    # Links work once.
    assert site.post(f"{NEWS}/confirm", json={"token": confirm}).status_code == 400

    assert site.post(f"{NEWS}/unsubscribe", json={"token": unsubscribe}).status_code == 200
    db.refresh(sub)
    assert sub.status == "unsubscribed" and sub.unsubscribed_at
    # Unsubscribing twice is fine.
    assert site.post(f"{NEWS}/unsubscribe", json={"token": unsubscribe}).status_code == 200


def test_newsletter_needs_consent(site, db):
    assert site.post(NEWS, json=news(consent=False)).status_code == 422
    body = news()
    body.pop("consent")
    assert site.post(NEWS, json=body).status_code == 422
    assert db.scalar(select(NewsletterSubscriber)) is None


def test_newsletter_does_not_reveal_who_is_subscribed(site, db):
    site.post(NEWS, json=news())
    site.post(f"{NEWS}/confirm", json={"token": link_token("confirm")})
    sent = len(email.outbox)
    res = site.post(NEWS, json=news())
    assert res.status_code == 202 and res.json() == {"received": True}
    assert len(email.outbox) == sent  # no second email to someone already confirmed


def test_expired_and_unknown_links_fail(site, db):
    site.post(NEWS, json=news())
    token = link_token("confirm")
    db.execute(update(NewsletterSubscriber).values(
        confirm_token_expires_at=NewsletterSubscriber.consent_at - timedelta(minutes=1)))
    db.commit()
    res = site.post(f"{NEWS}/confirm", json={"token": token})
    assert res.status_code == 400 and res.json()["error"]["code"] == "invalid_link"
    assert site.post(f"{NEWS}/unsubscribe", json={"token": "x" * 40}).status_code == 400


def test_newsletter_spam_is_ignored(site, db):
    assert site.post(NEWS, json=news(nickname="bot")).status_code == 202
    assert db.scalar(select(NewsletterSubscriber)) is None and email.outbox == []


def test_unsubscribed_reader_can_opt_in_again(site, db):
    site.post(NEWS, json=news())
    site.post(f"{NEWS}/unsubscribe", json={"token": link_token("unsubscribe")})
    site.post(NEWS, json=news())
    sub = db.scalar(select(NewsletterSubscriber))
    assert sub.status == "pending" and sub.unsubscribed_at is None
    assert site.post(f"{NEWS}/confirm", json={"token": link_token("confirm")}).status_code == 200


# --- the website and the API agree ------------------------------------------------------------

def test_website_form_choices_match_the_api():
    """The website's options (config/forms.ts) must be values the API accepts, and the consent
    wording shown must be exactly what is stored."""
    from pathlib import Path
    from typing import get_args

    from app.modules.leads import schemas

    forms = (Path(__file__).parents[2] / "frontend/projects/marketing/src/app/config/forms.ts"
             ).read_text()

    def values(const: str) -> list[str]:
        block = forms.split(f"export const {const}")[1].split("];")[0]
        return re.findall(r"value: '([^']+)'", block)

    assert values("SERVICE_OPTIONS") == list(get_args(schemas.SERVICE_CHOICES))
    assert values("BUDGET_OPTIONS") == list(get_args(schemas.BUDGET_CHOICES))
    assert values("CONTACT_TOPICS") == list(get_args(schemas.CONTACT_TOPICS))
    consent = forms.split("NEWSLETTER_CONSENT_TEXT =")[1].split(";")[0]
    parts = re.findall(r""""([^"]*)"|'([^']*)'""", consent)  # concatenated string literals
    text = "".join(double or single for double, single in parts)
    assert text == NEWSLETTER_CONSENT_TEXT
